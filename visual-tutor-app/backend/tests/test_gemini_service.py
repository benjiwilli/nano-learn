"""Tests for Gemini service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.gemini_service import GeminiService


@pytest.fixture
def gemini_service():
    """Create a Gemini service instance for testing."""
    return GeminiService(api_key="test_api_key")


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes for testing."""
    # Create a minimal valid JPEG
    import io
    from PIL import Image
    
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def sample_annotations():
    """Create sample annotations for testing."""
    return [
        {"type": "circle", "x": 0.5, "y": 0.5, "radius": 0.1, "color": "#FF0000"},
        {"type": "text", "x": 0.6, "y": 0.4, "text": "?", "color": "#0000FF"},
    ]


class TestGeminiService:
    """Tests for GeminiService class."""

    @pytest.mark.asyncio
    async def test_analyze_annotated_image_success(
        self, gemini_service, sample_image_bytes, sample_annotations
    ):
        """Test successful image analysis."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "confusion_concept": "mechanical advantage",
                            "difficulty_level": "intermediate",
                            "suggested_explanation_type": "schematic",
                            "subject": "physics",
                            "subtopic": "mechanics"
                        })
                    }]
                }
            }]
        }
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
        ):
            result = await gemini_service.analyze_annotated_image(
                image=sample_image_bytes,
                annotations=sample_annotations,
                student_question="How does this work?"
            )
            
            assert result["confusion_concept"] == "mechanical advantage"
            assert result["difficulty_level"] == "intermediate"
            assert result["subject"] == "physics"

    @pytest.mark.asyncio
    async def test_analyze_annotated_image_handles_invalid_json(
        self, gemini_service, sample_image_bytes
    ):
        """Test handling of invalid JSON response."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "This is not valid JSON"
                    }]
                }
            }]
        }
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
        ):
            result = await gemini_service.analyze_annotated_image(
                image=sample_image_bytes,
                annotations=[]
            )
            
            # Should return defaults
            assert "confusion_concept" in result
            assert "difficulty_level" in result

    @pytest.mark.asyncio
    async def test_generate_nanobananapro_prompt(self, gemini_service):
        """Test prompt generation for Nano Banana Pro."""
        analysis = {
            "confusion_concept": "quadratic formula",
            "subject": "math",
            "difficulty_level": "intermediate",
            "suggested_explanation_type": "schematic"
        }
        
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "Create a detailed diagram showing the quadratic formula..."
                    }]
                }
            }]
        }
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
        ):
            result = await gemini_service.generate_nanobananapro_prompt(
                analysis=analysis,
                style="educational"
            )
            
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_explain_generated_image(
        self, gemini_service, sample_image_bytes
    ):
        """Test explanation generation for generated image."""
        analysis = {
            "confusion_concept": "test concept",
            "subject": "physics",
            "difficulty_level": "intermediate"
        }
        
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": "Look at the diagram I created for you..."
                    }]
                }
            }]
        }
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
        ):
            result = await gemini_service.explain_generated_image(
                original_image=sample_image_bytes,
                generated_image=sample_image_bytes,
                analysis=analysis
            )
            
            assert isinstance(result, str)
            assert "diagram" in result.lower()

    @pytest.mark.asyncio
    async def test_api_error_handling(self, gemini_service, sample_image_bytes):
        """Test handling of API errors."""
        import httpx
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPError("API Error")
        ):
            with pytest.raises(RuntimeError, match="Failed to analyze image"):
                await gemini_service.analyze_annotated_image(
                    image=sample_image_bytes,
                    annotations=[]
                )


class TestVideoFrameAnalysis:
    """Tests for video frame analysis."""

    @pytest.mark.asyncio
    async def test_analyze_video_frame_success(
        self, gemini_service, sample_image_bytes
    ):
        """Test successful video frame analysis."""
        mock_response = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": json.dumps({
                            "content_type": "textbook",
                            "visible_concepts": ["algebra", "equations"],
                            "potential_confusion": "solving for x",
                            "suggested_action": "generate_diagram"
                        })
                    }]
                }
            }]
        }
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            return_value=MagicMock(
                status_code=200,
                json=lambda: mock_response,
                raise_for_status=lambda: None
            )
        ):
            result = await gemini_service.analyze_video_frame(
                frame=sample_image_bytes,
                context=[],
                transcript="What is this?"
            )
            
            assert result["content_type"] == "textbook"
            assert "algebra" in result["visible_concepts"]

    @pytest.mark.asyncio
    async def test_analyze_video_frame_error_returns_defaults(
        self, gemini_service, sample_image_bytes
    ):
        """Test that errors return default values."""
        import httpx
        
        with patch.object(
            gemini_service._client, "post",
            new_callable=AsyncMock,
            side_effect=httpx.HTTPError("API Error")
        ):
            result = await gemini_service.analyze_video_frame(
                frame=sample_image_bytes,
                context=[],
                transcript=None
            )
            
            assert result["content_type"] == "unknown"
            assert result["suggested_action"] == "wait"
