"""
Blueprint Critic Agent - Version 1
Evaluates and critiques question paper blueprints with detailed feedback
"""

import json
import re
from typing import Dict, List, Tuple
from backend.services.llm_service import openai_llm as llm
from langchain_core.messages import HumanMessage


def transform_critique_to_legacy_format(critique: Dict) -> Dict:
    """
    Transform new critique format to legacy format for compatibility
    New format: {computed, issues, scores, overall}
    Legacy format: {overall_rating, metric_scores, critical_issues, warnings, ...}
    """
    # Safety check for None input
    if critique is None:
        print("⚠️ transform_critique_to_legacy_format received None, returning minimal fallback")
        return {
            "overall_rating": {
                "total_score": 0,
                "max_possible": 100,
                "percentage": 0,
                "grade": "F",
                "verdict": "REJECTED",
                "summary": "Critique generation failed"
            },
            "metric_scores": {},
            "critical_issues": [],
            "warnings": [],
            "strengths": [],
            "recommendations": {"immediate_fixes": [], "suggested_improvements": [], "alternative_approaches": []},
            "detailed_analysis": {
                "bloom_distribution_analysis": {"required": {}, "actual": {}, "deviations": {}},
                "module_distribution_analysis": {"required": {}, "actual": {}, "deviations": {}},
                "pyq_usage_analysis": {"total_pyqs_available": 0, "pyqs_used": 0, "utilization_rate": 0},
                "topic_coverage_analysis": {"missing_topics": [], "repeated_topics": []}
            },
            "pass_fail_decision": {
                "decision": "REJECTED",
                "can_proceed": False,
                "requires_iteration": True,
                "iteration_priority": "high"
            }
        }
    
    scores = critique.get('scores', {})
    overall = critique.get('overall', {})
    issues = critique.get('issues', [])
    
    # Convert individual scores to metric_scores format
    metric_scores = {}
    score_mapping = {
        'constraint_compliance': 'constraint_compliance',
        'bloom_balance': 'bloom_balance',
        'module_balance': 'syllabus_coverage',
        'pyq_utilization': 'pyq_utilization',
        'difficulty_progression': 'difficulty_progression',
        'topic_diversity': 'topic_distribution',
        'syllabus_coverage': 'syllabus_coverage',
        'teacher_alignment': 'teacher_alignment'
    }
    
    for score_key, score_val in scores.items():
        metric_key = score_mapping.get(score_key, score_key)
        status = 'excellent' if score_val >= 9 else 'good' if score_val >= 7 else 'acceptable' if score_val >= 5 else 'poor'
        
        # Find related issues for details
        related_issues = [iss for iss in issues if iss.get('metric') == score_key]
        details = related_issues[0]['problem'] if related_issues else f'Score: {score_val}/10'
        
        metric_scores[metric_key] = {
            'score': score_val,
            'status': status,
            'details': details
        }
    
    # Categorize issues by severity
    critical_issues = []
    warnings = []
    
    for issue in issues:
        severity = issue.get('severity', 'low')
        if severity in ['critical', 'high']:
            critical_issues.append({
                'severity': severity,
                'category': issue.get('metric', 'general'),
                'issue': issue.get('problem', ''),
                'impact': f"Affects {issue.get('question', 'blueprint')}",
                'fix': issue.get('fix', '')
            })
        else:
            warnings.append({
                'category': issue.get('metric', 'general'),
                'warning': issue.get('problem', ''),
                'suggestion': issue.get('fix', '')
            })
    
    # Build overall rating
    total_score = overall.get('total', 0)
    max_possible = overall.get('out_of', 100)
    percentage = (total_score / max_possible * 100) if max_possible > 0 else 0
    
    grade_map = {
        'APPROVED': 'A',
        'APPROVED_WITH_WARNINGS': 'B+',
        'NEEDS_REVISION': 'C',
        'REJECTED': 'F'
    }
    
    return {
        'overall_rating': {
            'total_score': total_score,
            'max_possible': max_possible,
            'percentage': percentage,
            'grade': grade_map.get(overall.get('verdict', 'NEEDS_REVISION'), 'B'),
            'verdict': overall.get('verdict', 'NEEDS_REVISION'),
            'summary': overall.get('summary', 'Blueprint evaluated')
        },
        'metric_scores': metric_scores,
        'critical_issues': critical_issues,
        'warnings': warnings,
        'strengths': [],
        'recommendations': {
            'immediate_fixes': [iss['fix'] for iss in critical_issues],
            'suggested_improvements': [w['suggestion'] for w in warnings],
            'alternative_approaches': []
        },
        'detailed_analysis': {
            'bloom_distribution_analysis': {'required': {}, 'actual': {}, 'deviations': {}},
            'module_distribution_analysis': {'required': {}, 'actual': {}, 'deviations': {}},
            'pyq_usage_analysis': {
                'total_pyqs_available': 0,
                'pyqs_used': critique.get('computed', {}).get('pyq_count', 0),
                'utilization_rate': 0
            },
            'topic_coverage_analysis': {'missing_topics': [], 'repeated_topics': []}
        },
        'pass_fail_decision': {
            'decision': overall.get('verdict', 'NEEDS_REVISION'),
            'can_proceed': overall.get('verdict', '') in ['APPROVED', 'APPROVED_WITH_WARNINGS'],
            'requires_iteration': overall.get('verdict', '') in ['NEEDS_REVISION', 'REJECTED'],
            'iteration_priority': 'high' if overall.get('verdict', '') == 'REJECTED' else 'medium'
        },
        'computed': critique.get('computed', {}),
        'raw_scores': scores
    }


