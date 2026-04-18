"""
pipeline.py  — QPilot LangGraph pipeline with repair loops.

Changes vs original:
  1. blueprint_verify_node  → now calls repair_blueprint_loop() when verdict is bad
  2. paper_verify_node      → now calls repair_paper_loop() when verdict is REJECTED
  3. PipelineState          → two new optional fields: blueprint_repair_summary,
                                                        paper_repair_summary
  4. New helper save_repair_summary() keeps audit trail on disk
  5. Everything else is identical to the original file
"""

import asyncio
import json
import os
from datetime import datetime
from typing import TypedDict, Optional, List, cast
from langgraph.graph import StateGraph, END

from backend.websocket.manager import manager
from backend.services.prompts import format_syllabus as SYLLABUS_PROMPT
from backend.services.input_analysis.syllabus_service import get_syllabus_json
from backend.services.input_analysis.pyq_service import format_pyqs
from backend.services.input_analysis.knowledge_graph import build_knowledge_graph_from_minimal_syllabus
from backend.services.blueprint.blueprint_service import generate_blueprint
from backend.services.blueprint.blueprint_verify import critique_blueprint
from backend.services.question_selection.question_service import select_questions
from backend.services.question_verification.verify_paper import verify_question_paper
from backend.services.input_analysis.process_pdf import extract_text_from_pdf
from backend.services.llm_service import openrouter_llm, openai_llm
from openai import RateLimitError

# ── NEW imports ──────────────────────────────────────────────────────────────
from backend.services.repair_loops import repair_blueprint_loop, repair_paper_loop
# ─────────────────────────────────────────────────────────────────────────────


# ============================================================================
# STATE
# ============================================================================

class PipelineState(TypedDict):
    session_id: str
    pdf_path: Optional[str]
    pyqs_pdf_path: Optional[str]
    syllabus_text: Optional[str]
    syllabus: Optional[dict]
    knowledge_graph: Optional[dict]
    pyqs_text: Optional[str]
    pyqs: Optional[dict]
    teacher_inputs: Optional[dict]
    bloom_taxanomy_levels: Optional[dict]
    qp_pattern: Optional[dict]
    pyqs_analysis: Optional[dict]
    blueprint: Optional[dict]
    blueprint_verdict: Optional[dict]
    draft_paper: Optional[dict]
    paper_verdict: Optional[dict]
    final_path: Optional[str]
    # ── NEW ──────────────────────────────────────────
    blueprint_repair_summary: Optional[dict]
    paper_repair_summary: Optional[dict]
    # ─────────────────────────────────────────────────


# ============================================================================
# HELPERS
# ============================================================================

async def send(session_id: str, message: str):
    await manager.send(session_id, message)


