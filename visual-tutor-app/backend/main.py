"""
FastAPI entry point for Visual Tutor App.

A comprehensive educational AI application that provides visual
explanations for student questions using Gemini and Nano Banana Pro.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from api.routes import router as api_router
from api.websocket import router as ws_router
from utils.logging_config import setup_logging
from utils.rate_limiter import RateLimitMiddleware, rate_limiter, cleanup_rate_limiters
from utils.exceptions import VisualTutorError


# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown tasks including background jobs.
    """
    logger.info("Starting Visual Tutor App...")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    
    # Start background cleanup task
    cleanup_task = asyncio.create_task(cleanup_rate_limiters())
    
    yield
    
    # Cleanup on shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    
    logger.info("Shutting down Visual Tutor App...")


# Create FastAPI application
app = FastAPI(
    title="Visual Tutor API",
    description="""
    AI-powered educational visual explanations using Gemini and Nano Banana Pro.
    
    ## Features
    
    - **Snap & Explain**: Upload an image with annotations, get a visual explanation
    - **Live Lens**: Real-time video analysis with on-demand diagram generation
    - **Step-by-Step**: Break down complex concepts into digestible steps
    - **Analogies**: Connect abstract concepts to familiar everyday experiences
    
    ## Rate Limits
    
    - Standard endpoints: 60 requests/minute
    - Generation endpoints: 12 requests/minute (5 tokens each)
    - Burst capacity: 10 requests
    
    ## Authentication
    
    API keys should be configured in the backend environment.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add rate limiting middleware
app.add_middleware(
    RateLimitMiddleware,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/"],
    cost_by_path={
        "/api/v1/snap-and-explain": 5,
        "/api/v1/snap-and-explain/upload": 5,
        "/api/v1/explain/step-by-step": 3,
        "/api/v1/explain/analogy": 3,
        "/api/v1/live-lens": 2,
    }
)


# Custom exception handler for VisualTutorError
@app.exception_handler(VisualTutorError)
async def visual_tutor_exception_handler(
    request: Request, 
    exc: VisualTutorError
) -> JSONResponse:
    """Handle Visual Tutor specific exceptions."""
    logger.error(
        f"VisualTutorError: {exc.message}",
        extra={
            "code": exc.code.value,
            "details": exc.details,
            "path": request.url.path
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request, 
    exc: Exception
) -> JSONResponse:
    """Handle all unhandled exceptions."""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"path": request.url.path},
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
            "detail": str(exc) if settings.debug else None
        },
    )


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns service status and basic system information.
    """
    return {
        "status": "healthy",
        "service": "visual-tutor-api",
        "version": "1.0.0",
        "features": {
            "snap_and_explain": True,
            "live_lens": True,
            "step_by_step": True,
            "analogies": True
        }
    }


# Rate limiter stats endpoint
@app.get("/health/rate-limiter", tags=["System"])
async def rate_limiter_health():
    """Get rate limiter statistics."""
    return rate_limiter.get_stats()


# Include routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """
    Root endpoint with API information.
    
    Provides quick links to documentation and key endpoints.
    """
    return {
        "name": "Visual Tutor API",
        "version": "1.0.0",
        "description": "AI-powered educational visual explanations",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        },
        "endpoints": {
            "health": "/health",
            "snap_and_explain": "/api/v1/snap-and-explain",
            "step_by_step": "/api/v1/explain/step-by-step",
            "analogy": "/api/v1/explain/analogy",
            "live_lens": "/api/v1/live-lens (WebSocket)",
            "subjects": "/api/v1/subjects",
            "styles": "/api/v1/styles"
        },
        "features": [
            "Image analysis with Gemini 3.0 Pro",
            "Visual explanation generation with Nano Banana Pro",
            "Real-time video analysis (Live Lens)",
            "Step-by-step concept breakdowns",
            "Analogy-based explanations",
            "Multiple diagram styles",
            "Difficulty level adaptation"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True,
    )
