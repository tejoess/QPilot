"""
Blueprint Generator Agent - Version 1
Generates question paper blueprint from syllabus, PYQ analysis, and requirements
"""

import json
import re
from typing import Dict, List
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


def create_fallback_blueprint(paper_pattern: Dict) -> Dict:
    """
    Create a minimal valid blueprint when LLM fails
    """
    print("⚠️ Creating fallback blueprint...")
    
    sections = []
    for section_pattern in paper_pattern.get('sections', []):
        questions = []
        for i in range(section_pattern.get('question_count', 1)):
            questions.append({
                "question_number": f"{section_pattern['section_name']}-Q{i+1}",
                "module": "Module 1",
                "topic": "General Topic",
                "subtopic": "General Subtopic",
                "marks": section_pattern.get('marks_per_question', 5),
                "bloom_level": "Understand",
                "is_pyq": False,
                "rationale": "Fallback"
            })
        
        sections.append({
            "section_name": section_pattern['section_name'],
            "section_description": section_pattern.get('section_description', ''),
            "questions": questions
        })
    
    return {
        "blueprint_metadata": {
            "total_marks": paper_pattern['total_marks'],
            "total_questions": paper_pattern['total_questions'],
            "bloom_distribution": {
                "Remember": 0.2,
                "Understand": 0.3,
                "Apply": 0.3,
                "Analyze": 0.2,
                "Evaluate": 0.0,
                "Create": 0.0
            },
            "module_distribution": {"Module 1": 1.0},
            "pyq_usage": {
                "actual_pyq_count": 0,
                "new_question_count": paper_pattern['total_questions'],
                "pyq_percentage": 0.0
            }
        },
        "sections": sections
    }


def fix_incomplete_json(json_str: str) -> str:
    """
    Attempt to fix incomplete JSON by adding missing closing brackets
    """
    # Try to extract JSON from text
    # Look for first { and try to find matching }
    start_idx = json_str.find('{')
    if start_idx == -1:
        return json_str
    
    json_str = json_str[start_idx:]
    
    # Count opening and closing brackets
    open_braces = json_str.count('{')
    close_braces = json_str.count('}')
    open_brackets = json_str.count('[')
    close_brackets = json_str.count(']')
    
    # Add missing closing brackets/braces
    json_str = json_str.rstrip()
    if json_str.endswith(','):
        json_str = json_str[:-1]  # Remove trailing comma
    
    # Add missing closing brackets
    json_str += ']' * (open_brackets - close_brackets)
    json_str += '}' * (open_braces - close_braces)
    
    return json_str


