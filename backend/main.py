# backend/main.py
import uuid
import os
import json as json_lib
from fastapi import FastAPI, WebSocket, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from starlette.websockets import WebSocketDisconnect
from typing import Optional
from backend.websocket.manager import manager
from backend.services.pipeline import (
    analyze_syllabus_workflow,
    analyze_pyqs_workflow,
    generate_paper_workflow
)
from backend.services.template_service.extractor import extract_placeholders, extract_pattern
from backend.services.template_service.storage import save_template, list_templates, get_template_meta, get_template_path
from backend.services.template_service.renderer import render_template
from backend.services.Answer_Key_Generator.answer_key import generate_answer_key, generate_pdf
from backend.Storage.Blob_Storage.blob_upload import upload_to_azure
from backend.services.paper_pdf_gen import format_paper_to_pdf
from backend.database import get_db, engine
from backend.models import Base, User, Project, PipelineData, Document, TemplateData
from sqlalchemy.orm import Session

# Create DB tables
Base.metadata.create_all(bind=engine)

backend = FastAPI()

def ensure_db_user_project(db_session: Session, user_id: str, project_id: Optional[str] = None, 
                           name: Optional[str] = None, subject: Optional[str] = None, 
                           grade: Optional[str] = None, total_marks: Optional[int] = None, 
                           duration: Optional[str] = None):
    # Check/Create User
    if user_id:
        user = db_session.query(User).filter_by(clerk_id=user_id).first()
        if not user:
            user = User(clerk_id=user_id, name="User", email="no-email")
            db_session.add(user)
            db_session.flush()
    
    # Check/Create Project
    if project_id and user_id:
        proj = db_session.query(Project).filter_by(id=project_id).first()
        if not proj:
            proj = Project(
                id=project_id,
                user_id=user_id,
                name=name or f"Generated Project",
                subject=subject or "Unknown",
                grade=grade or "Unknown",
                total_marks=total_marks or 80,
                duration=duration or "3 Hours",
                status="draft"
            )
            db_session.add(proj)
        else:
            # Update metadata if provided
            if name: proj.name = name
            if subject: proj.subject = subject
            if grade: proj.grade = grade
            if total_marks: proj.total_marks = total_marks
            if duration: proj.duration = duration
        
        db_session.commit()

def ensure_pipeline_data(db_session: Session, project_id: str):
    pld = db_session.query(PipelineData).filter_by(project_id=project_id).first()
    if not pld:
        pld = PipelineData(project_id=project_id)
        db_session.add(pld)
        db_session.flush()
    return pld

