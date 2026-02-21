# backend/main.py
from fastapi import FastAPI , WebSocket
from backend.schemas.request import PaperGenerationRequest
from backend.schemas.response import PaperGenerationResponse
from backend.services.pipeline import run_question_paper_pipeline
from backend.websocket.manager import manager


backend = FastAPI()



@backend.websocket("/ws/{session_id}")
async def websocket_logs(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    while True:
        await websocket.receive_text()


@backend.post("/generate-paper", response_model=PaperGenerationResponse)
def generate_question_paper(payload: PaperGenerationRequest):
    session_id = "session_1"
    file_path = run_question_paper_pipeline(session_id)

    return PaperGenerationResponse(
        status="success",
        file_path=file_path
    )
