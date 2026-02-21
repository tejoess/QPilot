# app/main.py
from fastapi import FastAPI , WebSocket
from app.schemas.request import PaperGenerationRequest
from app.schemas.response import PaperGenerationResponse
from app.services.pipeline import run_question_paper_pipeline
from app.websocket.manager import manager


app = FastAPI()



@app.websocket("/ws/{session_id}")
async def websocket_logs(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    while True:
        await websocket.receive_text()


@app.post("/generate-paper", response_model=PaperGenerationResponse)
def generate_question_paper(payload: PaperGenerationRequest):
    session_id = "session_1"
    file_path = run_question_paper_pipeline(session_id)

    return PaperGenerationResponse(
        status="success",
        file_path=file_path
    )