async def save_json_data(session_id: str, filename: str, data: dict, silent: bool = False) -> str:
    session_folder = os.path.join("backend", "services", "data", session_id)
    os.makedirs(session_folder, exist_ok=True)
    file_path = os.path.join(session_folder, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    if not silent:
        try:
            dump_str = json.dumps({'file': filename, 'content': data}, default=str)
            if len(dump_str) > 8000:
                dump_str = dump_str[:8000] + "\n... [view truncated in backend]"
            await manager.send_log(session_id, "info", f"JSON_DATA:{dump_str}")
        except Exception as e:
            pass
    return file_path


def compute_dynamic_module_weights(
    total_marks: int,
    total_questions: int, 
    num_active_modules: int,   # modules teacher actually wants covered
    allowed_marks: list
) -> dict:
    """
    Compute feasible min/max module weightage for this specific paper size.
    
    Rule: min must be achievable with at least 1 question of smallest marks value.
    Max must leave room for other modules to each get at least 1 question.
    """
    if num_active_modules == 0:
        return {"min": 0.0, "max": 1.0}
    
    smallest_marks = min(allowed_marks) if allowed_marks else 2
    largest_marks  = max(allowed_marks) if allowed_marks else 10
    
    # Min = smallest possible single question as fraction of total
    computed_min = round(smallest_marks / total_marks, 3)
    
    # Max = total minus (num_modules - 1) minimum questions
    # i.e. worst case: one module gets everything except one question per other module
    marks_reserved_for_others = (num_active_modules - 1) * smallest_marks
    computed_max = round((total_marks - marks_reserved_for_others) / total_marks, 3)
    computed_max = min(computed_max, 0.60)  # hard cap at 60% regardless
    
    # Safety: if min > max (impossible paper), relax to 0–1
    if computed_min >= computed_max:
        return {"min": 0.0, "max": 1.0}
    
    return {"min": computed_min, "max": computed_max}


# ============================================================================
# KNOWLEDGE GRAPH HELPERS (deterministic topic normalization)
# ============================================================================

def _normalize_for_match(text: str) -> str:
    """
    Normalize topic strings for matching remaps (case-insensitive, punctuation-free).
    """
    import re
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _flatten_kg_topic_labels(knowledge_graph: dict) -> set[str]:
    """
    KG produced by `generate_structured_tree()` has shape:
      { "Modules": [ { "Topics": [ { "Topic_Name": ..., "Subtopics": [...] } ] } ] }
    We defensively support minor key casing/variants.
    """
    if not isinstance(knowledge_graph, dict):
        return set()

    modules = knowledge_graph.get("Modules") or knowledge_graph.get("modules") or []
    labels: set[str] = set()
    if not isinstance(modules, list):
        return labels

    for mod in modules:
        if not isinstance(mod, dict):
            continue
        topics = mod.get("Topics") or mod.get("topics") or []
        if not isinstance(topics, list):
            continue
        for t in topics:
            if not isinstance(t, dict):
                continue
            topic_name = (
                t.get("Topic_Name")
                or t.get("topic_name")
                or t.get("Topic")
                or t.get("topic")
            )
            if isinstance(topic_name, str) and topic_name.strip():
                labels.add(topic_name.strip())
            subtopics = t.get("Subtopics") or t.get("subtopics") or []
            if isinstance(subtopics, list):
                for st in subtopics:
                    if isinstance(st, str) and st.strip():
                        labels.add(st.strip())
    return labels


def map_blueprint_topics_to_knowledge_graph(blueprint: dict, knowledge_graph: dict) -> dict:
    """
    Fix blueprint question `topic` values so they must be exact KG labels
    (Topic_Name or Subtopics entry).
    """
    if not isinstance(blueprint, dict):
        return blueprint

    allowed_labels = _flatten_kg_topic_labels(knowledge_graph)
    if not allowed_labels:
        return blueprint

    from difflib import SequenceMatcher

    allowed_norm_map = {lab: _normalize_for_match(lab) for lab in allowed_labels}

    def best_label_for(raw_topic: str) -> str | None:
        raw_topic = raw_topic or ""
        if not raw_topic.strip():
            return None

        # Exact match
        if raw_topic.strip() in allowed_labels:
            return raw_topic.strip()

        raw_norm = _normalize_for_match(raw_topic)

        # Containment preference (helps with question text containing the label)
        containment_best = None
        for lab in allowed_labels:
            lab_norm = allowed_norm_map.get(lab, "")
            if lab_norm and (lab_norm in raw_norm or raw_norm in lab_norm):
                # choose the shortest label to avoid overly broad matches
                if containment_best is None or len(lab) < len(containment_best):
                    containment_best = lab
        if containment_best:
            return containment_best

        # Fuzzy match fallback
        best = None
        best_score = 0.0
        for lab in allowed_labels:
            lab_norm = allowed_norm_map.get(lab, "")
            if not lab_norm:
                continue
            score = SequenceMatcher(None, raw_norm, lab_norm).ratio()
            if score > best_score:
                best_score = score
                best = lab

        # Tight threshold to reduce wrong remaps
        if best is not None and best_score >= 0.62:
            return best
        return None

    # Mutate in-place (we return the same dict for convenience)
    for section in blueprint.get("sections", []) or []:
        if not isinstance(section, dict):
            continue
        for q in section.get("questions", []) or []:
            if not isinstance(q, dict):
                continue
            mapped = best_label_for(str(q.get("topic", "")))
            if mapped:
                q["topic"] = mapped

    return blueprint

# ============================================================================
# NODES — unchanged from original (syllabus_fetch through pyqs_format)
# ============================================================================

async def syllabus_fetch(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "syllabus_fetch", "running", 0, "Starting syllabus extraction")

    if state.get("syllabus_text"):
        await manager.send_log(session_id, "info", "Using provided text content")
        text = state["syllabus_text"]
    elif state.get("pdf_path"):
        await manager.send_log(session_id, "info", "Extracting text from PDF")
        await manager.send_progress(session_id, "syllabus_fetch", "running", 25, "Reading PDF file")
        pdf_path = cast(str, state["pdf_path"])
        text = extract_text_from_pdf(pdf_path, "syllabus")
        await manager.send_progress(session_id, "syllabus_fetch", "running", 50, "Text extracted successfully")
    else:
        await manager.send_log(session_id, "error", "No syllabus content provided")
        raise ValueError("Either syllabus_text or pdf_path must be provided")

    session_folder = os.path.join("backend", "services", "data", state["session_id"])
    os.makedirs(session_folder, exist_ok=True)
    text_path = os.path.join(session_folder, "syllabus_raw.txt")
    await manager.send_progress(session_id, "syllabus_fetch", "running", 75, "Saving raw text")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(cast(str, text))

    await manager.send_progress(session_id, "syllabus_fetch", "completed", 100, "Saved raw syllabus text")
    return {"syllabus_text": text}


async def syllabus_format(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "syllabus_format", "running", 0, "Starting syllabus parsing")
    await asyncio.sleep(1.5)

    syllabus_json = get_syllabus_json(SYLLABUS_PROMPT, state.get("syllabus_text") or "")
    if not syllabus_json or not isinstance(syllabus_json, dict):
        syllabus_json = {"modules": [], "error": "Failed to parse syllabus"}

    await save_json_data(state["session_id"], "syllabus.json", syllabus_json)
    await manager.send_progress(session_id, "syllabus_format", "completed", 100, "Syllabus formatted successfully")
    await manager.send_completion(session_id, True, {"modules": len(syllabus_json.get("modules", []))})
    return {"syllabus": syllabus_json}


async def knowledge_graph_build_node(state: PipelineState):
    """
    Input-analysis augmentation:
    - Build a structured knowledge graph (topic/subtopic tree)
    - Save it to `knowledge_graph.json`
    """
    session_id = state["session_id"]
    await manager.send_progress(session_id, "knowledge_graph_build", "running", 0, "Building knowledge graph")

    syllabus = state.get("syllabus") or {}
    course_name = syllabus.get("course_name", "")
    modules = syllabus.get("modules", []) or []

    # Minimal syllabus subset for KG generation: course_name + module_name -> topics[]
    module_topics_map = {}
    if isinstance(modules, list):
        for m in modules:
            module_name = m.get("module_name") or f"Module {m.get('module_number', '')}".strip()
            if not module_name:
                continue
            module_topics_map[module_name] = {"topics": m.get("topics", []) or []}

    kg_input = {"course_name": course_name, "modules": module_topics_map}

    await manager.send_progress(session_id, "knowledge_graph_build", "running", 40, "Calling KG builder")

    # Upstream providers can rate-limit; don't crash the pipeline hard on 429.
    max_attempts = 3
    backoff_seconds = 3
    knowledge_graph = None

    for attempt in range(1, max_attempts + 1):
        try:
            knowledge_graph = await asyncio.to_thread(
                build_knowledge_graph_from_minimal_syllabus,
                kg_input,
                openai_llm,
            )
            break
        except RateLimitError as e:
            last_err = str(e)
            await manager.send_log(
                session_id,
                "warning",
                f"⚠️ knowledge_graph_build rate-limited (attempt {attempt}/{max_attempts}). Retrying in {backoff_seconds}s. {last_err}",
            )
            await asyncio.sleep(backoff_seconds)
            backoff_seconds *= 2
        except Exception as e:
            # For any other exception, fail over to the OpenAI model once.
            await manager.send_log(
                session_id,
                "warning",
                f"⚠️ knowledge_graph_build failed on OpenRouter. Falling back to OpenAI. Error: {str(e)}",
            )
            knowledge_graph = await asyncio.to_thread(
                build_knowledge_graph_from_minimal_syllabus,
                kg_input,
                openai_llm,
            )
            break

    if knowledge_graph is None:
        # All OpenRouter attempts exhausted; fall back to OpenAI.
        await manager.send_log(
            session_id,
            "warning",
            "⚠️ knowledge_graph_build exhausted OpenRouter attempts; using OpenAI fallback.",
        )
        knowledge_graph = await asyncio.to_thread(
            build_knowledge_graph_from_minimal_syllabus,
            kg_input,
            openai_llm,
        )

    await save_json_data(session_id, "knowledge_graph.json", knowledge_graph)
    await manager.send_progress(session_id, "knowledge_graph_build", "completed", 100, "Knowledge graph built successfully")
    await manager.send_completion(session_id, True, {"modules": len(module_topics_map)})

    return {"knowledge_graph": knowledge_graph}


async def pyqs_fetch(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "pyqs_fetch", "running", 0, "Starting PYQ extraction")

    # Prefer uploaded PDF when present; text_content may contain only helper hints
    # (e.g., weightage) and should not bypass OCR/extraction.
    if state.get("pyqs_pdf_path"):
        await manager.send_progress(session_id, "pyqs_fetch", "running", 25, "Reading PDF file")
        pyqs_pdf_path = cast(str, state["pyqs_pdf_path"])
        pyqs_text = extract_text_from_pdf(pyqs_pdf_path, "pyqs")
    elif state.get("pyqs_text"):
        pyqs_text = state["pyqs_text"]
    else:
        raise ValueError("Either pyqs_text or pyqs_pdf_path must be provided")

    if pyqs_text:
        session_folder = os.path.join("backend", "services", "data", state["session_id"])
        os.makedirs(session_folder, exist_ok=True)
        with open(os.path.join(session_folder, "pyqs_raw.txt"), "w", encoding="utf-8") as f:
            f.write(pyqs_text)

    await manager.send_progress(session_id, "pyqs_fetch", "completed", 100, "PYQ extraction complete")
    return {"pyqs_text": pyqs_text}


async def pyqs_format_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "pyqs_format", "running", 0, "Starting PYQ parsing")

    pyqs_result = format_pyqs(
        state.get("pyqs_text") or "",
        knowledge_graph_json=state.get("knowledge_graph") or {},
        syllabus_json=state.get("syllabus", {}) or {},
    )
    try:
        pyqs_dict = json.loads(pyqs_result) if isinstance(pyqs_result, str) else pyqs_result
    except Exception:
        pyqs_dict = {"questions": [], "error": "Failed to parse PYQs"}

    # Persist both the raw structured PYQs and the aggregated analysis so that
    # later workflows (like generate_paper_workflow) can load pyqs.json.
    await save_json_data(state["session_id"], "pyqs.json", pyqs_dict)

    from backend.services.input_analysis.pyq_service import analyse_pyqs
    pyqs_analysis = analyse_pyqs(pyqs_dict)
    await save_json_data(state["session_id"], "pyqs_analysis.json", pyqs_analysis)

    await manager.send_log(session_id, "info", f"PYQ analysis: {pyqs_analysis.get('total_pyqs', 0)} questions across {len(pyqs_analysis.get('module_wise_count', {}))} modules")
    await manager.send_progress(session_id, "pyqs_format", "completed", 100, "PYQs formatted successfully")
    await manager.send_completion(session_id, True, {"questions": len(pyqs_dict.get("questions", []))})
    return {"pyqs": pyqs_dict, "pyqs_analysis": pyqs_analysis}