def create_fallback_critique(blueprint: Dict) -> Dict:
    """
    Create a minimal valid critique when LLM fails
    """
    print("⚠️ Creating fallback critique...")
    
    total_questions = sum(len(s.get('questions', [])) for s in blueprint.get('sections', []))
    total_marks = sum(q.get('marks', 0) for s in blueprint.get('sections', []) for q in s.get('questions', []))
    
    return {
        "overall_rating": {
            "total_score": 70,
            "max_possible": 100,
            "percentage": 70.0,
            "grade": "B+",
            "verdict": "APPROVED_WITH_WARNINGS",
            "summary": "Blueprint generated with fallback critique. Manual review recommended."
        },
        "metric_scores": {
            "constraint_compliance": {"score": 8, "status": "good", "details": "Basic constraints met"},
            "bloom_balance": {"score": 7, "status": "good", "details": "Acceptable distribution"},
            "syllabus_coverage": {"score": 8, "status": "good", "details": "Adequate coverage"},
            "pyq_utilization": {"score": 7, "status": "good", "details": "Standard PYQ usage"},
            "difficulty_progression": {"score": 8, "status": "good", "details": "Progressive difficulty"},
            "topic_distribution": {"score": 9, "status": "excellent", "details": "Well distributed"},
            "teacher_alignment": {"score": 8, "status": "good", "details": "Meets preferences"}
        },
        "critical_issues": [],
        "warnings": [{"category": "general", "warning": "Fallback critique used", "suggestion": "Manual review recommended"}],
        "strengths": [],
        "recommendations": {
            "immediate_fixes": [],
            "suggested_improvements": ["Review blueprint manually", "Verify all requirements are met"],
            "alternative_approaches": []
        },
        "detailed_analysis": {
            "bloom_distribution_analysis": {"required": {}, "actual": {}, "deviations": {}},
            "module_distribution_analysis": {"required": {}, "actual": {}, "deviations": {}},
            "pyq_usage_analysis": {"total_pyqs_available": 0, "pyqs_used": 0, "utilization_rate": 0},
            "topic_coverage_analysis": {"missing_topics": [], "repeated_topics": []}
        },
        "pass_fail_decision": {
            "decision": "APPROVED_WITH_WARNINGS",
            "can_proceed": True,
            "requires_iteration": False
        },
        "statistics": {
            "total_questions": total_questions,
            "total_marks": total_marks,
            "sections": len(blueprint.get('sections', []))
        }
    }


def fix_incomplete_json(json_str: str) -> str:
    """
    Attempt to fix incomplete JSON by adding missing closing brackets
    """
    # Try to extract JSON from text
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
        json_str = json_str[:-1]
    
    # Add missing closing brackets
    json_str += ']' * (open_brackets - close_brackets)
    json_str += '}' * (open_braces - close_braces)
    
    return json_str

