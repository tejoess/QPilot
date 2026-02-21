# backend/services/pipeline.py
import asyncio
from backend.websocket.manager import manager
from backend.services.prompts import format_syllabus as SYLLABUS_PROMPT
from backend.services.input_analysis.syllabus_service import get_syllabus_json, format_syllabus
from backend.services.input_analysis.pyq_service import get_pyqs, format_pyqs
from backend.services.blueprint.blueprint_service import build_blueprint, verify_blueprint
from backend.services.question_selection.question_service import (
    select_questions,
    verify_question_paper,
    generate_final_paper
)
from backend.services.input_analysis.process_pdf import process_pdf

def run_question_paper_pipeline(session_id: str = "default"):

    async def send(msg):
        await manager.send(session_id, msg)

    async def run():

        await send("Step 1: syllabus fetch")
        dummy_syllabus = process_pdf(r"C:\Users\Tejas\Desktop\Multi-Agent-Question-Paper-Generator\syllabus.pdf")
        
        await send("Step 2: syllabus format")
        get_syllabus_json(SYLLABUS_PROMPT, dummy_syllabus)
        
        await send("Step 3: pyqs fetch")
        get_pyqs()

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