def generate_blueprint(
    syllabus: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict
) -> Dict:
    """
    Generate question paper blueprint using LLM
    
    Args:
        syllabus: Module-wise topics and weightages
        pyq_analysis: PYQ availability statistics
        bloom_coverage: Required Bloom's taxonomy distribution
        teacher_input: Teacher preferences (bias, focus areas)
        paper_pattern: University pattern (sections, marks, question types)
    
    Returns:
        Blueprint dict with sections and questions
    """
    
    # Build comprehensive prompt
    prompt = f"""You are a Mumbai University question paper designer.

Your ONLY job: produce a list of questions. Do NOT compute totals, percentages, or metadata.

**PAPER PATTERN:**
- Total marks: {paper_pattern['total_marks']}
- Total questions: {paper_pattern['total_questions']}
- Sections: {json.dumps(paper_pattern['sections'], indent=2)}

**MODULES & TOPICS:**
{json.dumps(syllabus, indent=2)}

**PYQ AVAILABILITY:**
{json.dumps(pyq_analysis, indent=2)}

**BLOOM'S TARGET DISTRIBUTION:**
{json.dumps(bloom_coverage, indent=2)}

**TEACHER PREFERENCES:**
{json.dumps(teacher_input, indent=2)}


**RULES:**

MARKS — follow this exactly:
- Place exactly {paper_pattern['total_questions']} questions across all sections
- Keep a running total as you assign questions
- Your last question's marks must close the gap to exactly {paper_pattern['total_marks']}
- If you cannot reach {paper_pattern['total_marks']} exactly with remaining questions, adjust earlier questions before finalising

MODULE BALANCE — per module, marks / {paper_pattern['total_marks']} must be:
- At least {paper_pattern['module_weightage_range']['min'] * 100}%
- At most {paper_pattern['module_weightage_range']['max'] * 100}%
- Every module in the syllabus must appear in at least 1 question

BLOOM'S — assign levels to match target distribution within ±5%:
- First 30% of questions: only Remember or Understand
- Middle 40%: Apply or Analyze
- Last 30%: Evaluate or Create

PYQ USAGE:
- Topic PYQ count > 5 → is_pyq: true
- Topic PYQ count 2–5 → mix true/false
- Topic PYQ count < 2 → is_pyq: false
- No PYQs for topic → always is_pyq: false

TOPIC FIELD:
- Must exactly match a topic or subtopic name from the syllabus above
- Do not invent or paraphrase topic names

**OUTPUT FORMAT:**

Return ONLY valid JSON. No markdown. No explanation. No metadata fields.

{{
  "sections": [
    {{
      "section_name": "Section A",
      "section_description": "Short Answer Questions",
      "questions": [
        {{
          "question_number": "1a",
          "module": "Module 1",
          "topic": "<exact name from syllabus>",
          "marks": 5,
          "bloom_level": "Remember",
          "is_pyq": true,
          "rationale": "max 10 words"
        }}
      ]
    }}
  ]
}}

Bloom level must be one of: Remember, Understand, Apply, Analyze, Evaluate, Create
"""

    # Call LLM with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            message = HumanMessage(content=prompt)
            response = llm.invoke([message])
            
            # Extract content
            response_text = response.content.strip()
            
            print(f"\n📥 LLM Response Length: {len(response_text)} characters")
            print(f"📥 First 200 chars: {response_text[:200]}")
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            # Try to extract JSON using regex
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                response_text = json_match.group(0)
                print(f"✅ Extracted JSON from response")
            
            # Try parsing JSON
            try:
                blueprint = json.loads(response_text)
                print(f"✅ Successfully parsed JSON directly")
            except json.JSONDecodeError as parse_error:
                # Try fixing incomplete JSON
                print(f"⚠️ Initial parse failed: {parse_error}")
                print(f"⚠️ Attempting to fix incomplete JSON...")
                fixed_json = fix_incomplete_json(response_text)
                blueprint = json.loads(fixed_json)
                print(f"✅ Successfully fixed and parsed JSON")
            
            # Validate blueprint structure
            if not isinstance(blueprint, dict) or 'sections' not in blueprint:
                raise ValueError("Invalid blueprint structure: missing 'sections' key")
            
            # Validate blueprint
            validation_errors = validate_blueprint(blueprint, paper_pattern)
            if validation_errors:
                print("\n⚠️ VALIDATION WARNINGS:")
                for error in validation_errors:
                    print(f"  - {error}")
            
            print(f"✅ Successfully generated blueprint on attempt {attempt + 1}")
            return blueprint
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"\n❌ Attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}")
            print(f"Error: {e}")
            
            if attempt < max_retries - 1:
                print(f"🔄 Retrying with adjusted prompt...")
                # Add instruction to keep response concise
                prompt += "\n\nCRITICAL: Return ONLY valid JSON. No explanations. Keep rationale SHORT (max 3 words). Ensure JSON is complete and properly closed."
            else:
                print(f"\n❌ ERROR: Failed to parse LLM response after {max_retries} attempts")
                print(f"\nLLM Response (first 500 chars):\n{response_text[:500]}")
                print(f"\nLLM Response (last 300 chars):\n...{response_text[-300:]}")
                print(f"\nTotal length: {len(response_text)} characters")
                
                # Return a minimal valid blueprint instead of crashing
                print("\n🔧 Returning minimal fallback blueprint...")
                return create_fallback_blueprint(paper_pattern)


