import asyncio
import json
import os
from datetime import datetime
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from backend.websocket.manager import manager
from backend.services.prompts import format_syllabus as SYLLABUS_PROMPT
from backend.services.input_analysis.syllabus_service import get_syllabus_json, format_syllabus
from backend.services.input_analysis.pyq_service import format_pyqs
from backend.services.blueprint.blueprint_service import build_blueprint, verify_blueprint
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
    pdf_path: Optional[str]  # For syllabus PDF
    pyqs_pdf_path: Optional[str]  # For PYQs PDF
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
    session_id = state["session_id"]
    
    # Send start message
    await manager.send_progress(session_id, "syllabus_fetch", "running", 0, "Starting syllabus extraction")

    # Check if text content is provided directly
    if state.get("syllabus_text"):
        await manager.send_log(session_id, "info", "Using provided text content")
        text = state["syllabus_text"]
    elif state.get("pdf_path"):
        await manager.send_log(session_id, "info", f"Extracting text from PDF")
        await manager.send_progress(session_id, "syllabus_fetch", "running", 25, "Reading PDF file")
        text = extract_text_from_pdf(state["pdf_path"], "syllabus")
        await manager.send_progress(session_id, "syllabus_fetch", "running", 50, "Text extracted successfully")
    else:
        await manager.send_log(session_id, "error", "No syllabus content provided")
        raise ValueError("Either syllabus_text or pdf_path must be provided")
    
    # Save raw syllabus text
    session_folder = os.path.join("backend", "services", "data", state["session_id"])
    os.makedirs(session_folder, exist_ok=True)
    text_path = os.path.join(session_folder, "syllabus_raw.txt")
    
    await manager.send_progress(session_id, "syllabus_fetch", "running", 75, "Saving raw text")
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    await manager.send_progress(session_id, "syllabus_fetch", "completed", 100, f"Saved raw syllabus text")
    await manager.send_log(session_id, "info", f"💾 Saved: syllabus_raw.txt")
    print(f"💾 Saved: {text_path}")
    
    return {"syllabus_text": text}


async def syllabus_format(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "syllabus_format", "running", 0, "Starting syllabus parsing")
    await manager.send_log(session_id, "info", "Step 2: Formatting syllabus with LLM")

    await manager.send_progress(session_id, "syllabus_format", "running", 25, "Sending to LLM for parsing")
    syllabus_json = get_syllabus_json(SYLLABUS_PROMPT, state["syllabus_text"])
    
    # Ensure it's a dict, if None or parsing failed, use empty dict
    if not syllabus_json or not isinstance(syllabus_json, dict):
        await manager.send_log(session_id, "warning", "Failed to parse syllabus, using empty structure")
        syllabus_json = {"modules": [], "error": "Failed to parse syllabus"}
    else:
        await manager.send_progress(session_id, "syllabus_format", "running", 75, f"Parsed {len(syllabus_json.get('modules', []))} modules")
    
    # Save syllabus JSON
    await manager.send_progress(session_id, "syllabus_format", "running", 90, "Saving structured data")
    save_json_data(state["session_id"], "syllabus.json", syllabus_json)
    
    await manager.send_progress(session_id, "syllabus_format", "completed", 100, "Syllabus formatted successfully")
    await manager.send_log(session_id, "info", f"💾 Saved: syllabus.json")
    await manager.send_completion(session_id, True, {"modules": len(syllabus_json.get("modules", []))})
    
    return {"syllabus": syllabus_json}


