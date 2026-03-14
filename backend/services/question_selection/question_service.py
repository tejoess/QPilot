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


def match_level_1(pyq: Dict, topic: str, marks: int, bloom_level: str) -> bool:
    """Exact match: topic + marks + bloom_level (ignore subtopic)"""
    # Match blueprint topic against PYQ subtopic (common case) or topic
    topic_match = (
        normalize(pyq.get("subtopic", "")) == normalize(topic) or
        normalize(pyq.get("topic", "")) == normalize(topic)
    )
    return (
        topic_match
        and pyq.get("marks") == marks
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_2(pyq: Dict, topic: str, bloom_level: str) -> bool:
    """Drop marks: topic + bloom_level only (ignore subtopic)"""
    topic_match = (
        normalize(pyq.get("subtopic", "")) == normalize(topic) or
        normalize(pyq.get("topic", "")) == normalize(topic)
    )
    return (
        topic_match
        and normalize(pyq.get("bloom_level", "")) == normalize(bloom_level)
    )


def match_level_3(pyq: Dict, topic: str) -> bool:
    """Drop marks + bloom: topic only (ignore subtopic)"""
    return (
        normalize(pyq.get("subtopic", "")) == normalize(topic) or
        normalize(pyq.get("topic", "")) == normalize(topic)
    )


def find_match(pyq_bank: List[Dict], used_pyq_ids: set, **criteria) -> Optional[Dict]:
    """
    Search PYQ bank with given criteria, skipping already-used PYQs.
    criteria keys: topic, subtopic, marks (optional), bloom_level (optional)
    """
    level = criteria.get("level", 1)
    topic = criteria["topic"]
    marks = criteria.get("marks")
    bloom_level = criteria.get("bloom_level")

    for pyq in pyq_bank:
        # Safety check: skip if PYQ doesn't have an id
        pyq_id = pyq.get("id")
        if not pyq_id:
            continue
        if pyq_id in used_pyq_ids:
            continue
        if level == 1 and match_level_1(pyq, topic, marks, bloom_level):
            return pyq
        elif level == 2 and match_level_2(pyq, topic, bloom_level):
            return pyq
        elif level == 3 and match_level_3(pyq, topic):
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
                # Level 1: topic + marks + bloom_level (exact)
                match = find_match(
                    pyq_bank, used_pyq_ids,
                    level=1, topic=topic, marks=marks, bloom_level=bloom_level
                )
                if match:
                    match_id = match.get("id", "unknown")
                    match_text = match.get("text", match.get("question", ""))
                    print(f"     ✅ Level 1 match (exact) → PYQ #{match_id} used as-is")
                    selected_text = match_text
                    selection_method = "pyq_exact"
                    source_pyq_id = match_id
                    if match_id != "unknown":
                        used_pyq_ids.add(match_id)
                    stats["pyq_exact_match"] += 1

                # Level 2: topic + bloom_level (drop marks)
                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=2, topic=topic, bloom_level=bloom_level
                    )
                    if match:
                        match_id = match.get("id", "unknown")
                        orig_marks = match.get("marks", marks)
                        match_text = match.get("text", match.get("question", ""))
                        print(f"     🔄 Level 2 match (drop marks: {orig_marks}M→{marks}M) → Rephrasing PYQ #{match_id}")
                        selected_text = rephrase_pyq(match_text, marks, topic, bloom_level)
                        selection_method = "pyq_rephrased_marks"
                        source_pyq_id = match_id
                        if match_id != "unknown":
                            used_pyq_ids.add(match_id)
                        stats["pyq_rephrased_marks"] += 1

                # Level 3: topic only (drop marks + bloom)
                if not match:
                    match = find_match(
                        pyq_bank, used_pyq_ids,
                        level=3, topic=topic
                    )
                    if match:
                        match_id = match.get("id", "unknown")
                        orig_bloom = match.get("bloom_level", bloom_level)
                        match_text = match.get("text", match.get("question", ""))
                        print(f"     🔄 Level 3 match (bloom: {orig_bloom}→{bloom_level}) → Rephrasing PYQ #{match_id}")
                        selected_text = rephrase_pyq(match_text, marks, topic, bloom_level)
                        selection_method = "pyq_rephrased_bloom"
                        source_pyq_id = match_id
                        if match_id != "unknown":
                            used_pyq_ids.add(match_id)
                        stats["pyq_rephrased_bloom"] += 1

                # Fallback: Generate new question if no PYQ match
                if not match:
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
        "question": "Design AND gate using Perceptron.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Multilayer Perceptrons (MLPs)",
        "marks": 2,
        "bloom_level": "Apply"
    },
    {
        "id": "pyq_002",
        "question": "Suppose we have input-output pairs. Our goal is to find parameters that predict the output from the input according to. Calculate the sum-of-squared error function. Derive the gradient descent update rule.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Loss functions: Squared Error loss",
        "marks": 10,
        "bloom_level": "Apply"
    },
    {
        "id": "pyq_003",
        "question": "Explain dropout. How does it solve the problem of overfitting?",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Regularization Methods: Dropout",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_004",
        "question": "Explain denoising autoencoder model.",
        "topic": "Autoencoders: Unsupervised Learning",
        "subtopic": "Denoising Autoencoders",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_005",
        "question": "Describe sequence learning problem.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Sequence Learning Problem",
        "marks": 2,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_006",
        "question": "Explain Gated Recurrent Unit (GRU) in detail.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Long Short Term Memory(LSTM): Gated Recurrent Unit (GRU)",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_007",
        "question": "What is an activation function? Describe any four activation functions.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Activation functions",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_008",
        "question": "Explain CNN architecture in detail. Calculate parameters for a layer with input, ten filters, stride 1, and pad 2.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "CNN architecture",
        "marks": 10,
        "bloom_level": "Apply"
    },
    {
        "id": "pyq_009",
        "question": "Explain early stopping, batch normalization, and data augmentation.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Regularization Methods: Early stopping, Batch normalization",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_010",
        "question": "Explain RNN architecture in detail.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Recurrent Neural Network",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_011",
        "question": "Explain the working of Generative Adversarial Network (GAN).",
        "topic": "Recent Trends and Applications",
        "subtopic": "Generative Adversarial Network (GAN): Architecture",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_012",
        "question": "Explain Stochastic Gradient Descent and momentum-based gradient descent optimization techniques.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Optimization Learning with backpropagation",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_013",
        "question": "Explain LSTM architecture.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_014",
        "question": "Describe LeNet architecture.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "Modern Deep Learning Architectures: LeNET: Architecture",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_015",
        "question": "Explain vanishing and exploding gradient in RNNs.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Limitation of 'vanilla RNN' Vanishing and Exploding Gradients",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_016",
        "question": "Comment on the Representation Power of MLPs.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Representation Power of MLPs",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_017",
        "question": "Explain Gradient Descent in Deep Learning.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Learning Parameters: Gradient Descent (GD)",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_018",
        "question": "Explain the dropout method and its advantages.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Regularization Methods: Dropout",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_019",
        "question": "What are Denoising Autoencoders?",
        "topic": "Autoencoders: Unsupervised Learning",
        "subtopic": "Denoising Autoencoders",
        "marks": 2,
        "bloom_level": "Remember"
    },
    {
        "id": "pyq_020",
        "question": "Explain Pooling operation in CNN.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "Pooling Layer",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_021",
        "question": "What are the Three Classes of Deep Learning? Explain each.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Deep Networks: Three Classes of Deep Learning",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_022",
        "question": "Explain and analyze the architectural components of AlexNet CNN.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "Modern Deep Learning Architectures: AlexNET: Architecture",
        "marks": 10,
        "bloom_level": "Analyze"
    },
    {
        "id": "pyq_023",
        "question": "What are the different types of Gradient Descent methods? Explain any three.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Learning Parameters: Gradient Descent (GD)",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_024",
        "question": "Differentiate between the architecture of LSTM and GRU networks.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget, Gated Recurrent Unit (GRU)",
        "marks": 5,
        "bloom_level": "Analyze"
    },
    {
        "id": "pyq_025",
        "question": "Explain the key components of an RNN.",
        "topic": "Recurrent Neural Networks (RNN)",
        "subtopic": "Recurrent Neural Network",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_026",
        "question": "Calculate the total number of parameters in a CNN layer: Input 32 channels, 64 filters, stride 1, no padding.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "CNN architecture",
        "marks": 10,
        "bloom_level": "Apply"
    },
    {
        "id": "pyq_027",
        "question": "Comment on the significance of Loss functions and explain different types.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Loss functions",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_028",
        "question": "Explain any three types of Autoencoders.",
        "topic": "Autoencoders: Unsupervised Learning",
        "subtopic": "Application of Autoencoders",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_029",
        "question": "What is the significance of Activation Functions? Explain types used in NN.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Activation functions",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_030",
        "question": "Explain GAN architecture and its applications.",
        "topic": "Recent Trends and Applications",
        "subtopic": "Generative Adversarial Network (GAN): Architecture, Applications",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_031",
        "question": "Explain basic architecture of feedforward neural network.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Feedforward Neural Networks",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_032",
        "question": "Explain regularization in neural network.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Regularization Overview of Overfitting",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_033",
        "question": "Explain types of neural network.",
        "topic": "Fundamentals of Neural Network",
        "subtopic": "Types of Neural Networks",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_034",
        "question": "Explain the concept of overfitting and under fitting.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Overview of Overfitting",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_035",
        "question": "Explain basic working of CNN.",
        "topic": "Convolutional Neural Networks (CNN)",
        "subtopic": "CNN architecture",
        "marks": 5,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_036",
        "question": "Explain the gradient descent algorithm and discuss types in detail.",
        "topic": "Training, Optimization and Regularization of Deep Neural Network",
        "subtopic": "Learning Parameters: Gradient Descent (GD)",
        "marks": 10,
        "bloom_level": "Understand"
    },
    {
        "id": "pyq_037",
        "question": "Explain the working and types of autoencoders in detail.",
        "topic": "Autoencoders: Unsupervised Learning",
        "subtopic": "Application of Autoencoders",
        "marks": 10,
        "bloom_level": "Understand"
    }
]


