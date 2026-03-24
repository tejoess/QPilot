# app/services/pyq_service.py

import json
import os
from typing import Dict, Any, Optional
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from backend.services.schemas.llm_schemas import PYQOutput


def format_pyqs(
    pyq_text: str = "",
    knowledge_graph_json: Optional[Dict[str, Any]] = None,
    syllabus_json: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Takes raw PYQ text + knowledge graph JSON and extracts questions in a single pass (no chunking).
    When knowledge_graph_json is provided, `topic` is forced strictly from KG labels (either Topic_Name or any Subtopics entry).
    When it is not provided, it falls back to the older syllabus-constrained mapping.
    Uses Pydantic Output Parser for strict JSON enforcement.
    """

    print("\n🛠️  [GRAPH NODE] Formatting PYQ JSON (KnowledgeGraph-Constrained Mode)...")

    if not pyq_text:
        return json.dumps({"error": "No PYQ text available."})

    # Backward compatible: if KG not provided, fall back to syllabus mode.
    use_kg = bool(knowledge_graph_json)
    if use_kg:
        if not isinstance(knowledge_graph_json, dict):
            return json.dumps({"error": "knowledge_graph_json must be a dict."})
    else:
        if not syllabus_json:
            return json.dumps({"error": "knowledge_graph_json not provided and syllabus_json is empty."})

    # Create output parser
    parser = PydanticOutputParser(pydantic_object=PYQOutput)
    format_instructions = parser.get_format_instructions()

    syllabus_text = json.dumps(syllabus_json or {}, indent=2)
    knowledge_graph_text = json.dumps(knowledge_graph_json or {}, indent=2)

    extraction_source_line = (
        "from the provided Knowledge Graph"
        if use_kg
        else "from the provided syllabus"
    )

    if use_kg:
        topic_mapping_rules = """3. Topic Mapping (Knowledge Graph constrained):
   - Set `topic` to EXACTLY ONE label taken from the knowledge graph:
       a) either the KG `Topic_Name`
       b) or one of the KG `Subtopics` entries
   - Do NOT paraphrase, rename, infer, generalize, or create new labels.
   - Set `subtopic` to an empty string: "" (PYQs keep only a single topic label).
   - If a match is unclear, choose the closest exact KG label."""
    else:
        topic_mapping_rules = """3. Topic & Subtopic Mapping:
   - Topics/Subtopics must be mapped strictly from the provided syllabus.
   - topics/subtopic which you will label should be strictly from syllabus as it is, no change.
   - Do NOT paraphrase, rename, infer, generalize, or create new labels.
   - If a match is unclear, choose the closest exact syllabus entry."""

    prompt = f"""
You are an expert academic exam extraction system.

Your job:
Extract ONLY valid academic questions from PYQ text and label them {extraction_source_line}.

STRICT RULES:

1. Question Text:
   - Extract FULL, COMPLETE question text.
   - Do NOT include question numbers or parenthesized parts like "(a)".
   - Fix broken words if present.

2. Filter Noise:
   - IGNORE instructions like "Attempt any", "Time allowed", "Max marks".
   - IGNORE headers, footers, page numbers, and section titles.
   - IGNORE statements that are not questions.
   - ONLY extract actual questions containing action verbs/interrogatives.

{topic_mapping_rules}

4. Marks:
   - Extract if explicitly present.
   - If not present, infer only from complexity: 2, 5, or 10.

5. Bloom's Taxonomy Level:
   - Classify each question into one of: Remember, Understand, Apply, Analyze, Evaluate, Create.
   - Use the action verb in the question to determine the level:
     * Remember: List, Define, State, Name
     * Understand: Explain, Describe, Discuss, Summarize
     * Apply: Calculate, Solve, Demonstrate, Design
     * Analyze: Compare, Differentiate, Examine, Analyze
     * Evaluate: Evaluate, Justify, Critique, Assess
     * Create: Design, Propose, Develop, Formulate

6. Cleanliness:
   - Remove numbering artifacts.
   - Normalize spacing and broken words.

{ "KNOWLEDGE GRAPH:" if use_kg else "SYLLABUS (fallback):" }
---
{knowledge_graph_text if use_kg else syllabus_text}
---

PYQ TEXT:
---
{pyq_text}
---

{format_instructions}

