"""
Blueprint Critic Agent - Simplified Version
Evaluates blueprint with a minimal, focused scorecard.

Scorecard (all LLM-evaluated, fully dynamic):
  - teacher_input_followed   : 1 / 2 / 3   (3 = perfectly followed)
  - pyq_utilized             : yes / no
  - syllabus_oriented        : yes / no
  - module_weightage         : 1 / 2 / 3   (3 = perfectly balanced)
  - bloom_balanced           : 1 / 2 / 3   (3 = perfectly distributed)
  - pattern_followed         : yes / no     (marks, sections, totals)

Priority: teacher_input_followed, syllabus_oriented, pattern_followed,
          module_weightage  →  these four drive ACCEPT / REJECT.

Verdict:  ACCEPTED  — all 4 high-priority pass + overall score ≥ 6
          REJECTED  — any high-priority fail OR overall score < 6

Overall score: computed in Python from the six metrics (0–10 scale).
"""

import json
from typing import Dict, List, Optional
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from .blueprint_service import parse_teacher_constraints

# ─────────────────────────────────────────────────────────────
# SCORE COMPUTATION  (deterministic — no LLM)
# ─────────────────────────────────────────────────────────────

def _compute_score(metrics: Dict) -> float:
    """
    Convert the six metric values to a 0-10 overall score.

    Weights (must sum to 10):
        teacher_input_followed  2.5  (scale 1-3 → 0 / 1.25 / 2.5)
        module_weightage        2.0  (scale 1-3 → 0 / 1.0  / 2.0)
        bloom_balanced          1.5  (scale 1-3 → 0 / 0.75 / 1.5)
        syllabus_oriented       1.5  (yes=1.5 / no=0)
        pattern_followed        1.5  (yes=1.5 / no=0)
        pyq_utilized            1.0  (yes=1.0 / no=0)
    """
    def scale3(val, weight):
        v = int(val) if str(val).isdigit() else 1
        v = max(1, min(3, v))
        return (v - 1) / 2 * weight

    def yn(val, weight):
        return weight if str(val).strip().lower() in ("yes", "true", "1") else 0.0

    score = (
        scale3(metrics.get("teacher_input_followed", 1), 2.5) +
        scale3(metrics.get("module_weightage",        1), 2.0) +
        scale3(metrics.get("bloom_balanced",          1), 1.5) +
        yn(metrics.get("syllabus_oriented",  "no"),   1.5) +
        yn(metrics.get("pattern_followed",   "no"),   1.5) +
        yn(metrics.get("pyq_utilized",       "no"),   1.0)
    )
    return round(score, 2)


def _compute_verdict(metrics: Dict, score: float) -> str:
    """
    ACCEPTED if all four high-priority metrics pass AND score ≥ 6.
    REJECTED otherwise.

    High-priority thresholds:
        teacher_input_followed  == 3
        module_weightage        ≥ 2
        syllabus_oriented       = yes
        pattern_followed        = yes
    """
    def is_yes(val):
        return str(val).strip().lower() in ("yes", "true", "1")

    def at_least_2(val):
        try:
            return int(val) >= 2
        except (ValueError, TypeError):
            return False

    def is_3(val):
        try:
            return int(val) == 3
        except (ValueError, TypeError):
            return False

    high_priority_pass = (
        at_least_2(metrics.get("teacher_input_followed", 1)) and
        at_least_2(metrics.get("module_weightage",        1)) and
        is_yes(metrics.get("syllabus_oriented",  "no"))      and
        is_yes(metrics.get("pattern_followed",   "no"))
    )

    return "ACCEPTED" if (high_priority_pass and score >= 6.0) else "REJECTED"


# ─────────────────────────────────────────────────────────────
# DETERMINISTIC BLOOM CHECK  (fast, no LLM)
# ─────────────────────────────────────────────────────────────

def _check_blueprint_bloom(blueprint: Dict, bloom_coverage: Dict) -> tuple:
    """
    Detect questions assigned a bloom level that has 0% allocation.
    Returns (issues_list, has_violations).
    """
    CANONICAL = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]
    allowed = set()
    for level in CANONICAL:
        pct = bloom_coverage.get(level.lower(), 0) or bloom_coverage.get(level, 0) or 0
        if pct > 0:
            allowed.add(level)

    if not allowed:
        return [], False

    issues = []
    for section in blueprint.get("sections", []):
        for q in section.get("questions", []):
            bloom = (q.get("bloom_level") or "").strip()
            q_num = str(q.get("question_number", "?"))
            if bloom and bloom not in allowed:
                issues.append({
                    "question": f"Q{q_num}",
                    "problem":  f"bloom_level '{bloom}' has 0% allocation — forbidden",
                    "fix":      f"Change to one of: {', '.join(sorted(allowed))}",
                })

    return issues, len(issues) > 0


