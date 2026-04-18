"""
Blueprint Generator Agent - Updated Version
- Passes pyq_available flag to prompt so LLM never sets is_pyq:true when bank is empty
- Knowledge graph used for valid topic labels
- All other logic unchanged
"""

import json
import re
from typing import Dict, List, Optional
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from backend.services.llm_service import openai4o_llm as llm2


def compute_bloom_question_counts(bloom_coverage: Dict, total_questions: int) -> Dict[str, int]:
    """
    Convert percentage-based bloom distribution to exact question counts.

    Uses the largest-remainder method so the counts always sum to total_questions
    without drifting due to floating-point rounding.

    Skips levels with 0% so the LLM isn't told "0 questions of Create".
    Keys are returned with proper capitalisation (Remember, Understand, …).
    """
    CANONICAL = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

    # Accept both lowercase ("remember") and capitalised ("Remember") keys
    pct_map: Dict[str, float] = {}
    for level in CANONICAL:
        pct = bloom_coverage.get(level.lower(), 0) or bloom_coverage.get(level, 0) or 0
        if pct > 0:
            pct_map[level] = float(pct)

    if not pct_map:
        # Fallback: four equal buckets if caller sent nothing useful
        base = total_questions // 4
        rem  = total_questions % 4
        fallback = {l: base for l in ["Remember", "Understand", "Apply", "Analyze"]}
        fallback["Remember"] += rem
        return fallback

    total_pct = sum(pct_map.values())
    floats    = {l: (p / total_pct) * total_questions for l, p in pct_map.items()}
    floors    = {l: int(v) for l, v in floats.items()}
    remainders = {l: floats[l] - floors[l] for l in floors}

    # Distribute remaining question slots to levels with the highest fractional parts
    shortage = total_questions - sum(floors.values())
    for level in sorted(remainders, key=lambda x: remainders[x], reverse=True):
        if shortage <= 0:
            break
        floors[level] += 1
        shortage -= 1

    return floors


def build_bloom_instruction(bloom_counts: Dict[str, int], total_questions: int) -> str:
    """
    Build the prompt block that tells the LLM exactly how many questions
    to assign per Bloom level. Passed as a HARD CONSTRAINT, not a soft target.
    """
    lines = [
        "BLOOM'S DISTRIBUTION — EXACT QUESTION COUNTS (HARD CONSTRAINT):",
        f"You MUST assign bloom_level so the finished blueprint has EXACTLY:",
    ]
    for level, count in bloom_counts.items():
        lines.append(f"  • {level}: {count} question{'s' if count != 1 else ''}")
    lines.append(f"  ─────────────────────────────")
    lines.append(f"  Total: {sum(bloom_counts.values())} (must equal {total_questions})")
    lines.append("")
    lines.append("HOW TO APPLY:")
    lines.append("  - Keep a running tally of bloom_level assignments as you fill each section.")
    lines.append("  - Spread the levels naturally — do NOT cluster all low-level questions in one section.")
    lines.append("  - If a level's quota is already met, do NOT add more questions of that level.")
    lines.append("  - For short-answer sections prefer Remember/Understand; for long-answer prefer Apply/Analyze/Evaluate.")
    lines.append("  - These counts are non-negotiable. Zero deviation is expected.")
    return "\n".join(lines)


def create_fallback_blueprint(paper_pattern: Dict) -> Dict:
    sections = []
    for sp in paper_pattern.get("sections", []):
        questions = []
        for i in range(sp.get("question_count", 1)):
            questions.append({
                "question_number": f"{sp['section_name']}-Q{i+1}",
                "module":          "Module 1",
                "topic":           "General Topic",
                "subtopic":        "",
                "marks":           sp.get("marks_per_question", 5),
                "bloom_level":     "Understand",
                "is_pyq":          False,
                "rationale":       "Fallback",
            })
        sections.append({
            "section_name":        sp["section_name"],
            "section_description": sp.get("section_description", ""),
            "questions":           questions,
        })
    return {"sections": sections}


def fix_incomplete_json(json_str: str) -> str:
    start = json_str.find("{")
    if start == -1:
        return json_str
    json_str = json_str[start:]
    json_str = json_str.rstrip()
    if json_str.endswith(","):
        json_str = json_str[:-1]
    json_str += "]" * (json_str.count("[") - json_str.count("]"))
    json_str += "}" * (json_str.count("{") - json_str.count("}"))
    return json_str


