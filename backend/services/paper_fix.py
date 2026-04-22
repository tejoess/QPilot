"""
Paper Fixer - Surgical repair for question paper verification failures.

Root cause from logs: blueprint has wrong marks → paper inherits them →
re-selecting questions (paper_fix) regenerates text but KEEPS wrong marks
→ loop never converges.

Fix strategy (two-phase):
  Phase 1 — Blueprint mark correction (deterministic, no LLM):
    Compute which questions have wrong marks vs paper_pattern.
    Correct them directly in the blueprint so the next generation is correct.

  Phase 2 — Question re-selection (only for quality issues):
    For issues that are about content (repeated topic, wrong text, quality),
    re-select those specific questions using the now-correct blueprint.

This means the paper fixer MUTATES the blueprint too, which is passed back
to the repair_paper_loop so subsequent iterations use the corrected version.
"""

import copy
import uuid
from typing import Dict, List, Set, Tuple, Optional

from backend.services.question_selection.question_service import (
    generate_new_question,
    generate_new_question_with_gdt,
    _needs_gdt,
    rephrase_pyq,
    find_match,
)


# ─────────────────────────────────────────────────────────────
# PHASE 1: BLUEPRINT MARK CORRECTION
# ─────────────────────────────────────────────────────────────

def _correct_blueprint_marks(blueprint: Dict, paper_pattern: Dict) -> Tuple[Dict, List[str]]:
    """
    Correct marks in the blueprint so they match the paper_pattern section spec.
    Returns (corrected_blueprint, change_log).

    Strategy:
      For each section, if a per-section marks_per_question is specified,
      set every question in that section to that value.
      After per-section correction, do a final balance pass to hit total_marks exactly.
    """
    new_bp   = copy.deepcopy(blueprint)
    changes  = []

    pat_map = {s["section_name"]: s for s in paper_pattern.get("sections", [])}

    # Pass 1 — enforce marks_per_question per section
    for section in new_bp.get("sections", []):
        name = section["section_name"]
        pat  = pat_map.get(name, {})
        exp_mpq = pat.get("marks_per_question")
        if not exp_mpq:
            continue
        for q in section.get("questions", []):
            if q.get("marks") != exp_mpq:
                changes.append(
                    f"Q{q['question_number']}: marks {q['marks']}→{exp_mpq} "
                    f"(section rule)"
                )
                q["marks"] = exp_mpq

    # Pass 2 — total marks balance
    exp_total = paper_pattern.get("total_marks", 0)
    all_qs    = [q for s in new_bp.get("sections", []) for q in s.get("questions", [])]
    current   = sum(q.get("marks", 0) for q in all_qs)
    delta     = exp_total - current

    if delta != 0:
        # Adjust the last question to close the gap (simplest deterministic fix)
        allowed = paper_pattern.get("allowed_marks_per_question", [])
        last_q  = all_qs[-1] if all_qs else None
        if last_q:
            new_marks = last_q["marks"] + delta
            # Clamp to allowed values if specified
            if allowed:
                closest = min(allowed, key=lambda x: abs(x - new_marks))
                new_marks = closest
            if new_marks > 0:
                changes.append(
                    f"Q{last_q['question_number']}: marks {last_q['marks']}→{new_marks} "
                    f"(total balance, delta was {delta:+d})"
                )
                last_q["marks"] = new_marks

    if changes:
        print(f"  📐 Blueprint mark corrections ({len(changes)}):")
        for c in changes:
            print(f"     • {c}")
    else:
        print("  ✅ Blueprint marks already correct — no corrections needed")

    return new_bp, changes


# ─────────────────────────────────────────────────────────────
# PHASE 2: ISSUE PARSING & QUESTION RE-SELECTION
# ─────────────────────────────────────────────────────────────

def _parse_flagged_questions(paper_verdict: Dict) -> List[str]:
    """
    Extract question numbers from the 'issues' list in paper_verdict.
    Accepts formats: Q1a, Q2b, Q10, etc.
    """
    flagged: Set[str] = set()
    for iss in paper_verdict.get("issues", []):
        q_ref = iss.get("question", "")
        for token in q_ref.replace(",", " ").split():
            if token.upper().startswith("Q") and len(token) > 1:
                flagged.add(token[1:])   # strip Q prefix
    return list(flagged)


def _find_duplicate_topic_questions(draft_paper: Dict) -> List[str]:
    """Return question numbers of SECOND+ occurrences of the same topic."""
    seen: Dict[str, str] = {}
    duplicates: List[str] = []
    for section in draft_paper.get("sections", []):
        for q in section.get("questions", []):
            key   = f"{q.get('topic', '')}__{q.get('subtopic', '')}"
            q_num = str(q.get("question_number", ""))
            if key in seen:
                duplicates.append(q_num)
            else:
                seen[key] = q_num
    return duplicates


def _collect_used_pyq_ids(draft_paper: Dict, skip_questions: List[str]) -> Set[str]:
    used: Set[str] = set()
    skip_set = set(skip_questions)
    for section in draft_paper.get("sections", []):
        for q in section.get("questions", []):
            if str(q.get("question_number", "")) not in skip_set:
                pid = q.get("source_pyq_id")
                if pid:
                    used.add(str(pid))
    return used


