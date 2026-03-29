from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class User(Base):
    __tablename__ = "users"
    
    clerk_id = Column(String, primary_key=True, index=True) # Clerk user ID
    email = Column(String, index=True, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    papers = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")

class Project(Base):
    """
    Project / Paper details
    """
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True) # Like proj-xyz
    user_id = Column(String, ForeignKey("users.clerk_id"))
    
    name = Column(String, index=True)
    subject = Column(String)
    grade = Column(String)
    total_marks = Column(Integer)
    duration = Column(String)
    status = Column(String, default="draft") # draft, processing, done, error
    
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="papers")
    pipeline = relationship("PipelineData", back_populates="project", uselist=False, cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")

class PipelineData(Base):
    """
    Pipeline generation JSON outputs
    """
    __tablename__ = "pipeline_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), unique=True)
    
    syllabus_json = Column(JSON, nullable=True)
    knowledge_graph_json = Column(JSON, nullable=True)
    pyqs_json = Column(JSON, nullable=True)
    blueprint_json = Column(JSON, nullable=True)
    blueprint_verification_json = Column(JSON, nullable=True)
    paper_metadata_json = Column(JSON, nullable=True)
    draft_paper_json = Column(JSON, nullable=True)
    final_paper_json = Column(JSON, nullable=True)
    answer_key_json = Column(JSON, nullable=True)

    project = relationship("Project", back_populates="pipeline")

class Document(Base):
    """
    Azure Blob linked documents
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.clerk_id"))
    project_id = Column(String, ForeignKey("projects.id"), nullable=True) # Optional link to a specific paper
    
    name = Column(String)
    doc_type = Column(String) # syllabus, pyq, template, final_pdf, answer_key_pdf
    azure_url = Column(String)
    file_size_bytes = Column(Integer, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="documents")
    project = relationship("Project", back_populates="documents")
