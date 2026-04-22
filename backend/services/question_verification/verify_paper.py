"""
Question Paper Verifier - Simplified Version

Scorecard (mostly LLM-evaluated, pattern checks are deterministic):
  - pattern_followed        : yes / no   (marks, section counts, marks-per-question)
  - constraints_followed    : 1 / 2 / 3  (teacher input + bloom distribution)
  - syllabus_oriented       : yes / no   (topics from KG, COs reflected)
  - balanced_coverage       : 1 / 2 / 3  (module spread, no topic repeats)
  - student_accessibility   : 1 / 2 / 3  (solvable for weak AND strong students)

Priority (drive ACCEPTED / REJECTED):
  pattern_followed, constraints_followed, syllabus_oriented  →  HIGH
  balanced_coverage, student_accessibility                   →  medium

Verdict:  ACCEPTED  if all HIGH-priority pass AND score ≥ 7
          REJECTED  otherwise

score is computed in Python from the five metrics (0–10).
"""

import json
import re
from typing import Dict, List, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


# Automated verifier ceiling: keep room for human moderation.
MAX_AUTOMATED_SCORE = 9.5


# ─────────────────────────────────────────────────────────────
# DETERMINISTIC PATTERN CHECK  (fast, no LLM)
# ─────────────────────────────────────────────────────────────

def _check_pattern(paper: Dict, paper_pattern: Dict) -> Tuple[bool, List[str]]:
    """
    Returns (passed, issues_list).
    Checks: total marks, total question count, per-section counts and marks.
    """
    issues = []

    # Total marks
    total_marks = sum(
        q.get("marks", 0)
        for s in paper.get("sections", [])
        for q in s.get("questions", [])
    )
    expected_marks = paper_pattern.get("total_marks", 0)
    if total_marks != expected_marks:
        issues.append(
            f"Total marks {total_marks} ≠ expected {expected_marks} "
            f"(delta {expected_marks - total_marks:+d})"
        )

    # Total question count
    total_qs = sum(len(s.get("questions", [])) for s in paper.get("sections", []))
    expected_qs = paper_pattern.get("total_questions", 0)
    if total_qs != expected_qs:
        issues.append(f"Total questions {total_qs} ≠ expected {expected_qs}")

    # Per-section structure
    pat_map = {s["section_name"]: s for s in paper_pattern.get("sections", [])}
    for section in paper.get("sections", []):
        name = section["section_name"]
        qs   = section.get("questions", [])
        if name not in pat_map:
            issues.append(f"Unknown section '{name}'")
            continue
        pat = pat_map[name]
        exp_count = pat.get("question_count", len(qs))
        if len(qs) != exp_count:
            issues.append(f"{name}: {len(qs)} questions ≠ expected {exp_count}")
        exp_mpq = pat.get("marks_per_question")
        if exp_mpq:
            wrong = [
                f"Q{q['question_number']}({q['marks']}M)"
                for q in qs if q.get("marks") != exp_mpq
            ]
            if wrong:
                issues.append(
                    f"{name} marks mismatch (expected {exp_mpq}M each): "
                    f"{', '.join(wrong)}"
                )

    return len(issues) == 0, issues


# ─────────────────────────────────────────────────────────────
# DETERMINISTIC UNIQUENESS CHECK  (fast, no LLM)
# ─────────────────────────────────────────────────────────────

