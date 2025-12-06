"""
Response models for Visual Tutor API.

Defines Pydantic models for all API responses ensuring
consistent, well-documented, and validated response structures.
"""

from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ConfusionAnalysis(BaseModel):
    """Analysis of student's confusion point."""
    
    confusion_concept: str = Field(
        default="unknown",
        description="The specific concept the student is confused about"
    )
    difficulty_level: str = Field(
        default="intermediate",
        description="Estimated difficulty level (beginner, intermediate, advanced)"
    )
    suggested_explanation_type: str = Field(
        default="schematic",
        description="Recommended visual style for explanation"
    )
    subject: str = Field(
        default="general",
        description="Detected subject area"
    )
    subtopic: str = Field(
        default="general",
        description="Specific subtopic within the subject"
    )
    key_elements: List[str] = Field(
        default_factory=list,
        description="Key elements identified in the analysis"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the analysis reasoning"
    )


class SnapAndExplainResponse(BaseModel):
    """Response model for snap-and-explain endpoint."""
    
    request_id: str = Field(
        ...,
        description="Unique identifier for this request"
    )
    original_image_url: str = Field(
        ...,
        description="URL or data URI of the original image"
    )
    generated_image_url: str = Field(
        ...,
        description="URL or data URI of the generated explanation image"
    )
    explanation: str = Field(
        ...,
        description="Verbal explanation of the generated diagram"
    )
    confusion_analysis: ConfusionAnalysis = Field(
        ...,
        description="Analysis of the student's confusion"
    )
    generation_time_ms: int = Field(
        ...,
        description="Total time taken for generation in milliseconds"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "original_image_url": "data:image/jpeg;base64,...",
                "generated_image_url": "https://cdn.example.com/generated/123.png",
                "explanation": "Look at the diagram I created. The red arrow shows the direction of force...",
                "confusion_analysis": {
                    "confusion_concept": "mechanical advantage in pulleys",
                    "difficulty_level": "intermediate",
                    "suggested_explanation_type": "schematic",
                    "subject": "physics",
                    "subtopic": "mechanics",
                    "key_elements": ["pulley", "force", "rope"],
                    "reasoning": "Student circled the pulley system"
                },
                "generation_time_ms": 4523
            }
        }


# ==================== Step-by-Step Models ====================

class ExplanationStep(BaseModel):
    """A single step in a step-by-step explanation."""
    
    step_number: int = Field(..., description="Step sequence number")
    title: str = Field(..., description="Short step title")
    explanation: str = Field(..., description="Detailed explanation text")
    visual_description: str = Field(
        default="",
        description="Description of visual that would help illustrate this step"
    )


class StepByStepResponse(BaseModel):
    """Response for step-by-step explanation endpoint."""
    
    request_id: str = Field(..., description="Unique request identifier")
    concept: str = Field(..., description="The concept being explained")
    subject: str = Field(..., description="Subject area")
    difficulty: str = Field(..., description="Difficulty level")
    steps: List[ExplanationStep] = Field(..., description="List of explanation steps")
    overview_image_url: str = Field(
        default="",
        description="URL to overview diagram"
    )
    total_steps: int = Field(..., description="Total number of steps")
    generation_time_ms: int = Field(..., description="Generation time in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "step-123",
                "concept": "photosynthesis",
                "subject": "biology",
                "difficulty": "intermediate",
                "steps": [
                    {
                        "step_number": 1,
                        "title": "Light Absorption",
                        "explanation": "Chlorophyll in plant leaves absorbs sunlight...",
                        "visual_description": "A chloroplast with light rays hitting it"
                    }
                ],
                "overview_image_url": "https://...",
                "total_steps": 5,
                "generation_time_ms": 3200
            }
        }


# ==================== Analogy Models ====================

class AnalogyMapping(BaseModel):
    """Mapping between analogy elements and concept elements."""
    
    analogy_element: str = Field(..., description="Element in the familiar analogy")
    concept_element: str = Field(..., description="Corresponding concept element")


class Analogy(BaseModel):
    """A single analogy for explaining a concept."""
    
    analogy: str = Field(..., description="The familiar scenario or object")
    mapping: dict = Field(..., description="Mapping of analogy to concept elements")
    explanation: str = Field(..., description="Why this analogy works")


class AnalogyResponse(BaseModel):
    """Response for analogy explanation endpoint."""
    
    request_id: str = Field(..., description="Unique request identifier")
    concept: str = Field(..., description="The concept being explained")
    subject: str = Field(..., description="Subject area")
    analogies: List[Analogy] = Field(..., description="Generated analogies")
    featured_analogy: Optional[Analogy] = Field(
        None,
        description="The best analogy to use"
    )
    analogy_image_url: str = Field(
        default="",
        description="URL to analogy visualization"
    )
    generation_time_ms: int = Field(..., description="Generation time in milliseconds")