def validate_blueprint(blueprint: Dict, paper_pattern: Dict) -> List[str]:
    """
    Validate blueprint against requirements
    Returns list of validation errors (empty if valid)
    """
    errors = []
    
    # Check total marks
    total_marks = sum(
        q['marks'] 
        for section in blueprint['sections'] 
        for q in section['questions']
    )
    if total_marks != paper_pattern['total_marks']:
        errors.append(f"Total marks mismatch: Expected {paper_pattern['total_marks']}, got {total_marks}")
    
    # Check total questions
    total_questions = sum(
        len(section['questions']) 
        for section in blueprint['sections']
    )
    if total_questions != paper_pattern['total_questions']:
        errors.append(f"Total questions mismatch: Expected {paper_pattern['total_questions']}, got {total_questions}")
    
    # Check required fields
    for section in blueprint['sections']:
        for q in section['questions']:
            required_fields = ['question_number', 'module', 'topic', 'marks', 'bloom_level', 'is_pyq']
            missing = [f for f in required_fields if f not in q]
            if missing:
                errors.append(f"Question {q.get('question_number', '?')} missing fields: {missing}")
    
    return errors


def print_blueprint_summary(blueprint: Dict):
    """Pretty print blueprint summary"""
    print("\n" + "="*80)
    print("📋 QUESTION PAPER BLUEPRINT GENERATED")
    print("="*80)
    
    #metadata = blueprint['blueprint_metadata']
    
    print(f"\n📊 OVERVIEW:")
    # print(f"  Total Marks: {metadata['total_marks']}")
    # print(f"  Total Questions: {metadata['total_questions']}")
    
    print(f"\n🧠 BLOOM'S TAXONOMY DISTRIBUTION:")
    # for level, pct in metadata['bloom_distribution'].items():
    #     print(f"  {level:12} : {pct*100:5.1f}%")
    
    print(f"\n📚 MODULE DISTRIBUTION:")
    # for module, pct in metadata['module_distribution'].items():
    #     print(f"  {module:12} : {pct*100:5.1f}%")
    
    print(f"\n📝 PYQ USAGE:")
    # pyq_info = metadata['pyq_usage']
    # print(f"  Actual PYQs: {pyq_info['actual_pyq_count']}")
    # print(f"  New Questions: {pyq_info['new_question_count']}")
    # print(f"  PYQ Percentage: {pyq_info['pyq_percentage']*100:.1f}%")
    
    print(f"\n📄 SECTIONS & QUESTIONS:")
    for section in blueprint['sections']:
        print(f"\n  {section['section_name']} - {section['section_description']}")
        for q in section['questions']:
            pyq_badge = "📌PYQ" if q['is_pyq'] else "✨NEW"
            print(f"    {q['question_number']:4} | {q['marks']:2}M | {q['bloom_level']:10} | {q['module']:10} | {q['topic']:30} | {pyq_badge}")
    
    print(f"\n💡 STRATEGY NOTES:")
    print(f"  {blueprint['strategy_notes']}")
    
    print("\n" + "="*80)


# ============================================================================
# SAMPLE TEST DATA
# ============================================================================

