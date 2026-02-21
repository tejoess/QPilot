import asyncio
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
    build_blueprint,
    verify_blueprint,
)
from backend.services.question_selection.question_service import (
    select_questions,
    verify_question_paper,
    generate_final_paper,
)
from backend.services.input_analysis.process_pdf import process_pdf, extract_text_from_pdf


# -------------------------
# Graph State
# -------------------------
class PipelineState(TypedDict):
    session_id: str
    syllabus_text: Optional[str]
    final_path: Optional[str]


# -------------------------
# Helper: websocket sender
# -------------------------
async def send(session_id: str, message: str):
    await manager.send(session_id, message)


# -------------------------
# Nodes
# -------------------------
async def syllabus_fetch(state: PipelineState):
    await send(state["session_id"], "Step 1: syllabus fetch")

    text = extract_text_from_pdf(
        r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf",
        "syllabus"
    )

    return {"syllabus_text": text}


async def syllabus_format(state: PipelineState):
    await send(state["session_id"], "Step 2: syllabus format")

    get_syllabus_json(SYLLABUS_PROMPT, state["syllabus_text"])
    return {}


async def pyqs_fetch(state: PipelineState):
    await send(state["session_id"], "Step 3: pyqs fetch")
    print("okay")
    process_pdf(r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\pyqs.pdf", "pyqs")
    return {}


async def pyqs_format_node(state: PipelineState):
    await send(state["session_id"], "Step 4: pyqs format")
    format_pyqs()
    return {}


async def blueprint_build_node(state: PipelineState):
    await send(state["session_id"], "Step 5: blueprint build")
    build_blueprint()
    return {}


async def blueprint_verify_node(state: PipelineState):
    await send(state["session_id"], "Step 6: blueprint verify")
    verify_blueprint()
    return {}


async def question_select_node(state: PipelineState):
    await send(state["session_id"], "Step 7: select questions")
    select_questions()
    return {}


async def paper_verify_node(state: PipelineState):
    await send(state["session_id"], "Step 8: verify paper")
    verify_question_paper()
    return {}


async def final_generate_node(state: PipelineState):
    await send(state["session_id"], "Step 9: generate final")

    generate_final_paper()
    final_path = "generated/final_question_paper.pdf"

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
        "final_path": None,
    }

    result = await app.ainvoke(initial_state)

    return result.get("final_path")