def _build_question_history(draft_paper: Dict) -> List[str]:
    """Build the current complete question history from the paper itself."""
    history: List[str] = []
    for section in draft_paper.get("sections", []):
        for q in section.get("questions", []):
            text = q.get("question_text", "")
            if not str(text).strip():
                continue
            history.append(str(text).strip())
    if history:
        return history

    stored_history = draft_paper.get("question_history", [])
    if isinstance(stored_history, list):
        normalized: List[str] = []
        for item in stored_history:
            if isinstance(item, dict):
                item = item.get("text") or item.get("question_text") or item.get("question") or ""
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized
    return []


def _get_blueprint_question(blueprint: Dict, question_number: str) -> Optional[Dict]:
    for section in blueprint.get("sections", []):
        for q in section.get("questions", []):
            if str(q.get("question_number", "")) == str(question_number):
                return q
    return None


def _reselect_one_question(
    blueprint_q: Dict,
    pyq_bank: List[Dict],
    used_pyq_ids: Set[str],
    teacher_input: Optional[Dict] = None,
    history: Optional[List[str]] = None,
) -> Dict:
    """Re-run PYQ-first selection for a single question spec."""
    topic       = blueprint_q.get("topic", "")
    subtopic    = blueprint_q.get("subtopic", "")
    module      = blueprint_q.get("module", "")
    marks       = blueprint_q.get("marks", 5)
    bloom_level = blueprint_q.get("bloom_level", "Understand")
    is_pyq      = blueprint_q.get("is_pyq", False)
    q_num       = blueprint_q.get("question_number", "?")

    selected_text    = None
    selection_method = None
    source_pyq_id    = None

    if not is_pyq:
        if _needs_gdt(bloom_level, marks):
            selected_text, gdt_blocks = generate_new_question_with_gdt(
                topic, subtopic, module, marks, bloom_level, q_num,
                teacher_input, history=history,
            )
        else:
            selected_text = generate_new_question(topic, subtopic, module, marks, bloom_level, q_num, teacher_input, history=history)
            gdt_blocks = []
        selection_method = "generated_direct"
    else:
        gdt_blocks = []
        # Level 1 — exact match
        match = find_match(pyq_bank, used_pyq_ids, level=1, topic=topic, marks=marks, bloom_level=bloom_level)
        if match:
            mid  = match.get("id", "unknown")
            selected_text    = match.get("text", match.get("question", ""))
            selection_method = "pyq_exact"
            source_pyq_id    = mid
            if mid != "unknown": used_pyq_ids.add(mid)

        # Level 2 — drop marks
        if not match:
            match = find_match(pyq_bank, used_pyq_ids, level=2, topic=topic, bloom_level=bloom_level)
            if match:
                mid  = match.get("id", "unknown")
                selected_text    = rephrase_pyq(match.get("text", match.get("question", "")), marks, topic, bloom_level, history=history)
                selection_method = "pyq_rephrased_marks"
                source_pyq_id    = mid
                if mid != "unknown": used_pyq_ids.add(mid)

        # Level 3 — topic only
        if not match:
            match = find_match(pyq_bank, used_pyq_ids, level=3, topic=topic)
            if match:
                mid  = match.get("id", "unknown")
                selected_text    = rephrase_pyq(match.get("text", match.get("question", "")), marks, topic, bloom_level, history=history)
                selection_method = "pyq_rephrased_bloom"
                source_pyq_id    = mid
                if mid != "unknown": used_pyq_ids.add(mid)

        # Fallback
        if not match:
            if _needs_gdt(bloom_level, marks):
                selected_text, gdt_blocks = generate_new_question_with_gdt(
                    topic, subtopic, module, marks, bloom_level, q_num,
                    teacher_input, history=history,
                )
            else:
                selected_text = generate_new_question(topic, subtopic, module, marks, bloom_level, q_num, teacher_input, history=history)
            selection_method = "generated_fallback"

    return {
        "id":               str(uuid.uuid4())[:8],
        "question_number":  q_num,
        "module":           module,
        "topic":            topic,
        "subtopic":         subtopic,
        "marks":            marks,
        "bloom_level":      bloom_level,
        "question_text":    selected_text or "",
        "selection_method": selection_method,
        "source_pyq_id":    source_pyq_id,
        "is_pyq_sourced":   source_pyq_id is not None,
        "gdt":              gdt_blocks,
    }


# ─────────────────────────────────────────────────────────────
# MAIN FIX FUNCTION
# ─────────────────────────────────────────────────────────────