def _check_paper_uniqueness(paper: Dict) -> Tuple[List[str], List[Dict]]:
    """
    Detect repeated topics and near-duplicate question texts in the paper.
    Returns (text_issues_list, structured_issues_list).
    """
    import re

    def _norm(text: str) -> str:
        text = (text or "").lower().strip()
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    topic_to_qs: Dict[str, List[str]] = {}
    text_to_q:   Dict[str, str]       = {}
    issues:      List[Dict]           = []
    text_issues: List[str]            = []

    for section in paper.get("sections", []):
        for q in section.get("questions", []):
            q_num  = str(q.get("question_number", "?"))
            topic  = (q.get("topic") or "").strip()
            q_text = (q.get("question_text") or "").strip()

            # Repeated topic
            if topic:
                topic_to_qs.setdefault(topic, []).append(q_num)

            # Near-duplicate text (first 80 normalised chars as fingerprint)
            if q_text:
                fp = _norm(q_text)[:80]
                if fp in text_to_q:
                    first = text_to_q[fp]
                    msg = f"Q{q_num}: question text nearly identical to Q{first}"
                    text_issues.append(msg)
                    issues.append({
                        "question": f"Q{q_num}",
                        "problem":  f"Duplicate question text (same as Q{first})",
                        "fix":      "Replace with a distinct question on a related subtopic",
                    })
                else:
                    text_to_q[fp] = q_num

    for topic, q_nums in topic_to_qs.items():
        if len(q_nums) > 1:
            repeated = ", ".join(f"Q{n}" for n in q_nums[1:])
            first    = f"Q{q_nums[0]}"
            msg = f"Repeated topic '{topic}': {repeated} (first use: {first})"
            text_issues.append(msg)
            issues.append({
                "question": repeated,
                "problem":  f"Repeated topic '{topic}' (already in {first})",
                "fix":      "Replace with a different topic from the same module",
            })

    return text_issues, issues


def _flatten_kg_topics(knowledge_graph: Dict) -> set:
    """Return a set of valid topic labels from KG topics + subtopics."""
    labels = set()
    modules = knowledge_graph.get("Modules", []) if isinstance(knowledge_graph, dict) else []
    if not isinstance(modules, list):
        return labels

    for m in modules:
        if not isinstance(m, dict):
            continue
        topics = m.get("Topics", [])
        if not isinstance(topics, list):
            continue
        for t in topics:
            if isinstance(t, dict):
                topic_name = (t.get("Topic_Name") or "").strip()
                if topic_name:
                    labels.add(topic_name)
                for st in t.get("Subtopics", []) or []:
                    if isinstance(st, str) and st.strip():
                        labels.add(st.strip())
            elif isinstance(t, str) and t.strip():
                labels.add(t.strip())
    return labels


def _infer_allowed_modules(teacher_input: Dict, knowledge_graph: Dict) -> List[str] | None:
    """Deterministically infer allowed modules from teacher text like first/last N modules."""
    text = str((teacher_input or {}).get("input") or (teacher_input or {}).get("preferences") or "").lower()
    modules = knowledge_graph.get("Modules", []) if isinstance(knowledge_graph, dict) else []
    ordered_names: List[str] = [
        str(m.get("Module_Name")).strip()
        for m in modules
        if isinstance(m, dict) and m.get("Module_Name")
    ]
    if not text or not ordered_names:
        return None

    module_word = r"(?:modules?|mdoules?|moduels?)"
    m_first = re.search(rf"first\s+(\d+)\s+{module_word}", text)
    if m_first:
        n = max(0, min(int(m_first.group(1)), len(ordered_names)))
        return ordered_names[:n] if n else None

    m_last = re.search(rf"last\s+(\d+)\s+{module_word}", text)
    if m_last:
        n = max(0, min(int(m_last.group(1)), len(ordered_names)))
        return ordered_names[-n:] if n else None

    return None


def _deterministic_teacher_syllabus_issues(
    paper: Dict,
    knowledge_graph: Dict,
    teacher_input: Dict,
) -> Tuple[List[Dict], bool, bool]:
    """
    Returns (issues, has_constraint_violation, has_syllabus_violation).
    """
    issues: List[Dict] = []
    allowed_modules = _infer_allowed_modules(teacher_input, knowledge_graph)
    valid_topics = _flatten_kg_topics(knowledge_graph)

    has_constraint_violation = False
    has_syllabus_violation = False

    for section in paper.get("sections", []):
        for q in section.get("questions", []):
            q_num = str(q.get("question_number", "?"))
            module = str(q.get("module", "")).strip()
            topic = str(q.get("topic", "")).strip()

            if allowed_modules and module and module not in allowed_modules:
                has_constraint_violation = True
                issues.append({
                    "question": f"Q{q_num}",
                    "problem": "Module violates teacher module restriction",
                    "fix": "Replace with a question from allowed modules",
                })

            if valid_topics and topic and topic not in valid_topics:
                has_syllabus_violation = True
                issues.append({
                    "question": f"Q{q_num}",
                    "problem": "Topic not found in syllabus knowledge graph",
                    "fix": "Use a topic/subtopic label present in knowledge graph",
                })

    return issues, has_constraint_violation, has_syllabus_violation


