"""
Question Selector Agent — Updated Version
Changes from previous version:
  1. Marks → Answer Structure constraint block (hard constraints injected into both
     generate and rephrase prompts — no sub-parts for 2M, no "and" joining, etc.)
  2. Few-shot examples tightened: 2-3M are strictly one-concept / one-line,
     4-6M are one-line deep, 8-10M capped at 1-2 sub-parts. Domain variety kept.
  3. Rephrase prompt hardened with STRIP RULE: if target marks < 50% of source,
     extract atomic core only — no second LLM call, just smarter prompting.
  4. History tracking upgraded to complete in-run history: every generation
      call receives the full prior question list, and the prompt shows only
      the question texts in order. It still does NOT hard-block repeats.
  5. KG child-node enrichment for marks > 5: passes child subtopics from the
     knowledge graph as additional context when available, falls back cleanly.
"""

import json
import uuid
import re
from typing import Dict, List, Optional, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage

# GDT bloom levels that trigger structured visual output (Apply / Analyze, marks >= 5)
_GDT_BLOOM_LEVELS = {"apply", "analyze", "analyse"}


def _needs_gdt(bloom_level: str, marks: int) -> bool:
    return str(bloom_level).lower().strip() in _GDT_BLOOM_LEVELS and marks >= 5


# ============================================================================
# CORE MATCHING HELPERS
# ============================================================================

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


# Generic CS words that appear in almost every topic name — too common to use
# as matching signals, would cause false positives (e.g. "algorithm" matches
# Floyd-Warshall slot against KMP PYQ).
_TOPIC_MATCH_STOPWORDS = {
    "algorithm", "algorithms", "problem", "problems", "method", "methods",
    "approach", "approaches", "technique", "techniques", "concept", "concepts",
    "strategy", "analysis", "design", "study", "using", "based", "introduction",
}


def _topic_match(pyq_field: str, blueprint_topic: str) -> bool:
    pt = normalize(pyq_field)
    bt = normalize(blueprint_topic)
    if not pt or not bt:
        return False
    if pt == bt:
        return True
    if bt in pt:
        return True
    if pt in bt:
        return True
    bt_words = {w for w in bt.split() if len(w) >= 5 and w not in _TOPIC_MATCH_STOPWORDS}
    if bt_words and any(w in pt for w in bt_words):
        return True
    return False


# Patterns that indicate a question references external data (table, figure,
# "following strings/input/data") which cannot appear inline on the paper.
_DATALESS_PATTERNS = [
    r"\bfor\s+(?:the\s+)?following\b",
    r"\bsolve\s+(?:the\s+)?following\b",
    r"\bconsider\s+(?:the\s+)?following\b",
    r"\bapply\s+(?:\w+\s+)?(?:to\s+)?(?:the\s+)?following\b",
    r"\bgiven\s+(?:in\s+)?(?:the\s+)?(?:table|figure|diagram|below|above)\b",
    r"\bgiven\s+(?:the\s+)?following\b",
    r"\bshown\s+in\s+(?:the\s+)?(?:figure|table|diagram)\b",
    r"\bas\s+shown\s+(?:in\s+)?(?:the\s+)?(?:figure|table|diagram|below|above)\b",
    r"\brefer\s+(?:to\s+)?(?:the\s+)?(?:figure|table|diagram)\b",
    r"\bwith\s+reference\s+to\s+(?:the\s+)?(?:figure|table|diagram)\b",
    r"\bfrom\s+(?:the\s+)?(?:following|given|above|below)\b",
    r"\busing\s+(?:the\s+)?(?:following|given|above)\b",
    r"\bfollowing\s+(?:strings?|arrays?|inputs?|data|graph|table|numbers?|values?|sequences?|examples?|instances?)\b",
    r"\bobtain\s+(?:the\s+)?solution\s+to\s+(?:the\s+)?following\b",
    r"\bcalculate\s+(?:\w+\s+){0,4}(?:for\s+)?(?:the\s+)?following\b",
    r"\bfind\s+(?:\w+\s+){0,4}(?:for\s+)?(?:the\s+)?following\b",
    r"\bcompute\s+(?:\w+\s+){0,4}(?:for\s+)?(?:the\s+)?following\b",
    r"\bdata\s+(?:is\s+)?given\s+(?:in|below|above)\b",
]


def _is_dataless(text: str) -> bool:
    """
    Returns True when the question text references external data (table, figure,
    'following strings', etc.) that is not embedded in the question itself.
    Such questions cannot be used verbatim on a paper — they must be rephrased.
    """
    tl = text.lower()
    return any(re.search(p, tl) for p in _DATALESS_PATTERNS)


def _pyq_topic_match(pyq: Dict, blueprint_topic: str) -> bool:
    return (
        _topic_match(pyq.get("topic", ""), blueprint_topic) or
        _topic_match(pyq.get("subtopic", ""), blueprint_topic)
    )