def fix_paper(
    draft_paper: Dict,
    paper_verdict: Dict,
    blueprint: Dict,
    pyq_bank: List[Dict],
    paper_pattern: Dict,
    teacher_input: Optional[Dict] = None,
    iteration: int = 1,
) -> Tuple[Dict, Dict, List[str]]:
    """
    Two-phase repair of the draft question paper.

    Returns:
        (repaired_draft_paper, corrected_blueprint, change_log)

    The corrected_blueprint is returned so repair_paper_loop can store it
    and pass it to future iterations / re-verification calls.
    """
    print(f"\n{'=' * 58}")
    print(f"🔧  PAPER FIXER — Iteration {iteration}")
    print(f"{'=' * 58}")

    issues  = paper_verdict.get("issues", [])
    change_log: List[str] = []

    # ── Phase 1: Fix blueprint marks ────────────────────────────────────────
    print("\n  📐 Phase 1: Blueprint mark correction")
    corrected_blueprint, mark_changes = _correct_blueprint_marks(blueprint, paper_pattern)
    change_log.extend(mark_changes)

    # Sync marks from corrected blueprint back into the draft paper
    # (don't regenerate text — just update the marks field)
    bp_q_map = {
        str(q.get("question_number", "")): q
        for s in corrected_blueprint.get("sections", [])
        for q in s.get("questions", [])
    }

    synced_paper = copy.deepcopy(draft_paper)
    marks_synced = []
    for section in synced_paper.get("sections", []):
        for q in section.get("questions", []):
            num    = str(q.get("question_number", ""))
            bp_q   = bp_q_map.get(num)
            if bp_q and q.get("marks") != bp_q.get("marks"):
                old_m = q["marks"]
                q["marks"] = bp_q["marks"]
                marks_synced.append(f"Q{num}: marks synced {old_m}→{q['marks']}")

    if marks_synced:
        print(f"  🔄 Marks synced in paper ({len(marks_synced)}):")
        for m in marks_synced:
            print(f"     • {m}")
        change_log.extend(marks_synced)
    else:
        print("  ✅ Paper marks already match blueprint")

    # ── Phase 2: Re-select questions with quality issues ─────────────────────
    print("\n  🔍 Phase 2: Content re-selection")

    flagged_from_issues = _parse_flagged_questions(paper_verdict)
    flagged_from_dupes  = _find_duplicate_topic_questions(synced_paper)
    empty_text_qs       = [
        str(q.get("question_number", ""))
        for s in synced_paper.get("sections", [])
        for q in s.get("questions", [])
        if not q.get("question_text", "").strip()
    ]

    all_flagged = list(set(flagged_from_issues + flagged_from_dupes + empty_text_qs))

    if not all_flagged and paper_verdict.get("verdict") == "REJECTED":
        # No specific questions to target — regenerate weakest ones
        method_priority = ["generated_fallback", "pyq_rephrased_bloom", "pyq_rephrased_marks"]
        for method in method_priority:
            for section in synced_paper.get("sections", []):
                for q in section.get("questions", []):
                    if q.get("selection_method") == method:
                        all_flagged.append(str(q.get("question_number", "")))
            if all_flagged:
                break

    if not all_flagged:
        print("  ℹ️  No content issues to fix — mark corrections were sufficient")
        # Update stats
        stats = synced_paper.get("selection_stats", {})
        stats["repair_iterations"] = stats.get("repair_iterations", 0) + 1
        synced_paper["selection_stats"] = stats
        synced_paper["question_history"] = _build_question_history(synced_paper)
        return synced_paper, corrected_blueprint, change_log

    print(f"  📌 Questions to re-select: {all_flagged}")
    used_pyq_ids = _collect_used_pyq_ids(synced_paper, all_flagged)
    print(f"  🔒 Protecting {len(used_pyq_ids)} already-used PYQ IDs")

    for section in synced_paper.get("sections", []):
        for i, q in enumerate(section.get("questions", [])):
            q_num = str(q.get("question_number", ""))
            if q_num not in all_flagged:
                continue

            print(f"\n  🔄 Re-selecting Q{q_num}...")
            bp_q = _get_blueprint_question(corrected_blueprint, q_num)
            if not bp_q:
                bp_q = {
                    "question_number": q_num,
                    "topic":           q.get("topic", ""),
                    "subtopic":        q.get("subtopic", ""),
                    "module":          q.get("module", ""),
                    "marks":           q.get("marks", 5),
                    "bloom_level":     q.get("bloom_level", "Understand"),
                    "is_pyq":          q.get("is_pyq_sourced", False),
                }

            old_method = q.get("selection_method", "unknown")
            current_history = _build_question_history(synced_paper)
            new_q      = _reselect_one_question(bp_q, pyq_bank, used_pyq_ids, teacher_input, history=current_history)
            section["questions"][i] = new_q

            msg = f"Q{q_num}: {old_method} → {new_q['selection_method']}"
            print(f"     ✅ {msg}")
            change_log.append(msg)

    stats = synced_paper.get("selection_stats", {})
    stats["repair_iterations"] = stats.get("repair_iterations", 0) + 1
    synced_paper["selection_stats"] = stats
    synced_paper["used_pyq_ids"] = list(used_pyq_ids)
    synced_paper["question_history"] = _build_question_history(synced_paper)

    print(f"\n  📊 Re-selected {len(all_flagged)} question(s)")
    return synced_paper, corrected_blueprint, change_log