def _pyq_available(pyq_analysis: Dict) -> bool:
    if not pyq_analysis:
        return False
    
    # Check total_pyqs field
    total = pyq_analysis.get("total_pyqs", 0) or 0
    if total > 0:
        return True
    
    # Check module_wise_count sums
    for mod_data in pyq_analysis.get("module_wise_count", {}).values():
        if isinstance(mod_data, dict) and (mod_data.get("total", 0) or 0) > 0:
            return True
    
    # ✅ ADD THIS: Check for a populated questions list directly
    questions = pyq_analysis.get("questions", [])
    if isinstance(questions, list) and len(questions) > 0:
        return True
    
    return False

def _flatten_kg(kg: Dict) -> Dict[str, List[str]]:
    """Converts the raw nested Knowledge Graph into { 'Module_Name': ['Topic1', 'Topic2'] }"""
    if not isinstance(kg, dict):
        return {}
    modules = kg.get("Modules", [])
    if isinstance(modules, list) and len(modules) > 0:
        flat: Dict[str, List[str]] = {}
        for m in modules:
            m_name = m.get("Module_Name", "Unknown Module")
            topics = []
            for t in m.get("Topics", []):
                if isinstance(t, dict):
                    topics.append(t.get("Topic_Name", ""))
                elif isinstance(t, str):
                    topics.append(t)
            flat[m_name] = [t for t in topics if t]
        return flat
    # Already-flattened map (module name -> topics) from callers
    if "Modules" not in kg:
        return {
            k: v
            for k, v in kg.items()
            if k not in ("Subject", "Subject_Id") and isinstance(v, list)
        }
    return {}


def _teacher_text(teacher_input: Dict) -> str:
    """API sends instructions under `preferences`; older code used `input`."""
    if not teacher_input:
        return ""
    return str(
        teacher_input.get("input")
        or teacher_input.get("preferences")
        or ""
    ).strip()


def _infer_allowed_modules_from_text(text: str, flat_kg: Dict[str, List]) -> Optional[List[str]]:
    """
    Deterministic module window from natural language (e.g. last 3 modules).
    Uses module order as in the knowledge graph (Modules array order).
    """
    if not text or not flat_kg:
        return None
    names = list(flat_kg.keys())
    if not names:
        return None
    tl = text.lower()
    for pattern in (r"last\s+(\d+)\s+modules?", r"last\s+(\d+)\s+module"):
        m = re.search(pattern, tl)
        if m:
            n = int(m.group(1))
            n = max(0, min(n, len(names)))
            return names[-n:] if n else None
    for pattern in (r"first\s+(\d+)\s+modules?", r"first\s+(\d+)\s+module"):
        m = re.search(pattern, tl)
        if m:
            n = int(m.group(1))
            n = max(0, min(n, len(names)))
            return names[:n] if n else None
    return None