@backend.post("/init-project")
async def init_project(
    user_id: str = Form(...),
    project_id: str = Form(...),
    name: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    total_marks: Optional[int] = Form(None),
    duration: Optional[str] = Form(None),
):
    """
    Called by frontend to pre-warm the project in the DB with metadata.
    """
    try:
        db_session = next(get_db())
        ensure_db_user_project(
            db_session, user_id, project_id,
            name=name, subject=subject, grade=grade,
            total_marks=total_marks, duration=duration
        )
        return JSONResponse(content={"status": "success", "message": "Project initialized"})
    except Exception as e:
        print(f"Init Project Err: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Enable CORS for frontend access
backend.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@backend.websocket("/ws/{session_id}")
async def websocket_logs(websocket: WebSocket, session_id: str):
    await manager.connect(session_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# ==========================================
# API 1: Analyze Syllabus
# ==========================================
@backend.post("/analyze-syllabus")
async def analyze_syllabus(
    file: Optional[UploadFile] = File(None),
    text_content: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    subject: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    total_marks: Optional[int] = Form(None),
    duration: Optional[str] = Form(None)
):
    """Analyze syllabus from file or text."""
    if not file and not text_content:
        raise HTTPException(status_code=400, detail="Either 'file' or 'text_content' must be provided")

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
        
        # ☁️ Azure Upload: Syllabus PDF
        azure_url = None
        safe_subject = (subject or "subject").replace(" ", "_").lower()
        if pdf_path:
            blob_name = f"user_{user_id or 'anon'}/{project_id or session_id}/{safe_subject}_syllabus.pdf"
            azure_url = upload_to_azure(pdf_path, "qpilot-uploads", blob_name)
            print(f"☁️ Syllabus uploaded to Azure: {azure_url}")

        # ☁️ If text was provided instead of file, upload text if no PDF was uploaded
        if not azure_url and text_content:
            blob_name = f"user_{user_id or 'anon'}/{project_id or session_id}/{safe_subject}_syllabus.txt"
            azure_url = upload_to_azure(text_content.encode('utf-8'), "qpilot-uploads", blob_name, is_bytes=True)

        if user_id and project_id:
            try:
                db_session = next(get_db())
                # Update project metadata
                ensure_db_user_project(
                    db_session, user_id, project_id,
                    name=title, subject=subject, grade=grade, 
                    total_marks=total_marks, duration=duration
                )
                
                # 🔹 Record in Documents
                if azure_url:
                    _subj = subject or "Subject"
                    doc = Document(
                        user_id=user_id,
                        project_id=project_id,
                        name=f"{_subj}_syllabus.pdf",
                        doc_type="syllabus",
                        azure_url=azure_url
                    )
                    db_session.add(doc)
                
                # 🔹 Record in PipelineData
                pld = ensure_pipeline_data(db_session, project_id)
                pld.syllabus_json = result["syllabus"]
                
                db_session.commit()
            except Exception as e:
                print(f"Failed to record syllabus doc/data: {e}")

        return JSONResponse(content={
            "status": "success",
            "session_id": session_id,
            "syllabus": result["syllabus"],
            "azure_url": azure_url,
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
    text_content: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None)
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
    if text_content and not text_content.strip():
        text_content = None
    
    pyq_text = (text_content or "").strip()
    no_pyq_sentinel = pyq_text.lower().startswith("no pyqs available")
    has_real_pyq_input = bool(file) or (bool(pyq_text) and not no_pyq_sentinel)

    if not file and not text_content:
        raise HTTPException(status_code=400, detail="Either 'file' or 'text_content' must be provided")
    
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
        os.makedirs(os.path.join("backend", "services", "data", pyqs_session_id), exist_ok=True)

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
        
        # ☁️ Azure Upload: PYQs PDF
        azure_url = None
        if user_id and project_id:
            try:
                _db = next(get_db())
                _proj_for_pyq = _db.query(Project).filter_by(id=project_id).first()
                _pyq_subject = (_proj_for_pyq.subject if _proj_for_pyq and _proj_for_pyq.subject else "subject").replace(" ", "_").lower()
            except Exception:
                _pyq_subject = "subject"
        else:
            _pyq_subject = "subject"
        if has_real_pyq_input and pdf_path:
            blob_name = f"user_{user_id or 'anon'}/{project_id or pyqs_session_id}/{_pyq_subject}_pyqs.pdf"
            azure_url = upload_to_azure(pdf_path, "qpilot-uploads", blob_name)
            print(f"☁️ PYQs uploaded to Azure: {azure_url}")

        if user_id and project_id:
            # ☁️ If text was provided instead of file, upload text as a convenience record too
            if has_real_pyq_input and (not azure_url) and text_content:
                blob_name = f"user_{user_id}/{project_id}/{_pyq_subject}_pyqs.txt"
                azure_url = upload_to_azure(text_content.encode('utf-8'), "qpilot-uploads", blob_name, is_bytes=True)

            try:
                db_session = next(get_db())
                ensure_db_user_project(db_session, user_id, project_id)
                
                # 🔹 Record in Documents
                if has_real_pyq_input and azure_url:
                    if file and file.filename:
                        saved_name = file.filename
                    elif text_content:
                        saved_name = f"{_pyq_subject.replace('_', ' ').title()}_pyqs.txt"
                    else:
                        saved_name = f"{_pyq_subject.replace('_', ' ').title()}_pyqs.pdf"
                    doc = Document(
                        user_id=user_id,
                        project_id=project_id,
                        name=saved_name,
                        doc_type="pyqs",
                        azure_url=azure_url
                    )
                    db_session.add(doc)
                    
                # 🔹 Record in PipelineData
                pld = ensure_pipeline_data(db_session, project_id)
                pld.pyqs_json = result["pyqs"]
                
                db_session.commit()
            except Exception as e:
                print(f"Failed to record PYQ doc/data: {e}")

        return JSONResponse(content={
            "status": "success",
            "session_id": pyqs_session_id,
            "pyqs": result["pyqs"],
            "azure_url": azure_url,
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
    total_marks: Optional[int] = Form(None),
    total_questions: Optional[int] = Form(None),
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
    session_id: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None)
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
    raw_bloom = {
        "remember": bloom_remember or 0,
        "understand": bloom_understand or 0,
        "apply": bloom_apply or 0,
        "analyze": bloom_analyze or 0,
        "evaluate": bloom_evaluate or 0,
        "create": bloom_create or 0,
    }
    total_bloom = sum(raw_bloom.values())
    if total_bloom > 0:
        # Auto-normalize to 100 so partial inputs still work
        bloom_levels = {k: round(v / total_bloom * 100) for k, v in raw_bloom.items()}
        # Fix any rounding drift on the largest key
        drift = 100 - sum(bloom_levels.values())
        if drift:
            largest = max(bloom_levels, key=bloom_levels.get)  # type: ignore[arg-type]
            bloom_levels[largest] += drift
    else:
        bloom_levels = {"remember": 20, "understand": 30, "apply": 30, "analyze": 20, "evaluate": 0, "create": 0}
    
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
        "preferences": teacher_input or "Standard difficulty",
        # Same text as `preferences` so pipeline / blueprint / question code using `input` still see it
        "input": teacher_input or "",
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
            total_marks=total_marks or 0,
            total_questions=total_questions or 0,
            bloom_levels=bloom_levels,
            paper_sections=sections,
            teacher_inputs=teacher_instructions
        )
        
        # Extract paper from result (use draft_paper, not final_paper)
        paper_data = result.get("draft_paper", {})
        verification_data = result.get("paper_verdict", {})
        pdf_path = result.get("final_path", "")
        
        # 📄 Convert JSON Paper to Formatted PDF
        generated_pdf_path = os.path.join("backend", "services", "data", paper_session_id, "question_paper.pdf")
        os.makedirs(os.path.dirname(generated_pdf_path), exist_ok=True)
        
        # Add metadata for PDF formatting
        paper_for_pdf = paper_data.copy()
        paper_for_pdf.update({
            "title": "Question Paper",
            "subject": "Examination",  # Could be pulled from metadata if available
            "grade": "Semester",
            "total_marks": total_marks or 80,
            "duration": "3 Hours"
        })
        
        format_paper_to_pdf(paper_for_pdf, generated_pdf_path)
        
        # ☁️ Azure Upload: Generated Paper PDF (temp upload before we have subject info)
        _tmp_subject = "subject"
        azure_pdf_url = upload_to_azure(generated_pdf_path, "qpilot-results", f"user_unknown/{paper_session_id}/{_tmp_subject}_generated_paper.pdf")
        print(f"☁️ Generated Paper uploaded to Azure: {azure_pdf_url}")

        if user_id and project_id:
            try:
                db_session = next(get_db())
                
                # Check User and Project using our helper
                ensure_db_user_project(db_session, user_id, project_id)
                proj = db_session.query(Project).filter_by(id=project_id).first()
                
                # Use project metadata for PDF if available
                pdf_subject = proj.subject if proj and proj.subject else "Examination"
                pdf_grade = proj.grade if proj and proj.grade else "Semester"
                pdf_title = proj.name if proj and proj.name else "Question Paper"

                # 📄 Re-generate PDF with REAL metadata if available
                paper_for_pdf = paper_data.copy()
                paper_for_pdf.update({
                    "title": pdf_title,
                    "subject": pdf_subject,
                    "grade": pdf_grade,
                    "total_marks": total_marks or 80,
                    "duration": proj.duration if proj and proj.duration else "3 Hours"
                })
                format_paper_to_pdf(paper_for_pdf, generated_pdf_path)
                _safe_subj_paper = pdf_subject.replace(" ", "_").lower()
                azure_pdf_url = upload_to_azure(generated_pdf_path, "qpilot-results", f"user_{user_id}/{project_id}/{_safe_subj_paper}_generated_paper.pdf")

                if proj:
                    proj.status = "done"
                    proj.total_marks = total_marks or 80
                
                # Add Paper Doc
                if azure_pdf_url:
                    doc = Document(
                        user_id=user_id,
                        project_id=project_id,
                        name=f"{pdf_subject}_generated_paper.pdf",
                        doc_type="final_pdf",
                        azure_url=azure_pdf_url
                    )
                    db_session.add(doc)

                # Add/Update Pipeline Data
                pld = ensure_pipeline_data(db_session, project_id)
                
                def load_json(name):
                    try:
                        with open(os.path.join("backend", "services", "data", paper_session_id, name), "r", encoding="utf-8") as f:
                            return json_lib.load(f)
                    except Exception:
                        return None
                
                pld.syllabus_json = load_json("syllabus.json")
                pld.knowledge_graph_json = load_json("knowledge_graph.json")
                pld.pyqs_json = load_json("pyqs.json")
                pld.blueprint_json = load_json("blueprint.json")
                pld.blueprint_verification_json = load_json("blueprint_verification.json")
                pld.draft_paper_json = load_json("draft_paper.json")
                pld.final_paper_json = load_json("final_paper.json")
                
                db_session.commit()
                print("✅ Successfully saved paper data to database")
            except Exception as db_err:
                print(f"❌ Database save error: {db_err}")

        return JSONResponse(content={
            "status": "success",
            "session_id": paper_session_id,
            "paper": paper_data,
            "verification": verification_data,
            "pdf_url": azure_pdf_url,
            "message": "Question paper generated successfully"
        })
        
    except Exception as e:
        import traceback
        print(f"❌ Error in paper generation: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Paper generation failed: {str(e)}")


# ==========================================
# API 4: Upload Template
# ==========================================
@backend.post("/templates/upload")
async def upload_template(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
):
    """
    Upload a DOCX template file, extract its placeholders + pattern,
    and store it for the given user_id (or a default 'anonymous').
    Returns the extracted pattern and placeholder list.
    """
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are supported.")

    uid = (user_id or "anonymous").strip()
    file_bytes = await file.read()

    # Save temporarily to extract metadata
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx", mode="wb") as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        placeholders = extract_placeholders(tmp_path)
        pattern = extract_pattern(tmp_path)
    finally:
        os.unlink(tmp_path)

    # Persist the template
    meta = save_template(
        user_id=uid,
        file_bytes=file_bytes,
        filename=file.filename,
        pattern=pattern,
        placeholders=placeholders.get("all", []),
    )

    # ☁️ Azure Upload: DOCX Template
    template_id = meta["template_id"]
    blob_name = f"templates/{uid}/{template_id}/{file.filename}"
    azure_template_url = upload_to_azure(file_bytes, "qpilot-templates", blob_name, is_bytes=True)

    if user_id and azure_template_url:
        try:
            db_session = next(get_db())
            ensure_db_user_project(db_session, user_id)
            doc = Document(
                user_id=user_id,
                name=f"Template: {file.filename}",
                doc_type="template",
                azure_url=azure_template_url
            )
            db_session.add(doc)
            
            # Persist to TemplateData so it survives container restarts
            td = TemplateData(
                id=template_id,
                user_id=user_id,
                name=file.filename,
                azure_url=azure_template_url,
                pattern_json=pattern,
                placeholders_json=placeholders.get("all", [])
            )
            db_session.add(td)
            
            db_session.commit()
        except Exception as e:
            print(f"Failed to record template doc: {e}")
            
    # Inject azure url into meta so it can be sent in /templates/list
    meta["azure_url"] = azure_template_url
    
    user_dir = os.path.dirname(meta["docx_path"])
    meta_path = os.path.join(user_dir, f"{template_id}.meta.json")
    with open(meta_path, "w") as f:
        json_lib.dump(meta, f, indent=2)

    return JSONResponse(content={
        "status": "success",
        "template_id": meta["template_id"],
        "name": meta["name"],
        "pattern": pattern,
        "placeholders": placeholders,
        "azure_url": azure_template_url,
        "message": "Template uploaded and analyzed successfully.",
    })


# ==========================================
# API 5: List Templates
# ==========================================
@backend.get("/templates/list")
async def list_user_templates(user_id: Optional[str] = None):
    """
    List all uploaded templates for a user.
    """
    uid = (user_id or "anonymous").strip()
    
    templates = []
    
    # Try fetching from database first
    if user_id:
        try:
            db_session = next(get_db())
            db_templates = db_session.query(TemplateData).filter_by(user_id=uid).all()
            for t in db_templates:
                templates.append({
                    "template_id": t.id,
                    "name": t.name,
                    "azure_url": t.azure_url,
                    "pattern": t.pattern_json,
                    "placeholders": t.placeholders_json,
                })
        except Exception as e:
            print(f"Error fetching templates from DB: {e}")
            
    # Fallback to local disk if DB is empty or fails
    if not templates:
        templates = list_templates(uid)
        
    return JSONResponse(content={
        "status": "success",
        "templates": templates,
    })


# ==========================================
# API 6: Get Template Pattern
# ==========================================
@backend.get("/templates/{template_id}/pattern")
async def get_template_pattern(template_id: str, user_id: Optional[str] = None):
    """
    Get the extracted pattern for a specific template (for autofill in frontend).
    """
    uid = (user_id or "anonymous").strip()
    
    # Check DB first
    if user_id:
        try:
            db_session = next(get_db())
            t = db_session.query(TemplateData).filter_by(id=template_id, user_id=uid).first()
            if t:
                return JSONResponse(content={
                    "status": "success",
                    "template_id": template_id,
                    "name": t.name,
                    "pattern": t.pattern_json,
                    "placeholders": t.placeholders_json or [],
                })
        except:
            pass
            
    meta = get_template_meta(uid, template_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found.")

    return JSONResponse(content={
        "status": "success",
        "template_id": template_id,
        "name": meta["name"],
        "pattern": meta["pattern"],
        "placeholders": meta.get("placeholders", []),
    })


# ==========================================
# API 7: Render Paper in Template
# ==========================================
@backend.post("/templates/render")
async def render_paper_in_template(
    template_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    paper_json: str = Form(...),          # JSON string of the generated paper
    subject: Optional[str] = Form(None),
    class_name: Optional[str] = Form(None),
    marks: Optional[str] = Form(None),
    date: Optional[str] = Form(None),
    duration: Optional[str] = Form(None),
    exam_name: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None),
):
    """
    Render a generated paper JSON into the chosen DOCX template.
    Replaces all [placeholder] tokens and returns the DOCX file for download.
    """
    uid = (user_id or "anonymous").strip()
    docx_path = get_template_path(uid, template_id)
    
    # If not found locally, download it from Azure Blob Storage using DB
    if not docx_path or not os.path.exists(docx_path):
        azure_url = None
        if user_id:
            try:
                db_session = next(get_db())
                t = db_session.query(TemplateData).filter_by(id=template_id, user_id=uid).first()
                if t and t.azure_url:
                    azure_url = t.azure_url
            except Exception as e:
                print(f"Error querying template DB: {e}")
                
        if azure_url:
            import urllib.request
            import tempfile
            try:
                temp_docx_path = os.path.join(tempfile.gettempdir(), f"{template_id}_downloaded.docx")
                urllib.request.urlretrieve(azure_url, temp_docx_path)
                docx_path = temp_docx_path
            except Exception as e:
                print(f"Failed to download azure url {azure_url} : {e}")
                
    if not docx_path or not os.path.exists(docx_path):
        raise HTTPException(status_code=404, detail=f"Template {template_id} DOCX file not found.")

    try:
        paper = json_lib.loads(paper_json)
    except json_lib.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in paper_json field.")

    # Fill missing template metadata from project to avoid blank [subject]/[class]
    project_fallback = None
    if user_id and project_id:
        try:
            db_session = next(get_db())
            project_fallback = db_session.query(Project).filter_by(id=project_id, user_id=uid).first()
        except Exception:
            project_fallback = None

    normalized_subject = (subject or "").strip()
    normalized_class = (class_name or "").strip()
    normalized_marks = (marks or "").strip()
    normalized_duration = (duration or "").strip()
    normalized_exam_name = (exam_name or "").strip()
    dash_like = {"-", "--", "---", "----", "-----", "—"}

    metadata = {
        "subject": normalized_subject if normalized_subject and normalized_subject not in dash_like else (project_fallback.subject if project_fallback and project_fallback.subject else ""),
        "class": normalized_class if normalized_class and normalized_class not in dash_like else (project_fallback.grade if project_fallback and project_fallback.grade else ""),
        "marks": normalized_marks if normalized_marks and normalized_marks not in dash_like else (str(project_fallback.total_marks) if project_fallback and project_fallback.total_marks is not None else ""),
        "date": (date or "").strip(),
        "duration": normalized_duration if normalized_duration and normalized_duration not in dash_like else (project_fallback.duration if project_fallback and project_fallback.duration else ""),
        "exam_name": normalized_exam_name if normalized_exam_name and normalized_exam_name not in dash_like else (project_fallback.name if project_fallback and project_fallback.name else ""),
    }

    try:
        import tempfile
        out_path = os.path.join(tempfile.gettempdir(), f"rendered_{template_id}_{uuid.uuid4().hex[:8]}.docx")
        rendered_path = render_template(
            docx_path=docx_path,
            paper_json=paper,
            metadata=metadata,
            out_path=out_path,
        )
    except Exception as e:
        import traceback
        print(f"❌ Template render error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Template rendering failed: {str(e)}")

    # Build human-readable filename: {subject}_generated_paper.docx
    _render_subject = (subject or exam_name or "subject").replace(" ", "_")
    filename = f"{_render_subject}_generated_paper.docx"
    
    # Upload generated template DOCX to Azure + DB if tied to a project
    if user_id and project_id:
        try:
            import uuid as uuid_pkg
            blob_name = f"user_{user_id}/{project_id}/{filename}"
            azure_url = upload_to_azure(rendered_path, "qpilot-results", blob_name)
            if azure_url:
                db_session = next(get_db())
                ensure_db_user_project(db_session, user_id, project_id)
                doc = Document(
                    user_id=user_id,
                    project_id=project_id,
                    name=filename,
                    doc_type="docx_paper",
                    azure_url=azure_url
                )
                db_session.add(doc)
                db_session.commit()
        except:
            pass

    return FileResponse(
        path=rendered_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename,
    )


@backend.delete("/templates/delete")
async def delete_template_endpoint(
    template_id: str,
    user_id: Optional[str] = None
):
    uid = (user_id or "anonymous").strip()
    
    # Remove from DB if possible
    azure_url = None
    if user_id:
        try:
            db_session = next(get_db())
            t = db_session.query(TemplateData).filter_by(id=template_id, user_id=uid).first()
            if t:
                azure_url = t.azure_url
                db_session.delete(t)
            
            # Also clean up Document table
            if azure_url:
                db_session.query(Document).filter_by(azure_url=azure_url, user_id=uid).delete()
            else:
                db_session.query(Document).filter(Document.name.contains(template_id), Document.user_id==uid).delete()
                
            db_session.commit()
        except Exception as e:
            print(f"Error deleting template from DB: {e}")
            
    # Remove from local
    user_dir = os.path.join("backend", "Storage", "templates", uid)
    meta_path = os.path.join(user_dir, f"{template_id}.meta.json")
    
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                meta = json_lib.load(f)
                docx_path = meta.get("docx_path")
                if docx_path and os.path.exists(docx_path):
                    os.unlink(docx_path)
            os.unlink(meta_path)
        except Exception:
            pass

    return JSONResponse(content={"status": "success", "message": "Template deleted"})

# ==========================================
# API 8: Generate Answer Key
# ==========================================
@backend.post("/generate-answer-key")
async def generate_answer_key_api(
    paper_json: str = Form(...),          # JSON string of the generated paper (same format as /generate-paper response)
    syllabus_text: Optional[str] = Form(None),  # Optional raw syllabus text for richer context
    download_pdf: Optional[str] = Form(None),    # "true" to return PDF, else returns JSON
    user_id: Optional[str] = Form(None),
    project_id: Optional[str] = Form(None)
):
    """
    Accepts the generated paper JSON, calls the Answer Key Generator
    (using the shared OpenAI LLM service), and returns either:
    - JSON answer key  (default)
    - PDF file download (when download_pdf="true")
    """
    try:
        paper = json_lib.loads(paper_json)
    except json_lib.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in paper_json field.")

    syllabus = (syllabus_text or "").strip()

    try:
        answer_key_data = generate_answer_key(paper, syllabus)
    except Exception as e:
        import traceback
        print(f"\u274c Answer key generation error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Answer key generation failed: {str(e)}")

    if (download_pdf or "").lower() == "true":
        import tempfile
        import uuid as uuid_pkg
        out_path = os.path.join(tempfile.gettempdir(), f"answer_key_{uuid_pkg.uuid4().hex[:8]}.pdf")
        try:
            generate_pdf(answer_key_data, output_path=out_path)
            
            # ☁️ Azure Upload: Answer Key PDF - named by subject from project
            _ak_subject = "subject"
            if project_id and user_id:
                try:
                    _ak_db = next(get_db())
                    _ak_proj = _ak_db.query(Project).filter_by(id=project_id).first()
                    if _ak_proj and _ak_proj.subject:
                        _ak_subject = _ak_proj.subject.replace(" ", "_").lower()
                except Exception:
                    pass
            blob_name = f"user_{user_id or 'anon'}/{project_id or 'unknown'}/{_ak_subject}_answer_Key.pdf"
            azure_url = upload_to_azure(out_path, "qpilot-results", blob_name)
            print(f"☁️ Answer Key uploaded to Azure: {azure_url}")
            
            if user_id and azure_url:
                try:
                    db_session = next(get_db())
                    ensure_db_user_project(db_session, user_id, project_id)
                    # 🔹 Record in Documents
                    doc = Document(
                        user_id=user_id,
                        project_id=project_id,
                        name=f"{_ak_subject.replace('_', ' ').title()}_answer_Key.pdf",
                        doc_type="answer_key",
                        azure_url=azure_url
                    )
                    db_session.add(doc)
                    
                    # 🔹 Record in PipelineData
                    pld = ensure_pipeline_data(db_session, project_id)
                    pld.answer_key_json = answer_key_data
                    
                    db_session.commit()
                except Exception as db_err:
                    print(f"Failed to save Answer Key Doc/Data to DB: {db_err}")
            
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF generation or Azure upload failed: {str(e)}")
        
        return JSONResponse(content={
            "status": "success",
            "answer_key": answer_key_data,
            "pdf_url": azure_url,
            "message": "Answer key generated and saved to cloud"
        })

    return JSONResponse(content={
        "status": "success",
        "answer_key": answer_key_data,
        "message": "Answer key generated successfully"
    })