# ─────────────────────────────────────────────────────────────
# DETERMINISTIC UNIQUENESS CHECK  (fast, no LLM)
# ─────────────────────────────────────────────────────────────

def _check_blueprint_uniqueness(blueprint: Dict) -> tuple:
    """
    Detect repeated topics and repeated question assignments in the blueprint.
    Returns (issues_list, has_repeats) where issues_list is [{question, problem, fix}].
    """
    topic_to_qs: Dict[str, list] = {}
    for section in blueprint.get("sections", []):
        for q in section.get("questions", []):
            topic = (q.get("topic") or "").strip()
            q_num = str(q.get("question_number", "?"))
            if topic:
                topic_to_qs.setdefault(topic, []).append(q_num)

    issues = []
    for topic, q_nums in topic_to_qs.items():
        if len(q_nums) > 1:
            repeated = ", ".join(f"Q{n}" for n in q_nums[1:])
            first    = f"Q{q_nums[0]}"
            issues.append({
                "question": repeated,
                "problem":  f"Repeated topic '{topic}' already used in {first}",
                "fix":      "Replace with a different topic from the same module",
            })

    return issues, len(issues) > 0


# ─────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────

def _fallback_critique(blueprint: Dict) -> Dict:
    print("⚠️  Using fallback critique (LLM unavailable)")
    return {
        "metrics": {
            "teacher_input_followed": 2,
            "pyq_utilized":           "yes",
            "syllabus_oriented":      "yes",
            "module_weightage":       2,
            "bloom_balanced":         2,
            "pattern_followed":       "yes",
        },
        "score":    6.0,
        "verdict":  "ACCEPTED",
        "issues":   [],
        "summary":  "Fallback critique — manual review recommended.",
    }


# ─────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────

