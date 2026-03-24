"""
Question Selector Agent - Updated Version
- Fuzzy/substring PYQ topic matching (fixes zero-match problem)
- Few-shot examples in generate_new_question() and rephrase_pyq()
- PYQ-absent safe handling (all is_pyq treated as False when bank is empty)
"""

import json
import uuid
import re
from typing import Dict, List, Optional, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


# ============================================================================
# CORE MATCHING HELPERS  (fuzzy substring — fixes zero-match problem)
# ============================================================================

def normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _topic_match(pyq_field: str, blueprint_topic: str) -> bool:
    """
    Flexible matching between a PYQ topic/subtopic string and the blueprint
    topic string.  Tries in order:
      1. Exact normalized equality
      2. Blueprint topic is a substring of PYQ field  (e.g. "Dropout" in "Regularization Methods: Dropout")
      3. PYQ field is a substring of blueprint topic
      4. Any significant word (≥5 chars) from blueprint topic appears in PYQ field
    """
    pt = normalize(pyq_field)
    bt = normalize(blueprint_topic)

    if not pt or not bt:
        return False

    # 1 — exact
    if pt == bt:
        return True

    # 2 — blueprint topic is inside PYQ field
    if bt in pt:
        return True

    # 3 — PYQ field is inside blueprint topic
    if pt in bt:
        return True

    # 4 — significant word overlap
    bt_words = {w for w in bt.split() if len(w) >= 5}
    if bt_words and any(w in pt for w in bt_words):
        return True

    return False


def _pyq_topic_match(pyq: Dict, blueprint_topic: str) -> bool:
    """Check both topic and subtopic fields of a PYQ against blueprint topic."""
    return (
        _topic_match(pyq.get("topic", ""), blueprint_topic) or
        _topic_match(pyq.get("subtopic", ""), blueprint_topic)
    )