async def blueprint_build_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "blueprint_build", "running", 0, "Starting blueprint generation")
    await asyncio.sleep(2)

    syllabus      = state.get("syllabus") or {}
    knowledge_graph = state.get("knowledge_graph") or {}
    pyqs_analysis = state.get("pyqs_analysis") or {}
    teacher_inputs= state.get("teacher_inputs") or {}
    bloom_levels  = state.get("bloom_taxanomy_levels") or {}
    qp_pattern    = state.get("qp_pattern") or {}

    await manager.send_progress(session_id, "blueprint_build", "running", 40, "Generating blueprint with AI...")
    blueprint = generate_blueprint(syllabus, knowledge_graph, pyqs_analysis, bloom_levels, teacher_inputs, qp_pattern)

    if not isinstance(blueprint, dict):
        blueprint = {"sections": [], "error": "Failed to generate blueprint"}

    await save_json_data(state["session_id"], "blueprint.json", blueprint)
    await manager.send_progress(session_id, "blueprint_build", "completed", 100, "Blueprint generated successfully")
    return {"blueprint": blueprint}


# ============================================================================
# BLUEPRINT VERIFY NODE  ← UPDATED: now runs repair loop
# ============================================================================

async def blueprint_verify_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "blueprint_verify", "running", 0, "Starting blueprint verification")
    await asyncio.sleep(1)

    blueprint     = state.get("blueprint") or {}
    syllabus      = state.get("syllabus") or {}
    knowledge_graph = state.get("knowledge_graph") or {}
    pyqs_analysis = state.get("pyqs_analysis") or {}
    bloom_levels  = state.get("bloom_taxanomy_levels") or {}
    teacher_inputs= state.get("teacher_inputs") or {}
    qp_pattern    = state.get("qp_pattern") or {}

    # ── Step 1: Initial critique ─────────────────────────────────────────────
    await manager.send_progress(session_id, "blueprint_verify", "running", 30, "AI critiquing blueprint...")
    await manager.send_log(session_id, "info", "🔍 Initial blueprint critique")

    initial_critique = critique_blueprint(
        blueprint, syllabus, knowledge_graph, pyqs_analysis, bloom_levels, teacher_inputs, qp_pattern
    )

    initial_verdict = initial_critique.get("verdict", "UNKNOWN")
    await manager.send_log(session_id, "info", f"Initial verdict: {initial_verdict}")

    # ── Step 2: Repair loop if needed ───────────────────────────────────────
    ACCEPT = {"ACCEPTED", "APPROVED"}

    if initial_verdict not in ACCEPT:
        await manager.send_progress(session_id, "blueprint_verify", "running", 50,
                                    f"Blueprint needs repair (verdict: {initial_verdict}) — fixing...")
        await manager.send_log(session_id, "warning",
                               f"⚠️ Blueprint verdict '{initial_verdict}' — starting repair loop")

        final_blueprint, repair_summary = repair_blueprint_loop(
            blueprint     = blueprint,
            critique      = initial_critique,
            syllabus      = syllabus,
            knowledge_graph= knowledge_graph,
            pyq_analysis  = pyqs_analysis,
            bloom_coverage= bloom_levels,
            teacher_input = teacher_inputs,
            paper_pattern = qp_pattern,
        )

        await manager.send_log(
            session_id, "info",
            f"🔧 Blueprint repair done: {repair_summary['iterations_run']} iteration(s), "
            f"converged={repair_summary['converged']}, "
            f"final verdict={repair_summary['final_verdict']}"
        )
    else:
        await manager.send_log(session_id, "info", "✅ Blueprint acceptable — no repair needed")
        final_blueprint  = blueprint
        repair_summary   = {
            "iterations_run": 0,
            "converged": True,
            "final_verdict": initial_verdict,
            "change_log": [],
            "score_history": [],
        }

    # Deterministic post-processing: ensure blueprint `topic` is always a valid KG label.
    # Without this, blueprint may mistakenly put PYQ question text into `topic`, breaking PYQ matching.
    final_blueprint = map_blueprint_topics_to_knowledge_graph(final_blueprint, knowledge_graph)

    # ── Step 3: Final critique on the (possibly repaired) blueprint ──────────
    await manager.send_progress(session_id, "blueprint_verify", "running", 85,
                                "Running final critique on repaired blueprint...")
    final_critique = critique_blueprint(
        final_blueprint, syllabus, knowledge_graph, pyqs_analysis, bloom_levels, teacher_inputs, qp_pattern
    )

    # ── Step 4: Persist ──────────────────────────────────────────────────────
    await save_json_data(state["session_id"], "blueprint.json",              final_blueprint, silent=True)
    await save_json_data(state["session_id"], "blueprint_verification.json", final_critique)
    await save_json_data(state["session_id"], "blueprint_repair_summary.json", repair_summary, silent=True)

    await manager.send_log(session_id, "info", "💾 Saved: blueprint.json (repaired)")
    await manager.send_log(session_id, "info", "💾 Saved: blueprint_verification.json")
    await manager.send_log(session_id, "info", "💾 Saved: blueprint_repair_summary.json")
    await manager.send_progress(session_id, "blueprint_verify", "completed", 100, "Blueprint verified and repaired")

    return {
        "blueprint":                final_blueprint,   # ← overwrites with repaired version
        "blueprint_verdict":        final_critique,
        "blueprint_repair_summary": repair_summary,
    }