async def pyqs_fetch(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "pyqs_fetch", "running", 0, "Starting PYQ extraction")
    await manager.send_log(session_id, "info", "Step 3: Fetching PYQs")
    
    # Check if text content is provided directly
    if state.get("pyqs_text"):
        await manager.send_log(session_id, "info", "Using provided text content")
        pyqs_text = state["pyqs_text"]
    elif state.get("pyqs_pdf_path"):
        await manager.send_log(session_id, "info", "Extracting text from PYQ PDF")
        await manager.send_progress(session_id, "pyqs_fetch", "running", 25, "Reading PDF file")
        pyqs_text = extract_text_from_pdf(state["pyqs_pdf_path"], "pyqs")
        await manager.send_progress(session_id, "pyqs_fetch", "running", 50, "Text extracted successfully")
    else:
        await manager.send_log(session_id, "error", "No PYQ content provided")
        raise ValueError("Either pyqs_text or pyqs_pdf_path must be provided")
    
    if not pyqs_text:
        await manager.send_log(session_id, "warning", "Empty PYQ content")
        pyqs_text = ""
    
    print(pyqs_text[:500])  # Print first 500 characters for debugging
    
    # Save raw PYQs text
    if pyqs_text:
        await manager.send_progress(session_id, "pyqs_fetch", "running", 75, "Saving raw text")
        session_folder = os.path.join("backend", "services", "data", state["session_id"])
        text_path = os.path.join(session_folder, "pyqs_raw.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(pyqs_text)
        await manager.send_log(session_id, "info", "💾 Saved: pyqs_raw.txt")
        print(f"💾 Saved: {text_path}")
    
    await manager.send_progress(session_id, "pyqs_fetch", "completed", 100, "PYQ extraction complete")
    
    return {"pyqs_text": pyqs_text}


async def pyqs_format_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "pyqs_format", "running", 0, "Starting PYQ parsing")
    await manager.send_log(session_id, "info", "Step 4: Formatting PYQs with LLM")
    
    await manager.send_progress(session_id, "pyqs_format", "running", 25, "Mapping questions to syllabus topics")
    pyqs_result = format_pyqs(state.get("pyqs_text", ""), state.get("syllabus", {}))
    
    # format_pyqs returns JSON string, parse it
    try:
        pyqs_dict = json.loads(pyqs_result) if isinstance(pyqs_result, str) else pyqs_result
        question_count = len(pyqs_dict.get("questions", []))
        await manager.send_progress(session_id, "pyqs_format", "running", 75, f"Parsed {question_count} questions")
    except:
        await manager.send_log(session_id, "warning", "Failed to parse PYQs")
        pyqs_dict = {"questions": [], "error": "Failed to parse PYQs"}
    
    # Save PYQs JSON
    await manager.send_progress(session_id, "pyqs_format", "running", 90, "Saving structured data")
    save_json_data(state["session_id"], "pyqs.json", pyqs_dict)
    
    await manager.send_progress(session_id, "pyqs_format", "completed", 100, "PYQs formatted successfully")
    await manager.send_log(session_id, "info", f"💾 Saved: pyqs.json")
    await manager.send_completion(session_id, True, {"questions": len(pyqs_dict.get("questions", []))})
    
    return {"pyqs": pyqs_dict, "pyqs_analysis": pyqs_dict}


async def blueprint_build_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "blueprint_build", "running", 0, "Starting blueprint generation")
    await manager.send_log(session_id, "info", "Step 5: Building question paper blueprint")
    
    # Get inputs with defaults for missing values
    await manager.send_progress(session_id, "blueprint_build", "running", 20, "Gathering requirements")
    syllabus = state.get("syllabus", {})
    pyqs = state.get("pyqs", {})
    teacher_inputs = state.get("teacher_inputs", {"focus_areas": [], "preferences": ""})
    bloom_levels = state.get("bloom_taxanomy_levels", {"remember": 20, "understand": 30, "apply": 30, "analyze": 20})
    qp_pattern = state.get("qp_pattern", {"total_marks": 80, "sections": []})
    
    await manager.send_progress(session_id, "blueprint_build", "running", 40, "Generating blueprint with AI...")
    await manager.send_log(session_id, "info", "🤖 AI is analyzing syllabus and generating blueprint structure")
    blueprint = generate_blueprint(syllabus, pyqs, bloom_levels, teacher_inputs, qp_pattern)
    await manager.send_log(session_id, "info", "✅ Blueprint generation complete")
    
    # Ensure it's a dict
    if not isinstance(blueprint, dict):
        await manager.send_log(session_id, "warning", "Failed to generate valid blueprint")
        blueprint = {"sections": [], "error": "Failed to generate blueprint"}
    else:
        section_count = len(blueprint.get("sections", []))
        await manager.send_progress(session_id, "blueprint_build", "running", 80, f"Generated blueprint with {section_count} sections")
    
    # Save blueprint JSON
    save_json_data(state["session_id"], "blueprint.json", blueprint)
    await manager.send_log(session_id, "info", "💾 Saved: blueprint.json")
    
    await manager.send_progress(session_id, "blueprint_build", "completed", 100, "Blueprint generated successfully")
    
    return {"blueprint": blueprint}