SAMPLE_BLUEPRINT = {
  "blueprint_metadata": {
    "total_marks": 80,
    "total_questions": 8,
    "bloom_distribution": {
      "Remember": 0.15,
      "Understand": 0.25,
      "Apply": 0.3,
      "Analyze": 0.2,
      "Evaluate": 0.07,
      "Create": 0.03
    },
    "module_distribution": {
      "Module 1": 0.25,
      "Module 2": 0.3,
      "Module 3": 0.2,
      "Module 4": 0.1,
      "Module 5": 0.1,
      "Module 6": 0.0
    },
    "pyq_usage": {
      "actual_pyq_count": 5,
      "new_question_count": 3,
      "pyq_percentage": 62.5
    }
  },
  "sections": [
    {
      "section_name": "Section A",
      "section_description": "Short Answer Questions",
      "questions": [
        {
          "question_number": "1a",
          "module": "Module 1",
          "topic": "History of Deep Learning",
          "marks": 5,
          "bloom_level": "Remember",
          "is_pyq": True,
          "rationale": "High PYQ availability"
        },
        {
          "question_number": "1b",
          "module": "Module 2",
          "topic": "Fundamentals of Neural Network",
          "marks": 5,
          "bloom_level": "Understand",
          "is_pyq": True,
          "rationale": "High PYQ availability"
        },
        {
          "question_number": "1c",
          "module": "Module 3",
          "topic": "Denoising Autoencoders",
          "marks": 5,
          "bloom_level": "Remember",
          "is_pyq": True,
          "rationale": "New question generated"
        },
        {
          "question_number": "1d",
          "module": "Module 4",
          "topic": "CNN architecture",
          "marks": 5,
          "bloom_level": "Understand",
          "is_pyq": False,
          "rationale": "New question generated"
        }
      ]
    },
    {
      "section_name": "Section B",
      "section_description": "Long Answer Questions",
      "questions": [
        {
          "question_number": "2a",
          "module": "Module 2",
          "topic": "Regularization Methods",
          "marks": 15,
          "bloom_level": "Apply",
          "is_pyq": True,
          "rationale": "High PYQ availability"
        },
        {
          "question_number": "2b",
          "module": "Module 3",
          "topic": "Applications of Autoencoders",
          "marks": 15,
          "bloom_level": "Analyze",
          "is_pyq": False,
          "rationale": "New question generated"
        },
        {
          "question_number": "2c",
          "module": "Module 5",
          "topic": "Long Short Term Memory (LSTM)",
          "marks": 20,
          "bloom_level": "Evaluate",
          "is_pyq": True,
          "rationale": "High PYQ availability"
        },
        {
          "question_number": "2d",
          "module": "Module 2",
          "topic": "Choosing output function and loss function",
          "marks": 15,
          "bloom_level": "Apply",
          "is_pyq": True,
          "rationale": "High PYQ availability"
        }
      ]
    }
  ],
  "strategy_notes": "Balanced focus on Modules 2 and 3, with PYQs prioritized."
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