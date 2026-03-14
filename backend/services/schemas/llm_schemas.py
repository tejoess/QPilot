"""
Pydantic schemas for LLM output parsing
Ensures strict JSON structure enforcement
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


# ============================================================================
# SYLLABUS SCHEMAS
# ============================================================================

class SyllabusModule(BaseModel):
    module_number: int = Field(description="Module number (e.g., 1, 2, 3)")
    module_name: str = Field(description="Module name")
    weightage_hours: Optional[int] = Field(default=None, description="Weightage in hours")
    topics: List[str] = Field(default_factory=list, description="List of topic names as strings")


class SyllabusOutput(BaseModel):
    course_code: Optional[str] = Field(default="", description="Course code")
    course_name: Optional[str] = Field(default="", description="Course name")
    course_objectives: Optional[List[str]] = Field(default_factory=list, description="Course objectives")
    course_outcomes: Optional[List[str]] = Field(default_factory=list, description="Course outcomes")
    modules: List[SyllabusModule] = Field(description="List of modules")


# ============================================================================
# PYQ SCHEMAS
# ============================================================================


class PYQQuestion(BaseModel):
    question: str = Field(description="Full question text")
    topic: str = Field(description="Topic from syllabus")
    subtopic: str = Field(description="Subtopic from syllabus")
    marks: int = Field(description="Marks for the question")
    bloom_level: str = Field(default="Understand", description="Bloom's taxonomy level: Remember, Understand, Apply, Analyze, Evaluate, or Create")


class PYQOutput(BaseModel):
    questions: List[PYQQuestion] = Field(description="List of extracted questions")


# ============================================================================
# BLUEPRINT SCHEMAS
# ============================================================================

class BlueprintQuestion(BaseModel):
    question_number: str = Field(description="Question identifier (e.g., '1a')")
    module: str = Field(description="Module name")
    topic: str = Field(description="Topic name")
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

# NEW FORMAT (matches updated prompt)
class ComputedMetrics(BaseModel):
    total_marks: int = Field(description="Computed total marks")
    total_questions: int = Field(description="Computed total questions")
    module_distribution: Dict[str, int] = Field(description="Marks per module")
    bloom_distribution: Dict[str, float] = Field(description="Bloom level percentages")
    pyq_count: int = Field(description="Number of PYQs used")


class VerificationIssue(BaseModel):
    question: str = Field(description="Question identifier or 'overall'")
    metric: str = Field(description="Metric name (e.g., constraint_compliance)")
    severity: str = Field(description="critical, high, medium, or low")
    problem: str = Field(description="Problem description")
    fix: str = Field(description="How to fix")


class VerificationScores(BaseModel):
    constraint_compliance: int = Field(ge=0, le=10)
    bloom_balance: int = Field(ge=0, le=10)
    module_balance: int = Field(ge=0, le=10)
    pyq_utilization: int = Field(ge=0, le=10)
    difficulty_progression: int = Field(ge=0, le=10)
    topic_diversity: int = Field(ge=0, le=10)
    syllabus_coverage: int = Field(ge=0, le=10)
    teacher_alignment: int = Field(ge=0, le=10)


class VerificationOverall(BaseModel):
    total: int = Field(description="Sum of all scores")
    out_of: int = Field(default=100, description="Maximum possible score")
    verdict: str = Field(description="APPROVED | APPROVED_WITH_WARNINGS | NEEDS_REVISION | REJECTED")
    summary: str = Field(description="2-sentence summary")


class BlueprintVerificationOutputNew(BaseModel):
    """New format matching updated prompt"""
    computed: ComputedMetrics = Field(description="Computed metrics")
    issues: List[VerificationIssue] = Field(default_factory=list, description="List of issues")
    scores: VerificationScores = Field(description="Individual metric scores")
    overall: VerificationOverall = Field(description="Overall verdict")


# LEGACY FORMAT (for backwards compatibility)
class MetricScore(BaseModel):
    score: int = Field(ge=0, le=10, description="Score out of 10")
    status: str = Field(description="excellent, good, acceptable, or poor")
    details: str = Field(description="Brief feedback")


class BlueprintVerificationOutput(BaseModel):
    overall_rating: Dict[str, Any] = Field(description="Overall rating details")
    metric_scores: Dict[str, MetricScore] = Field(description="Individual metric scores")
    critical_issues: List[Dict[str, Any]] = Field(default_factory=list, description="Critical issues found")
    warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Warnings")
    recommendations: Dict[str, List[str]] = Field(default_factory=dict, description="Recommendations")
    detailed_analysis: Dict[str, Any] = Field(default_factory=dict, description="Detailed analysis")
    pass_fail_decision: Dict[str, Any] = Field(default_factory=dict, description="Pass/fail decision")
    statistics: Optional[Dict[str, Any]] = Field(default=None, description="Statistics")


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
