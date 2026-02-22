import asyncio
import json
import os
from datetime import datetime
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from backend.websocket.manager import manager
from backend.services.prompts import format_syllabus as SYLLABUS_PROMPT
from backend.services.input_analysis.syllabus_service import (
    get_syllabus_json,
)
from backend.services.input_analysis.pyq_service import (
    
    format_pyqs,
)
from backend.services.blueprint.blueprint_service import (
    generate_blueprint,
)
from backend.services.blueprint.blueprint_verify import (
 critique_blueprint
)
from backend.services.question_selection.question_service import (
    select_questions,
)
from backend.services.question_verification.verify_paper import (
    verify_question_paper,
)
from backend.services.input_analysis.process_pdf import extract_text_from_pdf


# -------------------------
# Graph State
# -------------------------
class PipelineState(TypedDict):
    session_id: str
    syllabus_text: Optional[str]
    syllabus: Optional[dict]
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



# -------------------------
# Helper: websocket sender
# -------------------------
async def send(session_id: str, message: str):
    await manager.send(session_id, message)


# -------------------------
# Helper: save JSON data
# -------------------------
def save_json_data(session_id: str, filename: str, data: dict):
    """
    Save JSON data to the data folder organized by session_id
    """
    # Create session folder
    session_folder = os.path.join("backend", "services", "data", session_id)
    os.makedirs(session_folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(session_folder, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved: {file_path}")
    return file_path


# -------------------------
# Nodes
# -------------------------
async def syllabus_fetch(state: PipelineState):
    await send(state["session_id"], "Step 1: syllabus fetch")

    text = extract_text_from_pdf(
        r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf",
        "syllabus"
    )
    
    # Save raw syllabus text
    session_folder = os.path.join("backend", "services", "data", state["session_id"])
    os.makedirs(session_folder, exist_ok=True)
    text_path = os.path.join(session_folder, "syllabus_raw.txt")
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f"💾 Saved: {text_path}")
    
    return {"syllabus_text": text}


async def syllabus_format(state: PipelineState):
    await send(state["session_id"], "Step 2: syllabus format")

    syllabus_json = get_syllabus_json(SYLLABUS_PROMPT, state["syllabus_text"])
    # Ensure it's a dict, if None or parsing failed, use empty dict
    if not syllabus_json or not isinstance(syllabus_json, dict):
        syllabus_json = {"modules": [], "error": "Failed to parse syllabus"}
    
    # Save syllabus JSON
    save_json_data(state["session_id"], "syllabus.json", syllabus_json)
    
    return {"syllabus": syllabus_json}


async def pyqs_fetch(state: PipelineState):
    await send(state["session_id"], "Step 3: pyqs fetch")
    
    pyqs_text = extract_text_from_pdf(r"C:\Users\Tejas\Downloads\BE AIDS SEM - VIII MAY-2024.pdf", "pyqs")
    # Return text if it's string, empty if None
    if not pyqs_text:
        pyqs_text = ""
    
    # Save raw PYQs text
    if pyqs_text:
        session_folder = os.path.join("backend", "services", "data", state["session_id"])
        text_path = os.path.join(session_folder, "pyqs_raw.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(pyqs_text)
        print(f"💾 Saved: {text_path}")
    
    return {"pyqs_text": pyqs_text}


async def pyqs_format_node(state: PipelineState):
    await send(state["session_id"], "Step 4: pyqs format")
    
    pyqs_result = format_pyqs(state.get("pyqs_text", ""), state.get("syllabus", {}))
    # format_pyqs returns JSON string, parse it
    try:
        pyqs_dict = json.loads(pyqs_result) if isinstance(pyqs_result, str) else pyqs_result
    except:
        pyqs_dict = {"questions": [], "error": "Failed to parse PYQs"}
    
    # Save PYQs JSON
    save_json_data(state["session_id"], "pyqs.json", pyqs_dict)
    
    return {"pyqs": pyqs_dict, "pyqs_analysis": pyqs_dict}


async def blueprint_build_node(state: PipelineState):
    await send(state["session_id"], "Step 5: blueprint build")
    
    # Get inputs with defaults for missing values
    syllabus = state.get("syllabus", {})
    pyqs = state.get("pyqs", {})
    teacher_inputs = state.get("teacher_inputs", {"focus_areas": [], "preferences": ""})
    bloom_levels = state.get("bloom_taxanomy_levels", {"remember": 20, "understand": 30, "apply": 30, "analyze": 20})
    qp_pattern = state.get("qp_pattern", {"total_marks": 80, "sections": []})
    
    blueprint = generate_blueprint(syllabus, pyqs, bloom_levels, teacher_inputs, qp_pattern)
    # Ensure it's a dict
    if not isinstance(blueprint, dict):
        blueprint = {"sections": [], "error": "Failed to generate blueprint"}
    
    # Save blueprint JSON
    save_json_data(state["session_id"], "blueprint.json", blueprint)
    
    return {"blueprint": blueprint}


async def blueprint_verify_node(state: PipelineState):
    await send(state["session_id"], "Step 6: blueprint verify")
    
    blueprint = state.get("blueprint", {})
    syllabus = state.get("syllabus", {})
    pyqs_analysis = state.get("pyqs_analysis", {})
    bloom_levels = state.get("bloom_taxanomy_levels", {})
    teacher_inputs = state.get("teacher_inputs", {})
    qp_pattern = state.get("qp_pattern", {})
    
    blueprint_verdict = critique_blueprint(blueprint, syllabus, pyqs_analysis, bloom_levels, teacher_inputs, qp_pattern)
    # Ensure it's a dict
    if not isinstance(blueprint_verdict, dict):
        blueprint_verdict = {"status": "pending", "issues": []}
    
    # Save blueprint verification JSON
    save_json_data(state["session_id"], "blueprint_verification.json", blueprint_verdict)
    
    return {"blueprint_verdict": blueprint_verdict}


async def question_select_node(state: PipelineState):
    await send(state["session_id"], "Step 7: select questions")
    
    blueprint = state.get("blueprint", {})
    pyqs = state.get("pyqs", {})
    # Extract questions list from pyqs dict
    pyq_list = pyqs.get("questions", []) if isinstance(pyqs, dict) else []
    
    draft_paper = select_questions(blueprint, pyq_list)
    # Ensure it's a dict
    if not isinstance(draft_paper, dict):
        draft_paper = {"sections": [], "error": "Failed to select questions"}
    
    # Save draft paper JSON
    save_json_data(state["session_id"], "draft_paper.json", draft_paper)
    
    return {"draft_paper": draft_paper}


async def paper_verify_node(state: PipelineState):
    await send(state["session_id"], "Step 8: verify paper")
    
    draft_paper = state.get("draft_paper", {})
    syllabus = state.get("syllabus", {})
    pyqs_analysis = state.get("pyqs_analysis", {})
    blueprint = state.get("blueprint", {})
    bloom_levels = state.get("bloom_taxanomy_levels", {})
    qp_pattern = state.get("qp_pattern", {})
    teacher_inputs = state.get("teacher_inputs", {})
    
    paper_verdict = verify_question_paper(draft_paper, syllabus, pyqs_analysis, blueprint, bloom_levels, qp_pattern, teacher_inputs)
    # Ensure it's a dict
    if not isinstance(paper_verdict, dict):
        paper_verdict = {"verdict": "pending", "rating": 0}
    
    # Save paper verification JSON
    save_json_data(state["session_id"], "paper_verification.json", paper_verdict)
    
    return {"paper_verdict": paper_verdict}


async def final_generate_node(state: PipelineState):
    await send(state["session_id"], "Step 9: generate final")
    
    session_id = state["session_id"]
    session_folder = os.path.join("backend", "services", "data", session_id)
    
    # Save final paper JSON
    draft_paper = state.get("draft_paper", {})
    final_paper_json_path = save_json_data(session_id, "final_paper.json", draft_paper)
    
    # Create a summary/metadata file
    summary = {
        "session_id": session_id,
        "timestamp": datetime.now().isoformat(),
        "status": "completed",
        "total_marks": sum(q.get("marks", 0) for s in draft_paper.get("sections", []) for q in s.get("questions", [])),
        "total_questions": sum(len(s.get("questions", [])) for s in draft_paper.get("sections", [])),
        "verdict": state.get("paper_verdict", {}).get("verdict", "unknown"),
        "rating": state.get("paper_verdict", {}).get("rating", 0),
        "files_generated": {
            "syllabus": "syllabus.json",
            "pyqs": "pyqs.json",
            "blueprint": "blueprint.json",
            "blueprint_verification": "blueprint_verification.json",
            "draft_paper": "draft_paper.json",
            "paper_verification": "paper_verification.json",
            "final_paper": "final_paper.json"
        }
    }
    save_json_data(session_id, "session_summary.json", summary)
    
    # TODO: Generate PDF from final_paper.json
    final_path = os.path.join(session_folder, "final_question_paper.pdf")
    
    await send(state["session_id"], f"✅ All files saved to: {session_folder}")
    await send(state["session_id"], f"✅ Paper generated at: {final_path}")
    print(f"\n✅ Final paper path: {final_path}")
    print(f"✅ All data saved to: {session_folder}")
    
    return {"final_path": final_path}


# -------------------------
# Build Graph
# -------------------------
def build_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("syllabus_fetch", syllabus_fetch)
    graph.add_node("syllabus_format", syllabus_format)
    graph.add_node("pyqs_fetch", pyqs_fetch)
    graph.add_node("pyqs_format", pyqs_format_node)
    graph.add_node("blueprint_build", blueprint_build_node)
    graph.add_node("blueprint_verify", blueprint_verify_node)
    graph.add_node("question_select", question_select_node)
    graph.add_node("paper_verify", paper_verify_node)
    graph.add_node("final_generate", final_generate_node)

    graph.set_entry_point("syllabus_fetch")

    graph.add_edge("syllabus_fetch", "syllabus_format")
    graph.add_edge("syllabus_format", "pyqs_fetch")
    graph.add_edge("pyqs_fetch", "pyqs_format")
    graph.add_edge("pyqs_format", "blueprint_build")
    graph.add_edge("blueprint_build", "blueprint_verify")
    graph.add_edge("blueprint_verify", "question_select")
    graph.add_edge("question_select", "paper_verify")
    graph.add_edge("paper_verify", "final_generate")
    graph.add_edge("final_generate", END)

    return graph.compile()


# -------------------------
# Runner
# -------------------------
async def run_question_paper_pipeline(session_id: str = "default"):
    app = build_graph()

    initial_state = {
        "session_id": session_id,
        "syllabus_text": None,
        "syllabus": None,
        "pyqs_text": None,
        "pyqs": None,
        "teacher_inputs": {"focus_areas": [], "preferences": "Standard difficulty"},
        "bloom_taxanomy_levels": {
            "remember": 20,
            "understand": 30, 
            "apply": 30,
            "analyze": 20
        },
        "qp_pattern": {
            "total_marks": 80,
            "total_questions": 10,
            "module_weightage_range": {
                "min": 0.10,  # 10% as decimal
                "max": 0.30   # 30% as decimal
            },
            "allowed_marks_per_question": [2, 5, 6, 10, 15],
            "sections": [
                {
                    "section_name": "Section A",
                    "section_description": "Short Answer Questions",
                    "question_count": 5,
                    "marks_per_question": 6  # 5 × 6 = 30 marks
                },
                {
                    "section_name": "Section B", 
                    "section_description": "Long Answer Questions",
                    "question_count": 5,
                    "marks_per_question": 10  # 5 × 10 = 50 marks
                }
            ]  # Total: 30 + 50 = 80 marks ✓
        },
        "pyqs_analysis": None,
        "blueprint": None,
        "blueprint_verdict": None,
        "draft_paper": None,
        "paper_verdict": None,
        "final_path": None,
    }

    result = await app.ainvoke(initial_state)

    return result.get("final_path", "generated/final_question_paper.pdf")