# ============================================================================
# QUESTION SELECT NODE  — unchanged
# ============================================================================

async def question_select_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "question_select", "running", 0, "Starting question selection")
    await asyncio.sleep(2)

    blueprint = state.get("blueprint") or {}
    pyqs      = state.get("pyqs", {})
    pyq_list  = pyqs.get("questions", []) if isinstance(pyqs, dict) else []

    await manager.send_log(session_id, "info", f"Available PYQ pool: {len(pyq_list)} questions")
    await manager.send_progress(session_id, "question_select", "running", 40, "Selecting questions...")

    draft_paper = select_questions(cast(dict, blueprint), pyq_list, teacher_input=state.get("teacher_inputs") or {}, qp_pattern=state.get("qp_pattern") or {})

    if not isinstance(draft_paper, dict):
        draft_paper = {"sections": [], "error": "Failed to select questions"}

    await save_json_data(state["session_id"], "draft_paper.json", draft_paper)
    await manager.send_progress(session_id, "question_select", "completed", 100, "Questions selected successfully")
    return {"draft_paper": draft_paper}


# ============================================================================
# PAPER VERIFY NODE  ← UPDATED: now runs repair loop
# ============================================================================

async def paper_verify_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "paper_verify", "running", 0, "Starting paper verification")
    await asyncio.sleep(2)

    draft_paper   = state.get("draft_paper") or {}
    syllabus      = state.get("syllabus") or {}
    knowledge_graph = state.get("knowledge_graph") or {}
    pyqs_analysis = state.get("pyqs_analysis") or {}
    blueprint     = state.get("blueprint") or {}
    bloom_levels  = state.get("bloom_taxanomy_levels") or {}
    qp_pattern    = state.get("qp_pattern") or {}
    teacher_inputs= state.get("teacher_inputs") or {}
    pyqs          = state.get("pyqs") or {}
    pyq_list      = pyqs.get("questions", []) if isinstance(pyqs, dict) else []

    # ── Step 1: Initial verification ─────────────────────────────────────────
    await manager.send_progress(session_id, "paper_verify", "running", 25, "Running initial verification...")
    await manager.send_log(session_id, "info", "📋 Initial paper verification")

    initial_verdict = verify_question_paper(
        paper         = draft_paper,
        syllabus      = syllabus,
        knowledge_graph= knowledge_graph,
        pyq_analysis  = pyqs_analysis,
        blueprint     = blueprint,
        bloom_coverage= bloom_levels,
        paper_pattern = qp_pattern,
        teacher_input = teacher_inputs,
    )

    initial_label = initial_verdict.get("verdict", "UNKNOWN")
    initial_rating= initial_verdict.get("rating", 0)
    await manager.send_log(session_id, "info",
                           f"Initial verdict: {initial_label} (rating: {initial_rating}/10)")

    # ── Step 2: Repair loop if needed ────────────────────────────────────────
    if initial_label != "ACCEPTED":
        await manager.send_progress(session_id, "paper_verify", "running", 45,
                                    f"Paper needs repair (verdict: {initial_label}) — fixing...")
        await manager.send_log(session_id, "warning",
                               f"⚠️ Paper verdict '{initial_label}' — starting repair loop")

        final_paper, repair_summary = repair_paper_loop(
            draft_paper   = draft_paper,
            paper_verdict = initial_verdict,
            blueprint     = blueprint,
            pyq_bank      = pyq_list,
            syllabus      = syllabus,
            knowledge_graph= knowledge_graph,
            pyq_analysis  = pyqs_analysis,
            bloom_coverage= bloom_levels,
            paper_pattern = qp_pattern,
            teacher_input = teacher_inputs,
        )

        await manager.send_log(
            session_id, "info",
            f"🔧 Paper repair done: {repair_summary['iterations_run']} iteration(s), "
            f"converged={repair_summary['converged']}, "
            f"final verdict={repair_summary['final_verdict']}"
        )
    else:
        await manager.send_log(session_id, "info", "✅ Paper accepted on first pass — no repair needed")
        final_paper    = draft_paper
        repair_summary = {
            "iterations_run": 0,
            "converged": True,
            "final_verdict": initial_label,
            "change_log": [],
            "rating_history": [initial_rating],
        }

    # ── Step 3: Final verification on the (possibly repaired) paper ──────────
    if initial_label != "ACCEPTED" and int(repair_summary.get("iterations_run", 0)) > 0:
        # Paper was repaired — need a fresh verdict on the new paper
        await manager.send_progress(session_id, "paper_verify", "running", 85,
                                    "Re-verifying repaired paper...")
        final_verdict = verify_question_paper(
            paper=final_paper,
            syllabus=syllabus,
            knowledge_graph=knowledge_graph,
            pyq_analysis=pyqs_analysis,
            blueprint=blueprint,
            bloom_coverage=bloom_levels,
            paper_pattern=qp_pattern,
            teacher_input=teacher_inputs,
        )
    else:
        # No repair ran — reuse the verdict we already have, no extra LLM call
        final_verdict = initial_verdict
        await manager.send_log(session_id, "info",
                               "Reusing initial verdict — no repair was performed")

    final_label  = final_verdict.get("verdict", "UNKNOWN")
    final_rating = final_verdict.get("rating", 0)
    await manager.send_log(session_id, "info",
                           f"Final paper verdict: {final_label} (rating: {final_rating}/10)")

    # ── Step 4: Persist ──────────────────────────────────────────────────────
    await save_json_data(state["session_id"], "draft_paper.json",          final_paper, silent=True)
    await save_json_data(state["session_id"], "paper_verification.json",   final_verdict)
    await save_json_data(state["session_id"], "paper_repair_summary.json", repair_summary, silent=True)

    await manager.send_log(session_id, "info", "💾 Saved: draft_paper.json (repaired)")
    await manager.send_log(session_id, "info", "💾 Saved: paper_verification.json")
    await manager.send_log(session_id, "info", "💾 Saved: paper_repair_summary.json")
    await manager.send_progress(session_id, "paper_verify", "completed", 100, "Paper verified and repaired")

    return {
        "draft_paper":          final_paper,       # ← overwrites with repaired version
        "paper_verdict":        final_verdict,
        "paper_repair_summary": repair_summary,
    }


