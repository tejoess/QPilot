# backend/main.py
from fastapi import FastAPI , WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas.request import PaperGenerationRequest
from backend.schemas.response import PaperGenerationResponse
from backend.websocket.manager import manager

backend = FastAPI()

backend.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin (for file:// local testing)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@backend.websocket("/ws/{session_id}")
async def websocket_logs(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    while True:
        await websocket.receive_text()

@backend.post("/generate-paper", response_model=PaperGenerationResponse)
def generate_question_paper(payload: PaperGenerationRequest):
    from backend.services.pipeline import run_question_paper_pipeline
    session_id = "session_1"
    file_path = run_question_paper_pipeline(session_id)

    return PaperGenerationResponse(
        status="success",
        file_path=file_path
    )

from fastapi import UploadFile, File, HTTPException
import json
from backend.QP_Verifier.question_paper_verifier import evaluate_question_paper

@backend.post("/verify-paper")
async def verify_paper(
    question_paper: UploadFile = File(...),
    syllabus: UploadFile = File(...),
    teacher_instructions: UploadFile = File(...),
    bloom_level: UploadFile = File(...)
):
    try:
        qp_data = json.loads(await question_paper.read())
        syllabus_data = json.loads(await syllabus.read())
        teacher_data = json.loads(await teacher_instructions.read())
        bloom_data = json.loads(await bloom_level.read())
        
        input_json = {
            "syllabus": syllabus_data,
            "teacher_input": teacher_data,
            "blooms_target_distribution": bloom_data,
            "question_paper": qp_data
        }
        
        result = evaluate_question_paper(input_json)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
