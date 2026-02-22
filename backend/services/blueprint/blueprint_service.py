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
    prompt = f"""You are an expert question paper blueprint planner for Mumbai University.

Your task is to create a detailed question paper blueprint that satisfies all requirements.

**INPUT DATA:**

1. SYLLABUS:
{json.dumps(syllabus, indent=2)}

2. PYQ ANALYSIS:
{json.dumps(pyq_analysis, indent=2)}

3. BLOOM'S TAXONOMY COVERAGE REQUIRED:
{json.dumps(bloom_coverage, indent=2)}

4. TEACHER PREFERENCES:
{json.dumps(teacher_input, indent=2)}

5. PAPER PATTERN:
{json.dumps(paper_pattern, indent=2)}

**YOUR TASK:**

Create a question paper blueprint following these STRICT RULES:

HARD CONSTRAINTS (MUST FOLLOW):
1. Total marks MUST equal exactly {paper_pattern['total_marks']}
2. Total questions MUST equal exactly {paper_pattern['total_questions']}
3. Each module weightage MUST be between {paper_pattern['module_weightage_range']['min']} and {paper_pattern['module_weightage_range']['max']}
4. Follow the section structure exactly as specified
5. Each question MUST have marks from the allowed values: {paper_pattern['allowed_marks_per_question']}

BLOOM'S TAXONOMY RULES:
1. Distribution should closely match the required coverage (within ±5%)
2. Remember: recall facts, definitions
3. Understand: explain concepts, describe
4. Apply: solve problems, use methods
5. Analyze: compare, differentiate, break down
6. Evaluate: critique, justify, assess
7. Create: design, formulate, construct

PYQ USAGE STRATEGY:
1. If PYQ count for a topic is HIGH (>5), prefer using actual PYQs (set is_pyq: true)
2. If PYQ count is MEDIUM (2-5), consider mix of PYQ and new
3. If PYQ count is LOW (<2), generate new questions (set is_pyq: false)
4. For topics with NO PYQs, MUST generate new questions

TEACHER PREFERENCE RULES:
1. If teacher specifies focus modules, increase their weightage (but respect pattern limits)
2. If teacher prefers PYQs, maximize PYQ usage where available
3. If teacher wants specific topics emphasized, include them

QUALITY RULES:
1. Distribute topics evenly - don't repeat same topic too often
2. Progress from easier to harder questions (Bloom's level should generally increase)
3. Balance between theory and application
4. Each module should have at least 1 question unless total questions < number of modules

**OUTPUT FORMAT:**

Return ONLY a valid JSON object (no markdown, no explanation) with this EXACT structure:

{{
  "blueprint_metadata": {{
    "total_marks": <number>,
    "total_questions": <number>,
    "bloom_distribution": {{
      "Remember": <percentage as decimal, e.g., 0.15>,
      "Understand": <percentage as decimal>,
      "Apply": <percentage as decimal>,
      "Analyze": <percentage as decimal>,
      "Evaluate": <percentage as decimal>,
      "Create": <percentage as decimal>
    }},
    "module_distribution": {{
      "Module 1": <percentage as decimal>,
      "Module 2": <percentage as decimal>,
      ...
    }},
    "pyq_usage": {{
      "actual_pyq_count": <number>,
      "new_question_count": <number>,
      "pyq_percentage": <percentage as decimal>
    }}
  }},
  "sections": [
    {{
      "section_name": "Section A",
      "section_description": "Short Answer Questions",
      "questions": [
        {{
          "question_number": "1a",
          "module": "Module 1",
          "topic": "Process Management",
          "subtopic": "Process States",
          "marks": 5,
          "bloom_level": "Remember",
          "is_pyq": true,
          "rationale": "High PYQ availability"
        }},
        ...
      ]
    }},
    ...
  ],
  "strategy_notes": "Brief explanation of your strategy and any trade-offs made"
}}

**IMPORTANT:**
- Output ONLY the JSON, nothing else
- Ensure all marks add up to {paper_pattern['total_marks']}
- Ensure total questions = {paper_pattern['total_questions']}
- Each question MUST have all required fields
- Bloom levels MUST be one of: Remember, Understand, Apply, Analyze, Evaluate, Create
- Module names MUST match exactly with syllabus module names
- Keep "rationale" field VERY brief (max 10 words each)
- Keep "strategy_notes" field VERY brief (max 50 words total)
- Keep "subtopic" field concise (max 5 words)

Now generate the blueprint:"""

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
    
    metadata = blueprint['blueprint_metadata']
    
    print(f"\n📊 OVERVIEW:")
    print(f"  Total Marks: {metadata['total_marks']}")
    print(f"  Total Questions: {metadata['total_questions']}")
    
    print(f"\n🧠 BLOOM'S TAXONOMY DISTRIBUTION:")
    for level, pct in metadata['bloom_distribution'].items():
        print(f"  {level:12} : {pct*100:5.1f}%")
    
    print(f"\n📚 MODULE DISTRIBUTION:")
    for module, pct in metadata['module_distribution'].items():
        print(f"  {module:12} : {pct*100:5.1f}%")
    
    print(f"\n📝 PYQ USAGE:")
    pyq_info = metadata['pyq_usage']
    print(f"  Actual PYQs: {pyq_info['actual_pyq_count']}")
    print(f"  New Questions: {pyq_info['new_question_count']}")
    print(f"  PYQ Percentage: {pyq_info['pyq_percentage']*100:.1f}%")
    
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
    "course_name": "Database Management Systems",
    "course_code": "CS301",
    "modules": {
        "Module 1": {
            "name": "Introduction to DBMS",
            "official_weightage": 0.25,
            "topics": [
                {
                    "name": "Database Concepts",
                    "subtopics": ["Data vs Information", "DBMS Architecture", "Data Independence"]
                },
                {
                    "name": "ER Modeling",
                    "subtopics": ["Entities", "Attributes", "Relationships", "ER Diagrams"]
                }
            ]
        },
        "Module 2": {
            "name": "Relational Model",
            "official_weightage": 0.25,
            "topics": [
                {
                    "name": "Relational Algebra",
                    "subtopics": ["Selection", "Projection", "Joins", "Set Operations"]
                },
                {
                    "name": "SQL",
                    "subtopics": ["DDL", "DML", "Queries", "Joins"]
                }
            ]
        },
        "Module 3": {
            "name": "Normalization",
            "official_weightage": 0.25,
            "topics": [
                {
                    "name": "Functional Dependencies",
                    "subtopics": ["FD Rules", "Closure", "Minimal Cover"]
                },
                {
                    "name": "Normal Forms",
                    "subtopics": ["1NF", "2NF", "3NF", "BCNF"]
                }
            ]
        },
        "Module 4": {
            "name": "Transaction Management",
            "official_weightage": 0.25,
            "topics": [
                {
                    "name": "Transactions",
                    "subtopics": ["ACID Properties", "Transaction States", "Schedules"]
                },
                {
                    "name": "Concurrency Control",
                    "subtopics": ["Locking", "Timestamps", "Deadlock"]
                }
            ]
        }
    }
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
    "module_weightage_range": {
        "min": 0.20,
        "max": 0.30
    },
    "sections": [
        {
            "section_name": "Section A",
            "description": "Short Answer Questions",
            "question_count": 4,
            "marks_per_question": 5,
            "total_marks": 20
        },
        {
            "section_name": "Section B",
            "description": "Long Answer Questions",
            "question_count": 4,
            "marks_per_question": 15,
            "total_marks": 60
        }
    ]
}


# ============================================================================
# TEST EXECUTION
# ============================================================================

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
#         print_blueprint_summary(blueprint)
        
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