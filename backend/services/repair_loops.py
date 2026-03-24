"""
Repair Loops — orchestrate fix → critique/verify → repeat cycles.

Two public functions:
  repair_blueprint_loop(...)  →  (final_blueprint, repair_summary)
  repair_paper_loop(...)      →  (final_draft_paper, repair_summary)

Blueprint loop uses the new simplified scorecard from blueprint_verify.
Paper loop is unchanged in structure but passes knowledge_graph through.
"""

import copy
from typing import Dict, List, Tuple

from backend.services.blueprint.blueprint_verify import critique_blueprint
from backend.services.question_verification.verify_paper import verify_question_paper
from backend.services.blueprint_fix import fix_blueprint
from backend.services.paper_fix import fix_paper


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

BLUEPRINT_MAX_ITERATIONS  = 3
BLUEPRINT_ACCEPT_VERDICT  = "ACCEPTED"

PAPER_MAX_ITERATIONS      = 2
PAPER_ACCEPT_VERDICT      = "ACCEPTED"


# ─────────────────────────────────────────────────────────────
# BLUEPRINT REPAIR LOOP
# ─────────────────────────────────────────────────────────────

def repair_blueprint_loop(
    blueprint: Dict,
    critique: Dict,
    syllabus: Dict,
    knowledge_graph: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    teacher_input: Dict,
    paper_pattern: Dict,
) -> Tuple[Dict, Dict]:
    """
    Run fix → critique → repeat until:
      - Verdict is ACCEPTED, OR
      - max iterations reached → return best blueprint seen.

    New critique schema:
        { metrics, score, verdict, issues, summary }

    Returns:
        (best_blueprint, repair_summary)
        repair_summary = {
            iterations_run, final_verdict, converged,
            change_log, score_history
        }
    """
    print("\n" + "=" * 65)
    print("🔁  BLUEPRINT REPAIR LOOP")
    print("=" * 65)

    current_bp      = copy.deepcopy(blueprint)
    current_critique = critique

    best_bp    = copy.deepcopy(blueprint)
    best_score = critique.get("score", 0.0)

    summary = {
        "iterations_run": 0,
        "final_verdict":  critique.get("verdict", "UNKNOWN"),
        "converged":      False,
        "change_log":     [],
        "score_history":  [best_score],
    }

    if critique.get("verdict") == BLUEPRINT_ACCEPT_VERDICT:
        print(f"  ✅ Blueprint already ACCEPTED (score: {best_score}) — skipping")
        summary["converged"] = True
        return current_bp, summary

    for iteration in range(1, BLUEPRINT_MAX_ITERATIONS + 1):
        print(f"\n  ── Iteration {iteration}/{BLUEPRINT_MAX_ITERATIONS} ──")

        # Fix
        fixed_bp, changes = fix_blueprint(
            blueprint      = current_bp,
            critique       = current_critique,
            paper_pattern  = paper_pattern,
            bloom_coverage = bloom_coverage,
            teacher_input  = teacher_input,
            knowledge_graph = knowledge_graph,
            iteration      = iteration,
        )
        summary["change_log"].append(changes)

        # Re-critique
        print("  🔍 Re-critiquing repaired blueprint...")
        new_critique = critique_blueprint(
            blueprint      = fixed_bp,
            syllabus       = syllabus,
            knowledge_graph = knowledge_graph,
            pyq_analysis   = pyq_analysis,
            bloom_coverage = bloom_coverage,
            teacher_input  = teacher_input,
            paper_pattern  = paper_pattern,
        )

        new_score   = new_critique.get("score", 0.0)
        new_verdict = new_critique.get("verdict", "UNKNOWN")
        summary["score_history"].append(new_score)
        summary["iterations_run"] = iteration

        print(f"  📊 Score: {new_score}/10  |  Verdict: {new_verdict}")
        _print_metrics(new_critique.get("metrics", {}))

        # Track best
        if new_score > best_score:
            best_score = new_score
            best_bp    = copy.deepcopy(fixed_bp)

        current_bp       = fixed_bp
        current_critique = new_critique

        if new_verdict == BLUEPRINT_ACCEPT_VERDICT:
            print(f"  ✅ Blueprint ACCEPTED after {iteration} iteration(s)")
            summary["converged"]     = True
            summary["final_verdict"] = new_verdict
            break
    else:
        print(f"\n  ⚠️  Max iterations ({BLUEPRINT_MAX_ITERATIONS}) reached.")
        print(f"  ↩️  Returning best seen (score: {best_score})")
        summary["final_verdict"] = current_critique.get("verdict", "UNKNOWN")

    _print_repair_summary("BLUEPRINT", summary)
    return best_bp, summary


# ─────────────────────────────────────────────────────────────
# PAPER REPAIR LOOP  (unchanged logic, passes knowledge_graph)
# ─────────────────────────────────────────────────────────────

