"""
Blueprint Critic Agent - Version 1
Evaluates and critiques question paper blueprints with detailed feedback
"""

import json
from typing import Dict, List, Tuple
from backend.services.llm_service import gemini_llm as llm
from langchain_core.messages import HumanMessage


def critique_blueprint(
    blueprint: Dict,
    syllabus: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict
) -> Dict:
    """
    Critique and evaluate a question paper blueprint
    
    Args:
        blueprint: The blueprint to evaluate
        syllabus: Module-wise topics and weightages
        pyq_analysis: PYQ availability statistics
        bloom_coverage: Required Bloom's taxonomy distribution
        teacher_input: Teacher preferences
        paper_pattern: University pattern requirements
    
    Returns:
        Critique dict with scores, issues, and recommendations
    """
    
    prompt = f"""You are an expert question paper quality evaluator for Mumbai University.

Your task is to thoroughly critique a question paper blueprint and provide detailed feedback.

**BLUEPRINT TO EVALUATE:**
{json.dumps(blueprint, indent=2)}

**CONTEXT DATA:**

1. SYLLABUS:
{json.dumps(syllabus, indent=2)}

2. PYQ ANALYSIS:
{json.dumps(pyq_analysis, indent=2)}

3. BLOOM'S TAXONOMY REQUIREMENTS:
{json.dumps(bloom_coverage, indent=2)}

4. TEACHER PREFERENCES:
{json.dumps(teacher_input, indent=2)}

5. PAPER PATTERN:
{json.dumps(paper_pattern, indent=2)}

**EVALUATION CRITERIA:**

You must evaluate the blueprint on these 8 METRICS (each scored 0-10):

1. **CONSTRAINT COMPLIANCE (0-10)**
   - Total marks equals {paper_pattern['total_marks']} (CRITICAL)
   - Total questions equals {paper_pattern['total_questions']} (CRITICAL)
   - Module weightages within {paper_pattern['module_weightage_range']['min']}-{paper_pattern['module_weightage_range']['max']} range
   - Section structure matches pattern
   - Question marks from allowed values only
   
   Scoring:
   - 10: All constraints perfectly met
   - 7-9: Minor deviations (1-2 marks off, slight weightage issues)
   - 4-6: Moderate violations (3-5 marks off, multiple weightage issues)
   - 0-3: Major violations (completely wrong totals, invalid structure)

2. **BLOOM'S TAXONOMY BALANCE (0-10)**
   - Distribution matches required percentages (±5% tolerance)
   - Appropriate cognitive level progression (easier to harder)
   - No over-reliance on lower levels (Remember/Understand shouldn't exceed 45%)
   - Higher-order thinking represented (Analyze/Evaluate/Create at least 25%)
   
   Scoring:
   - 10: Perfect match within ±3%
   - 7-9: Good match within ±5-7%
   - 4-6: Acceptable match within ±8-12%
   - 0-3: Poor distribution, >15% deviation

3. **SYLLABUS COVERAGE (0-10)**
   - All modules covered appropriately
   - Important topics included
   - No topic over-repetition
   - Coverage gaps identified
   
   Scoring:
   - 10: Excellent coverage, all important topics included
   - 7-9: Good coverage, 1-2 minor topics missing
   - 4-6: Moderate coverage, some important topics missing
   - 0-3: Poor coverage, major gaps

4. **PYQ UTILIZATION STRATEGY (0-10)**
   - Appropriate PYQ reuse (HIGH availability → use PYQs)
   - Sensible generation decisions (LOW availability → generate new)
   - Balance between PYQs and new questions
   - Aligns with teacher preference for PYQ usage
   
   Scoring:
   - 10: Optimal strategy, smart decisions
   - 7-9: Good strategy with minor inefficiencies
   - 4-6: Suboptimal but acceptable
   - 0-3: Poor strategy, ignores availability data

5. **MODULE BALANCE (0-10)**
   - Weightages match syllabus recommendations
   - Teacher focus areas appropriately emphasized
   - No module is over/under-represented beyond limits
   - Fair distribution across modules
   
   Scoring:
   - 10: Perfect balance, all modules within ±3% of target
   - 7-9: Good balance within ±5%
   - 4-6: Acceptable imbalance within ±10%
   - 0-3: Poor balance, major disparities

6. **DIFFICULTY PROGRESSION (0-10)**
   - Questions progress from easier to harder
   - Bloom's levels show logical flow
   - Mark allocation matches difficulty
   - No sudden difficulty spikes
   
   Scoring:
   - 10: Smooth progression, excellent flow
   - 7-9: Generally good with minor irregularities
   - 4-6: Somewhat erratic but manageable
   - 0-3: Poor progression, illogical ordering

7. **TOPIC DIVERSITY (0-10)**
   - No excessive repetition of same topic
   - Good spread across subtopics
   - Avoids testing same concept multiple times
   - Each question tests distinct knowledge
   
   Scoring:
   - 10: Excellent diversity, all unique
   - 7-9: Good diversity, 1-2 minor overlaps
   - 4-6: Moderate diversity, some repetition
   - 0-3: Poor diversity, heavy repetition

8. **TEACHER PREFERENCE ALIGNMENT (0-10)**
   - Focus modules/topics appropriately emphasized
   - PYQ preference respected
   - Special instructions followed
   - Difficulty preference matched
   
   Scoring:
   - 10: Perfectly aligned with all preferences
   - 7-9: Mostly aligned, 1-2 minor misses
   - 4-6: Partially aligned, some preferences ignored
   - 0-3: Poorly aligned, preferences not considered

**OUTPUT FORMAT:**

Return ONLY a valid JSON object (no markdown, no explanation) with this structure:

{{
  "overall_rating": {{
    "total_score": <sum of all 8 metric scores>,
    "max_possible": 80,
    "percentage": <percentage score>,
    "grade": "<A+/A/B+/B/C+/C/D/F>",
    "verdict": "<APPROVED / APPROVED_WITH_WARNINGS / NEEDS_REVISION / REJECTED>",
    "summary": "<1-2 sentence overall assessment>"
  }},
  "metric_scores": {{
    "constraint_compliance": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "blooms_balance": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "syllabus_coverage": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "pyq_utilization": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "module_balance": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "difficulty_progression": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "topic_diversity": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }},
    "teacher_alignment": {{
      "score": <0-10>,
      "max": 10,
      "status": "<excellent/good/acceptable/poor>",
      "details": "<specific evaluation>"
    }}
  }},
  "critical_issues": [
    {{
      "severity": "<critical/high/medium/low>",
      "category": "<which metric>",
      "issue": "<specific problem>",
      "impact": "<what's the consequence>",
      "fix": "<how to resolve it>"
    }}
  ],
  "warnings": [
    {{
      "category": "<which metric>",
      "warning": "<what's not ideal>",
      "suggestion": "<how to improve>"
    }}
  ],
  "strengths": [
    "<what's done well - be specific>"
  ],
  "recommendations": {{
    "immediate_fixes": [
      "<critical changes needed before approval>"
    ],
    "suggested_improvements": [
      "<optional improvements for better quality>"
    ],
    "alternative_approaches": [
      "<different strategies that could work>"
    ]
  }},
  "detailed_analysis": {{
    "bloom_distribution_analysis": {{
      "required": {{...}},
      "actual": {{...}},
      "deviations": {{...}}
    }},
    "module_distribution_analysis": {{
      "required": {{...}},
      "actual": {{...}},
      "deviations": {{...}}
    }},
    "pyq_usage_analysis": {{
      "total_pyqs_available": <number>,
      "pyqs_used": <number>,
      "utilization_rate": <percentage>,
      "missed_opportunities": [<topics where PYQs could have been used>]
    }},
    "topic_coverage_analysis": {{
      "covered_topics": [<list>],
      "missing_topics": [<list>],
      "repeated_topics": [<list>]
    }}
  }},
  "pass_fail_decision": {{
    "decision": "<PASS / FAIL>",
    "can_proceed": <true/false>,
    "requires_iteration": <true/false>,
    "iteration_priority": "<what to fix first>"
  }}
}}

**GRADING SCALE:**
- A+ (95-100%): Exceptional blueprint, ready for immediate use
- A  (90-94%): Excellent blueprint, minor tweaks optional
- B+ (85-89%): Very good blueprint, 1-2 improvements recommended
- B  (80-84%): Good blueprint, few changes needed
- C+ (75-79%): Acceptable blueprint, needs moderate revision
- C  (70-74%): Passable blueprint, significant improvements needed
- D  (60-69%): Poor blueprint, major revisions required
- F  (<60%): Unacceptable blueprint, complete overhaul needed

**VERDICT DEFINITIONS:**
- APPROVED: Score ≥85%, no critical issues
- APPROVED_WITH_WARNINGS: Score 70-84%, no critical issues but has warnings
- NEEDS_REVISION: Score 60-69% OR has 1-2 critical issues
- REJECTED: Score <60% OR has 3+ critical issues

Be thorough, specific, and constructive in your critique. Provide actionable feedback.

Now evaluate the blueprint:"""

    # Call LLM
    message = HumanMessage(content=prompt)
    response = llm.invoke([message])
    
    # Extract and parse
    response_text = response.content.strip()
    
    # Clean markdown
    if response_text.startswith("```json"):
        response_text = response_text.replace("```json", "").replace("```", "").strip()
    elif response_text.startswith("```"):
        response_text = response_text.replace("```", "").strip()
    
    try:
        critique = json.loads(response_text)
        return critique
        
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Failed to parse LLM response as JSON")
        print(f"Error: {e}")
        print(f"\nLLM Response:\n{response_text[:500]}...")
        raise