async def blueprint_verify_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "blueprint_verify", "running", 0, "Starting blueprint verification")
    await manager.send_log(session_id, "info", "Step 6: Verifying blueprint against requirements")
    
    await manager.send_progress(session_id, "blueprint_verify", "running", 30, "Analyzing blueprint structure")
    blueprint = state.get("blueprint", {})
    syllabus = state.get("syllabus", {})
    pyqs_analysis = state.get("pyqs_analysis", {})
    bloom_levels = state.get("bloom_taxanomy_levels", {})
    teacher_inputs = state.get("teacher_inputs", {})
    qp_pattern = state.get("qp_pattern", {})
    
    await manager.send_progress(session_id, "blueprint_verify", "running", 60, "AI is critiquing blueprint...")
    await manager.send_log(session_id, "info", "🔍 AI analyzing blueprint quality and requirements match")
    blueprint_verdict = critique_blueprint(blueprint, syllabus, pyqs_analysis, bloom_levels, teacher_inputs, qp_pattern)
    await manager.send_log(session_id, "info", "✅ Blueprint critique complete")
    
    # Ensure it's a dict
    if not isinstance(blueprint_verdict, dict):
        await manager.send_log(session_id, "warning", "Blueprint verification failed")
        blueprint_verdict = {"status": "pending", "issues": []}
    else:
        status = blueprint_verdict.get("status", "unknown")
        issues_count = len(blueprint_verdict.get("issues", []))
        await manager.send_log(session_id, "info", f"Blueprint status: {status}, {issues_count} issues found")
    
    # Save blueprint verification JSON
    await manager.send_progress(session_id, "blueprint_verify", "running", 90, "Saving verification results")
    save_json_data(state["session_id"], "blueprint_verification.json", blueprint_verdict)
    await manager.send_log(session_id, "info", "💾 Saved: blueprint_verification.json")
    
    await manager.send_progress(session_id, "blueprint_verify", "completed", 100, "Blueprint verified")
    
    return {"blueprint_verdict": blueprint_verdict}


async def question_select_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "question_select", "running", 0, "Starting question selection")
    await manager.send_log(session_id, "info", "Step 7: Selecting questions from PYQ bank")
    
    await manager.send_progress(session_id, "question_select", "running", 20, "Loading blueprint and PYQs")
    blueprint = state.get("blueprint", {})
    pyqs = state.get("pyqs", {})
    # Extract questions list from pyqs dict
    pyq_list = pyqs.get("questions", []) if isinstance(pyqs, dict) else []
    
    await manager.send_log(session_id, "info", f"Available PYQ pool: {len(pyq_list)} questions")
    await manager.send_progress(session_id, "question_select", "running", 40, "AI matching questions to blueprint...")
    await manager.send_log(session_id, "info", "🎯 AI selecting best-fit questions from PYQ pool")
    draft_paper = select_questions(blueprint, pyq_list)
    await manager.send_log(session_id, "info", "✅ Question selection complete")
    
    # Ensure it's a dict
    if not isinstance(draft_paper, dict):
        await manager.send_log(session_id, "warning", "Question selection failed")
        draft_paper = {"sections": [], "error": "Failed to select questions"}
    else:
        total_questions = sum(len(s.get("questions", [])) for s in draft_paper.get("sections", []))
        await manager.send_progress(session_id, "question_select", "running", 80, f"Selected {total_questions} questions")
    
    # Save draft paper JSON
    save_json_data(state["session_id"], "draft_paper.json", draft_paper)
    await manager.send_log(session_id, "info", "💾 Saved: draft_paper.json")
    
    await manager.send_progress(session_id, "question_select", "completed", 100, "Questions selected successfully")
    
    return {"draft_paper": draft_paper}


async def paper_verify_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "paper_verify", "running", 0, "Starting paper verification")
    await manager.send_log(session_id, "info", "Step 8: Verifying drafted question paper")
    
    await manager.send_progress(session_id, "paper_verify", "running", 25, "Loading draft paper and requirements")
    draft_paper = state.get("draft_paper", {})
    syllabus = state.get("syllabus", {})
    pyqs_analysis = state.get("pyqs_analysis", {})
    blueprint = state.get("blueprint", {})
    bloom_levels = state.get("bloom_taxanomy_levels", {})
    qp_pattern = state.get("qp_pattern", {})
    teacher_inputs = state.get("teacher_inputs", {})
    
    await manager.send_progress(session_id, "paper_verify", "running", 50, "AI running comprehensive verification...")
    await manager.send_log(session_id, "info", "📋 AI verifying paper quality, marks, and requirements")
    paper_verdict = verify_question_paper(draft_paper, syllabus, pyqs_analysis, blueprint, bloom_levels, qp_pattern, teacher_inputs)
    await manager.send_log(session_id, "info", "✅ Paper verification complete")
    
    # Ensure it's a dict
    if not isinstance(paper_verdict, dict):
        await manager.send_log(session_id, "warning", "Paper verification failed")
        paper_verdict = {"verdict": "pending", "rating": 0}
    else:
        verdict = paper_verdict.get("verdict", "unknown")
        rating = paper_verdict.get("rating", 0)
        await manager.send_log(session_id, "info", f"Paper verdict: {verdict}, Rating: {rating}/10")
        await manager.send_progress(session_id, "paper_verify", "running", 80, f"Verdict: {verdict}")
    
    # Save paper verification JSON
    save_json_data(state["session_id"], "paper_verification.json", paper_verdict)
    await manager.send_log(session_id, "info", "💾 Saved: paper_verification.json")
    
    await manager.send_progress(session_id, "paper_verify", "completed", 100, "Paper verified successfully")
    
    return {"paper_verdict": paper_verdict}