def _bloom_deviation_issue(paper: Dict, bloom_coverage: Dict) -> Tuple[List[Dict], bool, bool]:
    """
    Compare achieved Bloom distribution with target.
    Returns (issues, hard_violation, soft_violation).
    hard_violation: any level deviates > 15 percentage points
    soft_violation: any level deviates > 8 percentage points
    """
    questions = [
        q for s in paper.get("sections", []) for q in s.get("questions", [])
    ]
    total = len(questions)
    if total == 0:
        return [], True, False

    # Canonical target map in fractions (0-1)
    canonical = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
    target = {k: float((bloom_coverage or {}).get(k, 0) or (bloom_coverage or {}).get(k.title(), 0) or 0) for k in canonical}
    target_sum = sum(target.values())
    if target_sum <= 0:
        return [], False, False

    # normalize target to 1.0
    target = {k: v / target_sum for k, v in target.items()}

    achieved_counts = {k: 0 for k in canonical}
    for q in questions:
        level = str(q.get("bloom_level", "")).strip().lower()
        if level in achieved_counts:
            achieved_counts[level] += 1

    max_dev_pp = 0.0
    for k in canonical:
        achieved = achieved_counts[k] / total
        dev_pp = abs(achieved - target[k]) * 100
        max_dev_pp = max(max_dev_pp, dev_pp)

    if max_dev_pp <= 8:
        return [], False, False

    issues = [{
        "question": "overall",
        "problem": f"Bloom distribution deviation too high ({max_dev_pp:.1f}pp)",
        "fix": "Adjust bloom levels to match target distribution",
    }]
    return issues, (max_dev_pp > 15), (max_dev_pp > 8)


def _build_summary(metrics: Dict, issues: List[Dict], score: float, verdict: str) -> str:
    if issues:
        return f"{verdict} with score {score}/10. Found {len(issues)} critical issue(s) to fix."
    return f"{verdict} with score {score}/10. Deterministic checks and quality criteria are satisfied."


# ─────────────────────────────────────────────────────────────
# SCORE COMPUTATION  (deterministic — no LLM)
# ─────────────────────────────────────────────────────────────

def _compute_score(metrics: Dict) -> float:
    """
    Weights (sum to 10):
        pattern_followed       3.0  (yes=3 / no=0)
        constraints_followed   2.5  (scale 1-3 → 0 / 1.25 / 2.5)
        syllabus_oriented      2.0  (yes=2 / no=0)
        balanced_coverage      1.5  (scale 1-3 → 0 / 0.75 / 1.5)
        student_accessibility  1.0  (scale 1-3 → 0 / 0.5 / 1.0)
    """
    def yn(key, weight):
        return weight if str(metrics.get(key, "no")).strip().lower() in ("yes", "true", "1") else 0.0

    def scale3(key, weight):
        try:
            v = max(1, min(3, int(metrics.get(key, 1))))
        except (ValueError, TypeError):
            v = 1
        return (v - 1) / 2 * weight

    return round(
        yn("pattern_followed",       3.0) +
        scale3("constraints_followed", 2.5) +
        yn("syllabus_oriented",       2.0) +
        scale3("balanced_coverage",   1.5) +
        scale3("student_accessibility", 1.0),
        2
    )


def _compute_verdict(metrics: Dict, score: float) -> str:
    def is_yes(key):
        return str(metrics.get(key, "no")).strip().lower() in ("yes", "true", "1")

    def at_least_2(key):
        try:
            return int(metrics.get(key, 1)) >= 2
        except (ValueError, TypeError):
            return False

    high_priority_pass = (
        is_yes("pattern_followed") and
        at_least_2("constraints_followed") and
        is_yes("syllabus_oriented")
    )
    return "ACCEPTED" if (high_priority_pass and score >= 7.0) else "REJECTED"


# ─────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────

