"""
Blueprint Fixer - Two-mode repair for blueprint critique failures.

Called by repair_blueprint_loop() when critique verdict is REJECTED.

Repair modes (decided dynamically):
  LOCAL  — only the flagged questions change (issues list has specific Q numbers)
  HARD   — full blueprint regeneration request (no specific Qs flagged, or
            high-priority metrics all failing)

In both modes the LLM returns ONLY the changed questions as a list, which
are then spliced back into the blueprint — untouched questions are preserved.
"""

import json
import copy
import re
from typing import Dict, List, Tuple, Optional
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from backend.services.blueprint.blueprint_service import compute_bloom_question_counts, build_bloom_instruction


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _flatten_kg(kg: Dict) -> Dict[str, List[str]]:
    flat = {}
    modules = kg.get("Modules", [])
    if isinstance(modules, list):
        for m in modules:
            m_name = m.get("Module_Name", "Unknown Module")
            topics = []
            for t in m.get("Topics", []):
                if isinstance(t, dict):
                    topics.append(t.get("Topic_Name", ""))
                elif isinstance(t, str):
                    topics.append(t)
            flat[m_name] = [t for t in topics if t]
    else:
        flat = kg
    return flat

def _decide_repair_mode(critique: Dict) -> str:
    """
    LOCAL  → issues cite specific question numbers AND at least one
             high-priority metric scored ≥ 2 (something is mostly right).
    HARD   → no specific questions cited, OR ALL high-priority metrics fail.
    """
    metrics = critique.get("metrics", {})

    def at_least_2(key):
        try:
            return int(metrics.get(key, 1)) >= 2
        except (ValueError, TypeError):
            return False

    def is_yes(key):
        return str(metrics.get(key, "no")).strip().lower() in ("yes", "true", "1")

    high_priority_passing = sum([
        at_least_2("teacher_input_followed"),
        at_least_2("module_weightage"),
        is_yes("syllabus_oriented"),
        is_yes("pattern_followed"),
    ])

    has_specific_issues = any(
        re.search(r"\bQ?\d+[A-Za-z]?\b", str(iss.get("question", "")))
        for iss in critique.get("issues", [])
    )

    # Hard repair if fundamentals are broken
    if high_priority_passing <= 1:
        return "HARD"
    # Local repair if we have specific targets and fundamentals are mostly OK
    if has_specific_issues and high_priority_passing >= 2:
        return "LOCAL"
    # Default to hard if ambiguous
    return "HARD"


def _extract_flagged_q_numbers(critique: Dict) -> List[str]:
    """Pull explicit question numbers from issues list."""
    flagged = set()
    for iss in critique.get("issues", []):
        q_ref = str(iss.get("question", ""))
        for token in re.findall(r"\bQ?\d+[A-Za-z]?\b", q_ref):
            flagged.add(_normalize_question_number(token))
    return list(flagged)


def _normalize_question_number(value: object) -> str:
    raw = str(value or "").strip()
    raw = re.sub(r"^[Qq]\s*", "", raw)
    raw = re.sub(r"[^0-9A-Za-z]", "", raw)
    m = re.match(r"^(\d+)([A-Za-z]?)$", raw)
    if not m:
        return raw.lower()
    return f"{m.group(1)}{m.group(2).lower()}"


def _all_questions_list(blueprint: Dict) -> List[Dict]:
    return [
        {
            "section":         s["section_name"],
            "question_number": q["question_number"],
            "module":          q.get("module"),
            "topic":           q.get("topic"),
            "marks":           q.get("marks"),
            "bloom_level":     q.get("bloom_level"),
            "is_pyq":          q.get("is_pyq"),
        }
        for s in blueprint.get("sections", [])
        for q in s.get("questions", [])
    ]


def _merge_fixes(blueprint: Dict, fixed_questions: List[Dict]) -> Dict:
    """Splice fixed questions back by question_number. Deep-copies first."""
    fixed_map = {}
    for q in fixed_questions:
        if "question_number" not in q:
            continue
        fixed_map[_normalize_question_number(q["question_number"])] = q

    new_bp = copy.deepcopy(blueprint)
    for section in new_bp.get("sections", []):
        for q in section.get("questions", []):
            num = _normalize_question_number(q.get("question_number", ""))
            if num in fixed_map:
                fix = fixed_map[num]
                for field in ("module", "topic", "marks", "bloom_level", "is_pyq", "rationale"):
                    if field in fix:
                        q[field] = fix[field]
    return new_bp


# ─────────────────────────────────────────────────────────────
# PROMPT BUILDERS
# ─────────────────────────────────────────────────────────────

def _build_local_prompt(
    blueprint: Dict,
    flagged: List[str],
    critique: Dict,
    paper_pattern: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    knowledge_graph: Dict,
    iteration: int,
) -> str:
    all_qs   = _all_questions_list(blueprint)
    metrics  = critique.get("metrics", {})
    issues   = critique.get("issues", [])
    total_qs = paper_pattern.get("total_questions", len(all_qs))
    bloom_counts = compute_bloom_question_counts(bloom_coverage, total_qs)
    bloom_instr  = build_bloom_instruction(bloom_counts, total_qs)

    return f"""Repair iteration {iteration} — LOCAL MODE.
Only the flagged questions need changing.

WHAT IS WRONG (from critique):
Metrics  : {json.dumps(metrics)}
Issues   : {json.dumps(issues, indent=2)}

FLAGGED QUESTIONS TO FIX: {flagged}

ALL CURRENT QUESTIONS (context):
{json.dumps(all_qs, indent=2)}

CONSTRAINTS:
- Allowed mark values: {paper_pattern.get('allowed_marks_per_question')}
- Total marks must stay exactly {paper_pattern['total_marks']}
- Total questions must stay exactly {paper_pattern['total_questions']}
- Module range: {paper_pattern['module_weightage_range']['min']*100:.0f}%–{paper_pattern['module_weightage_range']['max']*100:.0f}% per module
- {bloom_instr}
- Teacher instructions: {json.dumps(teacher_input)}
- topic must exactly match a name from knowledge graph: {json.dumps(_flatten_kg(knowledge_graph))}

RULES:
1. Change ONLY the flagged questions
2. Do NOT change question_number values
3. topic must be copied exactly from the knowledge graph
4. After changes total marks and question count must stay the same
5. bloom_level must be one of the ALLOWED levels listed above — never use a FORBIDDEN level

Return ONLY a JSON list of the changed questions. No markdown. No explanation.
[
  {{
    "question_number": "...",
    "module":      "...",
    "topic":       "...",
    "marks":       <int>,
    "bloom_level": "...",
    "is_pyq":      <bool>,
    "rationale":   "max 8 words"
  }}
]"""