def print_critique_report(critique: Dict):
    """Pretty print critique report"""
    print("\n" + "="*100)
    print("📊 BLUEPRINT CRITIQUE REPORT")
    print("="*100)
    
    # Overall Rating
    overall = critique['overall_rating']
    print(f"\n🎯 OVERALL RATING:")
    print(f"  Score: {overall['total_score']}/{overall['max_possible']} ({overall['percentage']:.1f}%)")
    print(f"  Grade: {overall['grade']}")
    print(f"  Verdict: {overall['verdict']}")
    print(f"  Summary: {overall['summary']}")
    
    # Metric Scores
    print(f"\n📈 DETAILED METRIC SCORES:")
    metrics = critique['metric_scores']
    
    for metric_name, metric_data in metrics.items():
        status_emoji = {
            'excellent': '🟢',
            'good': '🟡',
            'acceptable': '🟠',
            'poor': '🔴'
        }.get(metric_data['status'], '⚪')
        
        metric_display = metric_name.replace('_', ' ').title()
        print(f"\n  {status_emoji} {metric_display}: {metric_data['score']}/10 ({metric_data['status']})")
        print(f"     {metric_data['details']}")
    
    # Critical Issues
    if critique['critical_issues']:
        print(f"\n🚨 CRITICAL ISSUES ({len(critique['critical_issues'])}):")
        for i, issue in enumerate(critique['critical_issues'], 1):
            severity_emoji = {
                'critical': '❌',
                'high': '⚠️',
                'medium': '⚡',
                'low': 'ℹ️'
            }.get(issue['severity'], '•')
            print(f"\n  {severity_emoji} Issue #{i} [{issue['severity'].upper()}] - {issue['category']}")
            print(f"     Problem: {issue['issue']}")
            print(f"     Impact: {issue['impact']}")
            print(f"     Fix: {issue['fix']}")
    
    # Warnings
    if critique['warnings']:
        print(f"\n⚠️  WARNINGS ({len(critique['warnings'])}):")
        for i, warning in enumerate(critique['warnings'], 1):
            print(f"\n  {i}. {warning['category']}")
            print(f"     Warning: {warning['warning']}")
            print(f"     Suggestion: {warning['suggestion']}")
    
    # Strengths
    if critique['strengths']:
        print(f"\n✅ STRENGTHS:")
        for strength in critique['strengths']:
            print(f"  • {strength}")
    
    # Recommendations
    recs = critique['recommendations']
    
    if recs['immediate_fixes']:
        print(f"\n🔧 IMMEDIATE FIXES REQUIRED:")
        for fix in recs['immediate_fixes']:
            print(f"  • {fix}")
    
    if recs['suggested_improvements']:
        print(f"\n💡 SUGGESTED IMPROVEMENTS:")
        for imp in recs['suggested_improvements']:
            print(f"  • {imp}")
    
    if recs.get('alternative_approaches'):
        print(f"\n🔄 ALTERNATIVE APPROACHES:")
        for alt in recs['alternative_approaches']:
            print(f"  • {alt}")
    
    # Detailed Analysis
    analysis = critique['detailed_analysis']
    
    print(f"\n📊 DETAILED ANALYSIS:")
    
    # Bloom's
    bloom_analysis = analysis['bloom_distribution_analysis']
    print(f"\n  Bloom's Taxonomy:")
    for level in ['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create']:
        if level in bloom_analysis.get('required', {}):
            req = bloom_analysis['required'][level]
            act = bloom_analysis['actual'].get(level, 0)
            dev = bloom_analysis['deviations'].get(level, 0)
            status = "✓" if abs(dev) <= 0.05 else "⚠" if abs(dev) <= 0.10 else "✗"
            print(f"    {status} {level:12}: Required {req*100:4.1f}% | Actual {act*100:4.1f}% | Deviation {dev*100:+5.1f}%")
    
    # Module
    module_analysis = analysis['module_distribution_analysis']
    print(f"\n  Module Distribution:")
    for module in sorted(module_analysis.get('required', {}).keys()):
        req = module_analysis['required'][module]
        act = module_analysis['actual'].get(module, 0)
        dev = module_analysis['deviations'].get(module, 0)
        status = "✓" if abs(dev) <= 0.03 else "⚠" if abs(dev) <= 0.08 else "✗"
        print(f"    {status} {module:12}: Required {req*100:4.1f}% | Actual {act*100:4.1f}% | Deviation {dev*100:+5.1f}%")
    
    # PYQ Usage
    pyq_analysis = analysis['pyq_usage_analysis']
    print(f"\n  PYQ Utilization:")
    print(f"    Available: {pyq_analysis['total_pyqs_available']} PYQs")
    print(f"    Used: {pyq_analysis['pyqs_used']} PYQs")
    print(f"    Utilization Rate: {pyq_analysis['utilization_rate']:.1f}%")
    if pyq_analysis.get('missed_opportunities'):
        print(f"    Missed Opportunities: {', '.join(pyq_analysis['missed_opportunities'])}")
    
    # Topic Coverage
    topic_analysis = analysis['topic_coverage_analysis']
    if topic_analysis.get('missing_topics'):
        print(f"\n  Missing Topics: {', '.join(topic_analysis['missing_topics'])}")
    if topic_analysis.get('repeated_topics'):
        print(f"  Repeated Topics: {', '.join(topic_analysis['repeated_topics'])}")
    
    # Final Decision
    decision = critique['pass_fail_decision']
    print(f"\n{'='*100}")
    print(f"🏁 FINAL DECISION:")
    print(f"  Decision: {decision['decision']}")
    print(f"  Can Proceed: {'✅ YES' if decision['can_proceed'] else '❌ NO'}")
    print(f"  Requires Iteration: {'YES' if decision['requires_iteration'] else 'NO'}")
    if decision.get('iteration_priority'):
        print(f"  Priority: {decision['iteration_priority']}")
    print("="*100 + "\n")