Return ONLY valid JSON matching the schema above.
"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        content: str = str(getattr(response, "content", "") or "")

        print(f"\n📥 LLM Response (first 300 chars): {content[:300]}")

        # ── Pre-clean: strip markdown fences ─────────────────────────────────
        if content.strip().startswith("```"):
            content = content.strip()
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip().rstrip("`")

        # ── Pre-clean: remove trailing empty objects from questions array ─────
        # LLM sometimes appends a trailing {} which breaks both parsers.
        # Fix: replace patterns like ", {}]" or ",{}]" or "{ }]" before parsing.
        import re as _re
        content = _re.sub(r',\s*\{\s*\}(?=\s*])', '', content)
        # Also collapse multiple trailing commas
        content = _re.sub(r',\s*]', ']', content)

        # ── Tier 1: Pydantic (strict, validates all fields) ───────────────────
        data = None
        try:
            parsed_obj = parser.parse(content)
            data = parsed_obj.dict()
            print(f"✅ Successfully parsed with Pydantic OutputParser")
        except Exception as pydantic_err:
            print(f"⚠️ Pydantic parse failed: {pydantic_err}")

        # ── Tier 2: json.loads on cleaned content ─────────────────────────────
        if data is None:
            print("Falling back to json.loads...")
            try:
                json_match = _re.search(r'\{[\s\S]*\}', content)
                raw = json_match.group(0) if json_match else content
                data = json.loads(raw)
                print(f"✅ json.loads succeeded")
            except json.JSONDecodeError as json_err:
                print(f"⚠️ json.loads failed: {json_err}")

        # ── Tier 3: Truncation recovery — extract every complete object ────────
        # Handles cut-off responses where outer JSON brackets are never closed.
        # Regex finds each self-contained {...} that contains a "question" key.
        if data is None:
            print("Falling back to truncation recovery — extracting individual question objects...")
            recovered = []
            # Match objects that contain at least a "question" field
            for obj_str in _re.finditer(r'\{[^{}]*"question"\s*:[^{}]*\}', content):
                try:
                    obj = json.loads(obj_str.group(0))
                    if obj.get("question", "").strip():
                        recovered.append(obj)
                except json.JSONDecodeError:
                    pass
            if recovered:
                print(f"✅ Truncation recovery salvaged {len(recovered)} complete questions")
                data = {"questions": recovered}
            else:
                return json.dumps({"error": "LLM returned unparseable JSON — no questions recovered."})

        if "questions" not in data:
            return json.dumps({"error": "Invalid JSON structure from LLM."})

        # Deduplicate questions and add unique IDs
        seen = set()
        unique_questions = []
        question_id_counter = 1

        for q in data["questions"]:
            # Skip empty or malformed entries (trailing {} from LLM)
            if not q or not q.get("question", "").strip():
                continue
            q_text = str(q.get("question", "")).strip().lower()
            if q_text and q_text not in seen:
                seen.add(q_text)
                # Add unique ID and normalize field names for compatibility
                q["id"] = f"pyq_{question_id_counter:03d}"
                # Rename 'question' to 'text' for compatibility with question_service.py
                if "question" in q and "text" not in q:
                    q["text"] = q["question"]
                # Ensure bloom_level exists (default to Understand if missing)
                if "bloom_level" not in q:
                    q["bloom_level"] = "Understand"
                question_id_counter += 1
                unique_questions.append(q)

        final_output = {
            "exam_info": {
                "note": "Generated using syllabus-constrained labeling with Pydantic validation."
            },
            "questions": unique_questions
        }

        print(f"✅  [PYQ FORMAT] Completed. Total Unique Questions: {len(unique_questions)}")
        return json.dumps(final_output, indent=4)

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return json.dumps({"error": "LLM returned invalid JSON."})

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return json.dumps({"error": str(e)})

def analyse_pyqs(pyqs: dict) -> dict:
    """
    Transform parsed PYQ list into a structured analysis summary
    for use by the blueprint generator.

    Input:  pyqs dict with shape  { "questions": [ {question, topic, subtopic,
                                    marks, bloom_level, module}, ... ] }
    Output: {
        "total_pyqs": int,
        "module_wise_count": {
            "Module Name": {
                "total": int,
                "topics": { "Topic Name": int, ... }
            }
        },
        "bloom_wise_count": {
            "Remember": int, "Understand": int, ...
        },
        "topic_wise_count": {
            "Topic Name": int, ...
        }
    }
    """
    questions = pyqs.get("questions", [])

    if not questions:
        return {}

    module_wise:  dict = {}
    bloom_wise:   dict = {}
    topic_wise:   dict = {}

    for q in questions:
        module = q.get("module", "Unknown")
        topic  = q.get("topic",  "Unknown")
        bloom  = q.get("bloom_level", "Unknown")

        # Module-wise count
        if module not in module_wise:
            module_wise[module] = {"total": 0, "topics": {}}
        module_wise[module]["total"] += 1
        module_wise[module]["topics"][topic] = (
            module_wise[module]["topics"].get(topic, 0) + 1
        )

        # Bloom-wise count
        bloom_wise[bloom] = bloom_wise.get(bloom, 0) + 1

        # Topic-wise count (flat, across all modules)
        topic_wise[topic] = topic_wise.get(topic, 0) + 1

    return {
        "total_pyqs":       len(questions),
        "module_wise_count": module_wise,
        "bloom_wise_count":  bloom_wise,
        "topic_wise_count":  topic_wise,
    }