def parse_teacher_constraints(teacher_input: Dict, knowledge_graph: Dict) -> Dict:
    """
    Calls LLM once to extract hard constraints from teacher input.
    Returns structured dict used by both generator and critic.
    """
    kg_flat = _flatten_kg(knowledge_graph)
    if not kg_flat and isinstance(knowledge_graph, dict) and "Modules" not in knowledge_graph:
        kg_flat = {
            k: v
            for k, v in knowledge_graph.items()
            if k not in ("Subject", "Subject_Id", "Modules")
        }

    mod_list = list(kg_flat.keys())
    prompt = f"""Extract hard constraints from this teacher input for a question paper.

Teacher Input: {json.dumps(teacher_input, indent=2)}
Available Modules (exact names — use these when returning allowed_modules): {mod_list}

Return ONLY valid JSON, no markdown:
{{
  "allowed_modules": ["Module 1", "Module 2"],  // null if no restriction
  "excluded_topics": ["topic name"],             // [] if none
  "forced_topics": ["topic name"],               // [] if none
  "pyq_weightage": 50,                           // extraction of % or weightage mentioned for PYQs, null if not mentioned
  "other_hard_rules": ["rule text"]              // [] if none
}}

Rules:
- allowed_modules must be null if teacher did NOT restrict modules
- If teacher says "first 3 modules" or "last 3 modules", resolve to actual module names from the available list
- For pyq_weightage, if teacher says "50% PYQs" or "half from previous papers", return 50. If they specify a different percentage, return that number. If they don't mention PYQ weightage at all, return null.
- Only extract things the teacher explicitly stated
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    text = str(getattr(response, "content", "")).strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    try:
        constraints = json.loads(text)
    except json.JSONDecodeError:
        constraints = {}

    if not isinstance(constraints, dict):
        constraints = {}

    # Deterministic "last N" / "first N" modules overrides LLM (exact KG names)
    det = _infer_allowed_modules_from_text(_teacher_text(teacher_input), kg_flat)
    if det:
        constraints["allowed_modules"] = det
    else:
        am = constraints.get("allowed_modules")
        if isinstance(am, list):
            valid = [m for m in am if m in kg_flat]
            constraints["allowed_modules"] = valid if valid else None

    return constraints


def generate_blueprint(
    syllabus: Dict,
    knowledge_graph: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict,
) -> Dict:
    """
    Generate question paper blueprint using LLM.
    When PYQ bank is empty/unavailable, all questions get is_pyq: false.
    """

    has_pyqs = _pyq_available(pyq_analysis)

    syllabus_metadata = {
        "course_code":      syllabus.get("course_code", ""),
        "course_name":      syllabus.get("course_name", ""),
        "course_objectives": syllabus.get("course_objectives", []),
        "course_outcomes":   syllabus.get("course_outcomes", []),
    }

    # Flatten the graph so the keys are actually Module Names
    flat_kg = _flatten_kg(knowledge_graph)

    constraints = parse_teacher_constraints(teacher_input, flat_kg)

    # FILTER knowledge graph — LLM won't even see forbidden modules
    if constraints.get("allowed_modules"):
        flat_kg = {k: v for k, v in flat_kg.items() 
                        if k in constraints["allowed_modules"]}

    # Pre-compute exact bloom question counts (do the math so LLM doesn't have to)
    total_qs = paper_pattern.get('total_questions', 0)
    bloom_counts = compute_bloom_question_counts(bloom_coverage, total_qs)
    bloom_instruction = build_bloom_instruction(bloom_counts, total_qs)

    # Compute target PYQ count
    pyq_wt = constraints.get("pyq_weightage")
    if pyq_wt is None:
        pyq_wt = 50 # Default 50% if not mentioned
    
    total_qs = paper_pattern.get('total_questions', 0)
    target_pyq_count = round((pyq_wt / 100) * total_qs) if has_pyqs else 0

    if has_pyqs:
        pyq_instructions = f"""PYQ USAGE (PYQs are available):
- You MUST set exactly {target_pyq_count} questions to is_pyq: true. 
- The remaining {total_qs - target_pyq_count} questions MUST have is_pyq: false.
- Do NOT use individual topic PYQ counts to decide this flag; follow the counts above strictly.
- Spread the {target_pyq_count} PYQ questions across different modules naturally.

PYQ AVAILABILITY (Reference for topic selection):
{json.dumps(pyq_analysis, indent=2)}"""
    else:
        pyq_instructions = """PYQ USAGE:
⚠️  No PYQ bank is available for this paper.
RULE: Set is_pyq: false for ALL questions. Do not set any question to is_pyq: true."""

    prompt = f"""You are a Mumbai University question paper designer.
Your ONLY job: produce a list of questions. Do NOT compute totals, percentages, or metadata.

**PAPER PATTERN:**
- Total marks    : {paper_pattern['total_marks']}
- Total questions: {paper_pattern['total_questions']}
- Sections       : {json.dumps(paper_pattern['sections'], indent=2)}

**SYLLABUS METADATA (context only):**
{json.dumps(syllabus_metadata, indent=2)}

**KNOWLEDGE GRAPH (VALID topic/subtopic labels — copy names exactly):**
{json.dumps(flat_kg, indent=2)}

**{pyq_instructions}**

**{bloom_instruction}**

TEACHER PREFERENCES:
{json.dumps(teacher_input, indent=2)}

HARD CONSTRAINTS (already enforced — do not violate):
{json.dumps(constraints, indent=2)}

ALLOWED MODULES ONLY: {list(flat_kg.keys())}
Every question must come from these modules exclusively.


- TEACHER MODULE RESTRICTION (HIGHEST PRIORITY):
- cover all modules in the knowledge graph.
  If modules are restricted by teacher, every allowed module must appear at least once.
  If modules are NOT restricted, every module in the knowledge graph must appear at least once.
- No two consecutive questions may share the same module
- Never repeat the same topic twice