# ==================== Feedback Models ====================

class FeedbackResponse(BaseModel):
    """Response for feedback submission."""
    
    status: str = Field(..., description="Submission status")
    message: str = Field(..., description="Response message")
    feedback_id: str = Field(..., description="Unique feedback identifier")


# ==================== Export Models ====================

class ExportResponse(BaseModel):
    """Response for export request."""
    
    status: str = Field(..., description="Export status (processing, ready, failed)")
    export_id: str = Field(..., description="Unique export identifier")
    format: str = Field(..., description="Export format")
    items_count: int = Field(..., description="Number of items being exported")
    download_url: Optional[str] = Field(None, description="URL to download when ready")
    message: str = Field(default="", description="Status message")


# ==================== Live Lens Models ====================

class LiveLensEvent(BaseModel):
    """Event from live lens WebSocket."""
    
    type: str = Field(
        ...,
        description="Event type (analysis, image_generated, explanation, error)"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp"
    )
    data: dict = Field(
        default_factory=dict,
        description="Event-specific data"
    )


class LiveLensAnalysisResponse(BaseModel):
    """Response for live lens frame analysis."""
    
    content_type: str = Field(
        default="unknown",
        description="Type of educational content detected"
    )
    visible_concepts: List[str] = Field(
        default_factory=list,
        description="Concepts visible in the frame"
    )
    potential_confusion: Optional[str] = Field(
        default=None,
        description="Detected confusion point, if any"
    )
    suggested_action: str = Field(
        default="wait",
        description="Recommended action (wait, explain, generate_diagram)"
    )


class LiveLensExplanationResponse(BaseModel):
    """Response when live lens generates an explanation."""
    
    session_id: str = Field(
        ...,
        description="Session identifier"
    )
    generated_image_url: str = Field(
        default="",
        description="URL of generated explanation image"
    )
    explanation: str = Field(
        default="",
        description="Verbal explanation"
    )
    concept: str = Field(
        default="",
        description="The concept being explained"
    )
    audio_url: Optional[str] = Field(
        default=None,
        description="URL for audio explanation (if available)"
    )


# ==================== Error & Status Models ====================

class ErrorResponse(BaseModel):
    """Standard error response."""
    
    error: str = Field(
        ...,
        description="Error type/code"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    details: Optional[dict] = Field(
        default=None,
        description="Additional error details"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for debugging"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "Image data is invalid or corrupted",
                "details": {"field": "image"},
                "request_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(
        default="healthy",
        description="Service status"
    )
    service: str = Field(
        default="visual-tutor-api",
        description="Service name"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    features: dict = Field(
        default_factory=dict,
        description="Available features"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Current timestamp"
    )


# ==================== Reference Data Models ====================

class SubtopicInfo(BaseModel):
    """Information about a subtopic."""
    
    id: str = Field(..., description="Subtopic identifier")
    name: str = Field(..., description="Display name")


class SubjectInfo(BaseModel):
    """Information about a supported subject."""
    
    id: str = Field(..., description="Subject identifier")
    name: str = Field(..., description="Display name")
    icon: str = Field(default="book", description="Icon name")
    subtopics: List[SubtopicInfo] = Field(
        default_factory=list, 
        description="Available subtopics"
    )


class StyleInfo(BaseModel):
    """Information about a diagram style."""
    
    id: str = Field(..., description="Style identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Style description")
    best_for: List[str] = Field(
        default_factory=list,
        description="Subjects this style works best for"
    )


class DifficultyInfo(BaseModel):
    """Information about a difficulty level."""
    
    id: str = Field(..., description="Difficulty identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description of this level")
    typical_grades: str = Field(
        default="",
        description="Typical grade levels"
    )


# ==================== Statistics Models ====================

class ServiceStats(BaseModel):
    """Statistics for a service."""
    
    request_count: int = Field(default=0, description="Total requests processed")
    average_time_ms: float = Field(default=0, description="Average processing time")
    client_active: bool = Field(default=False, description="Whether client is active")


class OrchestratorStats(BaseModel):
    """Statistics for the orchestrator."""
    
    total_workflows: int = Field(default=0, description="Total workflows executed")
    successful_workflows: int = Field(default=0, description="Successful workflows")
    failed_workflows: int = Field(default=0, description="Failed workflows")
    success_rate: float = Field(default=0, description="Success rate")
    active_workflows: int = Field(default=0, description="Currently active workflows")


class APIStatsResponse(BaseModel):
    """Response for API statistics endpoint."""
    
    orchestrator: dict = Field(..., description="Orchestrator statistics")
    gemini: dict = Field(..., description="Gemini service statistics")
    nanobananapro: dict = Field(..., description="Nano Banana Pro statistics")
    timestamp: float = Field(..., description="Stats timestamp")