async def final_generate_node(state: PipelineState):
    session_id = state["session_id"]
    
    await manager.send_progress(session_id, "final_generate", "running", 0, "Starting final paper generation")
    await manager.send_log(session_id, "info", "Step 9: Generating final question paper")
    
    session_folder = os.path.join("backend", "services", "data", session_id)
    
    # Save final paper JSON
    await manager.send_progress(session_id, "final_generate", "running", 30, "Finalizing paper structure")
    draft_paper = state.get("draft_paper", {})
    final_paper_json_path = save_json_data(session_id, "final_paper.json", draft_paper)
    await manager.send_log(session_id, "info", "💾 Saved: final_paper.json")
    
    # Create a summary/metadata file
    await manager.send_progress(session_id, "final_generate", "running", 60, "Creating session summary")
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
    await manager.send_log(session_id, "info", f"💾 Saved: session_summary.json")
    
    # TODO: Generate PDF from final_paper.json
    await manager.send_progress(session_id, "final_generate", "running", 90, "Preparing output files")
    final_path = os.path.join(session_folder, "final_question_paper.pdf")
    
    await manager.send_log(session_id, "info", f"✅ All files saved to: {session_folder}")
    await manager.send_log(session_id, "info", f"✅ Paper generated: {summary['total_questions']} questions, {summary['total_marks']} marks")
    
    await manager.send_progress(session_id, "final_generate", "completed", 100, "Question paper generated successfully")
    await manager.send_completion(session_id, True, {
        "session_id": session_id,
        "total_questions": summary['total_questions'],
        "total_marks": summary['total_marks'],
        "verdict": summary['verdict'],
        "rating": summary['rating'],
        "output_path": session_folder
    })
    
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


# ==========================================
# NEW: Separate Workflows
# ==========================================

async def analyze_syllabus_workflow(
    session_id: str,
    pdf_path: Optional[str] = None,
    text_content: Optional[str] = None
):
    """
    Workflow 1: Analyze Syllabus
    Runs: syllabus_fetch → syllabus_format
    """
    graph = StateGraph(PipelineState)
    graph.add_node("syllabus_fetch", syllabus_fetch)
    graph.add_node("syllabus_format", syllabus_format)
    graph.set_entry_point("syllabus_fetch")
    graph.add_edge("syllabus_fetch", "syllabus_format")
    graph.add_edge("syllabus_format", END)
    
    app = graph.compile()
    
    initial_state = {
        "session_id": session_id,
        "pdf_path": pdf_path,
        "syllabus_text": text_content,
        "syllabus": None,
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
    }
    
    result = await app.ainvoke(initial_state)
    return result


async def analyze_pyqs_workflow(
    session_id: str,
    syllabus_session_id: str,
    pdf_path: Optional[str] = None,
    text_content: Optional[str] = None
):
    """
    Workflow 2: Analyze PYQs
    Loads syllabus from previous session
    Runs: pyqs_fetch → pyqs_format
    """
    # Load syllabus from previous session
    syllabus_path = os.path.join("backend", "services", "data", syllabus_session_id, "syllabus.json")
    with open(syllabus_path, 'r', encoding='utf-8') as f:
        syllabus_data = json.load(f)
    
    graph = StateGraph(PipelineState)
    graph.add_node("pyqs_fetch", pyqs_fetch)
    graph.add_node("pyqs_format", pyqs_format_node)
    graph.set_entry_point("pyqs_fetch")
    graph.add_edge("pyqs_fetch", "pyqs_format")
    graph.add_edge("pyqs_format", END)
    
    app = graph.compile()
    
    initial_state = {
        "session_id": session_id,
        "pyqs_pdf_path": pdf_path,
        "pyqs_text": text_content,
        "syllabus": syllabus_data,  # Loaded from previous session
        "syllabus_text": None,
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
    }
    
    result = await app.ainvoke(initial_state)
    return result