def repair_paper_loop(
    draft_paper: Dict,
    paper_verdict: Dict,
    blueprint: Dict,
    pyq_bank: List[Dict],
    syllabus: Dict,
    knowledge_graph: Dict,
    pyq_analysis: Dict,
    bloom_coverage: Dict,
    paper_pattern: Dict,
    teacher_input: Dict,
) -> Tuple[Dict, Dict]:
    """
    Run fix → verify → repeat until ACCEPTED or max iterations.

    Returns:
        (best_draft_paper, repair_summary)
    """
    print("\n" + "=" * 65)
    print("🔁  PAPER REPAIR LOOP")
    print("=" * 65)

    current_paper   = copy.deepcopy(draft_paper)
    current_verdict = paper_verdict

    best_paper  = copy.deepcopy(draft_paper)
    best_rating = paper_verdict.get("rating", 0)

    summary = {
        "iterations_run": 0,
        "final_verdict":  paper_verdict.get("verdict", "UNKNOWN"),
        "converged":      False,
        "change_log":     [],
        "rating_history": [best_rating],
    }

    if paper_verdict.get("verdict") == PAPER_ACCEPT_VERDICT:
        print(f"  ✅ Paper already ACCEPTED (rating: {best_rating}) — skipping")
        summary["converged"] = True
        return current_paper, summary

    for iteration in range(1, PAPER_MAX_ITERATIONS + 1):
        print(f"\n  ── Iteration {iteration}/{PAPER_MAX_ITERATIONS} ──")

        fixed_paper, blueprint, changes = fix_paper(
            draft_paper   = current_paper,
            paper_verdict = current_verdict,
            blueprint     = blueprint,
            pyq_bank      = pyq_bank,
            paper_pattern = paper_pattern,
            teacher_input = teacher_input,
            iteration     = iteration,
        )
        summary["change_log"].append(changes)

        print("  📋 Re-verifying repaired paper...")
        new_verdict = verify_question_paper(
            paper          = fixed_paper,
            syllabus       = syllabus,
            knowledge_graph = knowledge_graph,
            pyq_analysis   = pyq_analysis,
            blueprint      = blueprint,
            bloom_coverage = bloom_coverage,
            paper_pattern  = paper_pattern,
            teacher_input  = teacher_input,
        )

        new_rating  = new_verdict.get("rating", 0)
        new_v_label = new_verdict.get("verdict", "UNKNOWN")
        summary["rating_history"].append(new_rating)
        summary["iterations_run"] = iteration

        print(f"  📊 Rating: {new_rating}/10  |  Verdict: {new_v_label}")

        if new_rating > best_rating:
            best_rating = new_rating
            best_paper  = copy.deepcopy(fixed_paper)

        current_paper   = fixed_paper
        current_verdict = new_verdict

        if new_v_label == PAPER_ACCEPT_VERDICT:
            print(f"  ✅ Paper ACCEPTED after {iteration} iteration(s)")
            summary["converged"]     = True
            summary["final_verdict"] = new_v_label
            break
    else:
        print(f"\n  ⚠️  Max iterations ({PAPER_MAX_ITERATIONS}) reached.")
        print(f"  ↩️  Returning best seen (rating: {best_rating})")
        summary["final_verdict"] = current_verdict.get("verdict", "UNKNOWN")

    _print_repair_summary("PAPER", summary)
    return best_paper, summary


# ─────────────────────────────────────────────────────────────
# PRINT HELPERS
# ─────────────────────────────────────────────────────────────

def _print_metrics(metrics: Dict):
    if not metrics:
        return
    labels = {
        "teacher_input_followed": ("Teacher Input",    "HIGH ⭐"),
        "syllabus_oriented":      ("Syllabus Orient.", "HIGH ⭐"),
        "pattern_followed":       ("Pattern Followed", "HIGH ⭐"),
        "module_weightage":       ("Module Weightage", "HIGH ⭐"),
        "bloom_balanced":         ("Bloom Balanced",   "medium"),
        "pyq_utilized":           ("PYQ Utilized",     "medium"),
    }
    for key, (label, prio) in labels.items():
        val = metrics.get(key, "?")
        print(f"       {label:<22} {str(val):<6}  ({prio})")


def _print_repair_summary(label: str, summary: Dict):
    print("\n" + "=" * 65)
    print(f"📋  {label} REPAIR SUMMARY")
    print(f"  Iterations : {summary['iterations_run']}")
    print(f"  Converged  : {summary['converged']}")
    print(f"  Verdict    : {summary['final_verdict']}")
    key = "score_history" if "score_history" in summary else "rating_history"
    history = " → ".join(str(v) for v in summary.get(key, []))
    print(f"  History    : {history}")
    print("=" * 65)