# ============================================================================
# SAMPLE TEST DATA
# ============================================================================

# Reuse syllabus and other data from blueprint generator
SAMPLE_SYLLABUS = {
    "course_name": "Database Management Systems",
    "course_code": "CS301",
    "modules": {
        "Module 1": {
            "name": "Introduction to DBMS",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Database Concepts", "subtopics": ["Data vs Information", "DBMS Architecture"]},
                {"name": "ER Modeling", "subtopics": ["Entities", "Relationships", "ER Diagrams"]}
            ]
        },
        "Module 2": {
            "name": "Relational Model",
            "official_weightage": 0.25,
            "topics": [
                {"name": "Relational Algebra", "subtopics": ["Selection", "Projection", "Joins"]},
                {"name": "SQL", "subtopics": ["DDL", "DML", "Queries"]}
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
        "Module 4": {"total": 8, "quality": "medium"}
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
    }
}

SAMPLE_TEACHER_INPUT = {
    "focus_modules": ["Module 3", "Module 4"],
    "prefer_pyqs": True,
    "difficulty_preference": "medium"
}

SAMPLE_PAPER_PATTERN = {
    "total_marks": 80,
    "total_questions": 8,
    "module_weightage_range": {"min": 0.20, "max": 0.30},
    "sections": [
        {"section_name": "Section A", "marks_per_question": 5},
        {"section_name": "Section B", "marks_per_question": 15}
    ]
}

# Sample Blueprint to Test (intentionally has some issues)
SAMPLE_BLUEPRINT_GOOD = {
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
            "questions": [
                {"question_number": "1", "module": "Module 1", "topic": "DBMS Architecture", "marks": 5, "bloom_level": "Remember", "is_pyq": True},
                {"question_number": "2", "module": "Module 2", "topic": "SQL Queries", "marks": 5, "bloom_level": "Understand", "is_pyq": True},
                {"question_number": "3", "module": "Module 3", "topic": "Functional Dependencies", "marks": 5, "bloom_level": "Apply", "is_pyq": True},
                {"question_number": "4", "module": "Module 4", "topic": "ACID Properties", "marks": 5, "bloom_level": "Understand", "is_pyq": True}
            ]
        },
        {
            "section_name": "Section B",
            "questions": [
                {"question_number": "5", "module": "Module 1", "topic": "ER Diagrams", "marks": 15, "bloom_level": "Apply", "is_pyq": True},
                {"question_number": "6", "module": "Module 2", "topic": "Relational Algebra", "marks": 15, "bloom_level": "Analyze", "is_pyq": False},
                {"question_number": "7", "module": "Module 3", "topic": "Normalization", "marks": 15, "bloom_level": "Analyze", "is_pyq": False},
                {"question_number": "8", "module": "Module 4", "topic": "Concurrency Control", "marks": 15, "bloom_level": "Evaluate", "is_pyq": False}
            ]
        }
    ],
    "strategy_notes": "Balanced approach with good PYQ utilization and coverage"
}