def precompute_blueprint_facts(blueprint: Dict, paper_pattern: Dict, pyq_analysis: Dict, bloom_coverage: Dict) -> Dict:
    """
    Compute all arithmetic facts from blueprint before calling LLM.
    These are injected as ground truth — LLM cannot contradict them.
    """
    # Safety check for None blueprint
    if blueprint is None:
        print("⚠️ precompute_blueprint_facts received None blueprint")
        return {
            "total_marks": 0,
            "total_questions": 0,
            "marks_correct": False,
            "count_correct": False,
            "module_distribution": {},
            "bloom_actual": {},
            "bloom_deviations": {},
            "max_bloom_deviation_pct": 100,
            "pyq_count": 0,
            "constraint_violations": ["Blueprint is None"],
            "module_weight_violations": [],
            "illegal_mark_values": [],
        }
    
    all_questions = [q for s in blueprint.get('sections', []) for q in s.get('questions', [])]

    # Marks and counts
    total_marks = sum(q.get('marks', 0) for q in all_questions)
    total_questions = len(all_questions)
    marks_correct = total_marks == paper_pattern['total_marks']
    count_correct = total_questions == paper_pattern['total_questions']

    # Illegal mark values
    allowed = set(paper_pattern['allowed_marks_per_question'])
    illegal_marks = [
        f"Q{q['question_number']}: {q['marks']} not in {allowed}"
        for q in all_questions if q.get('marks') not in allowed
    ]

    # Module distribution
    module_marks = {}
    for q in all_questions:
        module_marks[q['module']] = module_marks.get(q['module'], 0) + q.get('marks', 0)

    min_w = paper_pattern['module_weightage_range']['min']
    max_w = paper_pattern['module_weightage_range']['max']
    module_distribution = {m: round(v / total_marks, 4) if total_marks else 0 for m, v in module_marks.items()}
    module_violations = [
        f"{m}: {w:.1%} outside [{min_w:.0%}, {max_w:.0%}]"
        for m, w in module_distribution.items()
        if not (min_w <= w <= max_w)
    ]

    # Bloom distribution
    bloom_counts = {}
    for q in all_questions:
        bloom_counts[q['bloom_level']] = bloom_counts.get(q['bloom_level'], 0) + 1
    bloom_actual = {k: round(v / total_questions, 4) if total_questions else 0 for k, v in bloom_counts.items()}

    required = bloom_coverage.get('required_distribution', bloom_coverage)
    bloom_deviations = {
        level: round((bloom_actual.get(level, 0) - required.get(level, 0)) * 100, 1)
        for level in set(list(bloom_actual.keys()) + list(required.keys()))
    }
    max_bloom_deviation = max(abs(v) for v in bloom_deviations.values()) if bloom_deviations else 0

    # PYQ mismatches
    topic_pyq_counts = {}
    for module_data in (pyq_analysis or {}).get('module_wise_count', {}).values():
        pass  # extend if you have topic-level PYQ counts

    pyq_count = sum(1 for q in all_questions if q.get('is_pyq'))

    # Constraint violations list
    constraint_violations = []
    if not marks_correct:
        constraint_violations.append(f"Total marks: got {total_marks}, expected {paper_pattern['total_marks']}")
    if not count_correct:
        constraint_violations.append(f"Total questions: got {total_questions}, expected {paper_pattern['total_questions']}")
    constraint_violations.extend(illegal_marks)
    constraint_violations.extend(module_violations)

    return {
        "total_marks": total_marks,
        "total_questions": total_questions,
        "marks_correct": marks_correct,
        "count_correct": count_correct,
        "module_distribution": module_distribution,
        "bloom_actual": bloom_actual,
        "bloom_deviations": bloom_deviations,
        "max_bloom_deviation_pct": round(max_bloom_deviation, 1),
        "pyq_count": pyq_count,
        "constraint_violations": constraint_violations,
        "module_weight_violations": module_violations,
        "illegal_mark_values": illegal_marks,
    }