async def generate_paper_workflow(
    session_id: str,
    syllabus_session_id: str,
    pyqs_session_id: str,
    total_marks: int = 80,
    total_questions: int = 10,
    bloom_levels: Optional[dict] = None,
    paper_sections: Optional[list] = None,
    teacher_inputs: Optional[dict] = None
):
    """
    Workflow 3: Generate Paper
    Loads syllabus and PYQs from previous sessions
    Runs: blueprint_build → blueprint_verify → question_select → paper_verify → final_generate
    """
    # Load syllabus and PYQs from previous sessions
    syllabus_path = os.path.join("backend", "services", "data", syllabus_session_id, "syllabus.json")
    pyqs_path = os.path.join("backend", "services", "data", pyqs_session_id, "pyqs.json")
    
    with open(syllabus_path, 'r', encoding='utf-8') as f:
        syllabus_data = json.load(f)
    with open(pyqs_path, 'r', encoding='utf-8') as f:
        pyqs_data = json.load(f)
    
    graph = StateGraph(PipelineState)
    graph.add_node("blueprint_build", blueprint_build_node)
    graph.add_node("blueprint_verify", blueprint_verify_node)
    graph.add_node("question_select", question_select_node)
    graph.add_node("paper_verify", paper_verify_node)
    graph.add_node("final_generate", final_generate_node)
    
    graph.set_entry_point("blueprint_build")
    graph.add_edge("blueprint_build", "blueprint_verify")
    graph.add_edge("blueprint_verify", "question_select")
    graph.add_edge("question_select", "paper_verify")
    graph.add_edge("paper_verify", "final_generate")
    graph.add_edge("final_generate", END)
    
    app = graph.compile()
    
    # Use custom sections if provided, otherwise auto-calculate
    if paper_sections and len(paper_sections) > 0:
        sections = paper_sections
    else:
        # Default: Calculate section distribution
        section_a_count = total_questions // 2
        section_b_count = total_questions - section_a_count
        section_a_marks = 6
        section_b_marks = (total_marks - (section_a_count * section_a_marks)) // section_b_count
        
<<<<<<< HEAD
        sections = [
            {
                "section_name": "Section A",
                "section_description": "Short Answer Questions",
                "question_count": section_a_count,
                "marks_per_question": section_a_marks
            },
            {
                "section_name": "Section B",
                "section_description": "Long Answer Questions",
                "question_count": section_b_count,
                "marks_per_question": section_b_marks
            }
        ]
    
    # Use custom bloom levels if provided, otherwise use defaults
    if not bloom_levels or sum(bloom_levels.values()) == 0:
        bloom_levels = {
            "remember": 20,
            "understand": 30,
            "apply": 30,
            "analyze": 20,
            "evaluate": 0,
            "create": 0
        }
    
    # Use teacher inputs if provided
    if not teacher_inputs:
        teacher_inputs = {"focus_areas": [], "preferences": "Standard difficulty"}
    
    initial_state = {
        "session_id": session_id,
        "syllabus": syllabus_data,
        "pyqs": pyqs_data,
        "pdf_path": None,
        "pyqs_pdf_path": None,
        "syllabus_text": None,
        "pyqs_text": None,
        "teacher_inputs": teacher_inputs,
        "bloom_taxanomy_levels": bloom_levels,
        "qp_pattern": {
            "total_marks": total_marks,
            "total_questions": total_questions,
            "module_weightage_range": {
                "min": 0.10,
                "max": 0.30
            },
            "allowed_marks_per_question": [2, 5, 6, 10, 15],
            "sections": sections
        },
        "pyqs_analysis": None,
        "blueprint": None,
        "blueprint_verdict": None,
        "draft_paper": None,
        "paper_verdict": None,
        "final_path": None,
    }
    
    result = await app.ainvoke(initial_state)
    return result
=======
        await send("Step 2: syllabus format")
        get_syllabus_json(SYLLABUS_PROMPT, dummy_syllabus)
        
        await send("Step 4: pyqs format")
        format_pyqs()

        await send("Step 5: blueprint build")
        build_blueprint()

        await send("Step 6: blueprint verify")
        verify_blueprint()

        await send("Step 7: select questions")
        select_questions()

        await send("Step 8: verify paper")
        verify_question_paper()

        await send("Step 9: generate final")
        generate_final_paper()

    asyncio.run(run())

    return "generated/final_question_paper.pdf"
>>>>>>> graph_generator