def _fallback_result(paper: Dict) -> Dict:
    print("⚠️  Using fallback verifier result (LLM unavailable)")
    return {
        "metrics": {
            "pattern_followed":       "yes",
            "constraints_followed":   2,
            "syllabus_oriented":      "yes",
            "balanced_coverage":      2,
            "student_accessibility":  2,
        },
        "score":       7.0,
        "verdict":     "ACCEPTED",
        "issues":      [],
        "summary":     "Fallback verification — manual review recommended.",
    }


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def verify_question_paper(
    paper: Dict,
    syllabus: Dict,
    knowledge_graph: Dict,
    pyq_analysis: Dict,
    blueprint: Dict,
    bloom_coverage: Dict,
    paper_pattern: Dict,
    teacher_input: Dict,
) -> Dict:
    """
    Verify a drafted question paper.

    Returns:
    {
        "metrics": {
            "pattern_followed":       "yes"|"no",
            "constraints_followed":   1|2|3,
            "syllabus_oriented":      "yes"|"no",
            "balanced_coverage":      1|2|3,
            "student_accessibility":  1|2|3,
        },
        "score":   float,          # 0–10
        "verdict": "ACCEPTED"|"REJECTED",
        "issues":  [               # up to 3 critical issues with Q number
            {"question": "Q2a", "problem": "...", "fix": "..."},
        ],
        "summary": str,
    }
    """
    print("\n" + "=" * 65)
    print("⚖️   QUESTION PAPER VERIFIER")
    print("=" * 65)

    # ── Step 1: Deterministic pattern check ─────────────────────────────────
    pattern_ok, pattern_issues = _check_pattern(paper, paper_pattern)

    pattern_detail = "Pattern OK" if pattern_ok else "; ".join(pattern_issues)
    print(f"  {'✅' if pattern_ok else '❌'} Pattern check: {pattern_detail}")

    # ── Step 1b: Deterministic uniqueness check ──────────────────────────────
    unique_text_issues, unique_struct_issues = _check_paper_uniqueness(paper)
    has_uniqueness_issues = len(unique_struct_issues) > 0
    uniqueness_summary = (
        f"UNIQUENESS VIOLATIONS DETECTED: {'; '.join(unique_text_issues)}"
        if has_uniqueness_issues else "No repeated topics or duplicate questions detected."
    )
    print(f"  {'❌' if has_uniqueness_issues else '✅'} Uniqueness check: {uniqueness_summary}")

    # ── Step 1c: Deterministic teacher/syllabus checks ───────────────────────
    hard_issues, has_constraint_violation, has_syllabus_violation = _deterministic_teacher_syllabus_issues(
        paper=paper,
        knowledge_graph=knowledge_graph,
        teacher_input=teacher_input,
    )
    bloom_issues, has_bloom_hard_violation, has_bloom_soft_violation = _bloom_deviation_issue(
        paper=paper,
        bloom_coverage=bloom_coverage,
    )
    hard_issues.extend(bloom_issues)
    has_constraint_violation = has_constraint_violation or has_bloom_hard_violation
    if hard_issues:
        print(f"  ❌ Teacher/Syllabus hard checks found {len(hard_issues)} issue(s)")
    else:
        print("  ✅ Teacher/Syllabus hard checks passed")

    # Build compact paper view for LLM (300 char preview to catch near-duplicates)
    q_list = [
        {
            "q":      q.get("question_number"),
            "section": s["section_name"],
            "module": q.get("module"),
            "topic":  q.get("topic"),
            "marks":  q.get("marks"),
            "bloom":  q.get("bloom_level"),
            "text_preview": (q.get("question_text", "") or "")[:300],
        }
        for s in paper.get("sections", [])
        for q in s.get("questions", [])
    ]

    total_marks     = sum(q["marks"] for q in q_list)
    total_questions = len(q_list)

    syllabus_meta = {
        "course_name":     syllabus.get("course_name", ""),
        "course_outcomes": syllabus.get("course_outcomes", []),
    }

    # ── Step 2: LLM qualitative evaluation ──────────────────────────────────
    prompt = f"""You are a Mumbai University question paper quality judge.

Evaluate the question paper below. The following checks have already been run deterministically — treat them as ground truth:

PATTERN CHECK:
  pattern_followed = {"yes" if pattern_ok else "no"}
  pattern issues   = {json.dumps(pattern_issues)}

UNIQUENESS CHECK (deterministic — must reflect in balanced_coverage score):
  {uniqueness_summary}
  If violations are listed above, score balanced_coverage as 1 and include each violation in issues.

━━━ PAPER ━━━
Total marks    : {total_marks}  (expected: {paper_pattern.get('total_marks')})
Total questions: {total_questions}  (expected: {paper_pattern.get('total_questions')})
Questions:
{json.dumps(q_list, indent=2)}

━━━ CONTEXT ━━━
Syllabus: {json.dumps(syllabus_meta, indent=2)}
Knowledge Graph (valid topics): {json.dumps(knowledge_graph, indent=2)}
Paper Pattern: {json.dumps(paper_pattern, indent=2)}
Bloom Target: {json.dumps(bloom_coverage, indent=2)}
Teacher Input: {json.dumps(teacher_input, indent=2)}

If module nodes include `Weightage_Hours`, treat it as syllabus module weightage by module name.
Consider it while judging `balanced_coverage` and constraints alignment.

━━━ YOUR TASK ━━━
Score the paper on these 4 metrics (pattern_followed is already computed above — copy it as-is):

1. constraints_followed  [1 / 2 / 3]
   - 1 = ANY hard restriction violated (forbidden module present, excluded topic present — one question is enough to score 1, do not average with other passes)
   - 2 = soft preferences partially missed but no hard restrictions violated
   - 3 = all restrictions and preferences followed

2. syllabus_oriented  [yes / no]
   - yes = question topics exist in knowledge graph, course outcomes are reflected
   - no  = questions on topics outside syllabus or COs completely ignored

3. balanced_coverage  [1 / 2 / 3]
   - 3 = no repeated topics, modules well spread, no single module dominates
   - 2 = minor imbalance or one repeated topic
   - 1 = major imbalance, many repeats, or a module completely missing

4. student_accessibility  [1 / 2 / 3]
   - 3 = mix of recall + application; weak students can attempt section A, strong students challenged
   - 2 = slightly too hard or too easy overall
   - 1 = entirely recall-only OR entirely advanced (inaccessible to weak students)

━━━ ISSUES ━━━
List up to 3 critical issues, each with the exact question number (e.g. Q2a), problem, and fix.
Only real problems — do not invent issues.
Prioritise: wrong marks, repeated topic, wrong module, out-of-syllabus topic, violates teacher instruction.

━━━ OUTPUT FORMAT ━━━
Return ONLY valid JSON. No markdown.

{{
  "metrics": {{
    "pattern_followed":       "{("yes" if pattern_ok else "no")}",
    "constraints_followed":   <1|2|3>,
    "syllabus_oriented":      "<yes|no>",
    "balanced_coverage":      <1|2|3>,
    "student_accessibility":  <1|2|3>
  }},
  "issues": [
    {{
      "question": "<Q2a | Section B | overall>",
      "problem":  "<specific problem max 15 words>",
      "fix":      "<actionable fix max 15 words>"
    }}
  ],
  "summary": "<2 sentences — what is right and what needs fixing>"
}}
"""

    response = None
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = str(getattr(response, "content", "") or "").strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        raw = json.loads(text)

        if "metrics" not in raw:
            raise ValueError("Missing 'metrics' key")

        # Always enforce deterministic results — LLM cannot override these
        raw["metrics"]["pattern_followed"] = "yes" if pattern_ok else "no"
        if has_uniqueness_issues:
            raw["metrics"]["balanced_coverage"] = 1  # repeats = major imbalance
        if has_constraint_violation:
            raw["metrics"]["constraints_followed"] = 1
        elif has_bloom_soft_violation:
            try:
                raw["metrics"]["constraints_followed"] = min(2, int(raw["metrics"].get("constraints_followed", 2)))
            except Exception:
                raw["metrics"]["constraints_followed"] = 2
        if has_syllabus_violation:
            raw["metrics"]["syllabus_oriented"] = "no"

        # Merge deterministic issues (pattern + uniqueness) first, then LLM issues
        deterministic_issues: List[Dict] = []
        if not pattern_ok:
            for pi in pattern_issues:
                deterministic_issues.append({
                    "question": "overall",
                    "problem":  pi[:80],
                    "fix":      "Fix marks/counts to match paper pattern",
                })
        deterministic_issues.extend(unique_struct_issues)
        deterministic_issues.extend(hard_issues)

        llm_issues = raw.get("issues", [])
        merged_issues = deterministic_issues + [i for i in llm_issues if i not in deterministic_issues]

        metrics = raw["metrics"]
        score   = _compute_score(metrics)
        score   = min(score, MAX_AUTOMATED_SCORE)
        verdict = _compute_verdict(metrics, score)

        print(f"  📊 Score: {score}/10  |  Verdict: {verdict}")
        _print_metrics(metrics)

        return {
            "metrics": metrics,
            "score":   score,
            "verdict": verdict,
            "issues":  merged_issues[:5],
            "summary": _build_summary(metrics, merged_issues[:5], score, verdict),
        }

    except json.JSONDecodeError as e:
        raw_text = str(getattr(response, "content", ""))
        print(f"⚠️  Verifier JSON parse error: {e} | Raw (first 300): {raw_text[:300]}")
        # Still enforce deterministic checks in fallback
        result = _fallback_result(paper)
        result["metrics"]["pattern_followed"] = "yes" if pattern_ok else "no"
        if has_uniqueness_issues:
            result["metrics"]["balanced_coverage"] = 1
        if has_constraint_violation:
            result["metrics"]["constraints_followed"] = 1
        if has_syllabus_violation:
            result["metrics"]["syllabus_oriented"] = "no"
        result["score"]   = _compute_score(result["metrics"])
        result["score"]   = min(result["score"], MAX_AUTOMATED_SCORE)
        result["verdict"] = _compute_verdict(result["metrics"], result["score"])
        fallback_issues: List[Dict] = [
            {"question": "overall", "problem": pi[:80], "fix": "Fix marks/counts to match pattern"}
            for pi in pattern_issues
        ] + unique_struct_issues + hard_issues
        result["issues"] = fallback_issues[:5]
        result["summary"] = _build_summary(result["metrics"], result["issues"], result["score"], result["verdict"])
        return result

    except Exception as e:
        print(f"⚠️  Unexpected verifier error: {e}")
        import traceback; traceback.print_exc()
        result = _fallback_result(paper)
        if has_constraint_violation:
            result["metrics"]["constraints_followed"] = 1
        elif has_bloom_soft_violation:
            result["metrics"]["constraints_followed"] = 2
        if has_syllabus_violation:
            result["metrics"]["syllabus_oriented"] = "no"
        if has_uniqueness_issues:
            result["metrics"]["balanced_coverage"] = 1
        result["score"] = _compute_score(result["metrics"])
        result["score"] = min(result["score"], MAX_AUTOMATED_SCORE)
        result["verdict"] = _compute_verdict(result["metrics"], result["score"])
        result["issues"] = (hard_issues + unique_struct_issues)[:5]
        result["summary"] = _build_summary(result["metrics"], result["issues"], result["score"], result["verdict"])
        return result