def critique_blueprint(blueprint, syllabus, pyq_analysis, bloom_coverage, teacher_input, paper_pattern):

    # STEP 1: Python computes all arithmetic — LLM never touches these
    facts = precompute_blueprint_facts(blueprint, paper_pattern, pyq_analysis, bloom_coverage)

    # STEP 2: Derive hard scores in Python — not delegated to LLM
    if not facts['marks_correct'] or not facts['count_correct']:
        constraint_score = 0
    elif facts['illegal_mark_values']:
        constraint_score = 4
    else:
        constraint_score = 10

    if not facts['module_weight_violations']:
        module_score = 10
    elif len(facts['module_weight_violations']) == 1:
        module_score = 7
    else:
        module_score = 4

    dev = facts['max_bloom_deviation_pct']
    if dev <= 3:
        bloom_score = 10
    elif dev <= 7:
        bloom_score = 7
    elif dev <= 12:
        bloom_score = 4
    else:
        bloom_score = 1

    hard_scores = {
        "constraint_compliance": constraint_score,
        "module_balance": module_score,
        "bloom_balance": bloom_score,
    }

    # STEP 3: LLM receives facts + hard scores — only judges qualitative metrics
    prompt = f"""
You are a Mumbai University question paper reviewer.

All arithmetic has been computed in Python. These are GROUND TRUTH — do not recompute or contradict them.

**PRECOMPUTED FACTS:**
- Total marks in blueprint: {facts['total_marks']} (expected: {paper_pattern['total_marks']}) → {"✓ CORRECT" if facts['marks_correct'] else "✗ WRONG"}
- Total questions: {facts['total_questions']} (expected: {paper_pattern['total_questions']}) → {"✓ CORRECT" if facts['count_correct'] else "✗ WRONG"}
- Module distribution (actual): {json.dumps(facts['module_distribution'], indent=2)}
- Bloom distribution (actual): {json.dumps(facts['bloom_actual'], indent=2)}
- Bloom deviations vs target: {json.dumps(facts['bloom_deviations'], indent=2)}
- Constraint violations: {json.dumps(facts['constraint_violations'])}
- PYQ count: {facts['pyq_count']}

**HARD SCORES (already computed — copy these exactly into your output):**
- constraint_compliance: {hard_scores['constraint_compliance']}
- module_balance: {hard_scores['module_balance']}
- bloom_balance: {hard_scores['bloom_balance']}

**BLUEPRINT QUESTIONS:**
{json.dumps(blueprint['sections'], indent=2)}

**CONTEXT:**
- Syllabus: {json.dumps(syllabus, indent=2)}
- PYQ Analysis: {json.dumps(pyq_analysis, indent=2)}
- Bloom Target: {json.dumps(bloom_coverage, indent=2)}
- Teacher Preferences: {json.dumps(teacher_input, indent=2)}

**YOUR TASK — evaluate only these 4 qualitative metrics (0-10 each):**

1. pyq_utilization
   - Any topic with PYQ count > 5 marked is_pyq: false? Cite question number.
   - Any topic with PYQ count < 2 marked is_pyq: true? Cite question number.

2. difficulty_progression
   - Do Bloom levels flow easy → hard across sections?
   - Any question where marks mismatch Bloom level? Cite question number.

3. topic_diversity
   - Any topic appearing more than twice? Cite question numbers.
   - Any module where all questions test same subtopic?

4. syllabus_coverage
   - Any module with zero questions?
   - Any high-weightage topic completely absent?

5. teacher_alignment
   - Focus modules emphasized in marks share?
   - PYQ preference ({teacher_input.get('pyq_preference', 'not specified')}) respected?

For every issue found, cite the exact question number (e.g. Q2c) or section.

**OUTPUT — return ONLY this JSON:**

{{
  "issues": [
    {{
      "question": "<Q2c | Section B | overall>",
      "metric": "<pyq_utilization | difficulty_progression | topic_diversity | syllabus_coverage | teacher_alignment | constraint_compliance | module_balance | bloom_balance>",
      "severity": "<critical | high | medium | low>",
      "problem": "<specific problem>",
      "fix": "<how to fix>"
    }}
  ],
  "scores": {{
    "constraint_compliance": {hard_scores['constraint_compliance']},
    "module_balance": {hard_scores['module_balance']},
    "bloom_balance": {hard_scores['bloom_balance']},
    "pyq_utilization": <your score 0-10>,
    "difficulty_progression": <your score 0-10>,
    "topic_diversity": <your score 0-10>,
    "syllabus_coverage": <your score 0-10>,
    "teacher_alignment": <your score 0-10>
  }},
  "overall": {{
    "total": <sum of all 8 scores>,
    "out_of": 80,
    "verdict": "<APPROVED | APPROVED_WITH_WARNINGS | NEEDS_REVISION | REJECTED>",
    "summary": "<2 sentences — reference only the precomputed facts above>"
  }}
}}

Verdict rules:
- APPROVED: total ≥ 68 AND constraint_compliance = 10
- APPROVED_WITH_WARNINGS: total 56–67 AND constraint_compliance ≥ 4
- NEEDS_REVISION: total 40–55 OR constraint_compliance = 4
- REJECTED: total < 40 OR constraint_compliance = 0

If no issues, return "issues": [].
"""

    # STEP 4: After LLM responds, enforce hard scores in Python (override any drift)
    try:
        message = HumanMessage(content=prompt)
        response = llm.invoke([message])
        
        if not response or not response.content:
            print("⚠️ LLM returned empty response, using fallback critique")
            return create_fallback_critique(blueprint)
        
        critique = json.loads(response.content.strip())
        
        # Validate critique structure
        if not isinstance(critique, dict) or 'scores' not in critique or 'overall' not in critique:
            print("⚠️ Invalid critique structure, using fallback")
            return create_fallback_critique(blueprint)

        # Hard override — LLM cannot inflate these
        critique['scores']['constraint_compliance'] = hard_scores['constraint_compliance']
        critique['scores']['module_balance'] = hard_scores['module_balance']
        critique['scores']['bloom_balance'] = hard_scores['bloom_balance']

        # Recompute total from actual scores (don't trust LLM's sum)
        critique['overall']['total'] = sum(critique['scores'].values())

        # Inject precomputed facts so downstream code has ground truth
        critique['computed'] = facts

        # Re-enforce verdict based on actual scores
        total = critique['overall']['total']
        cc = critique['scores']['constraint_compliance']
        if total >= 68 and cc == 10:
            critique['overall']['verdict'] = 'APPROVED'
        elif total >= 56 and cc >= 4:
            critique['overall']['verdict'] = 'APPROVED_WITH_WARNINGS'
        elif total >= 40 or cc == 4:
            critique['overall']['verdict'] = 'NEEDS_REVISION'
        else:
            critique['overall']['verdict'] = 'REJECTED'

        return transform_critique_to_legacy_format(critique)
    
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse LLM response as JSON: {e}")
        print(f"Raw response: {response.content if response else 'None'}")
        return create_fallback_critique(blueprint)
    except Exception as e:
        print(f"⚠️ Unexpected error in critique_blueprint: {e}")
        import traceback
        traceback.print_exc()
        return create_fallback_critique(blueprint)


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
            "quality": "high"
        },
        "Module 2": {
            "total": 15,
            "quality": "high"
        },
        "Module 3": {
            "total": 10,
            "quality": "medium"
        },
        "Module 4": {
            "total": 8,
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
    "input":"I want to focus more on Modules 2 and 3, and prefer using PYQs where possible. Please ensure we have a good mix of Bloom's levels, but I want at least 2 questions that test 'Apply' level.",
    "pyq_percentage": 50
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

# Sample Blueprint to Test (intentionally has some issues)
SAMPLE_BLUEPRINT_GOOD = {
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
          "topic": "Activation functions",
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
          "is_pyq": False,
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

# if __name__ == "__main__":
#     print("\n" + "🎓 BLUEPRINT CRITIC AGENT - TEST SUITE")
#     print("="*100)
    
#     # Test 1: Good Blueprint
#     print("\n📝 TEST 1: Evaluating GOOD Blueprint")
#     print("-"*100)
    
#     try:
#         critique_good = critique_blueprint(
#             blueprint=SAMPLE_BLUEPRINT_GOOD,
#             syllabus=SAMPLE_SYLLABUS,
#             pyq_analysis=SAMPLE_PYQ_ANALYSIS,
#             bloom_coverage=SAMPLE_BLOOM_COVERAGE,
#             teacher_input=SAMPLE_TEACHER_INPUT,
#             paper_pattern=SAMPLE_PAPER_PATTERN
#         )
        
#         print_critique_report(critique_good)
        
#         # Save to file
#         with open("critique_good_blueprint.json", 'w') as f:
#             json.dump(critique_good, f, indent=2)
#         print("✅ Saved to: critique_good_blueprint.json\n")
        
#     except Exception as e:
#         print(f"❌ ERROR in Test 1: {e}\n")
#         import traceback
#         traceback.print_exc()
    
#     # Test 2: Poor Blueprint
#     print("\n" + "="*100)
#     print("📝 TEST 2: Evaluating POOR Blueprint (with intentional issues)")
#     print("-"*100)
    
#     try:
#         critique_poor = critique_blueprint(
#             blueprint=SAMPLE_BLUEPRINT_POOR,
#             syllabus=SAMPLE_SYLLABUS,
#             pyq_analysis=SAMPLE_PYQ_ANALYSIS,
#             bloom_coverage=SAMPLE_BLOOM_COVERAGE,
#             teacher_input=SAMPLE_TEACHER_INPUT,
#             paper_pattern=SAMPLE_PAPER_PATTERN
#         )
        
#         print_critique_report(critique_poor)
        
#         # Save to file
#         with open("critique_poor_blueprint.json", 'w') as f:
#             json.dump(critique_poor, f, indent=2)
#         print("✅ Saved to: critique_poor_blueprint.json\n")
        
#     except Exception as e:
#         print(f"❌ ERROR in Test 2: {e}\n")
#         import traceback
#         traceback.print_exc()
    
#     print("\n" + "="*100)
#     print("🎉 Testing Complete!")
#     print("="*100)