def _build_hard_prompt(
    blueprint: Dict,
    critique: Dict,
    paper_pattern: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    knowledge_graph: Dict,
    iteration: int,
) -> str:
    all_qs   = _all_questions_list(blueprint)
    metrics  = critique.get("metrics", {})
    issues   = critique.get("issues", [])
    total_qs = paper_pattern.get("total_questions", len(all_qs))
    bloom_counts = compute_bloom_question_counts(bloom_coverage, total_qs)
    bloom_instr  = build_bloom_instruction(bloom_counts, total_qs)

    return f"""Repair iteration {iteration} — HARD MODE.
The blueprint has fundamental problems. Propose replacements for ALL questions
that contribute to the failing metrics. You may change as many questions as needed.

CRITIQUE SUMMARY:
Score   : {critique.get('score', '?')}/10
Summary : {critique.get('summary', '')}
Metrics : {json.dumps(metrics, indent=2)}
Issues  : {json.dumps(issues, indent=2)}

ALL CURRENT QUESTIONS:
{json.dumps(all_qs, indent=2)}

CONSTRAINTS (must all be satisfied after fix):
- Total marks: exactly {paper_pattern['total_marks']}
- Total questions: exactly {paper_pattern['total_questions']}
- Allowed mark values: {paper_pattern.get('allowed_marks_per_question')}
- Module range: {paper_pattern['module_weightage_range']['min']*100:.0f}%–{paper_pattern['module_weightage_range']['max']*100:.0f}% per module
- {bloom_instr}
- Sections: {json.dumps([{s['section_name']: {'count': s['question_count'], 'marks_each': s['marks_per_question']}} for s in paper_pattern.get('sections', [])])}
- Teacher instructions: {json.dumps(teacher_input)}
- topic must be copied exactly from knowledge graph: {json.dumps(_flatten_kg(knowledge_graph), indent=2)}

RULES:
1. Do NOT change question_number values — only change module/topic/marks/bloom_level/is_pyq
2. Fix ALL failing high-priority metrics:
   teacher_input_followed, syllabus_oriented, pattern_followed, module_weightage, bloom_balanced
3. topic must exactly match a node in the knowledge graph
4. bloom_level must be one of the ALLOWED levels listed above — never use a FORBIDDEN level

Return ONLY a JSON list of ALL changed questions. No markdown. No explanation.
[
  {{
    "question_number": "...",
    "module":      "...",
    "topic":       "...",
    "marks":       <int>,
    "bloom_level": "...",
    "is_pyq":      <bool>,
    "rationale":   "max 8 words"
  }}
]"""


# ─────────────────────────────────────────────────────────────
# MAIN FIX FUNCTION
# ─────────────────────────────────────────────────────────────

def fix_blueprint(
    blueprint: Dict,
    critique: Dict,
    paper_pattern: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    knowledge_graph: Dict,
    iteration: int = 1,
) -> Tuple[Dict, List[str]]:
    """
    Perform one repair pass on the blueprint.

    Returns:
        (repaired_blueprint, change_log)
    """
    print(f"\n{'='*55}")
    print(f"🔧  BLUEPRINT FIXER — Iteration {iteration}")
    print(f"{'='*55}")

    # Decide repair mode
    mode    = _decide_repair_mode(critique)
    flagged = _extract_flagged_q_numbers(critique) if mode == "LOCAL" else []

    print(f"  🔍 Repair mode : {mode}")
    print(f"  📌 Flagged Qs  : {flagged if flagged else 'all (hard mode)'}")
    print(f"  📋 Score before: {critique.get('score', '?')}/10  Verdict: {critique.get('verdict', '?')}")

    # Build prompt
    if mode == "LOCAL":
        prompt = _build_local_prompt(
            blueprint, flagged, critique,
            paper_pattern, bloom_coverage, teacher_input, knowledge_graph, iteration
        )
    else:
        prompt = _build_hard_prompt(
            blueprint, critique,
            paper_pattern, bloom_coverage, teacher_input, knowledge_graph, iteration
        )

    # Call LLM
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        text = str(getattr(response, "content", "") or "").strip()

        # Strip markdown fences
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        fixed_questions: List[Dict] = json.loads(text)

        if not isinstance(fixed_questions, list):
            raise ValueError("LLM returned non-list response")

        change_log = []
        print(f"  🤖 LLM changed {len(fixed_questions)} question(s):")
        for fq in fixed_questions:
            msg = f"Q{fq.get('question_number')}: {fq.get('rationale', 'updated')}"
            print(f"     • {msg}")
            change_log.append(msg)

        repaired = _merge_fixes(blueprint, fixed_questions)
        return repaired, change_log

    except Exception as e:
        print(f"  ❌ Repair call failed: {e}")
        return blueprint, [f"Repair failed ({mode}): {e}"]