# ─────────────────────────────────────────────────────────────
# PRETTY PRINTER
# ─────────────────────────────────────────────────────────────

def _print_metrics(metrics: Dict):
    labels = {
        "pattern_followed":      ("Pattern Followed",      "HIGH ⭐"),
        "constraints_followed":  ("Constraints Followed",  "HIGH ⭐"),
        "syllabus_oriented":     ("Syllabus Oriented",     "HIGH ⭐"),
        "balanced_coverage":     ("Balanced Coverage",     "medium"),
        "student_accessibility": ("Student Accessibility", "medium"),
    }
    for key, (label, prio) in labels.items():
        val = metrics.get(key, "?")
        print(f"       {label:<26} {str(val):<6}  ({prio})")


def print_verification_report(result: Dict):
    m = result.get("metrics", {})
    print("\n" + "=" * 60)
    print("📋  PAPER VERIFICATION REPORT")
    print("=" * 60)
    print(f"  Overall Score : {result['score']}/10")
    print(f"  Verdict       : {result['verdict']}")
    print(f"  Summary       : {result.get('summary', '')}")
    print()
    _print_metrics(m)
    issues = result.get("issues", [])
    if issues:
        print(f"\n  🚨 Critical Issues ({len(issues)}):")
        for iss in issues:
            print(f"     [{iss.get('question','?')}] {iss.get('problem','')}")
            print(f"       → Fix: {iss.get('fix','')}")
    print("=" * 60)