def critique_blueprint(
    blueprint: Dict,
    syllabus: Dict,
    knowledge_graph: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict,
) -> Dict:
    """
    Evaluate the blueprint and return a simple scorecard.

    Returns:
    {
        "metrics": {
            "teacher_input_followed": 1|2|3,
            "pyq_utilized":           "yes"|"no",
            "syllabus_oriented":      "yes"|"no",
            "module_weightage":       1|2|3,
            "bloom_balanced":         1|2|3,
            "pattern_followed":       "yes"|"no",
        },
        "score":   float,          # 0–10
        "verdict": "ACCEPTED"|"REJECTED",
        "issues":  [               # up to 3 critical issues
            {"question": "Q2a", "problem": "...", "fix": "..."},
            ...
        ],
        "summary": str,
    }
    """

    # Build compact blueprint view for the prompt
    q_list = [
        {
            "q":      q.get("question_number"),
            "module": q.get("module"),
            "topic":  q.get("topic"),
            "marks":  q.get("marks"),
            "bloom":  q.get("bloom_level"),
            "is_pyq": q.get("is_pyq"),
        }
        for s in blueprint.get("sections", [])
        for q in s.get("questions", [])
    ]

    total_marks     = sum(q["marks"] for q in q_list)
    total_questions = len(q_list)

    # ── Deterministic bloom check (before LLM) ──────────────────────────────
    bloom_issues, has_bloom_violations = _check_blueprint_bloom(blueprint, bloom_coverage)
    bloom_check_summary = (
        f"FORBIDDEN BLOOM LEVELS DETECTED (deterministic): {len(bloom_issues)} violation(s). "
        + " | ".join(f"'{iss['problem']}'" for iss in bloom_issues)
        if has_bloom_violations else "No forbidden bloom levels detected."
    )
    print(f"  {'❌' if has_bloom_violations else '✅'} Bloom check: {bloom_check_summary}")

    # ── Deterministic uniqueness check (before LLM) ──────────────────────────
    repeat_issues, has_repeats = _check_blueprint_uniqueness(blueprint)
    repeat_summary = (
        f"REPEATED TOPICS DETECTED (deterministic): {len(repeat_issues)} violation(s). "
        + " | ".join(f"'{iss['problem']}'" for iss in repeat_issues)
        if has_repeats else "No repeated topics detected."
    )
    print(f"  {'❌' if has_repeats else '✅'} Uniqueness check: {repeat_summary}")

    # Syllabus metadata only (not full module list — that lives in knowledge_graph)
    syllabus_meta = {
        "course_name": syllabus.get("course_name", ""),
        "course_outcomes": syllabus.get("course_outcomes", []),
    }
    constraints = parse_teacher_constraints(teacher_input, knowledge_graph)

    prompt = f"""You are a Mumbai University question paper blueprint reviewer.

Evaluate the blueprint below against the given context and return a scorecard.

━━━ PRE-CHECKED ISSUES (deterministic — treat as ground truth) ━━━
BLOOM: {bloom_check_summary}
If forbidden bloom levels are listed above, you MUST score bloom_balanced as 1 and include those in issues.

UNIQUENESS: {repeat_summary}
If repeated topics are listed above, you MUST score module_weightage as 1 and include those repeats in issues.

━━━ BLUEPRINT ━━━
Total marks    : {total_marks}  (expected: {paper_pattern.get('total_marks')})
Total questions: {total_questions}  (expected: {paper_pattern.get('total_questions')})
Questions:
{json.dumps(q_list, indent=2)}

━━━ CONTEXT ━━━
Syllabus: {json.dumps(syllabus_meta, indent=2)}
Knowledge Graph (valid topics): {json.dumps(knowledge_graph, indent=2)}
Paper Pattern (sections, marks): {json.dumps(paper_pattern, indent=2)}
Bloom Target Distribution: {json.dumps(bloom_coverage, indent=2)}
PYQ Analysis: {json.dumps(pyq_analysis, indent=2)}
Teacher Input: {json.dumps(teacher_input, indent=2)}

If module nodes include `Weightage_Hours`, treat it as syllabus module weightage mapped to module names.
Use it while scoring `module_weightage` balance.

Pre-parsed Hard Constraints (ground truth — use this for scoring):
{json.dumps(constraints, indent=2)}

For teacher_input_followed scoring:
- Score 1 immediately if ANY question's module is not in allowed_modules (if allowed_modules is set)
- Score 1 if ANY excluded_topic appears
- Score 1 if ANY other_hard_rules are violated
- Score 2 if soft preferences partially missed but no hard rule broken
- Score 3 only if everything above is clean

━━━ YOUR TASK ━━━
Score the blueprint on these 6 metrics. Be concise and direct.

1. teacher_input_followed  [1 / 2 / 3]
   - 1 = ANY hard restriction violated (module exclusion, topic ban, format rule — even one question breaking it = score 1, no exceptions)
   - 2 = soft preferences partially followed but no hard restrictions violated
   - 3 = everything followed

2. pyq_utilized  [yes / no]
   - yes = questions marked is_pyq:true align with topics that have PYQ availability
   - no  = is_pyq flags are wrong or PYQs ignored where available

3. syllabus_oriented  [yes / no]
   - yes = topics come from the knowledge graph, COs are reflected
   - no  = topics invented or outside syllabus

4. module_weightage  [1 / 2 / 3]
   - 1 = severe imbalance (one module dominates or a module missing)
   - 2 = minor imbalance
   - 3 = well balanced within allowed range

5. bloom_balanced  [1 / 2 / 3]
   - 1 = large deviation from target distribution (>15%)
   - 2 = moderate deviation (5–15%)
   - 3 = within ±5% of target

6. pattern_followed  [yes / no]
   - yes = total marks correct, section counts correct, marks-per-question correct
   - no  = any of the above wrong

━━━ ISSUES ━━━
List up to 3 critical issues with the question number, problem, and fix.
Only include real problems — do not invent issues.
If blueprint has question from any module teacher hasnt asked or inlcuded, flag it in issues.  

Hard constraints: 
- If teacher input is not followed in any aspect, then do not give score 3 for teacher_input_followed. 
- See minor details if they are ruining paper balance with respect to constraints given, list in issues. 

━━━ OUTPUT FORMAT ━━━
Return ONLY valid JSON. No markdown. No extra text.

{{
  "metrics": {{
    "teacher_input_followed": <1|2|3>,
    "pyq_utilized":           "<yes|no>",
    "syllabus_oriented":      "<yes|no>",
    "module_weightage":       <1|2|3>,
    "bloom_balanced":         <1|2|3>,
    "pattern_followed":       "<yes|no>"
  }},
  "issues": [
    {{
      "question": "<Q2a | overall | Section B>",
      "problem":  "<specific problem in max 15 words>",
      "fix":      "<actionable fix in max 15 words>"
    }}
  ],
  "summary": "<2 sentences max — what is right and what needs fixing>"
}}
"""

    response = None
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = str(getattr(response, "content", "") or "").strip()

        # Strip markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        raw = json.loads(text)

        if "metrics" not in raw:
            raise ValueError("Missing 'metrics' key in LLM response")

        metrics = raw["metrics"]

        # Hard deterministic overrides — LLM cannot ignore these
        if has_repeats:
            metrics["module_weightage"] = 1  # repeated topics = severe imbalance
        if has_bloom_violations:
            metrics["bloom_balanced"] = 1   # forbidden bloom level used

        score   = _compute_score(metrics)
        verdict = _compute_verdict(metrics, score)

        # Force REJECTED if bloom levels violate the 0% constraint
        if has_bloom_violations:
            verdict = "REJECTED"

        # Merge deterministic issues (bloom first, then repeats, then LLM)
        llm_issues = raw.get("issues", [])
        merged_issues = bloom_issues + repeat_issues + [i for i in llm_issues if i not in repeat_issues and i not in bloom_issues]

        # Hard PYQ constraint — override verdict if PYQs exist but none used
        pyqs_exist = bool((pyq_analysis or {}).get("total_pyqs", 0) > 0)
        pyq_utilized = str(metrics.get("pyq_utilized", "no")).strip().lower() == "yes"
        teacher_text = str(
            (teacher_input or {}).get("input")
            or (teacher_input or {}).get("preferences")
            or ""
        ).lower()
        teacher_no_pyqs = any(w in teacher_text for w in ["no pyq", "don't use pyq", "without pyq", "ignore pyq"])

        if pyqs_exist and not pyq_utilized and not teacher_no_pyqs:
            verdict = "REJECTED"

        return {
            "metrics": metrics,
            "score":   score,
            "verdict": verdict,
            "issues":  merged_issues[:5],
            "summary": raw.get("summary", ""),
        }

    except json.JSONDecodeError as e:
        print(f"⚠️  Critique JSON parse error: {e}")
        raw_text = str(getattr(response, "content", ""))
        print(f"    Raw (first 300): {raw_text[:300]}")
        result = _fallback_critique(blueprint)
        if has_repeats:
            result["metrics"]["module_weightage"] = 1
        if has_bloom_violations:
            result["metrics"]["bloom_balanced"] = 1
        result["score"]   = _compute_score(result["metrics"])
        result["verdict"] = _compute_verdict(result["metrics"], result["score"])
        if has_bloom_violations:
            result["verdict"] = "REJECTED"
        result["issues"] = (bloom_issues + repeat_issues + result.get("issues", []))[:5]
        return result

    except Exception as e:
        print(f"⚠️  Unexpected critique error: {e}")
        import traceback; traceback.print_exc()
        result = _fallback_critique(blueprint)
        if has_repeats:
            result["metrics"]["module_weightage"] = 1
        if has_bloom_violations:
            result["metrics"]["bloom_balanced"] = 1
        result["score"]   = _compute_score(result["metrics"])
        result["verdict"] = _compute_verdict(result["metrics"], result["score"])
        if has_bloom_violations:
            result["verdict"] = "REJECTED"
        result["issues"] = (bloom_issues + repeat_issues + result.get("issues", []))[:5]
        return result