# ============================================================================
# FINAL GENERATE NODE  — updated to include repair summaries in session summary
# ============================================================================

async def final_generate_node(state: PipelineState):
    session_id = state["session_id"]
    await manager.send_progress(session_id, "final_generate", "running", 0, "Starting final paper generation")

    session_folder = os.path.join("backend", "services", "data", session_id)
    draft_paper    = state.get("draft_paper") or {}
    draft_paper_dict = cast(dict, draft_paper)

    await save_json_data(session_id, "final_paper.json", draft_paper_dict)

    bp_repair  = state.get("blueprint_repair_summary") or {}
    pap_repair = state.get("paper_repair_summary") or {}

    summary = {
        "session_id":       session_id,
        "timestamp":        datetime.now().isoformat(),
        "status":           "completed",
        "total_marks":      sum(q.get("marks", 0) for s in draft_paper_dict.get("sections", []) for q in s.get("questions", [])),
        "total_questions":  sum(len(s.get("questions", [])) for s in draft_paper_dict.get("sections", [])),
        "verdict":          (state.get("paper_verdict") or {}).get("verdict", "unknown"),
        "rating":           (state.get("paper_verdict") or {}).get("rating", 0),
        # ── NEW: repair audit trail ──────────────────────────────────────────
        "blueprint_repair": {
            "iterations":      bp_repair.get("iterations_run", 0),
            "converged":       bp_repair.get("converged", True),
            "final_verdict":   bp_repair.get("final_verdict", "N/A"),
            "score_history":   bp_repair.get("score_history", []),
        },
        "paper_repair": {
            "iterations":      pap_repair.get("iterations_run", 0),
            "converged":       pap_repair.get("converged", True),
            "final_verdict":   pap_repair.get("final_verdict", "N/A"),
            "rating_history":  pap_repair.get("rating_history", []),
        },
        # ────────────────────────────────────────────────────────────────────
        "files_generated": {
            "syllabus":                  "syllabus.json",
            "pyqs":                      "pyqs.json",
            "blueprint":                 "blueprint.json",
            "blueprint_verification":    "blueprint_verification.json",
            "blueprint_repair_summary":  "blueprint_repair_summary.json",
            "draft_paper":               "draft_paper.json",
            "paper_verification":        "paper_verification.json",
            "paper_repair_summary":      "paper_repair_summary.json",
            "final_paper":               "final_paper.json",
        },
    }
    await save_json_data(session_id, "session_summary.json", summary)

    final_path = os.path.join(session_folder, "final_question_paper.pdf")
    await manager.send_progress(session_id, "final_generate", "completed", 100,
                                "Question paper generated successfully")
    await manager.send_completion(session_id, True, {
        "session_id":       session_id,
        "total_questions":  summary["total_questions"],
        "total_marks":      summary["total_marks"],
        "verdict":          summary["verdict"],
        "rating":           summary["rating"],
        "output_path":      session_folder,
        "blueprint_repair_iterations": bp_repair.get("iterations_run", 0),
        "paper_repair_iterations":     pap_repair.get("iterations_run", 0),
    })

    return {"final_path": final_path}


