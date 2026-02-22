"""
Pydantic schemas for LLM output parsing
Ensures strict JSON structure enforcement
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# SYLLABUS SCHEMAS
# ============================================================================

class SyllabusSubtopic(BaseModel):
    name: str = Field(description="Subtopic name")
    description: Optional[str] = Field(default="", description="Brief description")


class SyllabusTopic(BaseModel):
    name: str = Field(description="Topic name")
    subtopics: List[SyllabusSubtopic] = Field(default_factory=list)


class SyllabusModule(BaseModel):
    module_number: str = Field(description="Module number (e.g., 'Module 1')")
    module_name: str = Field(description="Module name")
    weightage: float = Field(description="Weightage as decimal (e.g., 0.20 for 20%)")
    topics: List[SyllabusTopic] = Field(default_factory=list)


class SyllabusOutput(BaseModel):
    course_code: Optional[str] = Field(default="", description="Course code")
    course_name: Optional[str] = Field(default="", description="Course name")
    modules: List[SyllabusModule] = Field(description="List of modules")


# ============================================================================
# PYQ SCHEMAS
# ============================================================================

class PYQQuestion(BaseModel):
    question: str = Field(description="Full question text")
    topic: str = Field(description="Topic from syllabus")
    subtopic: str = Field(description="Subtopic from syllabus")
    marks: int = Field(description="Marks for the question")


class PYQOutput(BaseModel):
    questions: List[PYQQuestion] = Field(description="List of extracted questions")


# ============================================================================
# BLUEPRINT SCHEMAS
# ============================================================================

class BlueprintQuestion(BaseModel):
    question_number: str = Field(description="Question identifier (e.g., '1a')")
    module: str = Field(description="Module name")
    topic: str = Field(description="Topic name")
    subtopic: str = Field(description="Subtopic name")
    marks: int = Field(description="Marks allocated")
    bloom_level: str = Field(description="Bloom's taxonomy level")
    is_pyq: bool = Field(description="Whether to use a PYQ")
    rationale: str = Field(description="Brief rationale (max 5 words)")


class BlueprintSection(BaseModel):
    section_name: str = Field(description="Section name")
    section_description: str = Field(description="Section description")
    questions: List[BlueprintQuestion] = Field(description="Questions in this section")


class BlueprintMetadata(BaseModel):
    total_marks: int
    total_questions: int
    bloom_distribution: Dict[str, float] = Field(description="Bloom level percentages")
    module_distribution: Dict[str, float] = Field(description="Module weightage percentages")
    pyq_usage: Dict[str, float] = Field(description="PYQ usage statistics")


class BlueprintOutput(BaseModel):
    blueprint_metadata: BlueprintMetadata
    sections: List[BlueprintSection]


# ============================================================================
# BLUEPRINT VERIFICATION SCHEMAS
# ============================================================================

class MetricScore(BaseModel):
    score: int = Field(ge=0, le=10, description="Score out of 10")
    status: str = Field(description="excellent, good, acceptable, or poor")
    feedback: str = Field(description="Brief feedback")


class BlueprintVerificationOutput(BaseModel):
    overall_rating: Dict[str, Any] = Field(description="Overall rating details")
    metric_scores: Dict[str, MetricScore] = Field(description="Individual metric scores")
    critical_issues: List[str] = Field(default_factory=list, description="Critical issues found")
    warnings: List[str] = Field(default_factory=list, description="Warnings")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="Statistics")


# ============================================================================
# PAPER VERIFICATION SCHEMAS
# ============================================================================

class PaperVerificationOutput(BaseModel):
    rating: float = Field(ge=0, le=10, description="Overall rating")
    verdict: str = Field(description="ACCEPTED or REJECTED")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")
    summary: str = Field(description="Summary text")
    detailed_scores: Dict[str, Any] = Field(default_factory=dict, description="Detailed breakdown")
