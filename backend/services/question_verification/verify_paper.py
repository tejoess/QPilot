"""
Question Paper Verifier - Algorithmic + LLM Judge
Evaluates a generated question paper and returns:
  - rating       : float (0–10)
  - verdict      : "ACCEPTED" | "REJECTED"
  - issues       : list of specific problems (only when rating < 8)
  - suggestions  : actionable improvements (only when rating < 8)
  - summary      : short human-readable verdict note

Verdict rule: rating >= 8 → ACCEPTED, rating < 8 → REJECTED (with issues)
"""

import json
from typing import Dict, List, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


# ============================================================================
# DETERMINISTIC CHECKS (no LLM needed)
# ============================================================================

def check_marks_total(paper: Dict, paper_pattern: Dict) -> Tuple[bool, str]:
    total = sum(
        q["marks"]
        for section in paper["sections"]
        for q in section["questions"]
    )
    expected = paper_pattern["total_marks"]
    ok = total == expected
    msg = f"Total marks: {total}/{expected}" if ok else f"FAIL — Total marks {total} ≠ expected {expected}"
    return ok, msg


def check_question_count(paper: Dict, paper_pattern: Dict) -> Tuple[bool, str]:
    total = sum(len(s["questions"]) for s in paper["sections"])
    expected = paper_pattern["total_questions"]
    ok = total == expected
    msg = f"Question count: {total}/{expected}" if ok else f"FAIL — {total} questions ≠ expected {expected}"
    return ok, msg


def check_section_structure(paper: Dict, paper_pattern: Dict) -> Tuple[bool, str]:
    pattern_sections = {s["section_name"]: s for s in paper_pattern.get("sections", [])}
    issues = []
    for section in paper["sections"]:
        name = section["section_name"]
        if name not in pattern_sections:
            issues.append(f"Unknown section '{name}'")
            continue
        pat = pattern_sections[name]
        q_count = len(section["questions"])
        expected_count = pat.get("question_count", q_count)
        if q_count != expected_count:
            issues.append(f"{name}: {q_count} questions ≠ expected {expected_count}")
        for q in section["questions"]:
            if "marks_per_question" in pat and q["marks"] != pat["marks_per_question"]:
                issues.append(
                    f"Q{q['question_number']} in {name}: {q['marks']}M ≠ expected {pat['marks_per_question']}M"
                )
    ok = len(issues) == 0
    return ok, "; ".join(issues) if issues else "Section structure valid"


def check_allowed_marks(paper: Dict, paper_pattern: Dict) -> Tuple[bool, str]:
    allowed = set(paper_pattern.get("allowed_marks_per_question", []))
    if not allowed:
        return True, "No allowed marks restriction defined"
    bad = [
        f"Q{q['question_number']}({q['marks']}M)"
        for section in paper["sections"]
        for q in section["questions"]
        if q["marks"] not in allowed
    ]
    ok = len(bad) == 0
    return ok, f"Invalid mark values: {', '.join(bad)}" if bad else "All marks from allowed values"


def check_module_weightage(paper: Dict, paper_pattern: Dict) -> Tuple[bool, str]:
    total_marks = sum(q["marks"] for s in paper["sections"] for q in s["questions"])
    if total_marks == 0:
        return False, "Total marks = 0, cannot compute weightage"

    module_marks: Dict[str, int] = {}
    for section in paper["sections"]:
        for q in section["questions"]:
            mod = q.get("module", "Unknown")
            module_marks[mod] = module_marks.get(mod, 0) + q["marks"]

    min_w = paper_pattern.get("module_weightage_range", {}).get("min", 0)
    max_w = paper_pattern.get("module_weightage_range", {}).get("max", 1)
    
    # Convert to percentage if values are between 0-1 (decimal format)
    if min_w <= 1 and max_w <= 1:
        min_w_display = min_w * 100
        max_w_display = max_w * 100
    else:
        min_w_display = min_w
        max_w_display = max_w
    
    issues = []
    for mod, marks in module_marks.items():
        pct = marks / total_marks
        if not (min_w <= pct <= max_w):
            issues.append(f"{mod}: {pct*100:.1f}% (allowed {min_w_display:.0f}%–{max_w_display:.0f}%)")
    ok = len(issues) == 0
    return ok, f"Module weightage issues: {'; '.join(issues)}" if issues else "Module weightages valid"