# ============================================================================
# GRAPH  — identical topology to original
# ============================================================================

def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("syllabus_fetch",    syllabus_fetch)
    graph.add_node("syllabus_format",   syllabus_format)
    graph.add_node("knowledge_graph_build", knowledge_graph_build_node)
    graph.add_node("pyqs_fetch",        pyqs_fetch)
    graph.add_node("pyqs_format",       pyqs_format_node)
    graph.add_node("blueprint_build",   blueprint_build_node)
    graph.add_node("blueprint_verify",  blueprint_verify_node)
    graph.add_node("question_select",   question_select_node)
    graph.add_node("paper_verify",      paper_verify_node)
    graph.add_node("final_generate",    final_generate_node)

    graph.set_entry_point("syllabus_fetch")
    graph.add_edge("syllabus_fetch",   "syllabus_format")
    graph.add_edge("syllabus_format",  "knowledge_graph_build")
    graph.add_edge("knowledge_graph_build",  "pyqs_fetch")
    graph.add_edge("pyqs_fetch",       "pyqs_format")
    graph.add_edge("pyqs_format",      "blueprint_build")
    graph.add_edge("blueprint_build",  "blueprint_verify")
    graph.add_edge("blueprint_verify", "question_select")
    graph.add_edge("question_select",  "paper_verify")
    graph.add_edge("paper_verify",     "final_generate")
    graph.add_edge("final_generate",   END)

    return graph.compile()


