"""Request models for Visual Tutor API."""

from typing import Optional, Literal
from pydantic import BaseModel, Field, validator


class AnnotationData(BaseModel):
    """Data for a single annotation on an image."""
    
    type: Literal["circle", "arrow", "freehand", "text", "rectangle", "highlight"] = Field(
        ...,
        description="Type of annotation"
    )
    x: float = Field(
        ...,
        description="X coordinate (relative to image width, 0-1)",
        ge=0,
        le=1
    )
    y: float = Field(
        ...,
        description="Y coordinate (relative to image height, 0-1)",
        ge=0,
        le=1
    )
    color: str = Field(
        default="#FF0000",
        description="Annotation color in hex format"
    )
    
    # Type-specific fields
    radius: Optional[float] = Field(
        default=None,
        description="Radius for circle annotations (relative to image size)",
        ge=0,
        le=1
    )
    width: Optional[float] = Field(
        default=None,
        description="Width for rectangle annotations",
        ge=0,
        le=1
    )
    height: Optional[float] = Field(
        default=None,
        description="Height for rectangle annotations",
        ge=0,
        le=1
    )
    end_x: Optional[float] = Field(
        default=None,
        description="End X coordinate for arrows",
        ge=0,
        le=1
    )
    end_y: Optional[float] = Field(
        default=None,
        description="End Y coordinate for arrows",
        ge=0,
        le=1
    )
    text: Optional[str] = Field(
        default=None,
        description="Text content for text annotations",
        max_length=500
    )
    points: Optional[list[dict]] = Field(
        default=None,
        description="List of points for freehand annotations"
    )
    stroke_width: float = Field(
        default=2.0,
        description="Stroke width for drawing"
    )


class SnapAndExplainRequest(BaseModel):
    """Request model for snap-and-explain endpoint."""
    
    image: str = Field(
        ...,
        description="Base64-encoded image data"
    )
    annotations: Optional[list[AnnotationData]] = Field(
        default=None,
        description="List of annotations on the image"
    )
    question: Optional[str] = Field(
        default=None,
        description="Optional explicit question from the student",
        max_length=1000
    )
    subject: Optional[str] = Field(
        default=None,
        description="Optional subject area hint (math, physics, etc.)"
    )
    style_preference: Optional[Literal["schematic", "cartoon", "realistic", "minimalist", "gamified"]] = Field(
        default=None,
        description="Preferred visual style for generated explanation"
    )
    
    @validator("image")
    def validate_image(cls, v):
        """Validate that the image is not empty."""
        if not v or len(v) < 100:
            raise ValueError("Image data appears to be empty or invalid")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "image": "base64_encoded_image_data_here...",
                "annotations": [
                    {
                        "type": "circle",
                        "x": 0.5,
                        "y": 0.5,
                        "radius": 0.1,
                        "color": "#FF0000"
                    },
                    {
                        "type": "text",
                        "x": 0.6,
                        "y": 0.4,
                        "text": "?",
                        "color": "#0000FF"
                    }
                ],
                "question": "I don't understand how this pulley system works",
                "subject": "physics"
            }
        }


class LiveLensFrameRequest(BaseModel):
    """Request model for live lens frame processing."""
    
    frame: str = Field(
        ...,
        description="Base64-encoded video frame"
    )
    timestamp_ms: int = Field(
        ...,
        description="Frame timestamp in milliseconds"
    )
    session_id: str = Field(
        ...,
        description="Live lens session ID"
    )


class LiveLensAudioRequest(BaseModel):
    """Request model for live lens audio processing."""
    
    transcript: str = Field(
        ...,
        description="Transcribed audio text"
    )
    session_id: str = Field(
        ...,
        description="Live lens session ID"
    )
    include_frame: bool = Field(
        default=True,
        description="Whether to include current frame in analysis"
    )


class BatchExplainRequest(BaseModel):
    """Request model for batch explanation processing."""
    
    items: list[SnapAndExplainRequest] = Field(
        ...,
        description="List of images with annotations to process",
        min_length=1,
        max_length=10
    )