def check_bloom_distribution(paper: Dict, bloom_coverage: Dict) -> Tuple[float, str, Dict]:
    """Returns (deviation_score 0-1, message, actual_distribution)"""
    required: Dict[str, float] = bloom_coverage.get("required_distribution", {})
    if not required:
        return 1.0, "No Bloom requirement defined", {}

    total_marks = sum(q["marks"] for s in paper["sections"] for q in s["questions"])
    bloom_marks: Dict[str, int] = {}
    for section in paper["sections"]:
        for q in section["questions"]:
            bl = q.get("bloom_level", "Unknown")
            bloom_marks[bl] = bloom_marks.get(bl, 0) + q["marks"]

    actual = {bl: (bloom_marks.get(bl, 0) / total_marks) for bl in required} if total_marks else {}
    tolerance = 0.07  # 7%

    deviations = []
    for level, req_pct in required.items():
        act_pct = actual.get(level, 0.0)
        deviation = abs(act_pct - req_pct)
        if deviation > tolerance:
            deviations.append(f"{level}: got {act_pct*100:.1f}% vs required {req_pct*100:.1f}%")

    score = max(0.0, 1.0 - len(deviations) / max(len(required), 1))
    msg = f"Bloom deviations: {'; '.join(deviations)}" if deviations else "Bloom distribution within tolerance"
    return score, msg, actual


def check_duplicate_topics(paper: Dict) -> Tuple[bool, str]:
    seen: Dict[str, int] = {}
    for section in paper["sections"]:
        for q in section["questions"]:
            key = f"{q.get('topic','')}__{q.get('subtopic','')}"
            seen[key] = seen.get(key, 0) + 1
    dupes = [k.replace("__", "/") for k, v in seen.items() if v > 1]
    ok = len(dupes) == 0
    return ok, f"Repeated topic/subtopic: {', '.join(dupes)}" if dupes else "No duplicate topics"


def check_question_text_present(paper: Dict) -> Tuple[bool, str]:
    missing = [
        f"Q{q['question_number']}"
        for section in paper["sections"]
        for q in section["questions"]
        if not q.get("question_text", "").strip()
    ]
    ok = len(missing) == 0
    return ok, f"Missing question text: {', '.join(missing)}" if missing else "All questions have text"


# ============================================================================
# LLM JUDGE
# ============================================================================

