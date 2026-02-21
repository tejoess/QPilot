"""
Question Selector Agent - Algorithmic Version
Selects questions based on blueprint using PYQ-first strategy with fallback generation.

Logic Flow per blueprint question:
1. If blueprint is_pyq=False → Generate directly (skip PYQ search)
2. If blueprint is_pyq=True:
   a. Try: topic + subtopic + marks + bloom_level  → use PYQ as-is
   b. Try: topic + subtopic + bloom_level (drop marks) → rephrase PYQ for target marks
   c. Try: topic + subtopic only (drop bloom)       → rephrase PYQ for target marks
   d. Fallback: Generate new question with all params
"""

import json
import uuid
import re
from typing import Dict, List, Optional, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


# ============================================================================
# CORE MATCHING HELPERS
# ============================================================================

def normalize(text: str) -> str:
    """Lowercase and strip for comparison."""
    return text.lower().strip()


def match_level_1(pyq: Dict, topic: str, subtopic: str, marks: int, bloom_level: str) -> bool:
    """Exact match: topic + subtopic + marks + bloom_level"""
    return (
        normalize(pyq.get("topic", "")) == normalize(topic)
        and normalize(pyq.get("subtopic", "")) == normalize(subtopic)
        and pyq.get("marks") == marks
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_2(pyq: Dict, topic: str, subtopic: str, bloom_level: str) -> bool:
    """Drop marks: topic + subtopic + bloom_level"""
    return (
        normalize(pyq.get("topic", "")) == normalize(topic)
        and normalize(pyq.get("subtopic", "")) == normalize(subtopic)
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_3(pyq: Dict, topic: str, subtopic: str) -> bool:
    """Drop marks + bloom: topic + subtopic only"""
    return (
        normalize(pyq.get("topic", "")) == normalize(topic)
        and normalize(pyq.get("subtopic", "")) == normalize(subtopic)
    )


def find_match(pyq_bank: List[Dict], used_pyq_ids: set, **criteria) -> Optional[Dict]:
    """
    Search PYQ bank with given criteria, skipping already-used PYQs.
    criteria keys: topic, subtopic, marks (optional), bloom_level (optional)
    """
    level = criteria.get("level", 1)
    topic = criteria["topic"]
    subtopic = criteria["subtopic"]
    marks = criteria.get("marks")
    bloom_level = criteria.get("bloom_level")

    for pyq in pyq_bank:
        if pyq["id"] in used_pyq_ids:
            continue
        if level == 1 and match_level_1(pyq, topic, subtopic, marks, bloom_level):
            return pyq
        elif level == 2 and match_level_2(pyq, topic, subtopic, bloom_level):
            return pyq
        elif level == 3 and match_level_3(pyq, topic, subtopic):
            return pyq
    return None


# ============================================================================
# LLM CALLS
# ============================================================================

def rephrase_pyq(pyq_text: str, target_marks: int, topic: str, bloom_level: str) -> str:
    """
    Rephrase a PYQ to fit target marks. Small, focused prompt.
    """
    prompt = f"""Rephrase this exam question to suit {target_marks} marks ({bloom_level} level).
Topic: {topic}

Original: {pyq_text}

Rules:
- Keep the same concept
- Adjust scope/depth for {target_marks} marks
- Output ONLY the rephrased question, no explanation

Rephrased question:"""

    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    return response.content.strip()


def generate_new_question(
    topic: str,
    subtopic: str,
    module: str,
    marks: int,
    bloom_level: str,
    question_number: str
) -> str:
    """
    Generate a brand-new question. Medium-sized, structured prompt.
    """
    bloom_guidance = {
        "Remember": "Ask to define, list, state, name, or recall facts.",
        "Understand": "Ask to explain, describe, summarize, or classify concepts.",
        "Apply": "Ask to solve a problem, use a method, demonstrate, or compute.",
        "Analyze": "Ask to compare, differentiate, break down, or examine relationships.",
        "Evaluate": "Ask to critique, justify, assess, or argue for/against.",
        "Create": "Ask to design, formulate, construct, or propose something new."
    }

    guidance = bloom_guidance.get(bloom_level, "Ask an appropriate question.")

    prompt = f"""Generate a university exam question for the following specifications:

Module: {module}
Topic: {topic}
Subtopic: {subtopic}
Marks: {marks}
Bloom's Level: {bloom_level}
Guidance: {guidance}

Requirements:
- Question must be clear and unambiguous
- Appropriate difficulty for {marks} marks at {bloom_level} level
- Relevant to the subtopic
- For numerical/application questions, include necessary data/context

Output ONLY the question text, nothing else:"""

    msg = HumanMessage(content=prompt)
    response = llm.invoke([msg])
    return response.content.strip()


# ============================================================================
# CORE QUESTION SELECTOR
# ============================================================================

def select_questions(
    blueprint: Dict,
    pyq_bank: List[Dict]
) -> Dict:
    """
    Main question selection function.
    
    Args:
        blueprint: Generated blueprint with sections and questions
        pyq_bank: List of available PYQs with fields:
                  {id, text, topic, subtopic, marks, bloom_level, year, module}
    
    Returns:
        Draft question paper with sections, questions, and selection metadata
    """
    
    used_pyq_ids = set()
    draft_sections = []
    selection_log = []
    
    stats = {
        "total_questions": 0,
        "pyq_exact_match": 0,
        "pyq_rephrased_marks": 0,
        "pyq_rephrased_bloom": 0,
        "generated_new": 0,
        "direct_generated": 0   # is_pyq=False from blueprint
    }

    print("\n" + "="*70)
    print("🔍 QUESTION SELECTION - ALGORITHMIC PYQ-FIRST STRATEGY")
    print("="*70)

    for section in blueprint.get("sections", []):
        section_name = section["section_name"]
        section_desc = section.get("section_description", "")
        print(f"\n📂 {section_name} - {section_desc}")
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
            is_pyq      = bp_q.get("is_pyq", False)

            print(f"\n  ▶ Q{q_num}: {topic}/{subtopic} | {marks}M | {bloom_level} | is_pyq={is_pyq}")

            selected_text = None
            selection_method = None
            source_pyq_id = None

            # ----------------------------------------------------------------
            # CASE A: Blueprint says NOT a PYQ → Generate directly
            # ----------------------------------------------------------------
            if not is_pyq:
                print(f"     → Blueprint is_pyq=False → Generating new question")
                selected_text = generate_new_question(
                    topic=topic, subtopic=subtopic, module=module,
                    marks=marks, bloom_level=bloom_level, question_number=q_num
                )
                selection_method = "generated_direct"
                stats["direct_generated"] += 1

            # ----------------------------------------------------------------
            # CASE B: Blueprint says IS a PYQ → Apply matching hierarchy
            # ----------------------------------------------------------------
            else:
                # Level 1: topic + subtopic + marks + bloom_level (exact)
                match = find_match(
                    pyq_bank, used_pyq_ids,
                    level=1, topic=topic, subtopic=subtopic,
                    marks=marks, bloom_level=bloom_level
                )
                if match:
                    print(f"     ✅ Level 1 match (exact) → PYQ #{match['id']} used as-is")
                    selected_text = match["text"]
                    selection_method = "pyq_exact"
                    source_pyq_id = match["id"]
                    used_pyq_ids.add(match["id"])
                    stats["pyq_exact_match"] += 1

                else:
                    # Level 2: topic + subtopic + bloom_level (drop marks)
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=2, topic=topic, subtopic=subtopic,
                        bloom_level=bloom_level
                    )
                    if match:
                        print(f"     🔄 Level 2 match (drop marks) → Rephrasing PYQ #{match['id']} for {marks}M")
                        selected_text = rephrase_pyq(
                            pyq_text=match["text"],
                            target_marks=marks,
                            topic=topic,
                            bloom_level=bloom_level
                        )
                        selection_method = "pyq_rephrased_marks"
                        source_pyq_id = match["id"]
                        used_pyq_ids.add(match["id"])
                        stats["pyq_rephrased_marks"] += 1

                    else:
                        # Level 3: topic + subtopic only (drop marks + bloom)
                        match = find_match(
                            pyq_bank, used_pyq_ids,
                            level=3, topic=topic, subtopic=subtopic
                        )
                        if match:
                            print(f"     🔄 Level 3 match (subtopic only) → Rephrasing PYQ #{match['id']} for {marks}M/{bloom_level}")
                            selected_text = rephrase_pyq(
                                pyq_text=match["text"],
                                target_marks=marks,
                                topic=topic,
                                bloom_level=bloom_level
                            )
                            selection_method = "pyq_rephrased_bloom"
                            source_pyq_id = match["id"]
                            used_pyq_ids.add(match["id"])
                            stats["pyq_rephrased_bloom"] += 1

                        else:
                            # Fallback: Generate new (no PYQ found despite is_pyq=True)
                            print(f"     ⚡ No PYQ match found → Generating new question")
                            selected_text = generate_new_question(
                                topic=topic, subtopic=subtopic, module=module,
                                marks=marks, bloom_level=bloom_level, question_number=q_num
                            )
                            selection_method = "generated_fallback"
                            stats["generated_new"] += 1

            # Build draft question entry
            draft_q = {
                "id": str(uuid.uuid4())[:8],
                "question_number": q_num,
                "module": module,
                "topic": topic,
                "subtopic": subtopic,
                "marks": marks,
                "bloom_level": bloom_level,
                "question_text": selected_text,
                "selection_method": selection_method,
                "source_pyq_id": source_pyq_id,
                "is_pyq_sourced": source_pyq_id is not None
            }
            draft_questions.append(draft_q)

            log_entry = {
                "question_number": q_num,
                "method": selection_method,
                "pyq_id": source_pyq_id
            }
            selection_log.append(log_entry)

            print(f"     📝 Method: {selection_method}")

        draft_sections.append({
            "section_name": section_name,
            "section_description": section_desc,
            "questions": draft_questions
        })

    # Build final draft paper
    draft_paper = {
        "paper_id": str(uuid.uuid4())[:12],
        "blueprint_metadata": blueprint.get("blueprint_metadata", {}),
        "sections": draft_sections,
        "selection_stats": stats,
        "selection_log": selection_log,
        "used_pyq_ids": list(used_pyq_ids)
    }

    # Print summary
    print("\n" + "="*70)
    print("📊 SELECTION SUMMARY")
    print("="*70)
    print(f"  Total Questions       : {stats['total_questions']}")
    print(f"  PYQ Exact Match       : {stats['pyq_exact_match']}")
    print(f"  PYQ Rephrased (marks) : {stats['pyq_rephrased_marks']}")
    print(f"  PYQ Rephrased (bloom) : {stats['pyq_rephrased_bloom']}")
    print(f"  Generated (fallback)  : {stats['generated_new']}")
    print(f"  Generated (direct)    : {stats['direct_generated']}")
    print(f"  PYQs Used             : {len(used_pyq_ids)}")
    print("="*70)

    return draft_paper


def print_draft_paper(draft_paper: Dict):
    """Pretty print the drafted question paper."""
    print("\n" + "="*80)
    print("📄 DRAFTED QUESTION PAPER")
    print("="*80)

    METHOD_LABELS = {
        "pyq_exact":            "📌 PYQ (exact)",
        "pyq_rephrased_marks":  "🔄 PYQ (rephrased for marks)",
        "pyq_rephrased_bloom":  "🔄 PYQ (rephrased for bloom)",
        "generated_fallback":   "✨ Generated (fallback)",
        "generated_direct":     "✨ Generated (direct)"
    }

    for section in draft_paper["sections"]:
        print(f"\n{'─'*80}")
        print(f"  {section['section_name']} — {section['section_description']}")
        print(f"{'─'*80}")
        for q in section["questions"]:
            method_label = METHOD_LABELS.get(q["selection_method"], q["selection_method"])
            print(f"\n  Q{q['question_number']}  [{q['marks']} marks | {q['bloom_level']} | {q['module']}]")
            print(f"  Topic: {q['topic']} → {q['subtopic']}")
            print(f"  Source: {method_label}", end="")
            if q["source_pyq_id"]:
                print(f" (PYQ ID: {q['source_pyq_id']})", end="")
            print()
            print(f"\n  {q['question_text']}")

    print("\n" + "="*80)
    stats = draft_paper["selection_stats"]
    total = stats["total_questions"]
    pyq_total = stats["pyq_exact_match"] + stats["pyq_rephrased_marks"] + stats["pyq_rephrased_bloom"]
    print(f"  PYQ utilization: {pyq_total}/{total} questions ({pyq_total/total*100:.0f}%)")
    print("="*80)


# ============================================================================
# SAMPLE TEST DATA
# ============================================================================

SAMPLE_PYQ_BANK = [
    {
        "id": "pyq_001",
        "text": "Define the concept of normalization and explain why it is important in database design.",
        "topic": "Normalization",
        "subtopic": "Normal Forms",
        "module": "Module 3",
        "marks": 5,
        "bloom_level": "Remember",
        "year": 2022
    },
    {
        "id": "pyq_002",
        "text": "Explain the difference between 2NF and 3NF with suitable examples.",
        "topic": "Normalization",
        "subtopic": "Normal Forms",
        "module": "Module 3",
        "marks": 10,
        "bloom_level": "Understand",
        "year": 2023
    },
    {
        "id": "pyq_003",
        "text": "Normalize the given relation to BCNF: R(A, B, C, D) with FDs: A→B, B→C, C→D.",
        "topic": "Normalization",
        "subtopic": "Normal Forms",
        "module": "Module 3",
        "marks": 15,
        "bloom_level": "Apply",
        "year": 2021
    },
    {
        "id": "pyq_004",
        "text": "What are functional dependencies? State Armstrong's axioms.",
        "topic": "Functional Dependencies",
        "subtopic": "FD Rules",
        "module": "Module 3",
        "marks": 5,
        "bloom_level": "Remember",
        "year": 2023
    },
    {
        "id": "pyq_005",
        "text": "Explain the ACID properties of transactions with examples.",
        "topic": "Transactions",
        "subtopic": "ACID Properties",
        "module": "Module 4",
        "marks": 5,
        "bloom_level": "Understand",
        "year": 2022
    },
    {
        "id": "pyq_006",
        "text": "Describe the different states of a transaction and draw the transaction state diagram.",
        "topic": "Transactions",
        "subtopic": "Transaction States",
        "module": "Module 4",
        "marks": 10,
        "bloom_level": "Understand",
        "year": 2023
    },
    {
        "id": "pyq_007",
        "text": "Explain two-phase locking protocol and prove that it ensures serializability.",
        "topic": "Concurrency Control",
        "subtopic": "Locking",
        "module": "Module 4",
        "marks": 15,
        "bloom_level": "Analyze",
        "year": 2021
    },
    {
        "id": "pyq_008",
        "text": "What is an ER diagram? Explain its components with examples.",
        "topic": "ER Modeling",
        "subtopic": "ER Diagrams",
        "module": "Module 1",
        "marks": 5,
        "bloom_level": "Remember",
        "year": 2022
    },
    {
        "id": "pyq_009",
        "text": "Draw an ER diagram for a library management system.",
        "topic": "ER Modeling",
        "subtopic": "ER Diagrams",
        "module": "Module 1",
        "marks": 15,
        "bloom_level": "Apply",
        "year": 2023
    },
    {
        "id": "pyq_010",
        "text": "Explain the different types of joins in SQL with examples.",
        "topic": "SQL",
        "subtopic": "Joins",
        "module": "Module 2",
        "marks": 10,
        "bloom_level": "Understand",
        "year": 2022
    },
    {
        "id": "pyq_011",
        "text": "Write SQL queries to: (a) Find all employees earning more than 50000, (b) List departments with more than 5 employees.",
        "topic": "SQL",
        "subtopic": "Queries",
        "module": "Module 2",
        "marks": 10,
        "bloom_level": "Apply",
        "year": 2023
    },
    {
        "id": "pyq_012",
        "text": "Explain relational algebra operations: Selection, Projection, and Join with examples.",
        "topic": "Relational Algebra",
        "subtopic": "Joins",
        "module": "Module 2",
        "marks": 15,
        "bloom_level": "Understand",
        "year": 2021
    }
]


SAMPLE_BLUEPRINT = {
    "blueprint_metadata": {
        "total_marks": 80,
        "total_questions": 8,
        "bloom_distribution": {
            "Remember": 0.125,
            "Understand": 0.25,
            "Apply": 0.35,
            "Analyze": 0.20,
            "Evaluate": 0.05,
            "Create": 0.025
        },
        "module_distribution": {
            "Module 1": 0.25,
            "Module 2": 0.25,
            "Module 3": 0.25,
            "Module 4": 0.25
        },
        "pyq_usage": {
            "actual_pyq_count": 5,
            "new_question_count": 3,
            "pyq_percentage": 0.625
        }
    },
    "sections": [
        {
            "section_name": "Section A",
            "section_description": "Short Answer Questions",
            "questions": [
                {
                    # Case: is_pyq=True, exact match exists (pyq_008)
                    "question_number": "1",
                    "module": "Module 1",
                    "topic": "ER Modeling",
                    "subtopic": "ER Diagrams",
                    "marks": 5,
                    "bloom_level": "Remember",
                    "is_pyq": True,
                    "rationale": "High PYQ availability"
                },
                {
                    # Case: is_pyq=True, marks mismatch → Level 2 match → rephrase (pyq_005 matches topic+subtopic+bloom but 5M)
                    "question_number": "2",
                    "module": "Module 4",
                    "topic": "Transactions",
                    "subtopic": "ACID Properties",
                    "marks": 10,
                    "bloom_level": "Understand",
                    "is_pyq": True,
                    "rationale": "PYQ available, adjust marks"
                },
                {
                    # Case: is_pyq=True, no exact or L2 match but L3 (subtopic) match exists → rephrase
                    "question_number": "3",
                    "module": "Module 3",
                    "topic": "Functional Dependencies",
                    "subtopic": "FD Rules",
                    "marks": 5,
                    "bloom_level": "Apply",   # pyq_004 is Remember → L3 match
                    "is_pyq": True,
                    "rationale": "Subtopic match found"
                },
                {
                    # Case: is_pyq=False → Generate directly
                    "question_number": "4",
                    "module": "Module 2",
                    "topic": "SQL",
                    "subtopic": "DDL",
                    "marks": 5,
                    "bloom_level": "Remember",
                    "is_pyq": False,
                    "rationale": "No PYQ available for DDL"
                }
            ]
        },
        {
            "section_name": "Section B",
            "section_description": "Long Answer Questions",
            "questions": [
                {
                    # Case: is_pyq=True, exact match (pyq_009)
                    "question_number": "5",
                    "module": "Module 1",
                    "topic": "ER Modeling",
                    "subtopic": "ER Diagrams",
                    "marks": 15,
                    "bloom_level": "Apply",
                    "is_pyq": True,
                    "rationale": "High PYQ availability"
                },
                {
                    # Case: is_pyq=True, exact match (pyq_012)
                    "question_number": "6",
                    "module": "Module 2",
                    "topic": "Relational Algebra",
                    "subtopic": "Joins",
                    "marks": 15,
                    "bloom_level": "Understand",
                    "is_pyq": True,
                    "rationale": "Good PYQ available"
                },
                {
                    # Case: is_pyq=True, exact match (pyq_003)
                    "question_number": "7",
                    "module": "Module 3",
                    "topic": "Normalization",
                    "subtopic": "Normal Forms",
                    "marks": 15,
                    "bloom_level": "Apply",
                    "is_pyq": True,
                    "rationale": "PYQ with numerical problem"
                },
                {
                    # Case: is_pyq=False → Generate a new analysis question
                    "question_number": "8",
                    "module": "Module 4",
                    "topic": "Concurrency Control",
                    "subtopic": "Deadlock",
                    "marks": 15,
                    "bloom_level": "Analyze",
                    "is_pyq": False,
                    "rationale": "No good PYQ for deadlock analysis"
                }
            ]
        }
    ],
    "strategy_notes": "Balanced coverage with PYQ preference for Modules 1-3, fresh questions for edge cases."
}


# ============================================================================
# TEST EXECUTION
# ============================================================================

# if __name__ == "__main__":
#     print("🚀 QUESTION SELECTOR AGENT — TEST RUN")
#     print("="*70)
#     print(f"PYQ Bank size  : {len(SAMPLE_PYQ_BANK)} questions")
#     print(f"Blueprint qs   : {sum(len(s['questions']) for s in SAMPLE_BLUEPRINT['sections'])}")
#     print(f"Total marks    : {SAMPLE_BLUEPRINT['blueprint_metadata']['total_marks']}")
#     print("="*70)

#     try:
#         draft_paper = select_questions(
#             blueprint=SAMPLE_BLUEPRINT,
#             pyq_bank=SAMPLE_PYQ_BANK
#         )

#         # Pretty-print results
#         print_draft_paper(draft_paper)

#         # Save to file
#         output_file = "drafted_question_paper.json"
#         with open(output_file, "w") as f:
#             json.dump(draft_paper, f, indent=2)
#         print(f"\n✅ Draft paper saved to: {output_file}")

#     except Exception as e:
#         print(f"\n❌ ERROR: {e}")
#         import traceback
#         traceback.print_exc()