def match_level_1(pyq: Dict, topic: str, marks: int, bloom_level: str) -> bool:
    """Fuzzy topic + exact marks + exact bloom_level."""
    return (
        _pyq_topic_match(pyq, topic)
        and pyq.get("marks") == marks
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_2(pyq: Dict, topic: str, bloom_level: str) -> bool:
    """Fuzzy topic + exact bloom_level (drop marks)."""
    return (
        _pyq_topic_match(pyq, topic)
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_3(pyq: Dict, topic: str) -> bool:
    """Fuzzy topic only (drop marks + bloom)."""
    return _pyq_topic_match(pyq, topic)


def find_match(pyq_bank: List[Dict], used_pyq_ids: set, **criteria) -> Optional[Dict]:
    """
    Search PYQ bank with given criteria, skipping already-used PYQs.
    criteria keys: level, topic, marks (optional), bloom_level (optional)
    """
    level       = criteria.get("level", 1)
    topic       = criteria["topic"]
    marks       = criteria.get("marks")
    bloom_level = criteria.get("bloom_level")

    for pyq in pyq_bank:
        pyq_id = pyq.get("id")
        if not pyq_id or pyq_id in used_pyq_ids:
            continue
        if level == 1 and match_level_1(pyq, topic, marks, bloom_level):
            return pyq
        elif level == 2 and match_level_2(pyq, topic, bloom_level):
            return pyq
        elif level == 3 and match_level_3(pyq, topic):
            return pyq
    return None


# ============================================================================
# MARK RANGE HELPER
# ============================================================================

def _mark_range_label(marks: int) -> str:
    if marks <= 3:
        return "2-3"
    elif marks <= 6:
        return "4-6"
    else:
        return "8-10"


# ============================================================================
# FEW-SHOT EXAMPLES
# ============================================================================

# Used in rephrase_pyq()
_REPHRASE_FEW_SHOTS = """
EXAMPLES — how to scale a question to different mark ranges:

Example 1 (ML — SVM):
  Original question: "Explain Support Vector Machines and their working with kernel functions."
  2–3 marks : What is a Support Vector Machine?
  4–6 marks : Explain how Support Vector Machines work and the role of kernels.
  8–10 marks: Explain Support Vector Machines in detail, including margin maximization, kernel trick, types of kernels, and real-world applications.

Example 2 (DBMS — Transactions):
  Original question: "Discuss ACID properties and their importance in transaction management systems."
  2–3 marks : What are ACID properties?
  4–6 marks : Explain the ACID properties in DBMS with brief examples.
  8–10 marks: Explain ACID properties in detail and analyze their role in ensuring reliability and consistency in transaction management systems with examples.

Example 3 (OS — Scheduling):
  Original question: "Compare different CPU scheduling algorithms and evaluate their performance."
  2–3 marks : What is CPU scheduling?
  4–6 marks : Explain any two CPU scheduling algorithms.
  8–10 marks: Compare CPU scheduling algorithms such as FCFS, SJF, and Round Robin. Analyze their performance based on waiting time and turnaround time.

Example 4 (CN — Routing):
  Original question: "Explain routing algorithms and compare distance vector and link state approaches."
  2–3 marks : What is routing in computer networks?
  4–6 marks : Explain distance vector and link state routing.
  8–10 marks: Explain routing algorithms in detail and compare distance vector and link state approaches based on working, advantages, and limitations.

Example 5 (SE — SDLC):
  Original question: "Explain different SDLC models and evaluate their suitability for various projects."
  2–3 marks : What is SDLC?
  4–6 marks : Explain any two SDLC models.
  8–10 marks: Explain different SDLC models such as Waterfall, Agile, and Spiral. Evaluate their suitability for different project types with examples.

Example 6 (Deep Learning — Autoencoders):
  Original question: "Explain the concept and architecture of denoising autoencoders with real-world applications."
  2–3 marks : What is a denoising autoencoder? How does it work?
  4–6 marks : Explain denoising autoencoders in detail.
  8–10 marks: Explain the concept of denoising autoencoders, describe their architecture, and explain their applications in real-world unsupervised learning scenarios.
"""

# Used in generate_new_question()
_GENERATE_FEW_SHOTS = """
EXAMPLES — what good Mumbai University questions look like at each mark range:

─── 2–3 marks (1 line, recall/definition) ───
  Topic: Denoising Autoencoders    | Bloom: Remember   → What are denoising autoencoders?
  Topic: Gradient Descent          | Bloom: Remember   → Define gradient descent. State its purpose.
  Topic: Sequence Learning Problem | Bloom: Understand → Describe the sequence learning problem.
  Topic: GAN Architecture          | Bloom: Understand → What is a Generative Adversarial Network?
  Topic: Pooling Layer             | Bloom: Remember   → What is pooling in CNNs? List its types.

─── 4–6 marks (2–4 lines, explanation with brief example) ───
  Topic: Dropout                   | Bloom: Understand → Explain dropout. How does it solve overfitting?
  Topic: LSTM                      | Bloom: Understand → Explain LSTM architecture.
  Topic: CNN Architecture          | Bloom: Understand → Explain basic working of CNN.
  Topic: Backpropagation           | Bloom: Understand → Explain Stochastic Gradient Descent and momentum-based gradient descent.
  Topic: Regularization            | Bloom: Understand → Explain early stopping, batch normalization, and data augmentation.
  Topic: Activation Functions      | Bloom: Understand → What is an activation function? Describe any four activation functions.

─── 8–10 marks (3–5 lines, detailed explanation, diagrams expected) ───
  Topic: CNN Architecture          | Bloom: Apply    → Explain CNN architecture in detail. Calculate parameters for a 32×32×3 input with ten 5×5 filters, stride 1, pad 2.
  Topic: LSTM                      | Bloom: Analyze  → Differentiate between LSTM and GRU networks in detail.
  Topic: Gradient Descent          | Bloom: Understand → What are the different types of Gradient Descent methods? Explain any three.
  Topic: Autoencoders              | Bloom: Understand → Explain any three types of autoencoders with their working.
  Topic: GAN                       | Bloom: Understand → Explain GAN architecture and its applications in detail.
  Topic: AlexNet                   | Bloom: Analyze  → Explain and analyze the architectural components of AlexNet CNN.
"""

# Bloom verb guidance — concise, used inline
_BLOOM_VERBS = {
    "Remember":   "Use verbs: define / list / state / name / recall",
    "Understand": "Use verbs: explain / describe / summarize / classify",
    "Apply":      "Use verbs: solve / demonstrate / calculate / use",
    "Analyze":    "Use verbs: compare / differentiate / examine / break down",
    "Evaluate":   "Use verbs: justify / critique / assess / argue for/against",
    "Create":     "Use verbs: design / formulate / construct / propose",
}


# ============================================================================
# LLM CALLS
# ============================================================================

def rephrase_pyq(pyq_text: str, target_marks: int, topic: str, bloom_level: str) -> str:
    """
    Rephrase / scale an existing PYQ to the target marks and bloom level.
    Uses few-shot examples so the model understands mark-range scaling.
    """
    mark_range = _mark_range_label(target_marks)
    bloom_verb = _BLOOM_VERBS.get(bloom_level, "Ask an appropriate question.")

    prompt = f"""You are a Mumbai University question paper setter.
Your job: rewrite the given question so it fits exactly {target_marks} marks at {bloom_level} level.

TOPIC: {topic}
TARGET MARKS: {target_marks}  (range: {mark_range})
BLOOM LEVEL: {bloom_level}  — {bloom_verb}

ORIGINAL QUESTION:
{pyq_text}

{_REPHRASE_FEW_SHOTS}

SCALING RULES:
  2–3 marks → 1 short line. Single concept. Definition or one-word-answer style.
  4–6 marks → 1 line. Brief explanation with an example or one sub-parts.
  8–10 marks → 1.5-2 lines. Detailed explanation. May include diagrams, comparisons, or sub-parts.

BLOOM ADJUSTMENT:
  - If bloom level is Remember/Understand: keep the question theoretical ("explain", "describe", "define").
  - If bloom level is Apply: add a small practical task ("demonstrate", "calculate", "show with example").
  - If bloom level is Analyze: add comparison or breakdown ("compare", "differentiate", "examine").
  - Do NOT add numerical problems unless the original question already has them.

OUTPUT: Write ONLY the rewritten question text. No preamble, no explanation.
"""
    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    return str(getattr(response, "content", "") or "").strip()


def generate_new_question(
    topic: str,
    subtopic: str,
    module: str,
    marks: int,
    bloom_level: str,
    question_number: str,
    teacher_input: dict = None,
) -> str:
    """
    Generate a brand-new Mumbai University style question.
    Uses few-shot examples calibrated to mark ranges.
    """
    mark_range = _mark_range_label(marks)
    bloom_verb = _BLOOM_VERBS.get(bloom_level, "Ask an appropriate question.")

    # Teacher context
    teacher_context = ""
    if teacher_input:
        t_text = teacher_input.get("input", "")
        if t_text:
            teacher_context = f"\nTeacher instructions (FOLLOW STRICTLY): {t_text}"
        t_lower = t_text.lower()
        if any(w in t_lower for w in ["easy", "simple", "basic", "introductory"]):
            teacher_context += "\nDifficulty: EASY — definitions and simple explanations only."
        elif any(w in t_lower for w in ["hard", "difficult", "advanced", "challenging"]):
            teacher_context += "\nDifficulty: HARD — multi-step reasoning or analysis required."
        if any(w in t_lower for w in ["no numerical", "avoid numerical", "no calculation"]):
            teacher_context += "\nIMPORTANT: Do NOT include numerical problems."

    prompt = f"""You are a Mumbai University question paper setter.
Generate ONE exam question for the specification below.

SPECIFICATION:
  Module      : {module}
  Topic       : {topic}
  Subtopic    : {subtopic if subtopic else topic}
  Marks       : {marks}  (mark range: {mark_range})
  Bloom Level : {bloom_level}  — {bloom_verb}
{teacher_context}

{_GENERATE_FEW_SHOTS}

STRICT RULES:
  1. Match the LENGTH to the mark range exactly:
       2–3 marks → 1 line maximum (short recall/definition/concept question)
       4–6 marks → 1 line (explanation, may have 1 sub-parts)
       8–10 marks → 1.5-2 lines (detailed)
  2. Match the VERB to the bloom level ({bloom_level}): {bloom_verb}
  3. Do NOT generate numerical/calculation problems unless teacher explicitly asked.
  4. Do NOT invent sub-topics outside the given topic.
  5. Keep language natural and direct — like the PYQ examples above.
  6. The question must be solvable in exam conditions by a student.
  
OUTPUT: Write ONLY the question text. No preamble, no label, no explanation.
"""
    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    return str(getattr(response, "content", "") or "").strip()


# ============================================================================
# PYQ BANK GUARD  (handles empty / missing PYQ bank)
# ============================================================================

def _pyq_bank_available(pyq_bank: List[Dict]) -> bool:
    """Returns True only if the bank has at least one question with an id."""
    return bool(pyq_bank) and any(q.get("id") for q in pyq_bank)


# ============================================================================
# CORE QUESTION SELECTOR
# ============================================================================

def select_questions(
    blueprint: Dict,
    pyq_bank: List[Dict],
    teacher_input: dict = None,
) -> Dict:
    """
    Main question selection function.

    If pyq_bank is empty / unavailable, all questions are treated as is_pyq=False
    and generated directly — no PYQ matching is attempted.
    """

    pyq_available = _pyq_bank_available(pyq_bank)
    if not pyq_available:
        print("⚠️  PYQ bank is empty or unavailable — all questions will be generated fresh.")

    used_pyq_ids   = set()
    draft_sections = []
    selection_log  = []

    stats = {
        "total_questions":      0,
        "pyq_exact_match":      0,
        "pyq_rephrased_marks":  0,
        "pyq_rephrased_bloom":  0,
        "generated_new":        0,
        "direct_generated":     0,
    }

    print("\n" + "=" * 70)
    print("🔍  QUESTION SELECTION — PYQ-FIRST STRATEGY")
    print("=" * 70)

    for section in blueprint.get("sections", []):
        section_name = section["section_name"]
        section_desc = section.get("section_description", "")
        print(f"\n📂 {section_name}")
        print("-" * 50)

        draft_questions = []

        for bp_q in section.get("questions", []):
            stats["total_questions"] += 1

            q_num       = bp_q["question_number"]
            topic       = bp_q["topic"]
            subtopic    = bp_q.get("subtopic", "")
            module      = bp_q["module"]
            marks       = bp_q["marks"]
            bloom_level = bp_q["bloom_level"]
            # If PYQ bank is absent, override is_pyq to False regardless of blueprint
            is_pyq      = bp_q.get("is_pyq", False) and pyq_available

            print(f"\n  ▶ Q{q_num}: {topic} | {marks}M | {bloom_level} | is_pyq={is_pyq}")

            selected_text    = None
            selection_method = None
            source_pyq_id    = None

            # ────────────────────────────────────────────────────────────────
            # CASE A: Generate directly (no PYQ needed)
            # ────────────────────────────────────────────────────────────────
            if not is_pyq:
                selected_text    = generate_new_question(
                    topic, subtopic, module, marks, bloom_level, q_num, teacher_input
                )
                selection_method = "generated_direct"
                stats["direct_generated"] += 1
                print(f"     → Generated directly (is_pyq=False or no PYQ bank)")

            # ────────────────────────────────────────────────────────────────
            # CASE B: PYQ-first matching hierarchy
            # ────────────────────────────────────────────────────────────────
            else:
                match = None

                # Level 1 — fuzzy topic + exact marks + exact bloom
                match = find_match(
                    pyq_bank, used_pyq_ids,
                    level=1, topic=topic, marks=marks, bloom_level=bloom_level
                )
                if match:
                    mid  = match.get("id", "unknown")
                    text = match.get("text", match.get("question", ""))
                    print(f"     ✅ L1 match (topic+marks+bloom) → PYQ #{mid} used as-is")
                    selected_text    = text
                    selection_method = "pyq_exact"
                    source_pyq_id    = mid
                    if mid != "unknown": used_pyq_ids.add(mid)
                    stats["pyq_exact_match"] += 1

                # Level 2 — fuzzy topic + exact bloom (drop marks)
                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=2, topic=topic, bloom_level=bloom_level
                    )
                    if match:
                        mid      = match.get("id", "unknown")
                        orig_m   = match.get("marks", marks)
                        text     = match.get("text", match.get("question", ""))
                        print(f"     🔄 L2 match (topic+bloom, {orig_m}M→{marks}M) → rephrasing PYQ #{mid}")
                        selected_text    = rephrase_pyq(text, marks, topic, bloom_level)
                        selection_method = "pyq_rephrased_marks"
                        source_pyq_id    = mid
                        if mid != "unknown": used_pyq_ids.add(mid)
                        stats["pyq_rephrased_marks"] += 1

                # Level 3 — fuzzy topic only (drop marks + bloom)
                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=3, topic=topic
                    )
                    if match:
                        mid      = match.get("id", "unknown")
                        orig_bl  = match.get("bloom_level", bloom_level)
                        text     = match.get("text", match.get("question", ""))
                        print(f"     🔄 L3 match (topic only, bloom {orig_bl}→{bloom_level}) → rephrasing PYQ #{mid}")
                        selected_text    = rephrase_pyq(text, marks, topic, bloom_level)
                        selection_method = "pyq_rephrased_bloom"
                        source_pyq_id    = mid
                        if mid != "unknown": used_pyq_ids.add(mid)
                        stats["pyq_rephrased_bloom"] += 1

                # Fallback — generate fresh
                if not match:
                    print(f"     ⚡ No PYQ match → generating fresh question")
                    selected_text    = generate_new_question(
                        topic, subtopic, module, marks, bloom_level, q_num, teacher_input
                    )
                    selection_method = "generated_fallback"
                    stats["generated_new"] += 1

            draft_q = {
                "id":               str(uuid.uuid4())[:8],
                "question_number":  q_num,
                "module":           module,
                "topic":            topic,
                "subtopic":         subtopic,
                "marks":            marks,
                "bloom_level":      bloom_level,
                "question_text":    selected_text,
                "selection_method": selection_method,
                "source_pyq_id":    source_pyq_id,
                "is_pyq_sourced":   source_pyq_id is not None,
            }
            draft_questions.append(draft_q)
            selection_log.append({
                "question_number": q_num,
                "method":          selection_method,
                "pyq_id":          source_pyq_id,
            })
            print(f"     📝 Method: {selection_method}")

        draft_sections.append({
            "section_name":        section_name,
            "section_description": section_desc,
            "questions":           draft_questions,
        })

    draft_paper = {
        "paper_id":           str(uuid.uuid4())[:12],
        "blueprint_metadata": blueprint.get("blueprint_metadata", {}),
        "sections":           draft_sections,
        "selection_stats":    stats,
        "selection_log":      selection_log,
        "used_pyq_ids":       list(used_pyq_ids),
    }

    # Summary
    print("\n" + "=" * 70)
    print("📊  SELECTION SUMMARY")
    print("=" * 70)
    total    = stats["total_questions"]
    pyq_hits = stats["pyq_exact_match"] + stats["pyq_rephrased_marks"] + stats["pyq_rephrased_bloom"]
    print(f"  Total Questions       : {total}")
    print(f"  PYQ Exact Match       : {stats['pyq_exact_match']}")
    print(f"  PYQ Rephrased (marks) : {stats['pyq_rephrased_marks']}")
    print(f"  PYQ Rephrased (bloom) : {stats['pyq_rephrased_bloom']}")
    print(f"  Generated (fallback)  : {stats['generated_new']}")
    print(f"  Generated (direct)    : {stats['direct_generated']}")
    print(f"  PYQ Utilization       : {pyq_hits}/{total} ({pyq_hits/total*100:.0f}%)" if total else "")
    if not pyq_available:
        print("  ⚠️  PYQ bank was empty — all questions generated fresh")
    print("=" * 70)

    return draft_paper


def print_draft_paper(draft_paper: Dict):
    METHOD_LABELS = {
        "pyq_exact":           "📌 PYQ (exact)",
        "pyq_rephrased_marks": "🔄 PYQ (rephrased — marks)",
        "pyq_rephrased_bloom": "🔄 PYQ (rephrased — bloom)",
        "generated_fallback":  "✨ Generated (fallback)",
        "generated_direct":    "✨ Generated (direct)",
    }
    print("\n" + "=" * 80)
    print("📄  DRAFTED QUESTION PAPER")
    print("=" * 80)
    for section in draft_paper["sections"]:
        print(f"\n{'─'*80}")
        print(f"  {section['section_name']} — {section['section_description']}")
        print(f"{'─'*80}")
        for q in section["questions"]:
            label = METHOD_LABELS.get(q["selection_method"], q["selection_method"])
            print(f"\n  Q{q['question_number']}  [{q['marks']}M | {q['bloom_level']} | {q['module']}]")
            print(f"  Topic : {q['topic']}")
            print(f"  Source: {label}" + (f" (PYQ #{q['source_pyq_id']})" if q["source_pyq_id"] else ""))
            print(f"\n  {q['question_text']}")
    print("\n" + "=" * 80)