"""
REST API routes for Visual Tutor App.

Provides endpoints for image analysis, explanation generation,
and various educational content services.
"""

import logging
import time
import uuid
from typing import Optional, List

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from models.request_models import SnapAndExplainRequest, AnnotationData
from models.response_models import (
    SnapAndExplainResponse, 
    ConfusionAnalysis,
    StepByStepResponse,
    FeedbackResponse,
    ExportResponse
)
from services.orchestrator import Orchestrator
from services.gemini_service import GeminiService
from services.nanobananapro_service import NanoBananaProService
from utils.image_processing import validate_image, decode_base64_image, encode_image_to_base64
from utils.exceptions import ValidationError, AnalysisError
from config import settings


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Visual Tutor"])


# ==================== Dependency Injection ====================

def get_gemini_service() -> GeminiService:
    """Dependency injection for Gemini service."""
    return GeminiService(api_key=settings.gemini_api_key)


def get_nano_service() -> NanoBananaProService:
    """Dependency injection for Nano Banana Pro service."""
    return NanoBananaProService(
        api_key=settings.genspark_api_key,
        base_url=settings.genspark_base_url
    )


def get_orchestrator(
    gemini: GeminiService = Depends(get_gemini_service),
    nano: NanoBananaProService = Depends(get_nano_service)
) -> Orchestrator:
    """Dependency injection for orchestrator service."""
    return Orchestrator(gemini_service=gemini, nano_service=nano)


# ==================== Request/Response Models ====================

class StepByStepRequest(BaseModel):
    """Request for step-by-step explanation."""
    concept: str = Field(..., min_length=2, max_length=200)
    subject: str = Field(default="general")
    difficulty: str = Field(default="intermediate")
    
    @validator('difficulty')
    def validate_difficulty(cls, v):
        if v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('difficulty must be beginner, intermediate, or advanced')
        return v


class AnalogyRequest(BaseModel):
    """Request for analogy-based explanation."""
    concept: str = Field(..., min_length=2, max_length=200)
    subject: str = Field(default="general")


class FeedbackRequest(BaseModel):
    """Request for submitting feedback on an explanation."""
    request_id: str = Field(..., min_length=1)
    rating: int = Field(..., ge=1, le=5)
    clarity_score: Optional[int] = Field(None, ge=1, le=5)
    helpfulness_score: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=1000)


class ExportRequest(BaseModel):
    """Request for exporting explanations."""
    request_ids: List[str] = Field(..., min_items=1, max_items=10)
    format: str = Field(default="pdf")
    include_originals: bool = Field(default=True)
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['pdf', 'zip', 'json']:
            raise ValueError('format must be pdf, zip, or json')
        return v


# ==================== Core Endpoints ====================