# ============================================================================
# RUNNER  — unchanged
# ============================================================================
def _count_active_modules(syllabus: dict, teacher_inputs: dict) -> int:
    """
    If teacher restricted to specific modules, count only those.
    Otherwise count all syllabus modules.
    """
    teacher_text = str(
        teacher_inputs.get("input") or teacher_inputs.get("preferences") or ""
    ).lower()
    
    # Check if teacher mentioned specific modules (e.g. "last 3 modules", "module 4 5 6")
    import re
    module_numbers = re.findall(r'module\s*(\d+)', teacher_text)
    if module_numbers:
        return len(set(module_numbers))
    
    # Check phrases like "last 3 modules", "first 2 modules"
    last_n = re.search(r'last\s+(\d+)\s+module', teacher_text)
    first_n = re.search(r'first\s+(\d+)\s+module', teacher_text)
    if last_n:
        return int(last_n.group(1))
    if first_n:
        return int(first_n.group(1))
    
    # Default: all modules
    modules = syllabus.get("modules", [])
    return len(modules) if isinstance(modules, list) else len(modules.keys())

async def run_question_paper_pipeline(session_id: str = "default"):
    app = build_graph()
    initial_state: PipelineState = {
        "session_id":              session_id,
        "pdf_path":                None,
        "pyqs_pdf_path":           None,
        "syllabus_text":           None,
        "syllabus":                None,
        "knowledge_graph":        None,
        "pyqs_text":               None,
        "pyqs":                    None,
        "teacher_inputs":          {"focus_areas": [], "preferences": "Standard difficulty"},
        "bloom_taxanomy_levels":   {"remember": 20, "understand": 30, "apply": 30, "analyze": 20},
        "qp_pattern": {
            "total_marks":         80,
            "total_questions":     10,
            "module_weightage_range": {"min": 0.10, "max": 0.30},  # default for standalone runner
            "allowed_marks_per_question": [2, 5, 6, 10, 15],
            "sections": [
                {"section_name": "Section A", "section_description": "Short Answer Questions",
                 "question_count": 5, "marks_per_question": 6},
                {"section_name": "Section B", "section_description": "Long Answer Questions",
                 "question_count": 5, "marks_per_question": 10},
            ],
        },
        "pyqs_analysis":           None,
        "blueprint":               None,
        "blueprint_verdict":       None,
        "draft_paper":             None,
        "paper_verdict":           None,
        "final_path":              None,
        "blueprint_repair_summary": None,
        "paper_repair_summary":    None,
    }
    result = await app.ainvoke(initial_state)
    return result.get("final_path", "generated/final_question_paper.pdf")


# ============================================================================
# SUB-WORKFLOWS  — generate_paper_workflow updated with new state fields
# ============================================================================

async def analyze_syllabus_workflow(session_id, pdf_path=None, text_content=None):
    graph = StateGraph(PipelineState)
    graph.add_node("syllabus_fetch",  syllabus_fetch)
    graph.add_node("syllabus_format", syllabus_format)
    graph.add_node("knowledge_graph_build", knowledge_graph_build_node)
    graph.set_entry_point("syllabus_fetch")
    graph.add_edge("syllabus_fetch", "syllabus_format")
    graph.add_edge("syllabus_format", "knowledge_graph_build")
    graph.add_edge("knowledge_graph_build", END)
    app = graph.compile()
    state: PipelineState = {
        "session_id": session_id,
        "pdf_path": pdf_path,
        "pyqs_pdf_path": None,
        "syllabus_text": text_content,
        "syllabus": None,
        "knowledge_graph": None,
        "pyqs_text": None,
        "pyqs": None,
        "teacher_inputs": None,
        "bloom_taxanomy_levels": None,
        "qp_pattern": None,
        "pyqs_analysis": None,
        "blueprint": None,
        "blueprint_verdict": None,
        "draft_paper": None,
        "paper_verdict": None,
        "final_path": None,
        "blueprint_repair_summary": None,
        "paper_repair_summary": None,
    }
    return await app.ainvoke(state)