SAMPLE_SYLLABUS = {
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
        "Deep Networks: Three Classes of Deep Learning",
        "Basic Terminologies of Deep Learning"
      ]
    },
    {
      "module_number": 2,
      "module_name": "Training, Optimization and Regularization of Deep Neural Network",
      "weightage_hours": 10,
      "topics": [
        "Training FeedforwardDNN Multi Layered Feed Forward Neural Network",
        "Learning Factors",
        "Activation functions: Tanh, Logistic, Linear, Softmax, ReLU, Leaky ReLU",
        "Loss functions: Squared Error loss, Cross Entropy",
        "Choosing output function and loss function",
        "Optimization Learning with backpropagation",
        "Learning Parameters: Gradient Descent (GD), Stochastic and Mini Batch GD, Momentum Based GD, Nesterov Accelerated GD, AdaGrad, Adam, RMSProp",
        "Regularization Overview of Overfitting",
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
        "Modern Deep Learning Architectures: LeNET: Architecture, AlexNET: Architecture, ResNet : Architecture"
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
        "Limitation of ' vanilla RNN' Vanishing and Exploding Gradients",
        "Truncated BTT",
        "Long Short Term Memory(LSTM): Selective Read, Selective write, Selective Forget",
        "Gated Recurrent Unit (GRU)"
      ]
    },
    {
      "module_number": 6,
      "module_name": "Recent Trends and Applications",
      "weightage_hours": 4,
      "topics": [
        "Generative Adversarial Network (GAN): Architecture",
        "Applications: Image Generation",
        "DeepFake"
      ]
    }
  ]
}

SAMPLE_PYQ_ANALYSIS = {
    "total_pyqs": 45,
    "year_range": [2019, 2024],
    "module_wise_count": {
        "Module 1": {
            "total": 12,
            "topics": {
                "Database Concepts": 5,
                "ER Modeling": 7
            },
            "quality": "high"
        },
        "Module 2": {
            "total": 15,
            "topics": {
                "Relational Algebra": 6,
                "SQL": 9
            },
            "quality": "high"
        },
        "Module 3": {
            "total": 10,
            "topics": {
                "Functional Dependencies": 3,
                "Normal Forms": 7
            },
            "quality": "medium"
        },
        "Module 4": {
            "total": 8,
            "topics": {
                "Transactions": 5,
                "Concurrency Control": 3
            },
            "quality": "medium"
        }
    },
    "bloom_wise_count": {
        "Remember": 8,
        "Understand": 12,
        "Apply": 15,
        "Analyze": 7,
        "Evaluate": 2,
        "Create": 1
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
    "flexibility": "±5% deviation allowed"
}

SAMPLE_TEACHER_INPUT = {
    "input":"I want this paper only on first 3 modules, keep all other accuracy constraint same, but quetion paper should be strictly on 1sst three modules only.",
    "pyq_percentage": 50
}

SAMPLE_PAPER_PATTERN = {
    "university": "Mumbai University",
    "exam_type": "Internal Assessment",
    "total_marks": 32,
    "total_questions": 10,
    "duration_minutes": 60,
    "module_weightage_range": {
        "min": 0.0,
        "max": 0.30
    },
    "sections": [
        {
            "section_name": "Section A",
            "description": "Answer the following(2 marks each)",
            "question_count": 6,
            "marks_per_question": 2,
            "total_marks": 12
        },
        {
            "section_name": "Section B",
            "description": "Long Answer Questions",
            "question_count": 4,
            "marks_per_question": 5,
            "total_marks": 20
        }
    ]
}


#============================================================================
#TEST EXECUTION
#============================================================================

# if __name__ == "__main__":
#     print("🚀 Starting Blueprint Generation...")
#     print("="*80)
    
#     try:
#         # Generate blueprint
#         blueprint = generate_blueprint(
#             syllabus=SAMPLE_SYLLABUS,
#             pyq_analysis=SAMPLE_PYQ_ANALYSIS,
#             bloom_coverage=SAMPLE_BLOOM_COVERAGE,
#             teacher_input=SAMPLE_TEACHER_INPUT,
#             paper_pattern=SAMPLE_PAPER_PATTERN
#         )
        
#         # Print summary
#         #print_blueprint_summary(blueprint)
        
#         # Save to file
#         output_file = "generated_blueprint.json"
#         with open(output_file, 'w') as f:
#             json.dump(blueprint, f, indent=2)
        
#         print(f"\n✅ Blueprint saved to: {output_file}")
#         print("="*80)
        
#     except Exception as e:
#         print(f"\n❌ ERROR: {e}")
#         import traceback
#         traceback.print_exc()