# backend/main.py
from fastapi import FastAPI , WebSocket
from fastapi.middleware.cors import CORSMiddleware
from backend.schemas.request import PaperGenerationRequest
from backend.schemas.response import PaperGenerationResponse
from backend.websocket.manager import manager
from backend.services.pipeline import (
    analyze_syllabus_workflow,
    analyze_pyqs_workflow,
    generate_paper_workflow
)

backend = FastAPI()

<<<<<<< HEAD
# ✅ Enable CORS for frontend access
backend.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
=======
backend.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow any origin (for file:// local testing)
>>>>>>> graph_generator
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
<<<<<<< HEAD

=======
>>>>>>> graph_generator

@backend.websocket("/ws/{session_id}")
async def websocket_logs(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    while True:
        await websocket.receive_text()

<<<<<<< HEAD

# ==========================================
# API 1: Analyze Syllabus
# ==========================================
@backend.post("/analyze-syllabus")
async def analyze_syllabus(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Accepts either:
    - file: PDF upload (multipart/form-data)
    - text: Plain text syllabus content
    - session_id: (Optional) Custom session ID for WebSocket tracking
    
    Returns: session_id and parsed syllabus data
    """
    # Clean up empty strings to None
    text_content = None
    if text and text.strip():
        text_content = text.strip()
    
    if not file and not text_content:
        raise HTTPException(status_code=400, detail="Either 'file' or 'text' must be provided")
    
    # Use provided session_id or generate new one
    if not session_id or not session_id.strip():
        session_id = str(uuid.uuid4())
    else:
        session_id = session_id.strip()
    
    print(f"📝 Using session_id: {session_id}")
    
    try:
        # If file uploaded, save it temporarily
        pdf_path = None
        if file:
            # Save uploaded file
            upload_dir = os.path.join("backend", "services", "data", session_id, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            pdf_path = os.path.join(upload_dir, "syllabus.pdf")
            
            with open(pdf_path, "wb") as f:
                content = await file.read()
                f.write(content)
            print(f"📁 Saved file to: {pdf_path}")
        
        print(f"🔍 DEBUG: pdf_path={pdf_path}, text_content={'<text>' if text_content else None}")
        
        # Run syllabus analysis workflow
        result = await analyze_syllabus_workflow(
            session_id=session_id,
            pdf_path=pdf_path,
            text_content=text_content
        )
        
        return JSONResponse(content={
            "status": "success",
            "session_id": session_id,
            "syllabus": result["syllabus"],
            "message": "Syllabus analyzed successfully"
        })
        
    except Exception as e:
        import traceback
        print("❌ ERROR:" + "="*50)
        print(traceback.format_exc())
        print("="*60)
        raise HTTPException(status_code=500, detail=f"Syllabus analysis failed: {str(e)}")


# ==========================================
# API 2: Analyze PYQs
# ==========================================
@backend.post("/analyze-pyqs")
async def analyze_pyqs(
    syllabus_session_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Accepts:
    - syllabus_session_id: Session ID from analyze-syllabus API
    - file: PDF upload (multipart/form-data) OR
    - text: Plain text PYQ content
    - session_id: (Optional) Custom session ID for WebSocket tracking
    
    Returns: session_id and parsed PYQs data
    """
    # Clean up empty strings to None
    text_content = None
    if text and text.strip():
        text_content = text.strip()
    
    if not file and not text_content:
        raise HTTPException(status_code=400, detail="Either 'file' or 'text' must be provided")
    
    # Verify syllabus session exists
    syllabus_folder = os.path.join("backend", "services", "data", syllabus_session_id)
    if not os.path.exists(syllabus_folder):
        raise HTTPException(status_code=404, detail=f"Syllabus session {syllabus_session_id} not found")
    
    # Use provided session_id or generate new one
    if not session_id or not session_id.strip():
        pyqs_session_id = str(uuid.uuid4())
    else:
        pyqs_session_id = session_id.strip()
    
    print(f"📝 Using PYQs session_id: {pyqs_session_id}")
    
    try:
        # If file uploaded, save it temporarily
        pdf_path = None
        if file:
            upload_dir = os.path.join("backend", "services", "data", pyqs_session_id, "uploads")
            os.makedirs(upload_dir, exist_ok=True)
            pdf_path = os.path.join(upload_dir, "pyqs.pdf")
            
            with open(pdf_path, "wb") as f:
                content = await file.read()
                f.write(content)
        
        # Run PYQ analysis workflow
        result = await analyze_pyqs_workflow(
            session_id=pyqs_session_id,
            syllabus_session_id=syllabus_session_id,
            pdf_path=pdf_path,
            text_content=text_content
        )
        
        return JSONResponse(content={
            "status": "success",
            "session_id": pyqs_session_id,
            "pyqs": result["pyqs"],
            "total_questions": len(result["pyqs"].get("questions", [])),
            "message": "PYQs analyzed successfully"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PYQ analysis failed: {str(e)}")


# ==========================================
# API 3: Generate Paper
# ==========================================
@backend.post("/generate-paper")
async def generate_paper(
    syllabus_session_id: str = Form(...),
    pyqs_session_id: str = Form(...),
    total_marks: int = Form(80),
    total_questions: int = Form(10),
    # Bloom Taxonomy Levels (percentages)
    bloom_remember: Optional[int] = Form(None),
    bloom_understand: Optional[int] = Form(None),
    bloom_apply: Optional[int] = Form(None),
    bloom_analyze: Optional[int] = Form(None),
    bloom_evaluate: Optional[int] = Form(None),
    bloom_create: Optional[int] = Form(None),
    # Paper Pattern (JSON string of sections)
    paper_pattern: Optional[str] = Form(None),
    # Teacher Input (custom instructions/focus areas)
    teacher_input: Optional[str] = Form(None),
    # WebSocket tracking
    session_id: Optional[str] = Form(None)
):
    """
    Accepts:
    - syllabus_session_id: Session ID from analyze-syllabus API
    - pyqs_session_id: Session ID from analyze-pyqs API
    - total_marks: Total marks for the paper (default: 80)
    - total_questions: Total number of questions (default: 10)
    - bloom_*: Bloom's Taxonomy level percentages (optional, must sum to 100)
    - paper_pattern: JSON string defining sections (optional)
    - teacher_input: Custom instructions from teacher (optional)
    - session_id: (Optional) Custom session ID for WebSocket tracking
    
    Returns: Generated question paper
    """
    import json as json_lib
    
    # Verify both sessions exist
    syllabus_folder = os.path.join("backend", "services", "data", syllabus_session_id)
    pyqs_folder = os.path.join("backend", "services", "data", pyqs_session_id)
    
    if not os.path.exists(syllabus_folder):
        raise HTTPException(status_code=404, detail=f"Syllabus session {syllabus_session_id} not found")
    if not os.path.exists(pyqs_folder):
        raise HTTPException(status_code=404, detail=f"PYQs session {pyqs_session_id} not found")
    
    # Parse Bloom Taxonomy levels
    bloom_levels = {}
    if any([bloom_remember, bloom_understand, bloom_apply, bloom_analyze, bloom_evaluate, bloom_create]):
        bloom_levels = {
            "remember": bloom_remember or 0,
            "understand": bloom_understand or 0,
            "apply": bloom_apply or 0,
            "analyze": bloom_analyze or 0,
            "evaluate": bloom_evaluate or 0,
            "create": bloom_create or 0
        }
        # Validate sum to 100
        total_bloom = sum(bloom_levels.values())
        if total_bloom != 100 and total_bloom != 0:
            raise HTTPException(status_code=400, detail=f"Bloom taxonomy levels must sum to 100, got {total_bloom}")
    else:
        # Default distribution
        bloom_levels = {
            "remember": 20,
            "understand": 30,
            "apply": 30,
            "analyze": 20,
            "evaluate": 0,
            "create": 0
        }
    
    # Parse paper pattern
    sections = None
    if paper_pattern:
        try:
            pattern_data = json_lib.loads(paper_pattern)
            sections = pattern_data.get("sections", [])
            print(f"📐 Received sections: {json_lib.dumps(sections, indent=2)}")
        except json_lib.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON format for paper_pattern")
    
    # Parse teacher input
    teacher_instructions = {
        "focus_areas": [],
        "preferences": teacher_input or "Standard difficulty"
    }
    
    # Use provided session_id or generate new one
    if not session_id or not session_id.strip():
        paper_session_id = str(uuid.uuid4())
    else:
        paper_session_id = session_id.strip()
    
    print(f"📄 Using paper generation session_id: {paper_session_id}")
    
    try:
        # Run paper generation workflow
        result = await generate_paper_workflow(
            session_id=paper_session_id,
            syllabus_session_id=syllabus_session_id,
            pyqs_session_id=pyqs_session_id,
            total_marks=total_marks,
            total_questions=total_questions,
            bloom_levels=bloom_levels,
            paper_sections=sections,
            teacher_inputs=teacher_instructions
        )
        
        # Extract paper from result (use draft_paper, not final_paper)
        paper_data = result.get("draft_paper", {})
        verification_data = result.get("paper_verdict", {})
        pdf_path = result.get("final_path", "")
        
        return JSONResponse(content={
            "status": "success",
            "session_id": paper_session_id,
            "paper": paper_data,
            "verification": verification_data,
            "pdf_path": pdf_path,
            "message": "Question paper generated successfully"
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in paper generation: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Paper generation failed: {str(e)}")
=======
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
>>>>>>> graph_generator