# ─────────────────────────────────────────────────────────────
# PRETTY PRINTER  (optional, for debugging)
# ─────────────────────────────────────────────────────────────

def print_critique_report(critique: Dict):
    m = critique.get("metrics", {})
    print("\n" + "=" * 60)
    print("📊  BLUEPRINT SCORECARD")
    print("=" * 60)
    print(f"  Overall Score  : {critique['score']}/10")
    print(f"  Verdict        : {critique['verdict']}")
    print(f"  Summary        : {critique.get('summary', '')}")
    print()
    print(f"  {'Metric':<30} {'Value':<10} {'Priority'}")
    print(f"  {'-'*55}")
    rows = [
        ("Teacher Input Followed",   str(m.get('teacher_input_followed', '?')), "HIGH ⭐"),
        ("Syllabus Oriented",         m.get('syllabus_oriented',  '?'),          "HIGH ⭐"),
        ("Pattern Followed",          m.get('pattern_followed',   '?'),          "HIGH ⭐"),
        ("Module Weightage",          str(m.get('module_weightage', '?')),       "HIGH ⭐"),
        ("Bloom Balanced",            str(m.get('bloom_balanced',  '?')),        "medium"),
        ("PYQ Utilized",              m.get('pyq_utilized',       '?'),          "medium"),
    ]
    for name, val, prio in rows:
        print(f"  {name:<30} {val:<10} {prio}")

    issues = critique.get("issues", [])
    if issues:
        print(f"\n  🚨 Critical Issues ({len(issues)}):")
        for iss in issues:
            print(f"     [{iss.get('question','?')}] {iss.get('problem','')}")
            print(f"       → Fix: {iss.get('fix','')}")
    print("=" * 60)