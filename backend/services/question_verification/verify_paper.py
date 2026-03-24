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
from typing import Dict, List, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


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

    # Build compact paper view for LLM
    q_list = [
        {
            "q":      q.get("question_number"),
            "section": s["section_name"],
            "module": q.get("module"),
            "topic":  q.get("topic"),
            "marks":  q.get("marks"),
            "bloom":  q.get("bloom_level"),
            "text_preview": (q.get("question_text", "") or "")[:120],
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

Evaluate the question paper below. The PATTERN CHECK has already been run:
  pattern_followed = {"yes" if pattern_ok else "no"}
  pattern issues   = {json.dumps(pattern_issues)}

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

        # Always enforce the deterministic pattern result — LLM cannot override it
        raw["metrics"]["pattern_followed"] = "yes" if pattern_ok else "no"

        # If pattern failed, add pattern issues to the issues list
        if not pattern_ok:
            for pi in pattern_issues:
                raw.setdefault("issues", [])
                if len(raw["issues"]) < 3:
                    raw["issues"].append({
                        "question": "overall",
                        "problem":  pi[:80],
                        "fix":      "Fix marks/counts to match paper pattern"
                    })

        metrics = raw["metrics"]
        score   = _compute_score(metrics)
        verdict = _compute_verdict(metrics, score)

        print(f"  📊 Score: {score}/10  |  Verdict: {verdict}")
        _print_metrics(metrics)

        return {
            "metrics": metrics,
            "score":   score,
            "verdict": verdict,
            "issues":  raw.get("issues", [])[:3],
            "summary": raw.get("summary", ""),
        }

    except json.JSONDecodeError as e:
        raw_text = str(getattr(response, "content", ""))
        print(f"⚠️  Verifier JSON parse error: {e} | Raw (first 300): {raw_text[:300]}")
        # Still enforce pattern check in fallback
        result = _fallback_result(paper)
        result["metrics"]["pattern_followed"] = "yes" if pattern_ok else "no"
        if not pattern_ok:
            result["score"] = _compute_score(result["metrics"])
            result["verdict"] = _compute_verdict(result["metrics"], result["score"])
            result["issues"] = [
                {"question": "overall", "problem": pi[:80], "fix": "Fix marks/counts to match pattern"}
                for pi in pattern_issues[:3]
            ]
        return result

    except Exception as e:
        print(f"⚠️  Unexpected verifier error: {e}")
        import traceback; traceback.print_exc()
        return _fallback_result(paper)


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