**RULES:**

MARKS:
- Place exactly {paper_pattern['total_questions']} questions across all sections
- Total marks must equal exactly {paper_pattern['total_marks']}
- Each section must have exactly the question count and marks-per-question specified in the pattern
- Keep a running total; adjust the last question if needed to hit the exact total

MODULE BALANCE:
- Prioritize teacher-specified modules if given, else follow syllabus weightage
- Min per module: {paper_pattern['module_weightage_range']['min'] * 100:.0f}%
- Max per module: {paper_pattern['module_weightage_range']['max'] * 100:.0f}%

BLOOM'S — follow the exact question counts in the BLOOM'S DISTRIBUTION block above.
No deviation. Count as you go; stop assigning a level once its quota is filled.

TOPIC FIELD:
- Must exactly match a topic or subtopic name from the knowledge graph above
- Do not invent or paraphrase topic names

IMPORTANT INSTRUCTIONS: 
- Blueprint must be balanced according to given constraints and follow the given pattern, marks, dstribution and importantly teachers input.
- Follow the weightage distrubition strictly considering teacher input as well. 
- Ensure Questions are not repeated and are from different modules as much as possible. Keep variety in modules and topics according to weightage assigned. 
- Teachers input should be always priotized and followed. 
- If teacher wants more questions from a module, or want question paper from specific modules only, then follow that strictly even if it skews the distribution.
- If teacher has given specific topics, ensure those topics are included. 



**OUTPUT FORMAT — return ONLY valid JSON, no markdown, no explanation:**

{{
  "sections": [
    {{
      "section_name": "Section A",
      "section_description": "Short Answer Questions",
      "questions": [
        {{
          "question_number": "1a",
          "module": "<exact name of the module from knowledge graph>",
          "topic": "<exact name from knowledge graph>",
          "marks": 5,
          "bloom_level": "Remember",
          "is_pyq": false,
          "rationale": "max 8 words"
        }}
      ]
    }}
  ]
}}

bloom_level must be one of: Remember, Understand, Apply, Analyze, Evaluate, Create
"""

    max_retries = 3
    response_text = ""
    for attempt in range(max_retries):
        try:
            response      = llm.invoke([HumanMessage(content=prompt)])
            response_text = str(getattr(response, "content", "") or "").strip()

            print(f"\n📥 LLM Response Length: {len(response_text)} chars")
            print(f"📥 First 200: {response_text[:200]}")

            # Strip markdown fences
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()

            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                response_text = json_match.group(0)

            try:
                blueprint = json.loads(response_text)
            except json.JSONDecodeError:
                blueprint = json.loads(fix_incomplete_json(response_text))

            if not isinstance(blueprint, dict) or "sections" not in blueprint:
                raise ValueError("Missing 'sections' key in blueprint")

            # Post-process: if no PYQs available, force all is_pyq to False
            if not has_pyqs:
                for section in blueprint.get("sections", []):
                    for q in section.get("questions", []):
                        q["is_pyq"] = False

            errors = validate_blueprint(blueprint, paper_pattern)
            if errors:
                print(f"⚠️  Validation warnings: {errors}")

            print(f"✅ Blueprint generated on attempt {attempt + 1}")
            return blueprint

        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                prompt += "\n\nCRITICAL: Return ONLY valid JSON. Keep rationale ≤3 words. Close all brackets."
            else:
                print("🔧 Returning fallback blueprint")
                return create_fallback_blueprint(paper_pattern)

    return create_fallback_blueprint(paper_pattern)


def validate_blueprint(blueprint: Dict, paper_pattern: Dict) -> List[str]:
    errors = []
    total_marks = sum(
        q["marks"]
        for s in blueprint["sections"]
        for q in s["questions"]
    )
    if total_marks != paper_pattern["total_marks"]:
        errors.append(f"Total marks: expected {paper_pattern['total_marks']}, got {total_marks}")

    total_qs = sum(len(s["questions"]) for s in blueprint["sections"])
    if total_qs != paper_pattern["total_questions"]:
        errors.append(f"Total questions: expected {paper_pattern['total_questions']}, got {total_qs}")

    for s in blueprint["sections"]:
        for q in s["questions"]:
            for field in ["question_number", "module", "topic", "marks", "bloom_level", "is_pyq"]:
                if field not in q:
                    errors.append(f"Q{q.get('question_number','?')} missing field: {field}")
    return errors