SAMPLE_BLUEPRINT_POOR = {
    "blueprint_metadata": {
        "total_marks": 78,  # WRONG - should be 80
        "total_questions": 8,
        "bloom_distribution": {
            "Remember": 0.40,  # Too high
            "Understand": 0.35,  # Too high
            "Apply": 0.15,
            "Analyze": 0.10,
            "Evaluate": 0.0,
            "Create": 0.0
        },
        "module_distribution": {
            "Module 1": 0.15,  # Too low
            "Module 2": 0.40,  # Too high
            "Module 3": 0.30,
            "Module 4": 0.15  # Too low
        },
        "pyq_usage": {
            "actual_pyq_count": 2,
            "new_question_count": 6,
            "pyq_percentage": 0.25
        }
    },
    "sections": [
        {
            "section_name": "Section A",
            "questions": [
                {"question_number": "1", "module": "Module 2", "topic": "SQL", "marks": 5, "bloom_level": "Remember", "is_pyq": True},
                {"question_number": "2", "module": "Module 2", "topic": "SQL Joins", "marks": 5, "bloom_level": "Remember", "is_pyq": False},
                {"question_number": "3", "module": "Module 2", "topic": "SQL Queries", "marks": 5, "bloom_level": "Understand", "is_pyq": False},
                {"question_number": "4", "module": "Module 3", "topic": "3NF", "marks": 3, "bloom_level": "Remember", "is_pyq": False}
            ]
        },
        {
            "section_name": "Section B",
            "questions": [
                {"question_number": "5", "module": "Module 1", "topic": "ER Diagrams", "marks": 15, "bloom_level": "Understand", "is_pyq": False},
                {"question_number": "6", "module": "Module 2", "topic": "SQL", "marks": 15, "bloom_level": "Understand", "is_pyq": True},
                {"question_number": "7", "module": "Module 3", "topic": "Normalization", "marks": 15, "bloom_level": "Apply", "is_pyq": False},
                {"question_number": "8", "module": "Module 4", "topic": "Transactions", "marks": 15, "bloom_level": "Understand", "is_pyq": False}
            ]
        }
    ],
    "strategy_notes": "Basic blueprint"
}