@router.post("/snap-and-explain", response_model=SnapAndExplainResponse)
async def snap_and_explain(
    request: SnapAndExplainRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> SnapAndExplainResponse:
    """
    Process an annotated image and generate a visual explanation.
    
    This endpoint:
    1. Receives a base64-encoded image with annotation metadata
    2. Uses Gemini 3.0 Pro to analyze the student's confusion
    3. Generates a Nano Banana Pro prompt for visual explanation
    4. Creates a high-fidelity educational diagram
    5. Returns both images with a verbal explanation
    
    Rate limit: 5 tokens per request
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Processing snap-and-explain request",
        extra={
            "request_id": request_id,
            "annotation_count": len(request.annotations) if request.annotations else 0
        }
    )
    
    try:
        # Validate and decode image
        image_bytes = decode_base64_image(request.image)
        if not validate_image(image_bytes, max_size_mb=settings.max_image_size_mb):
            raise HTTPException(status_code=400, detail="Invalid or oversized image")
        
        # Run the orchestrated workflow
        result = await orchestrator.snap_and_explain_workflow(
            image=image_bytes,
            annotations=[ann.model_dump() for ann in request.annotations] if request.annotations else [],
            student_question=request.question
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Snap-and-explain completed",
            extra={
                "request_id": request_id,
                "generation_time_ms": generation_time_ms
            }
        )
        
        return SnapAndExplainResponse(
            request_id=request_id,
            original_image_url=f"data:image/jpeg;base64,{encode_image_to_base64(image_bytes)}",
            generated_image_url=result.get("generated_image_url", ""),
            explanation=result.get("explanation", ""),
            confusion_analysis=ConfusionAnalysis(**result.get("confusion_analysis", {})),
            generation_time_ms=generation_time_ms
        )
        
    except ValueError as e:
        logger.error(f"Validation error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=400, detail=str(e))
    except AnalysisError as e:
        logger.error(f"Analysis error: {e}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e.message))
    except Exception as e:
        logger.error(f"Processing error: {e}", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process image")


@router.post("/snap-and-explain/upload")
async def snap_and_explain_upload(
    image: UploadFile = File(...),
    annotations: Optional[str] = Form(None),
    question: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> SnapAndExplainResponse:
    """
    Alternative endpoint accepting file upload instead of base64.
    
    Useful for direct file uploads from mobile devices.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Processing file upload request",
        extra={
            "request_id": request_id,
            "filename": image.filename,
            "content_type": image.content_type
        }
    )
    
    try:
        # Read image bytes
        image_bytes = await image.read()
        
        if not validate_image(image_bytes, max_size_mb=settings.max_image_size_mb):
            raise HTTPException(status_code=400, detail="Invalid or oversized image")
        
        # Parse annotations if provided
        import json
        parsed_annotations = []
        if annotations:
            try:
                parsed_annotations = json.loads(annotations)
            except json.JSONDecodeError:
                logger.warning("Failed to parse annotations JSON")
        
        # Run the orchestrated workflow
        result = await orchestrator.snap_and_explain_workflow(
            image=image_bytes,
            annotations=parsed_annotations,
            student_question=question,
            preferred_style=style
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return SnapAndExplainResponse(
            request_id=request_id,
            original_image_url=f"data:image/jpeg;base64,{encode_image_to_base64(image_bytes)}",
            generated_image_url=result.get("generated_image_url", ""),
            explanation=result.get("explanation", ""),
            confusion_analysis=ConfusionAnalysis(**result.get("confusion_analysis", {})),
            generation_time_ms=generation_time_ms
        )
        
    except Exception as e:
        logger.error(f"Upload processing error: {e}", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process uploaded image")


# ==================== Step-by-Step Explanation ====================

@router.post("/explain/step-by-step")
async def explain_step_by_step(
    request: StepByStepRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> dict:
    """
    Generate a step-by-step explanation with visuals.
    
    Creates a structured breakdown of a concept into digestible steps,
    each with its own explanation and optional visual.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Processing step-by-step request",
        extra={
            "request_id": request_id,
            "concept": request.concept,
            "subject": request.subject
        }
    )
    
    try:
        result = await orchestrator.generate_step_by_step(
            concept=request.concept,
            subject=request.subject,
            difficulty=request.difficulty
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "request_id": request_id,
            "concept": result["concept"],
            "subject": result["subject"],
            "difficulty": result["difficulty"],
            "steps": result["steps"],
            "overview_image_url": result.get("overview_image_url", ""),
            "total_steps": result["total_steps"],
            "generation_time_ms": generation_time_ms
        }
        
    except Exception as e:
        logger.error(f"Step-by-step error: {e}", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate step-by-step explanation")


@router.post("/explain/analogy")
async def explain_with_analogy(
    request: AnalogyRequest,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> dict:
    """
    Generate an explanation using relatable analogies.
    
    Creates analogies that connect abstract concepts to familiar
    everyday experiences, with visual representations.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(
        f"Processing analogy request",
        extra={
            "request_id": request_id,
            "concept": request.concept,
            "subject": request.subject
        }
    )
    
    try:
        result = await orchestrator.generate_with_analogy(
            concept=request.concept,
            subject=request.subject
        )
        
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "request_id": request_id,
            "concept": result["concept"],
            "subject": result["subject"],
            "analogies": result["analogies"],
            "featured_analogy": result.get("featured_analogy"),
            "analogy_image_url": result.get("analogy_image_url", ""),
            "generation_time_ms": generation_time_ms
        }
        
    except Exception as e:
        logger.error(f"Analogy error: {e}", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate analogy explanation")


# ==================== Feedback System ====================

@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest) -> dict:
    """
    Submit feedback for an explanation.
    
    Collects user ratings and comments to improve the system.
    """
    # In production, this would store feedback in a database
    logger.info(
        f"Feedback received",
        extra={
            "request_id": request.request_id,
            "rating": request.rating,
            "clarity": request.clarity_score,
            "helpfulness": request.helpfulness_score
        }
    )
    
    return {
        "status": "success",
        "message": "Thank you for your feedback!",
        "feedback_id": str(uuid.uuid4())
    }


# ==================== Export ====================

@router.post("/export")
async def export_explanations(request: ExportRequest) -> dict:
    """
    Export explanations as PDF, ZIP, or JSON.
    
    Bundles explanation content including images and text
    for offline use or sharing.
    """
    # In production, this would generate actual exports
    logger.info(
        f"Export requested",
        extra={
            "request_ids": request.request_ids,
            "format": request.format
        }
    )
    
    return {
        "status": "processing",
        "export_id": str(uuid.uuid4()),
        "format": request.format,
        "items_count": len(request.request_ids),
        "message": f"Export will be ready shortly. Check back in a few seconds."
    }


# ==================== Reference Data ====================

@router.get("/subjects")
async def get_supported_subjects():
    """Get list of supported educational subjects with subtopics."""
    return {
        "subjects": [
            {
                "id": "math", 
                "name": "Mathematics", 
                "icon": "calculator",
                "subtopics": [
                    {"id": "algebra", "name": "Algebra"},
                    {"id": "geometry", "name": "Geometry"},
                    {"id": "calculus", "name": "Calculus"},
                    {"id": "statistics", "name": "Statistics"},
                    {"id": "trigonometry", "name": "Trigonometry"}
                ]
            },
            {
                "id": "physics", 
                "name": "Physics", 
                "icon": "atom",
                "subtopics": [
                    {"id": "mechanics", "name": "Mechanics"},
                    {"id": "electromagnetism", "name": "Electromagnetism"},
                    {"id": "thermodynamics", "name": "Thermodynamics"},
                    {"id": "optics", "name": "Optics"},
                    {"id": "waves", "name": "Waves & Sound"}
                ]
            },
            {
                "id": "chemistry", 
                "name": "Chemistry", 
                "icon": "flask",
                "subtopics": [
                    {"id": "organic", "name": "Organic Chemistry"},
                    {"id": "inorganic", "name": "Inorganic Chemistry"},
                    {"id": "physical", "name": "Physical Chemistry"},
                    {"id": "biochemistry", "name": "Biochemistry"},
                    {"id": "analytical", "name": "Analytical Chemistry"}
                ]
            },
            {
                "id": "biology", 
                "name": "Biology", 
                "icon": "leaf",
                "subtopics": [
                    {"id": "cell_biology", "name": "Cell Biology"},
                    {"id": "genetics", "name": "Genetics"},
                    {"id": "ecology", "name": "Ecology"},
                    {"id": "anatomy", "name": "Anatomy"},
                    {"id": "evolution", "name": "Evolution"}
                ]
            },
            {
                "id": "history", 
                "name": "History", 
                "icon": "book-open",
                "subtopics": [
                    {"id": "ancient", "name": "Ancient History"},
                    {"id": "medieval", "name": "Medieval History"},
                    {"id": "modern", "name": "Modern History"},
                    {"id": "world_wars", "name": "World Wars"},
                    {"id": "civilizations", "name": "Civilizations"}
                ]
            },
            {
                "id": "geography", 
                "name": "Geography", 
                "icon": "globe",
                "subtopics": [
                    {"id": "physical", "name": "Physical Geography"},
                    {"id": "human", "name": "Human Geography"},
                    {"id": "cartography", "name": "Cartography"},
                    {"id": "climate", "name": "Climate Science"},
                    {"id": "geopolitics", "name": "Geopolitics"}
                ]
            },
            {
                "id": "computer_science",
                "name": "Computer Science",
                "icon": "code",
                "subtopics": [
                    {"id": "algorithms", "name": "Algorithms"},
                    {"id": "data_structures", "name": "Data Structures"},
                    {"id": "programming", "name": "Programming"},
                    {"id": "databases", "name": "Databases"},
                    {"id": "networking", "name": "Networking"}
                ]
            }
        ]
    }


@router.get("/styles")
async def get_diagram_styles():
    """Get available diagram styles for generation."""
    return {
        "styles": [
            {
                "id": "schematic", 
                "name": "Schematic", 
                "description": "Technical diagrams with precise layouts and professional appearance",
                "best_for": ["math", "physics", "engineering"]
            },
            {
                "id": "cartoon", 
                "name": "Cartoon", 
                "description": "Fun, engaging illustrations perfect for younger students",
                "best_for": ["biology", "history", "general"]
            },
            {
                "id": "realistic", 
                "name": "Realistic", 
                "description": "Photo-realistic representations with accurate details",
                "best_for": ["biology", "geography", "chemistry"]
            },
            {
                "id": "minimalist", 
                "name": "Minimalist", 
                "description": "Clean, simple diagrams focusing on essential elements",
                "best_for": ["math", "computer_science"]
            },
            {
                "id": "gamified", 
                "name": "Gamified", 
                "description": "Game-like visuals using familiar gaming elements",
                "best_for": ["all subjects", "younger students"]
            },
            {
                "id": "infographic",
                "name": "Infographic",
                "description": "Modern infographic style with data visualization",
                "best_for": ["statistics", "geography", "history"]
            },
            {
                "id": "comparison",
                "name": "Comparison",
                "description": "Side-by-side comparison layouts",
                "best_for": ["before/after", "concepts vs misconceptions"]
            }
        ]
    }


@router.get("/difficulties")
async def get_difficulty_levels():
    """Get available difficulty levels with descriptions."""
    return {
        "levels": [
            {
                "id": "beginner",
                "name": "Beginner",
                "description": "Simple terminology, lots of visuals, everyday examples",
                "typical_grades": "K-5"
            },
            {
                "id": "intermediate",
                "name": "Intermediate",
                "description": "Standard terminology, balanced visuals and text",
                "typical_grades": "6-10"
            },
            {
                "id": "advanced",
                "name": "Advanced",
                "description": "Technical language, complex relationships, detailed analysis",
                "typical_grades": "11-College"
            }
        ]
    }


# ==================== Health & Stats ====================

@router.get("/stats")
async def get_api_stats(
    orchestrator: Orchestrator = Depends(get_orchestrator)
):
    """Get API statistics and service health."""
    return {
        "orchestrator": orchestrator.get_stats(),
        "gemini": orchestrator.gemini.get_stats(),
        "nanobananapro": orchestrator.nano.get_stats(),
        "timestamp": time.time()
    }