def llm_judge(
    paper: Dict,
    syllabus: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict,
    pyq_analysis: Dict,
    deterministic_results: Dict
) -> Dict:
    """
    LLM evaluates qualitative aspects: clarity, relevance, difficulty progression,
    teacher alignment, and overall coherence. Returns structured JSON.
    """

    # Compact paper view for the prompt
    paper_summary = []
    for section in paper["sections"]:
        for q in section["questions"]:
            paper_summary.append({
                "Q": q["question_number"],
                "section": section["section_name"],
                "module": q.get("module"),
                "topic": q.get("topic"),
                "subtopic": q.get("subtopic"),
                "marks": q["marks"],
                "bloom": q.get("bloom_level"),
                "text": q.get("question_text", "")[:200]  # trim for token efficiency
            })

    prompt = f"""You are a strict university question paper quality judge for Mumbai University.

Evaluate this question paper on 5 qualitative dimensions. Be precise and concise.

QUESTION PAPER (compact view):
{json.dumps(paper_summary, indent=2)}

SYLLABUS MODULES:
{json.dumps(syllabus.get("modules", []) if isinstance(syllabus.get("modules"), list) else list(syllabus.get("modules", {}).values()), indent=2)}

TEACHER PREFERENCES:
{json.dumps(teacher_input, indent=2)}

BLOOM REQUIREMENTS:
{json.dumps(bloom_coverage.get("required_distribution", {}), indent=2)}

DETERMINISTIC CHECK RESULTS (already computed):
{json.dumps(deterministic_results, indent=2)}

Evaluate ONLY these 5 qualitative aspects (score each 0-10):

1. question_clarity     - Are questions clearly worded, unambiguous, appropriately scoped for marks?
2. syllabus_relevance   - Do questions cover relevant topics from the syllabus properly?
3. difficulty_flow      - Does difficulty logically progress (easier → harder within sections)?
4. teacher_alignment    - Are teacher focus areas and preferences respected?
5. overall_coherence    - Does the paper feel balanced, fair, and exam-ready as a whole?

Return ONLY valid JSON (no markdown):
{{
  "qualitative_scores": {{
    "question_clarity": <0-10>,
    "syllabus_relevance": <0-10>,
    "difficulty_flow": <0-10>,
    "teacher_alignment": <0-10>,
    "overall_coherence": <0-10>
  }},
  "qualitative_issues": [
    "<specific issue found, if any>"
  ],
  "qualitative_suggestions": [
    "<specific actionable suggestion, if any>"
  ],
  "llm_notes": "<1-2 sentence overall qualitative assessment>"
}}

If no issues found for a category, leave the list empty. Be concise (max 15 words per issue/suggestion)."""

    max_retries = 2
    for attempt in range(max_retries):
        try:
            msg = HumanMessage(content=prompt)
            response = llm.invoke([msg])
            text = response.content.strip()

            # Clean markdown if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()

            # Try parsing JSON
            return json.loads(text)
            
        except Exception as e:
            error_type = type(e).__name__
            print(f"  ⚠️ LLM judge attempt {attempt + 1}/{max_retries} failed: {error_type}")
            
            # Check if it's a connection error
            if "Connection" in error_type or "Timeout" in error_type or "APIConnectionError" in error_type:
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 2
                    print(f"  🔄 Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue
            
            # If not connection error or last attempt, raise to outer handler
            if attempt == max_retries - 1:
                raise


# ============================================================================
# MAIN VERIFIER
# ============================================================================

def verify_question_paper(
    paper: Dict,
    syllabus: Dict,
    pyq_analysis: Dict,
    blueprint: Dict,
    bloom_coverage: Dict,
    paper_pattern: Dict,
    teacher_input: Dict
) -> Dict:
    """
    Full verification pipeline.

    Returns:
        {
            "rating": float (0-10),
            "verdict": "ACCEPTED" | "REJECTED",
            "issues": [...],        # populated only when rating < 8
            "suggestions": [...],   # populated only when rating < 8
            "summary": str,
            "detailed_scores": {...}
        }
    """

    print("\n" + "="*70)
    print("⚖️  QUESTION PAPER VERIFIER")
    print("="*70)

    issues: List[str] = []
    suggestions: List[str] = []

    # ── DETERMINISTIC CHECKS ─────────────────────────────────────────────────

    print("\n🔢 Running deterministic checks...")

    det_results = {}

    ok, msg = check_marks_total(paper, paper_pattern)
    det_results["marks_total"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append(f"Adjust question marks so total equals {paper_pattern['total_marks']}")

    ok, msg = check_question_count(paper, paper_pattern)
    det_results["question_count"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append(f"Add or remove questions to reach exactly {paper_pattern['total_questions']}")
    ok, msg = check_section_structure(paper, paper_pattern)
    det_results["section_structure"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append("Fix section structure to match paper pattern specification")

    ok, msg = check_allowed_marks(paper, paper_pattern)
    det_results["allowed_marks"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append(f"Use only allowed mark values: {paper_pattern.get('allowed_marks_per_question')}")

    ok, msg = check_module_weightage(paper, paper_pattern)
    det_results["module_weightage"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append("Redistribute questions to balance module weightages within allowed range")

    bloom_score, bloom_msg, actual_bloom = check_bloom_distribution(paper, bloom_coverage)
    det_results["bloom_distribution"] = {"score": round(bloom_score, 2), "detail": bloom_msg}
    print(f"  {'✅' if bloom_score >= 0.7 else '⚠️'} {bloom_msg}")
    if bloom_score < 0.7:
        issues.append(bloom_msg)
        suggestions.append("Adjust question bloom levels to match required distribution")

    ok, msg = check_duplicate_topics(paper)
    det_results["duplicate_topics"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '⚠️'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append("Replace duplicate topic questions with questions from uncovered topics")

    ok, msg = check_question_text_present(paper)
    det_results["question_text"] = {"pass": ok, "detail": msg}
    print(f"  {'✅' if ok else '❌'} {msg}")
    if not ok:
        issues.append(msg)
        suggestions.append("Ensure all questions have question text before submission")

    # ── DETERMINISTIC SCORE ──────────────────────────────────────────────────
    # Critical checks (marks total, question count, question text) → heavy weight
    critical_pass = (
        det_results["marks_total"]["pass"]
        and det_results["question_count"]["pass"]
        and det_results["question_text"]["pass"]
    )
    soft_passes = sum([
        det_results["section_structure"]["pass"],
        det_results["allowed_marks"]["pass"],
        det_results["module_weightage"]["pass"],
        bloom_score >= 0.7,
        det_results["duplicate_topics"]["pass"]
    ])
    soft_total = 5

    det_score = (
        (5.0 if critical_pass else 2.0) +
        (5.0 * soft_passes / soft_total)
    )
    print(f"\n  📊 Deterministic score: {det_score:.1f}/10")

    # ── LLM QUALITATIVE JUDGE ────────────────────────────────────────────────

    print("\n🤖 Running LLM qualitative judge...")
    try:
        llm_result = llm_judge(
            paper=paper,
            syllabus=syllabus,
            bloom_coverage=bloom_coverage,
            teacher_input=teacher_input,
            paper_pattern=paper_pattern,
            pyq_analysis=pyq_analysis,
            deterministic_results=det_results
        )
        qual_scores = llm_result.get("qualitative_scores", {})
        qual_avg = (
            sum(qual_scores.values()) / len(qual_scores)
            if qual_scores else 5.0
        )
        llm_issues = llm_result.get("qualitative_issues", [])
        llm_suggestions = llm_result.get("qualitative_suggestions", [])
        llm_notes = llm_result.get("llm_notes", "")

        print(f"  Qualitative scores: {qual_scores}")
        print(f"  Qualitative avg   : {qual_avg:.1f}/10")

        for issue in llm_issues:
            if issue and issue not in issues:
                issues.append(f"[Quality] {issue}")
        for sug in llm_suggestions:
            if sug and sug not in suggestions:
                suggestions.append(sug)

    except Exception as e:
        print(f"  ⚠️ LLM judge failed ({e}), using deterministic only")
        qual_avg = det_score
        llm_notes = "LLM evaluation unavailable"
        qual_scores = {}

    # ── FINAL RATING ─────────────────────────────────────────────────────────
    # Weight: 60% deterministic (hard rules), 40% qualitative (LLM)
    final_rating = round(0.60 * det_score + 0.40 * qual_avg, 2)
    final_rating = max(0.0, min(10.0, final_rating))

    # Verdict: >= 8 → ACCEPTED
    verdict = "ACCEPTED" if final_rating >= 8.0 else "REJECTED"

    # Only expose issues/suggestions if rejected
    exposed_issues = issues if verdict == "REJECTED" else []
    exposed_suggestions = suggestions if verdict == "REJECTED" else []

    summary = (
        f"Paper rated {final_rating}/10 — {verdict}. "
        + (llm_notes if llm_notes else "")
    )

    result = {
        "rating": final_rating,
        "verdict": verdict,
        "issues": exposed_issues,
        "suggestions": exposed_suggestions,
        "summary": summary,
        "detailed_scores": {
            "deterministic_score": round(det_score, 2),
            "qualitative_avg": round(qual_avg, 2),
            "qualitative_breakdown": qual_scores,
            "bloom_score": round(bloom_score, 2),
            "actual_bloom_distribution": {k: round(v, 3) for k, v in actual_bloom.items()},
            "deterministic_checks": det_results
        }
    }

    return result


def print_verification_report(result: Dict):
    """Pretty-print the verification result."""
    print("\n" + "="*70)
    print("📋 VERIFICATION REPORT")
    print("="*70)

    verdict_icon = "✅" if result["verdict"] == "ACCEPTED" else "❌"
    print(f"\n  {verdict_icon}  VERDICT  : {result['verdict']}")
    print(f"  ⭐  RATING   : {result['rating']}/10")
    print(f"  📝  SUMMARY  : {result['summary']}")

    ds = result["detailed_scores"]
    print(f"\n  📊 Score Breakdown:")
    print(f"     Deterministic (60%) : {ds['deterministic_score']}/10")
    print(f"     Qualitative   (40%) : {ds['qualitative_avg']}/10")
    if ds.get("qualitative_breakdown"):
        for dim, score in ds["qualitative_breakdown"].items():
            print(f"       └─ {dim:25}: {score}/10")

    print(f"\n  🧠 Bloom Distribution (Actual vs Required):")
    for level, actual in ds.get("actual_bloom_distribution", {}).items():
        print(f"     {level:12}: {actual*100:.1f}%")

    if result["verdict"] == "REJECTED":
        if result["issues"]:
            print(f"\n  🚨 ISSUES IDENTIFIED ({len(result['issues'])}):")
            for i, issue in enumerate(result["issues"], 1):
                print(f"     {i}. {issue}")

        if result["suggestions"]:
            print(f"\n  💡 SUGGESTIONS ({len(result['suggestions'])}):")
            for i, sug in enumerate(result["suggestions"], 1):
                print(f"     {i}. {sug}")
    else:
        print(f"\n  ✅ No critical issues — paper is ready for use.")

    print("\n" + "="*70)


# ============================================================================
# TEST DATA
# ============================================================================

SAMPLE_SYLLABUS = {
    "course_name": "Database Management Systems",
    "course_code": "CS301",
    "modules": {
        "Module 1": {
            "name": "Introduction to DBMS",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Database Concepts", "subtopics": ["DBMS Architecture", "Data Independence"]},
                {"name": "ER Modeling", "subtopics": ["Entities", "Relationships", "ER Diagrams"]}
            ]
        },
        "Module 2": {
            "name": "Relational Model",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Relational Algebra", "subtopics": ["Selection", "Projection", "Joins"]},
                {"name": "SQL", "subtopics": ["DDL", "DML", "Queries", "Joins"]}
            ]
        },
        "Module 3": {
            "name": "Normalization",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Functional Dependencies", "subtopics": ["FD Rules", "Closure"]},
                {"name": "Normal Forms", "subtopics": ["1NF", "2NF", "3NF", "BCNF"]}
            ]
        },
        "Module 4": {
            "name": "Transaction Management",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Transactions", "subtopics": ["ACID Properties", "States"]},
                {"name": "Concurrency Control", "subtopics": ["Locking", "Deadlock"]}
            ]
        }
    }
}

SAMPLE_PYQ_ANALYSIS = {
    "total_pyqs": 45,
    "module_wise_count": {
        "Module 1": {"total": 12, "quality": "high"},
        "Module 2": {"total": 15, "quality": "high"},
        "Module 3": {"total": 10, "quality": "medium"},
        "Module 4": {"total": 8,  "quality": "medium"}
    }
}

SAMPLE_BLOOM_COVERAGE = {
    "required_distribution": {
        "Remember": 0.15,
        "Understand": 0.25,
        "Apply": 0.30,
        "Analyze": 0.20,
        "Evaluate": 0.07,
        "Create": 0.03
    },
    "flexibility": "±7% deviation allowed"
}

SAMPLE_TEACHER_INPUT = {
    "focus_modules": ["Module 3", "Module 4"],
    "focus_reason": "Students struggle with normalization and transactions",
    "prefer_pyqs": True,
    "difficulty_preference": "medium",
    "special_instructions": "Include at least one numerical problem on normalization"
}

SAMPLE_PAPER_PATTERN = {
    "university": "Mumbai University",
    "exam_type": "Internal Assessment",
    "total_marks": 80,
    "total_questions": 8,
    "duration_minutes": 180,
    "allowed_marks_per_question": [5, 10, 15, 20],
    "module_weightage_range": {"min": 0.20, "max": 0.30},
    "sections": [
        {"section_name": "Section A", "description": "Short Answer", "question_count": 4, "marks_per_question": 5,  "total_marks": 20},
        {"section_name": "Section B", "description": "Long Answer",  "question_count": 4, "marks_per_question": 15, "total_marks": 60}
    ]
}

SAMPLE_BLUEPRINT = {
    "blueprint_metadata": {"total_marks": 80, "total_questions": 8},
    "sections": [
        {"section_name": "Section A", "questions": [
            {"question_number": "1", "module": "Module 1", "topic": "ER Modeling", "marks": 5, "bloom_level": "Remember", "is_pyq": True},
            {"question_number": "2", "module": "Module 4", "topic": "Transactions", "marks": 5, "bloom_level": "Understand", "is_pyq": True},
            {"question_number": "3", "module": "Module 3", "topic": "Functional Dependencies", "marks": 5, "bloom_level": "Apply", "is_pyq": True},
            {"question_number": "4", "module": "Module 2", "topic": "SQL", "marks": 5, "bloom_level": "Remember", "is_pyq": False}
        ]},
        {"section_name": "Section B", "questions": [
            {"question_number": "5", "module": "Module 1", "topic": "ER Modeling", "marks": 15, "bloom_level": "Apply", "is_pyq": True},
            {"question_number": "6", "module": "Module 2", "topic": "Relational Algebra", "marks": 15, "bloom_level": "Understand", "is_pyq": True},
            {"question_number": "7", "module": "Module 3", "topic": "Normal Forms", "marks": 15, "bloom_level": "Apply", "is_pyq": True},
            {"question_number": "8", "module": "Module 4", "topic": "Concurrency Control", "marks": 15, "bloom_level": "Analyze", "is_pyq": False}
        ]}
    ]
}

# ── GOOD PAPER (should be ACCEPTED) ─────────────────────────────────────────
GOOD_PAPER = {
    "paper_id": "test_good_001",
    "sections": [
        {
            "section_name": "Section A",
            "section_description": "Short Answer Questions",
            "questions": [
                {"question_number": "1", "module": "Module 1", "topic": "ER Modeling", "subtopic": "ER Diagrams",
                 "marks": 5, "bloom_level": "Remember", "question_text": "Define an ER diagram. List its main components with a brief explanation of each."},
                {"question_number": "2", "module": "Module 4", "topic": "Transactions", "subtopic": "ACID Properties",
                 "marks": 5, "bloom_level": "Understand", "question_text": "Explain the ACID properties of a database transaction with one example for each property."},
                {"question_number": "3", "module": "Module 3", "topic": "Functional Dependencies", "subtopic": "FD Rules",
                 "marks": 5, "bloom_level": "Apply", "question_text": "Given relation R(A,B,C,D) with FDs A→B, B→C. Find the closure of {A}. Is A a candidate key?"},
                {"question_number": "4", "module": "Module 2", "topic": "SQL", "subtopic": "DDL",
                 "marks": 5, "bloom_level": "Remember", "question_text": "List the DDL commands in SQL and state the purpose of each."}
            ]
        },
        {
            "section_name": "Section B",
            "section_description": "Long Answer Questions",
            "questions": [
                {"question_number": "5", "module": "Module 1", "topic": "ER Modeling", "subtopic": "ER Diagrams",
                 "marks": 15, "bloom_level": "Apply", "question_text": "Design an ER diagram for a Hospital Management System. Include entities for Patient, Doctor, Ward, and Appointment. Show all relationships, cardinalities, and key attributes."},
                {"question_number": "6", "module": "Module 2", "topic": "Relational Algebra", "subtopic": "Joins",
                 "marks": 15, "bloom_level": "Understand", "question_text": "Explain the following relational algebra operations with examples: (a) Natural Join (b) Outer Join (c) Division. Also compare Natural Join vs Equijoin."},
                {"question_number": "7", "module": "Module 3", "topic": "Normal Forms", "subtopic": "BCNF",
                 "marks": 15, "bloom_level": "Apply", "question_text": "Normalize the following relation to BCNF: R(StudentID, CourseID, InstructorID, InstructorDept, Grade) with FDs: {StudentID, CourseID}→Grade, InstructorID→InstructorDept, CourseID→InstructorID. Show all steps."},
                {"question_number": "8", "module": "Module 4", "topic": "Concurrency Control", "subtopic": "Deadlock",
                 "marks": 15, "bloom_level": "Analyze", "question_text": "Analyze deadlock in database systems: (a) Explain conditions for deadlock to occur. (b) Compare deadlock prevention vs deadlock detection approaches. (c) Given a wait-for graph, determine if deadlock exists."}
            ]
        }
    ]
}

# ── BAD PAPER (should be REJECTED) ──────────────────────────────────────────
BAD_PAPER = {
    "paper_id": "test_bad_001",
    "sections": [
        {
            "section_name": "Section A",
            "section_description": "Short Answer Questions",
            "questions": [
                # Wrong marks (3 instead of 5)
                {"question_number": "1", "module": "Module 2", "topic": "SQL", "subtopic": "Queries",
                 "marks": 3, "bloom_level": "Remember", "question_text": "What is SQL?"},
                # Duplicate topic with Q1
                {"question_number": "2", "module": "Module 2", "topic": "SQL", "subtopic": "Queries",
                 "marks": 5, "bloom_level": "Remember", "question_text": "List SQL data types."},
                # Missing question text
                {"question_number": "3", "module": "Module 1", "topic": "ER Modeling", "subtopic": "ER Diagrams",
                 "marks": 5, "bloom_level": "Remember", "question_text": ""},
                {"question_number": "4", "module": "Module 2", "topic": "SQL", "subtopic": "DDL",
                 "marks": 5, "bloom_level": "Remember", "question_text": "Define DDL."}
            ]
        },
        {
            "section_name": "Section B",
            "section_description": "Long Answer Questions",
            "questions": [
                # Module 2 over-represented (3 questions)
                {"question_number": "5", "module": "Module 2", "topic": "SQL", "subtopic": "Joins",
                 "marks": 15, "bloom_level": "Understand", "question_text": "Explain SQL joins."},
                {"question_number": "6", "module": "Module 2", "topic": "Relational Algebra", "subtopic": "Joins",
                 "marks": 15, "bloom_level": "Remember", "question_text": "What is relational algebra?"},
                {"question_number": "7", "module": "Module 2", "topic": "SQL", "subtopic": "DML",
                 "marks": 15, "bloom_level": "Remember", "question_text": "List DML commands."},
                # Module 3 and 4 entirely skipped
                {"question_number": "8", "module": "Module 1", "topic": "Database Concepts", "subtopic": "DBMS Architecture",
                 "marks": 15, "bloom_level": "Remember", "question_text": "Explain DBMS architecture."}
            ]
        }
    ]
}


# ============================================================================
# TEST EXECUTION
# ============================================================================

# if __name__ == "__main__":
#     import sys

#     print("🎓 QUESTION PAPER VERIFIER — TEST SUITE")
#     print("="*70)

#     tests = [
#         ("TEST 1 — GOOD PAPER (expect ACCEPTED)", GOOD_PAPER),
#         ("TEST 2 — BAD PAPER  (expect REJECTED)", BAD_PAPER),
#     ]

#     all_results = []

#     for test_name, paper in tests:
#         print(f"\n{'#'*70}")
#         print(f"  {test_name}")
#         print(f"{'#'*70}")

#         result = verify_question_paper(
#             paper=paper,
#             syllabus=SAMPLE_SYLLABUS,
#             pyq_analysis=SAMPLE_PYQ_ANALYSIS,
#             blueprint=SAMPLE_BLUEPRINT,
#             bloom_coverage=SAMPLE_BLOOM_COVERAGE,
#             paper_pattern=SAMPLE_PAPER_PATTERN,
#             teacher_input=SAMPLE_TEACHER_INPUT
#         )

#         print_verification_report(result)
#         all_results.append({"test": test_name, "result": result})

#     # Save results
#     output_file = "verification_results.json"
#     with open(output_file, "w") as f:
#         json.dump(all_results, f, indent=2)
#     print(f"\n✅ Results saved to: {output_file}")