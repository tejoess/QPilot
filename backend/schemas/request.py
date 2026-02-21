# app/schemas/request.py
from pydantic import BaseModel

class PaperGenerationRequest(BaseModel):
    subject: str
    grade: str
    board: str