pyq_text ="""
Based on the provided documents, here is the extracted text from the previous year's question papers for the **Deep Learning (42371)** course.

---

## **Deep Learning - Examination Paper 1 (Dec 2023)**

**Duration:** 3 Hours | **Max Marks:** 80 

**Instructions:**

* Question No. 1 is compulsory.


* Attempt any three questions out of the remaining five.


* Assume suitable data, if required and state it clearly.



### **Questions**

* Q1. Attempt any four: 


* a. Design AND gate using Perceptron.


* b. Suppose we have  input-output pairs. Our goal is to find parameters that predict the output  from the input  according to . Calculate the sum-of-squared error function . Derive the gradient descent update rule .


* c. Explain dropout. How does it solve the problem of overfitting? 


* d. Explain denoising autoencoder model.


* e. Describe sequence learning problem.




* **Q2.**
* a. Explain Gated Recurrent Unit (GRU) in detail.


* b. What is an activation function? Describe any four activation functions.




* **Q3.**
* a. Explain CNN architecture in detail. Calculate parameters for a layer with input , ten  filters, stride 1, and pad 2.


* b. Explain early stopping, batch normalization, and data augmentation.




* **Q4.**
* a. Explain RNN architecture in detail.


* b. Explain the working of Generative Adversarial Network (GAN).




* **Q5.**
* a. Explain Stochastic Gradient Descent and momentum-based gradient descent optimization techniques.


* b. Explain LSTM architecture.




* **Q6.**
* a. Describe LeNet architecture.


* b. Explain vanishing and exploding gradient in RNNs.





---

## **Deep Learning - Examination Paper 2 (Nov 2024)**

**Duration:** 3 Hours | **Max Marks:** 80 

### **Questions**

* Q1. Attempt any four: 


* a. Comment on the Representation Power of MLPs.
* b. Explain Gradient Descent in Deep Learning.
* c. Explain the dropout method and its advantages.
* d. What are Denoising Autoencoders?
* e. Explain Pooling operation in CNN.


* **Q2.**
* a. What are the Three Classes of Deep Learning? Explain each.
* b. Explain and analyze the architectural components of AlexNet CNN.


* **Q3.**
* a. What are the different types of Gradient Descent methods? Explain any three.
* b. Differentiate between the architecture of LSTM and GRU networks.


* **Q4.**
* a. Explain the key components of an RNN.
* b. Calculate the total number of parameters in a CNN layer: Input 32 channels (), 64 filters (), stride 1, no padding.


* **Q5.**
* a. Comment on the significance of Loss functions and explain different types.
* b. Explain any three types of Autoencoders.


* **Q6.**
* a. What is the significance of Activation Functions? Explain types used in NN.
* b. Explain GAN architecture and its applications.



---

## **Deep Learning - Examination Paper 3 (June 2025)**

**Duration:** 3 Hours | **Max Marks:** 80 

### **Questions**

* Q1. Attempt any four: 


* a. Explain basic architecture of feedforward neural network.


* b. Explain regularization in neural network.


* c. Explain types of neural network.


* d. Explain the concept of overfitting and under fitting.


* e. Explain basic working of CNN.




* **Q2.**
* a. Explain the gradient descent algorithm and discuss types in detail.


* b. Explain the working and types of autoencoders in detail.




* **Q3.**
* a. Draw and explain any two modern deep learning architectures.


* b. Differentiate between the LSTM and GRU network.




* **Q4.**
* a. Explain working of RNN with a diagram and how they suit sequential data.


* b. Compare standard RNN with LSTM for long-term dependencies; provide a real-world application.




* **Q5.**
* a. Discuss the role of Loss functions. Compare MSE and Cross-Entropy Loss.


* b. Explain architecture of GAN in detail and its applications.




* **Q6.**
* a. Explain the significance and types of Activation Functions.


* b. Explain the learning process (forward/backpropagation, optimization) in NN.





Would you like me to solve any of the specific numerical problems or architectural explanations from these papers?
"""