# ============================================================================
# TEST EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("\n" + "🎓 BLUEPRINT CRITIC AGENT - TEST SUITE")
    print("="*100)
    
    # Test 1: Good Blueprint
    print("\n📝 TEST 1: Evaluating GOOD Blueprint")
    print("-"*100)
    
    try:
        critique_good = critique_blueprint(
            blueprint=SAMPLE_BLUEPRINT_GOOD,
            syllabus=SAMPLE_SYLLABUS,
            pyq_analysis=SAMPLE_PYQ_ANALYSIS,
            bloom_coverage=SAMPLE_BLOOM_COVERAGE,
            teacher_input=SAMPLE_TEACHER_INPUT,
            paper_pattern=SAMPLE_PAPER_PATTERN
        )
        
        print_critique_report(critique_good)
        
        # Save to file
        with open("critique_good_blueprint.json", 'w') as f:
            json.dump(critique_good, f, indent=2)
        print("✅ Saved to: critique_good_blueprint.json\n")
        
    except Exception as e:
        print(f"❌ ERROR in Test 1: {e}\n")
        import traceback
        traceback.print_exc()
    
    # Test 2: Poor Blueprint
    print("\n" + "="*100)
    print("📝 TEST 2: Evaluating POOR Blueprint (with intentional issues)")
    print("-"*100)
    
    try:
        critique_poor = critique_blueprint(
            blueprint=SAMPLE_BLUEPRINT_POOR,
            syllabus=SAMPLE_SYLLABUS,
            pyq_analysis=SAMPLE_PYQ_ANALYSIS,
            bloom_coverage=SAMPLE_BLOOM_COVERAGE,
            teacher_input=SAMPLE_TEACHER_INPUT,
            paper_pattern=SAMPLE_PAPER_PATTERN
        )
        
        print_critique_report(critique_poor)
        
        # Save to file
        with open("critique_poor_blueprint.json", 'w') as f:
            json.dump(critique_poor, f, indent=2)
        print("✅ Saved to: critique_poor_blueprint.json\n")
        
    except Exception as e:
        print(f"❌ ERROR in Test 2: {e}\n")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*100)
    print("🎉 Testing Complete!")
    print("="*100)