async def analyze_pyqs_workflow(session_id, syllabus_session_id, pdf_path=None, text_content=None):
    syllabus_path = os.path.join("backend", "services", "data", syllabus_session_id, "syllabus.json")
    kg_path = os.path.join("backend", "services", "data", syllabus_session_id, "knowledge_graph.json")
    with open(syllabus_path, "r", encoding="utf-8") as f:
        syllabus_data = json.load(f)

    knowledge_graph_data = {}
    try:
        with open(kg_path, "r", encoding="utf-8") as f:
            knowledge_graph_data = json.load(f)
    except Exception:
        knowledge_graph_data = {}

    graph = StateGraph(PipelineState)
    graph.add_node("pyqs_fetch",  pyqs_fetch)
    graph.add_node("pyqs_format", pyqs_format_node)
    graph.set_entry_point("pyqs_fetch")
    graph.add_edge("pyqs_fetch", "pyqs_format")
    graph.add_edge("pyqs_format", END)
    app = graph.compile()
    state: PipelineState = {
        "session_id": session_id,
        "pdf_path": None,
        "pyqs_pdf_path": pdf_path,
        "syllabus_text": None,
        "syllabus": syllabus_data,
        "knowledge_graph": knowledge_graph_data,
        "pyqs_text": text_content,
        "pyqs": None,
        "teacher_inputs": None,
        "bloom_taxanomy_levels": None,
        "qp_pattern": None,
        "pyqs_analysis": None,
        "blueprint": None,
        "blueprint_verdict": None,
        "draft_paper": None,
        "paper_verdict": None,
        "final_path": None,
        "blueprint_repair_summary": None,
        "paper_repair_summary": None,
    }
    return await app.ainvoke(state)


async def generate_paper_workflow(
    session_id, syllabus_session_id, pyqs_session_id,
    total_marks=80, total_questions=10,
    bloom_levels=None, paper_sections=None, teacher_inputs=None
):
    syllabus_path = os.path.join("backend", "services", "data", syllabus_session_id, "syllabus.json")
    pyqs_path     = os.path.join("backend", "services", "data", pyqs_session_id, "pyqs.json")
    kg_path       = os.path.join("backend", "services", "data", syllabus_session_id, "knowledge_graph.json")
    with open(syllabus_path, "r", encoding="utf-8") as f:
        syllabus_data = json.load(f)
    with open(pyqs_path, "r", encoding="utf-8") as f:
        pyqs_data = json.load(f)
    from backend.services.input_analysis.pyq_service import analyse_pyqs
    pyqs_analysis = analyse_pyqs(pyqs_data)
    knowledge_graph_data = {}
    try:
        with open(kg_path, "r", encoding="utf-8") as f:
            knowledge_graph_data = json.load(f)
    except Exception:
        knowledge_graph_data = {}

    graph = StateGraph(PipelineState)
    for name, fn in [
        ("blueprint_build",  blueprint_build_node),
        ("blueprint_verify", blueprint_verify_node),
        ("question_select",  question_select_node),
        ("paper_verify",     paper_verify_node),
        ("final_generate",   final_generate_node),
    ]:
        graph.add_node(name, fn)
    graph.set_entry_point("blueprint_build")
    graph.add_edge("blueprint_build",  "blueprint_verify")
    graph.add_edge("blueprint_verify", "question_select")
    graph.add_edge("question_select",  "paper_verify")
    graph.add_edge("paper_verify",     "final_generate")
    graph.add_edge("final_generate",   END)
    app = graph.compile()

    if not paper_sections:
        sa = total_questions // 2
        sb = total_questions - sa
        sb_marks = (total_marks - sa * 6) // sb
        paper_sections = [
            {"section_name": "Section A", "section_description": "Short Answer Questions",
             "question_count": sa, "marks_per_question": 6},
            {"section_name": "Section B", "section_description": "Long Answer Questions",
             "question_count": sb, "marks_per_question": sb_marks},
        ]

    if not bloom_levels or sum(bloom_levels.values()) == 0:
        bloom_levels = {"remember": 20, "understand": 30, "apply": 30, "analyze": 20}

    if not teacher_inputs:
        teacher_inputs = {"focus_areas": [], "preferences": "Standard difficulty"}

    state: PipelineState = {
        "session_id":            session_id,
        "syllabus":              syllabus_data,
        "knowledge_graph":       knowledge_graph_data,
        "pyqs":                  pyqs_data,
        "pdf_path":              None,
        "pyqs_pdf_path":         None,
        "syllabus_text":         None,
        "pyqs_text":             None,
        "teacher_inputs":        teacher_inputs,
        "bloom_taxanomy_levels": bloom_levels,
        "qp_pattern": {
            "total_marks":       total_marks,
            "total_questions":   total_questions,
            "module_weightage_range": compute_dynamic_module_weights(
                total_marks=total_marks,
                total_questions=total_questions,
                num_active_modules=_count_active_modules(syllabus_data, teacher_inputs or {}),
                allowed_marks=[2, 5, 6, 10, 15],
            ),
            "allowed_marks_per_question": [2, 5, 6, 10, 15],
            "sections":          paper_sections,
        },
        "pyqs_analysis":              None,
        "blueprint":                  None,
        "blueprint_verdict":          None,
        "draft_paper":                None,
        "paper_verdict":              None,
        "final_path":                 None,
        "blueprint_repair_summary":   None,
        "paper_repair_summary":       None,
    }

    # Save input configuration to disk so they can be loaded into DB later
    await save_json_data(session_id, "teacher_inputs.json",   teacher_inputs,          silent=True)
    await save_json_data(session_id, "bloom_distribution.json", bloom_levels,           silent=True)
    await save_json_data(session_id, "paper_pattern.json",    state["qp_pattern"],     silent=True)

    return await app.ainvoke(state)