dummy_syllabus = {
  "course_code": "CSC701",
  "course_name": "Deep Learning",
  "course_objectives": [
    "To learn the fundamentals of Neural Network.",
    "To gain an in-depth understanding of training Deep Neural Networks.",
    "To acquire knowledge of advanced concepts of Convolution Neural Networks, Autoencoders and Recurrent Neural Networks.",
    "Students should be familiar with the recent trends in Deep Learning."
  ],
  "course_outcomes": [
    "Gain basic knowledge of Neural Networks.",
    "Acquire in depth understanding of training Deep Neural Networks.",
    "Design appropriate DNN model for supervised, unsupervised and sequence learning applications.",
    "Gain familiarity with recent trends and applications of Deep Learning."
  ],
  "modules": [
    {
      "module_number": 1,
      "module_name": "Fundamentals of Neural Network",
      "weightage_hours": 4,
      "topics": [
        "History of Deep Learning",
        "Deep Learning Success Stories",
        "Multilayer Perceptrons (MLPs)",
        "Representation Power of MLPs",
        "Sigmoid Neurons",
        "Gradient Descent",
        "Feedforward Neural Networks",
        "Representation Power of Feedforward Neural Networks",
        "Deep Networks: Three Classes of Deep Learning Basic Terminologies of Deep Learning"
      ]
    },
    {
      "module_number": 2,
      "module_name": "Training, Optimization and Regularization of Deep Neural Network",
      "weightage_hours": 10,
      "topics": [
        "Training Feedforward DNN",
        "Multi Layered Feed Forward Neural Network",
        "Learning Factors",
        "Activation functions: Tanh, Logistic, Linear, Softmax, ReLU, Leaky ReLU",
        "Loss functions: Squared Error loss, Cross Entropy, Choosing output function and loss function",
        "Optimization",
        "Learning with backpropagation",
        "Learning Parameters: Gradient Descent (GD), Stochastic and Mini Batch GD, Momentum Based GD, Nesterov Accelerated GD, AdaGrad, Adam, RMSProp",
        "Regularization",
        "Overview of Overfitting",
        "Types of biases",
        "Bias Variance Tradeoff",
        "Regularization Methods: L1, L2 regularization, Parameter sharing, Dropout, Weight Decay, Batch normalization, Early stopping, Data Augmentation, Adding noise to input and output"
      ]
    },
    {
      "module_number": 3,
      "module_name": "Autoencoders: Unsupervised Learning",
      "weightage_hours": 6,
      "topics": [
        "Introduction",
        "Linear Autoencoder",
        "Undercomplete Autoencoder",
        "Overcomplete Autoencoders",
        "Regularization in Autoencoders",
        "Denoising Autoencoders",
        "Sparse Autoencoders",
        "Contractive Autoencoders",
        "Application of Autoencoders: Image Compression"
      ]
    },
    {
      "module_number": 4,
      "module_name": "Convolutional Neural Networks (CNN): Supervised Learning",
      "weightage_hours": 7,
      "topics": [
        "Convolution operation",
        "Padding",
        "Stride",
        "Relation between input, output and filter size",
        "CNN architecture: Convolution layer, Pooling Layer",
        "Weight Sharing in CNN",
        "Fully Connected NN vs CNN",
        "Variants of basic Convolution function",
        "Multichannel convolution operation",
        "2D convolution",
        "Modern Deep Learning Architectures: LeNET: Architecture, AlexNET: Architecture, ResNet: Architecture"
      ]
    },
    {
      "module_number": 5,
      "module_name": "Recurrent Neural Networks (RNN)",
      "weightage_hours": 8,
      "topics": [
        "Sequence Learning Problem",
        "Unfolding Computational graphs",
        "Recurrent Neural Network",
        "Bidirectional RNN",
        "Backpropagation Through Time (BTT)",
        "Limitation of “vanilla RNN” Vanishing and Exploding Gradients",
        "Truncated BTT",
        "Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget, Gated Recurrent Unit (GRU)"
      ]
    },
    {
      "module_number": 6,
      "module_name": "Recent Trends and Applications",
      "weightage_hours": 4,
      "topics": [
        "Generative Adversarial Network (GAN): Architecture",
        "Applications: Image Generation, DeepFake"
      ]
    }
  ]
}

# pyqs = format_pyqs(pyq_text, dummy_syllabus)
# print(pyqs)