def match_level_1(pyq: Dict, topic: str, marks: int, bloom_level: str) -> bool:
    return (
        _pyq_topic_match(pyq, topic)
        and pyq.get("marks") == marks
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_2(pyq: Dict, topic: str, bloom_level: str) -> bool:
    return (
        _pyq_topic_match(pyq, topic)
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_3(pyq: Dict, topic: str) -> bool:
    return _pyq_topic_match(pyq, topic)


def find_match(pyq_bank: List[Dict], used_pyq_ids: set, **criteria) -> Optional[Dict]:
    level       = criteria.get("level", 1)
    topic       = criteria["topic"]
    marks       = criteria.get("marks")
    bloom_level = criteria.get("bloom_level")
    marks_value = int(marks) if marks is not None else 0
    bloom_level_value = str(bloom_level) if bloom_level is not None else ""

    for pyq in pyq_bank:
        pyq_id = pyq.get("id")
        if not pyq_id or pyq_id in used_pyq_ids:
            continue
        if level == 1 and match_level_1(pyq, topic, marks_value, bloom_level_value):
            return pyq
        elif level == 2 and match_level_2(pyq, topic, bloom_level_value):
            return pyq
        elif level == 3 and match_level_3(pyq, topic):
            return pyq
    return None


# ============================================================================
# MARKS → ANSWER STRUCTURE  (Change #1)
# ============================================================================

MARKS_STRUCTURE = {
    "2-3": {
        "label":           "2–3 marks",
        "answer_length":   "3–5 lines in the answer booklet",
        "question_length": "ONE short sentence — strictly one line, no exceptions",
        "concepts":        "exactly ONE concept, ONE idea",
        "sub_parts":       "NEVER allowed. No 'and', no 'also', no '/', no OR between two concepts.",
        "style":           "definition / identification / one-point recall",
        "examples":        [
            "What is dropout in neural networks?",
            "Define gradient descent.",
            "What is a kernel function in SVM?",
            "State the purpose of the activation function.",
            "What is ACID in DBMS?",
        ],
        "banned_patterns": [
            "X and Y",
            "X as well as Y",
            "X along with Y",
            "X / Y",
            "both X and Y",
            "explain X and also explain Y",
        ],
    },
    "4-6": {
        "label":           "4–6 marks",
        "answer_length":   "half a page in the answer booklet",
        "question_length": "ONE line stictly. Less than 75 characters.",
        "concepts":        "ONE concept with depth, OR one concept + one brief example",
        "sub_parts":       "At most ONE sub-part, only if absolutely necessary. Prefer no sub-parts.",
        "style":           "explanation / working / brief comparison of two closely related ideas",
        "examples":        [
            "Explain dropout and how it prevents overfitting.",
            "Explain LSTM architecture.",
            "What is an activation function? Describe any two types.",
            "Explain the working of SVM with a kernel.",
            "Describe the producer-consumer problem in OS.",
        ],
        "banned_patterns": [
            "explain X, Y, and Z",
            "three or more sub-parts",
            "list all types of ...",
        ],
    },
    "8-10": {
        "label":           "8–10 marks",
        "answer_length":   "full page in the answer booklet",
        "question_length": "1–1.5 lines strictly, may or may not include one subpart. Less than 100 characters.",
        "concepts":        "one main concept with detailed explanation",
        "sub_parts":       "At most 1 sub-parts. No more.",
        "style":           "detailed explanation / comparison / application with example or calculation",
        "examples":        [
            "Explain CNN architecture in detail. Calculate the number of parameters for a 32×32×3 input with ten 5×5 filters.",
            "Differentiate between LSTM and GRU networks in detail.",
            "Explain any three types of autoencoders with their working.",
            "Explain GAN architecture with its applications.",
            "Compare distance vector and link state routing protocols based on working, advantages, and limitations.",
        ],
        "banned_patterns": [
            "more than two sub-parts",
            "list all ... explain all ...",
        ],
    },
}

def _get_marks_structure(marks: int) -> Dict:
    if marks <= 3:
        return MARKS_STRUCTURE["2-3"]
    elif marks <= 6:
        return MARKS_STRUCTURE["4-6"]
    else:
        return MARKS_STRUCTURE["8-10"]

def _mark_range_label(marks: int) -> str:
    if marks <= 3:
        return "2-3"
    elif marks <= 6:
        return "4-6"
    else:
        return "8-10"


# ============================================================================
# BLOOM VERB GUIDANCE
# ============================================================================

_BLOOM_VERBS = {
    "Remember":   "Use verbs: define / list / state / name / recall / what is / identify",
    "Understand": "Use verbs: explain / describe / summarize / classify / how does",
    "Apply":      "Use verbs: solve / demonstrate / calculate / use / show with example",
    "Analyze":    "Use verbs: compare / differentiate / examine / break down / analyze",
    "Evaluate":   "Use verbs: justify / critique / assess / argue for/against / evaluate",
    "Create":     "Use verbs: design / formulate / construct / propose / develop",
}


# ============================================================================
# HISTORY TRACKING — Complete question list  (Change #4)
# ============================================================================

def _build_soft_history_instruction(
    history: List[str],
) -> str:
    """
    Complete-history nudge: show every prior question in the current run.
    The prompt should contain only the question texts, in order.
    """
    if not history:
        return ""

    lines = [
        "\nCOMPLETE HISTORY (all previous questions in this run, oldest to newest):",
        "  Review the entire list before generating the next question.",
    ]

    for index, entry in enumerate(history, 1):
        if isinstance(entry, dict):
            entry = entry.get("text") or entry.get("question_text") or entry.get("question") or ""
        cleaned = re.sub(r"\s+", " ", str(entry)).strip()
        if cleaned:
            lines.append(f"  {index}. {cleaned}")

    lines.extend([
        "  Do not repeat or paraphrase any question above.",
        "  If a similar idea is unavoidable, change the opening verb and wording as much as possible.",
    ])
    return "\n".join(lines)


# ============================================================================
# KG CHILD-NODE ENRICHMENT  (Change #5)
# ============================================================================

def _get_kg_children(knowledge_graph: Dict, topic: str) -> List[str]:
    """
    Returns child subtopic names for a given topic from the knowledge graph.
    Supports both flat { module: [topics] } and nested { Modules: [...] } formats.
    Returns empty list if topic not found or has no children.
    """
    if not knowledge_graph or not topic:
        return []

    topic_norm = normalize(topic)

    # Handle nested format: { Modules: [ { Module_Name, Topics: [ { Topic_Name, Subtopics } ] } ] }
    modules = knowledge_graph.get("Modules", [])
    if isinstance(modules, list):
        for mod in modules:
            for t in mod.get("Topics", []):
                if isinstance(t, dict):
                    if normalize(t.get("Topic_Name", "")) == topic_norm:
                        subtopics = t.get("Subtopics", [])
                        if isinstance(subtopics, list):
                            return [
                                s.get("Subtopic_Name", s) if isinstance(s, dict) else s
                                for s in subtopics
                            ]

    # Handle flat format: { Module_Name: ["Topic1", "Topic2"] }
    # In flat format, topics are strings, no children available
    return []

def _enrich_topic_with_children(
    topic: str,
    subtopic: str,
    marks: int,
    knowledge_graph: Dict,
) -> str:
    """
    For marks > 5, appends child subtopics to topic context string.
    Falls back to topic + subtopic if no children found.
    """
    if marks <= 5 or not knowledge_graph:
        return topic if not subtopic else f"{topic} (focus: {subtopic})"

    children = _get_kg_children(knowledge_graph, topic)

    if children:
        children_str = ", ".join(children[:6])  # cap at 6 to avoid prompt bloat
        return f"{topic} [key sub-concepts: {children_str}]"
    elif subtopic:
        return f"{topic} (focus: {subtopic})"
    else:
        return topic


# ============================================================================
# FEW-SHOT EXAMPLES  (Change #2 — tightened per mark range)
# ============================================================================

_REPHRASE_FEW_SHOTS = """
EXAMPLES — how to scale a PYQ to a different mark range:

NOTE: Watch how the question SHRINKS or GROWS. A 2-3M question is ALWAYS one line,
one concept, zero sub-parts, no "and" joining two ideas.

Example 1 (Deep Learning — Autoencoders):
  Original (10M): "Explain the concept and architecture of denoising autoencoders with their real-world applications and limitations."
  2–3 marks : What is a denoising autoencoder?
  4–6 marks : Explain denoising autoencoders and their working.
  8–10 marks: Explain the architecture of denoising autoencoders and describe their real-world applications.

Example 2 (OS — Scheduling):
  Original (10M): "Compare FCFS, SJF, and Round Robin scheduling algorithms. Analyze their performance based on waiting time and turnaround time."
  2–3 marks : What is CPU scheduling?
  4–6 marks : Explain any two CPU scheduling algorithms.
  8–10 marks: Compare FCFS, SJF, and Round Robin scheduling algorithms based on waiting time and turnaround time.

Example 3 (DBMS — Transactions):
  Original (8M): "Discuss ACID properties and their importance in transaction management systems with suitable examples."
  2–3 marks : What are ACID properties?
  4–6 marks : Explain ACID properties in DBMS with a brief example.
  8–10 marks: Explain ACID properties in detail and analyze their importance in ensuring reliability in transaction management systems.

Example 4 (ML — SVM):
  Original (6M): "Explain Support Vector Machines and their working with kernel functions."
  2–3 marks : What is a Support Vector Machine?
  4–6 marks : Explain how SVM works with kernel functions.
  8–10 marks: Explain Support Vector Machines in detail, covering margin maximization, the kernel trick, and types of kernels.

Example 5 (CN — Routing):
  Original (8M): "Explain routing algorithms and compare distance vector and link state approaches."
  2–3 marks : What is routing in computer networks?
  4–6 marks : Explain distance vector and link state routing.
  8–10 marks: Compare distance vector and link state routing algorithms based on working, convergence, and overhead.

BAD EXAMPLES (do NOT do this):
  ❌ 2M: "What is dropout and how does it help prevent overfitting in neural networks?"  ← TWO ideas joined with "and"
  ❌ 2M: "Define gradient descent and explain its types."  ← sub-part hidden after "and"
  ❌ 5M: "Explain LSTM, GRU, and their differences with applications."  ← too many concepts
"""

_GENERATE_FEW_SHOTS = """
EXAMPLES — good Mumbai University questions at each mark range:

─── 2–3 marks (ONE line, ONE concept, ZERO "and" joining two ideas) ───
  Topic: Denoising Autoencoders    | Bloom: Remember   → What is a denoising autoencoder?
  Topic: Gradient Descent          | Bloom: Remember   → Define gradient descent.
  Topic: GAN Architecture          | Bloom: Understand → How does a Generative Adversarial Network work?
  Topic: Pooling Layer             | Bloom: Remember   → What is pooling in CNNs?
  Topic: Dropout                   | Bloom: Understand → How does dropout reduce overfitting?
  Topic: ACID Properties           | Bloom: Remember   → What are ACID properties in DBMS?
  Topic: CPU Scheduling            | Bloom: Remember   → What is CPU scheduling?
  Topic: Routing                   | Bloom: Remember   → What is routing in computer networks?

  ✅ Each is ONE line. ONE concept. No "and" between two different ideas.

─── 4–6 marks (ONE line, one concept with depth or brief comparison of two related things) ───
  Topic: Dropout                   | Bloom: Understand → Explain dropout and how it prevents overfitting.
  Topic: LSTM                      | Bloom: Understand → Explain the architecture of LSTM networks.
  Topic: Backpropagation           | Bloom: Understand → Explain stochastic and momentum-based gradient descent.
  Topic: Activation Functions      | Bloom: Understand → What is an activation function? Describe any two types.
  Topic: ACID Properties           | Bloom: Understand → Explain ACID properties with a suitable example.
  Topic: CPU Scheduling            | Bloom: Understand → Explain any two CPU scheduling algorithms.

─── 8–10 marks (1–1.5 lines strictly, detailed or comparative, AT MOST 1 sub-parts) ───
  Topic: CNN Architecture          | Bloom: Apply    → Explain CNN architecture in detail. Calculate parameters for a 32×32×3 input with ten 5×5 filters, stride 1.
  Topic: LSTM                      | Bloom: Analyze  → Differentiate between LSTM and GRU networks in detail.
  Topic: Autoencoders              | Bloom: Understand → Explain any three types of autoencoders with their working and applications.
  Topic: GAN                       | Bloom: Understand → Explain GAN architecture and its applications in detail.
  Topic: AlexNet                   | Bloom: Analyze  → Explain the architectural components of AlexNet and analyze their contribution to its performance.
  Topic: Routing                   | Bloom: Analyze  → Compare distance vector and link state routing based on working, convergence speed, and overhead.
"""


# ============================================================================
# LLM CALLS
# ============================================================================

def rephrase_pyq(
    pyq_text: str,
    target_marks: int,
    topic: str,
    bloom_level: str,
    question_type: str = "short_answer",
    history: Optional[List[str]] = None,
    enriched_topic: Optional[str] = None,
) -> str:
    """
    Rephrase / scale an existing PYQ to the target marks and bloom level.

    Changes:
    - Injects MARKS_STRUCTURE hard constraint block (Change #1)
    - Soft history nudge via complete question list (Change #4)
    - STRIP RULE for large downscaling (Change #3 — no extra LLM call)
    - Uses enriched_topic if provided (Change #5)
    """
    ms           = _get_marks_structure(target_marks)
    mark_range   = _mark_range_label(target_marks)
    bloom_verb   = _BLOOM_VERBS.get(bloom_level, "Ask an appropriate question.")
    display_topic = enriched_topic or topic

    # Detect if we're downscaling significantly
    # Estimate source marks from text length as a rough heuristic
    source_is_long = len(pyq_text.split()) > 20
    strip_rule = ""
    if target_marks <= 3 and source_is_long:
        strip_rule = """
STRIP RULE (target is 2–3 marks):
  The original question covers too much. You MUST:
  1. Extract ONLY the single core concept from the original question.
  2. Ask about ONLY that one concept. Discard everything else.
  3. Do NOT carry over any sub-parts, comparisons, or secondary ideas from the original.
"""

    type_instructions = _question_type_instruction(question_type)
    history_nudge     = _build_soft_history_instruction(history or [])

    # Special instruction when the original PYQ references missing external data
    dataless_note = ""
    if _is_dataless(pyq_text):
        dataless_note = """
⚠️  DATALESS ORIGINAL — MANDATORY REWRITE RULES (strictly enforced):
The original question references external data (tables, figures, strings, arrays)
that is NOT available on this paper.
You MUST produce a SELF-CONTAINED question. Rules:
  1. FORBIDDEN output phrases: "for the following", "given below", "consider the following",
     "solve the following", "refer to figure/table", "as shown", "the data given",
     "obtain solution to following", or ANY phrase implying input data not in the question.
  2. Do NOT require any table, graph, diagram, or supplementary data to answer.
  3. Convert numerical/trace questions into conceptual form:
     Ask to EXPLAIN the algorithm, DESCRIBE the approach, or DEMONSTRATE with a
     self-chosen example (student picks the example — do NOT leave blank inputs).
  4. Example rewrite: "Find LCS for following strings." →
     "Explain the Longest Common Subsequence algorithm and trace it with a suitable example."
  5. The output question must be fully answerable from memory alone.
"""

    prompt = f"""You are a Mumbai University question paper setter.
Rewrite the given question so it fits exactly {target_marks} marks at {bloom_level} Bloom level.

TOPIC: {display_topic}
TARGET MARKS: {target_marks}  (range: {mark_range})
BLOOM LEVEL: {bloom_level}  — {bloom_verb}
{type_instructions}

══════════════════════════════════════════════════════
MARKS CONSTRAINT — FOLLOW EXACTLY, NO EXCEPTIONS
══════════════════════════════════════════════════════
Mark range  : {ms['label']}
Answer size : {ms['answer_length']}
Question    : {ms['question_length']}
Concepts    : {ms['concepts']}
Sub-parts   : {ms['sub_parts']}
Style       : {ms['style']}

BANNED PATTERNS for this mark range:
{chr(10).join(f"  ✗ {p}" for p in ms['banned_patterns'])}

GOOD QUESTION EXAMPLES for {ms['label']}:
{chr(10).join(f"  ✓ {e}" for e in ms['examples'])}
══════════════════════════════════════════════════════
{strip_rule}
{dataless_note}
{history_nudge}

ORIGINAL QUESTION:
{pyq_text}

{_REPHRASE_FEW_SHOTS}

BLOOM ADJUSTMENT:
  - Remember/Understand → theoretical ("explain", "describe", "define", "what is")
  - Apply → add a small practical task ("demonstrate", "calculate", "show with example")
  - Analyze → add comparison ("compare", "differentiate", "examine")
  - Do NOT add numerical problems unless the original already has them AND includes all required data inline.
  - NEVER write "for the following", "given below", "consider the following", "solve the following",
    or any phrase that implies external data not present in the question text itself.
  - If the original is a trace/solve question with missing data, convert it to an EXPLAIN/DESCRIBE question.

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
    teacher_input: Optional[dict] = None,
    question_type: str = "short_answer",
    history: Optional[List[str]] = None,
    enriched_topic: Optional[str] = None,
) -> str:
    """
    Generate a brand-new Mumbai University style question.

    Changes:
    - Injects MARKS_STRUCTURE hard constraint block (Change #1)
    - Soft history nudge via complete question list (Change #4)
    - Uses enriched_topic if provided (Change #5)
    """
    ms            = _get_marks_structure(marks)
    mark_range    = _mark_range_label(marks)
    bloom_verb    = _BLOOM_VERBS.get(bloom_level, "Ask an appropriate question.")
    display_topic = enriched_topic or (f"{topic} (focus: {subtopic})" if subtopic else topic)

    teacher_context   = _build_teacher_context(teacher_input)
    type_instructions = _question_type_instruction(question_type)
    history_nudge     = _build_soft_history_instruction(history or [])

    prompt = f"""You are a Mumbai University question paper setter.
Generate ONE exam question for the specification below.

SPECIFICATION:
  Question No : {question_number}
  Module      : {module}
  Topic       : {display_topic}
  Marks       : {marks}  (mark range: {mark_range})
  Bloom Level : {bloom_level}  — {bloom_verb}
{teacher_context}
{type_instructions}

══════════════════════════════════════════════════════
MARKS CONSTRAINT — FOLLOW EXACTLY, NO EXCEPTIONS
══════════════════════════════════════════════════════
Mark range  : {ms['label']}
Answer size : {ms['answer_length']}
Question    : {ms['question_length']}
Concepts    : {ms['concepts']}
Sub-parts   : {ms['sub_parts']}
Style       : {ms['style']}

BANNED PATTERNS for this mark range:
{chr(10).join(f"  ✗ {p}" for p in ms['banned_patterns'])}

GOOD QUESTION EXAMPLES for {ms['label']}:
{chr(10).join(f"  ✓ {e}" for e in ms['examples'])}
══════════════════════════════════════════════════════
{history_nudge}

STRICT RULES:
  1. Match LENGTH to mark range — see constraint block above. Non-negotiable.
  2. Match VERB to bloom level ({bloom_level}): {bloom_verb}
  3. Do NOT generate numerical/calculation problems unless teacher explicitly asked. If teacher input says to include numerical problems, you may include ONE numerical problem for appropriate mark ranges which does not require table, graph or diagram.
  4. SELF-CONTAINED — this is non-negotiable:
     The question must be fully answerable from memory alone, with NO external data.
     FORBIDDEN phrases: "for the following", "given below", "consider the following",
     "solve the following", "refer to figure/table", "from the table", "as shown",
     "the data given", "obtain solution to following", or ANY phrase implying missing input.
     If the topic normally involves a worked example (LCS, knapsack, sorting, etc.),
     ask the student to EXPLAIN the algorithm or DEMONSTRATE it with a self-chosen example.
     Example — WRONG: "Find LCS for following strings."
     Example — RIGHT: "Explain the LCS algorithm with a suitable example of your choice."
  5. Keep language natural and direct.
  6. VARIETY: Vary your opening verb. Do not start with the same word as the nudge hints above.

{_GENERATE_FEW_SHOTS}

OUTPUT: Write ONLY the question text. No preamble, no label, no explanation.
"""
    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    return str(getattr(response, "content", "") or "").strip()


def generate_new_question_with_gdt(
    topic: str,
    subtopic: str,
    module: str,
    marks: int,
    bloom_level: str,
    question_number: str,
    teacher_input: Optional[dict] = None,
    question_type: str = "short_answer",
    history: Optional[List[str]] = None,
    enriched_topic: Optional[str] = None,
) -> Tuple[str, List[dict]]:
    """
    Generate a new question with optional GDT blocks (table / plot / graph_ds).
    Only called when _needs_gdt(bloom_level, marks) is True.

    Returns:
        (question_text, gdt_blocks)
        gdt_blocks is [] when the LLM decides no visual is needed or parsing fails.
    """
    ms            = _get_marks_structure(marks)
    mark_range    = _mark_range_label(marks)
    bloom_verb    = _BLOOM_VERBS.get(bloom_level, "Ask an appropriate question.")
    display_topic = enriched_topic or (f"{topic} (focus: {subtopic})" if subtopic else topic)

    teacher_context   = _build_teacher_context(teacher_input)
    type_instructions = _question_type_instruction(question_type)
    history_nudge     = _build_soft_history_instruction(history or [])

    prompt = f"""You are a Mumbai University question paper setter specialised in numerical/applied questions.
Generate ONE exam question. You MAY include a GDT element ONLY when it is the INPUT DATA that the student must work with.

SPECIFICATION:
  Question No : {question_number}
  Module      : {module}
  Topic       : {display_topic}
  Marks       : {marks}  (mark range: {mark_range})
  Bloom Level : {bloom_level}  — {bloom_verb}
{teacher_context}
{type_instructions}

══════════════════════════════════════════════════════
MARKS CONSTRAINT — FOLLOW EXACTLY, NO EXCEPTIONS
══════════════════════════════════════════════════════
Mark range  : {ms['label']}
Answer size : {ms['answer_length']}
Question    : {ms['question_length']}
Concepts    : {ms['concepts']}
Sub-parts   : {ms['sub_parts']}
Style       : {ms['style']}
══════════════════════════════════════════════════════
{history_nudge}

══════════════════════════════════════════════════════
GDT — USE ONLY WHEN IT GENUINELY ADDS VALUE
══════════════════════════════════════════════════════
A GDT element is raw input data the question is based on — nothing more.
Ask yourself: "Does the question become clearer with this visual, or can the
data be stated naturally in a sentence?" If a sentence works, use no GDT.

GDT is appropriate when:
  - The question operates on a specific graph/tree structure (run algorithm on it)
  - The question involves multiple numeric data points that a plot makes clearer
  - The question gives a dataset that is too large or structured to state inline

GDT is NOT appropriate when:
  - The question is conceptual, comparative, or explanatory
  - The data fits naturally in one sentence of question text
  - The topic is an algorithm description or design question

Quality bar — keep it minimal and purposeful:
  - A graph for Dijkstra: provide the exact graph, no more nodes than needed
  - A table: only the columns and rows the question directly refers to
  - A plot: only the data points that define the problem

The GDT is never the answer. It is the starting material the student works with.

Type matching: if the question is about a graph algorithm (shortest path, MST, BFS,
DFS, topological sort, etc.), the GDT must be graph_ds — not a distance matrix or
adjacency table. A distance/adjacency table already encodes the answer structure;
the raw graph (nodes + weighted edges) is the correct question input.

══════════════════════════════════════════════════════

OUTPUT FORMAT — strict JSON only, no markdown, no explanation:
{{
  "question_text": "<the exam question>",
  "gdt": [
    {{
      "type": "table | plot | graph_ds",
      "content": {{ ... }}
    }}
  ]
}}

table content schema:   {{"headers": [...], "rows": [[...], ...]}}
  → Answer cells must be "" (empty string), not filled with answers.
plot content schema:    {{"x": [...], "y": [...], "xlabel": "...", "ylabel": "...", "title": "..."}}
graph_ds content schema:{{"directed": true|false, "edges": [["A","B"], ...], "edge_labels": {{"(\\"A\\",\\"B\\")": 4}}}}
"""
    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    raw = str(getattr(response, "content", "") or "").strip()

    # Strip markdown fences if present
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"\s*```$", "", clean).strip()

    try:
        data = json.loads(clean)
        q_text = str(data.get("question_text", "")).strip()
        gdt_blocks = data.get("gdt", [])
        if not isinstance(gdt_blocks, list):
            gdt_blocks = []
        if q_text:
            return q_text, gdt_blocks
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass

    # Fall back: return raw text with no GDT
    return raw, []


# ============================================================================
# PROMPT HELPERS
# ============================================================================

def _question_type_instruction(question_type: str) -> str:
    if question_type == "mcq":
        return "\nQUESTION FORMAT: MCQ — provide 4 options labeled A), B), C), D)."
    elif question_type == "true_false":
        return "\nQUESTION FORMAT: True/False question."
    elif question_type == "fill_in_the_blank":
        return "\nQUESTION FORMAT: Fill-in-the-Blanks question."
    elif question_type == "short_notes":
        return "\nQUESTION FORMAT: 'Write a short note on...' style."
    return ""

def _build_teacher_context(teacher_input: Optional[dict]) -> str:
    if not teacher_input:
        return ""
    t_text = (teacher_input.get("input") or teacher_input.get("preferences") or "").strip()
    if not t_text:
        return ""
    ctx = f"\nTeacher instructions (FOLLOW STRICTLY): {t_text}"
    t_lower = t_text.lower()
    if any(w in t_lower for w in ["easy", "simple", "basic", "introductory"]):
        ctx += "\nDifficulty: EASY — definitions and simple explanations only."
    elif any(w in t_lower for w in ["hard", "difficult", "advanced", "challenging"]):
        ctx += "\nDifficulty: HARD — multi-step reasoning or analysis required."
    if any(w in t_lower for w in ["no numerical", "avoid numerical", "no calculation"]):
        ctx += "\nIMPORTANT: Do NOT include numerical problems."
    return ctx


def _compact_question_text(text: str, marks: int) -> str:
    """
    Small safety net to keep questions concise when model output is too long.
    Keeps existing prompt-first behavior; only trims obvious overlong compounds.
    """
    if not text:
        return text

    cleaned = re.sub(r"\s+", " ", text).strip()
    words = cleaned.split()

    # Keep limits conservative to avoid over-truncation.
    max_words = 17 if marks <= 3 else 24 if marks <= 6 else 32
    if len(words) <= max_words:
        return cleaned

    cut_markers = [
        " and explain ",
        " and how ",
        " and discuss ",
        " and analyze ",
        " and compare ",
        ". ",
        "; ",
    ]
    lower = cleaned.lower()
    for marker in cut_markers:
        idx = lower.find(marker)
        if idx > 0:
            candidate = cleaned[:idx].strip(" ,;:.")
            if len(candidate.split()) >= 6:
                return candidate + "?"

    return " ".join(words[:max_words]).strip(" ,;:.") + "?"


# ============================================================================
# PYQ BANK GUARD
# ============================================================================

def _pyq_bank_available(pyq_bank: List[Dict]) -> bool:
    return bool(pyq_bank) and any(q.get("id") for q in pyq_bank)


# ============================================================================
# CORE QUESTION SELECTOR
# ============================================================================

def select_questions(
    blueprint: Dict,
    pyq_bank: List[Dict],
    teacher_input: Optional[dict] = None,
    qp_pattern: Optional[dict] = None,
    knowledge_graph: Optional[Dict] = None,        # Change #5 — new optional param
) -> Dict:
    """
    Main question selection function.

    knowledge_graph: optional — used to enrich topic context with child subtopics
    for questions with marks > 5 (Change #5).
    """

    pyq_available = _pyq_bank_available(pyq_bank)
    if not pyq_available:
        print("⚠️  PYQ bank is empty or unavailable — all questions will be generated fresh.")

    used_pyq_ids  = set()
    draft_sections = []
    selection_log  = []

    # History now stores plain question texts for the current run (Change #4)
    history: List[str] = []

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

        section_type = "short_answer"
        if qp_pattern:
            for s in qp_pattern.get("sections", []):
                if s.get("section_name") == section_name:
                    section_type = s.get("section_description") or s.get("type") or "short_answer"
                    break

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
            is_pyq      = bp_q.get("is_pyq", False) and pyq_available

            # Change #5 — enrich topic with KG children for marks > 5
            enriched_topic = _enrich_topic_with_children(
                topic, subtopic, marks, knowledge_graph or {}
            )

            print(f"\n  ▶ Q{q_num}: {topic} | {marks}M | {bloom_level} | is_pyq={is_pyq}")
            if enriched_topic != topic:
                print(f"     🌿 Enriched topic: {enriched_topic}")

            selected_text    = None
            selection_method = None
            source_pyq_id    = None
            gdt_result       = []   # GDT blocks; populated only for Apply/Analyze new-gen

            # ────────────────────────────────────────────────────────────────
            # CASE A: Generate directly
            # ────────────────────────────────────────────────────────────────
            if not is_pyq:
                if _needs_gdt(bloom_level, marks):
                    selected_text, gdt_result = generate_new_question_with_gdt(
                        topic, subtopic, module, marks, bloom_level, q_num,
                        teacher_input, section_type,
                        history=history,
                        enriched_topic=enriched_topic,
                    )
                    print(f"     → Generated with GDT ({len(gdt_result)} block(s))")
                else:
                    selected_text = generate_new_question(
                        topic, subtopic, module, marks, bloom_level, q_num,
                        teacher_input, section_type,
                        history=history,
                        enriched_topic=enriched_topic,
                    )
                    gdt_result = []
                    print(f"     → Generated directly (is_pyq=False or no PYQ bank)")
                selection_method = "generated_direct"
                stats["direct_generated"] += 1

            # ────────────────────────────────────────────────────────────────
            # CASE B: PYQ-first matching hierarchy
            # ────────────────────────────────────────────────────────────────
            else:
                match = None

                match = find_match(
                    pyq_bank, used_pyq_ids,
                    level=1, topic=topic, marks=marks, bloom_level=bloom_level
                )
                if match:
                    mid  = match.get("id", "unknown")
                    text = match.get("text", match.get("question", ""))
                    if _is_dataless(text):
                        # PYQ references external data — rephrase to make self-contained
                        print(f"     ⚠️  L1 match PYQ #{mid} is dataless → rephrasing to self-contained")
                        selected_text = rephrase_pyq(
                            text, marks, topic, bloom_level, section_type,
                            history=history,
                            enriched_topic=enriched_topic,
                        )
                        selection_method = "pyq_rephrased_marks"
                        stats["pyq_rephrased_marks"] += 1
                    else:
                        print(f"     ✅ L1 match (topic+marks+bloom) → PYQ #{mid} used as-is")
                        selected_text    = text
                        selection_method = "pyq_exact"
                        stats["pyq_exact_match"] += 1
                    source_pyq_id = mid
                    if mid != "unknown": used_pyq_ids.add(mid)

                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=2, topic=topic, bloom_level=bloom_level
                    )
                    if match:
                        mid    = match.get("id", "unknown")
                        orig_m = match.get("marks", marks)
                        text   = match.get("text", match.get("question", ""))
                        print(f"     🔄 L2 match (topic+bloom, {orig_m}M→{marks}M) → rephrasing PYQ #{mid}")
                        selected_text = rephrase_pyq(
                            text, marks, topic, bloom_level, section_type,
                            history=history,
                            enriched_topic=enriched_topic,
                        )
                        selection_method = "pyq_rephrased_marks"
                        source_pyq_id    = mid
                        if mid != "unknown": used_pyq_ids.add(mid)
                        stats["pyq_rephrased_marks"] += 1

                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=3, topic=topic
                    )
                    if match:
                        mid     = match.get("id", "unknown")
                        orig_bl = match.get("bloom_level", bloom_level)
                        text    = match.get("text", match.get("question", ""))
                        print(f"     🔄 L3 match (topic only, bloom {orig_bl}→{bloom_level}) → rephrasing PYQ #{mid}")
                        selected_text = rephrase_pyq(
                            text, marks, topic, bloom_level, section_type,
                            history=history,
                            enriched_topic=enriched_topic,
                        )
                        selection_method = "pyq_rephrased_bloom"
                        source_pyq_id    = mid
                        if mid != "unknown": used_pyq_ids.add(mid)
                        stats["pyq_rephrased_bloom"] += 1

                if not match:
                    print(f"     ⚡ No PYQ match → generating fresh question")
                    if _needs_gdt(bloom_level, marks):
                        selected_text, gdt_result = generate_new_question_with_gdt(
                            topic, subtopic, module, marks, bloom_level, q_num,
                            teacher_input, section_type,
                            history=history,
                            enriched_topic=enriched_topic,
                        )
                        print(f"     → Fallback generated with GDT ({len(gdt_result)} block(s))")
                    else:
                        selected_text = generate_new_question(
                            topic, subtopic, module, marks, bloom_level, q_num,
                            teacher_input, section_type,
                            history=history,
                            enriched_topic=enriched_topic,
                        )
                    selection_method = "generated_fallback"
                    stats["generated_new"] += 1

            # Post-selection dataless guard — catches cases where rephrase/generate
            # still output a dataless question despite the instruction.
            if selected_text and _is_dataless(selected_text):
                print(f"     ⚠️  Output is still dataless after selection → regenerating fresh")
                if _needs_gdt(bloom_level, marks):
                    selected_text, gdt_result = generate_new_question_with_gdt(
                        topic, subtopic, module, marks, bloom_level, q_num,
                        teacher_input, section_type,
                        history=history,
                        enriched_topic=enriched_topic,
                    )
                else:
                    selected_text = generate_new_question(
                        topic, subtopic, module, marks, bloom_level, q_num,
                        teacher_input, section_type,
                        history=history,
                        enriched_topic=enriched_topic,
                    )
                    gdt_result = []
                selection_method = (selection_method or "generated_direct") + "_regen"

            # Append question text to the in-run history list (Change #4)
            if selected_text:
                selected_text = _compact_question_text(selected_text, marks)
                history.append(selected_text)

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
                "gdt":              gdt_result,
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
        "question_history":   history,
    }

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
    if total:
        print(f"  PYQ Utilization       : {pyq_hits}/{total} ({pyq_hits/total*100:.0f}%)")
    if not pyq_available:
        print("  ⚠️  PYQ bank was empty — all questions generated fresh")
    print("=" * 70)

    return draft_paper


# ============================================================================
# PRINT HELPER
# ============================================================================

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