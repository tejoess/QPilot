# app/schemas/response.py
from pydantic import BaseModel

class PaperGenerationResponse(BaseModel):
    status: str
    file_path: str
