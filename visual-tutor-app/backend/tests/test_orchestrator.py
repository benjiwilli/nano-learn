"""Tests for Orchestrator service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import io
from PIL import Image

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.orchestrator import Orchestrator
from services.gemini_service import GeminiService
from services.nanobananapro_service import NanoBananaProService


@pytest.fixture
def mock_gemini_service():
    """Create a mock Gemini service."""
    service = MagicMock(spec=GeminiService)
    service.analyze_annotated_image = AsyncMock(return_value={
        "confusion_concept": "mechanical advantage",
        "difficulty_level": "intermediate",
        "suggested_explanation_type": "schematic",
        "subject": "physics",
        "subtopic": "mechanics"
    })
    service.generate_nanobananapro_prompt = AsyncMock(
        return_value="Create a diagram showing mechanical advantage..."
    )
    service.explain_generated_image = AsyncMock(
        return_value="Look at the red arrow in the diagram..."
    )
    service.analyze_video_frame = AsyncMock(return_value={
        "content_type": "textbook",
        "visible_concepts": ["pulleys"],
        "potential_confusion": "mechanical advantage",
        "suggested_action": "generate_diagram"
    })
    return service


@pytest.fixture
def mock_nano_service():
    """Create a mock Nano Banana Pro service."""
    # Create a sample image
    img = Image.new("RGB", (100, 100), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()
    
    service = MagicMock(spec=NanoBananaProService)
    service.generate_explanation_image = AsyncMock(return_value={
        "image_bytes": image_bytes,
        "image_url": "https://example.com/image.png",
        "prompt_used": "test prompt"
    })
    return service


@pytest.fixture
def orchestrator(mock_gemini_service, mock_nano_service):
    """Create an orchestrator instance."""
    return Orchestrator(
        gemini_service=mock_gemini_service,
        nano_service=mock_nano_service
    )


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes."""
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


class TestSnapAndExplainWorkflow:
    """Tests for snap-and-explain workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow_success(
        self, orchestrator, sample_image_bytes, mock_gemini_service, mock_nano_service
    ):
        """Test successful end-to-end workflow."""
        annotations = [
            {"type": "circle", "x": 0.5, "y": 0.5, "radius": 0.1}
        ]
        
        result = await orchestrator.snap_and_explain_workflow(
            image=sample_image_bytes,
            annotations=annotations,
            student_question="How does this work?"
        )
        
        # Verify all steps were called
        mock_gemini_service.analyze_annotated_image.assert_called_once()
        mock_gemini_service.generate_nanobananapro_prompt.assert_called_once()
        mock_nano_service.generate_explanation_image.assert_called_once()
        mock_gemini_service.explain_generated_image.assert_called_once()
        
        # Verify result structure
        assert "generated_image_url" in result
        assert "explanation" in result
        assert "confusion_analysis" in result
        assert result["explanation"] == "Look at the red arrow in the diagram..."

    @pytest.mark.asyncio
    async def test_workflow_without_annotations(
        self, orchestrator, sample_image_bytes
    ):
        """Test workflow without annotations."""
        result = await orchestrator.snap_and_explain_workflow(
            image=sample_image_bytes,
            annotations=[],
            student_question=None
        )
        
        assert "generated_image_url" in result
        assert "explanation" in result

    @pytest.mark.asyncio
    async def test_workflow_image_generation_failure(
        self, orchestrator, sample_image_bytes, mock_nano_service
    ):
        """Test workflow handles image generation failure gracefully."""
        mock_nano_service.generate_explanation_image.side_effect = RuntimeError("Generation failed")
        
        result = await orchestrator.snap_and_explain_workflow(
            image=sample_image_bytes,
            annotations=[],
            student_question="Help me understand this"
        )
        
        # Should fallback to text-only explanation
        assert result["generated_image_url"] == ""
        assert "explanation" in result
        assert len(result["explanation"]) > 0

    @pytest.mark.asyncio
    async def test_confusion_analysis_preserved(
        self, orchestrator, sample_image_bytes, mock_gemini_service
    ):
        """Test that confusion analysis is preserved in result."""
        result = await orchestrator.snap_and_explain_workflow(
            image=sample_image_bytes,
            annotations=[],
            student_question=None
        )
        
        assert result["confusion_analysis"]["confusion_concept"] == "mechanical advantage"
        assert result["confusion_analysis"]["subject"] == "physics"


class TestLiveLensWorkflow:
    """Tests for live lens workflow."""

    @pytest.mark.asyncio
    async def test_live_lens_triggers_generation(
        self, orchestrator, sample_image_bytes, mock_gemini_service
    ):
        """Test that live lens triggers image generation when confusion detected."""
        result = await orchestrator.live_lens_workflow(
            video_frame=sample_image_bytes,
            audio_transcript="I don't understand this",
            context=[]
        )
        
        assert result["generated_image_url"] == "https://example.com/image.png"
        assert result["concept"] == "mechanical advantage"
        assert len(result["explanation"]) > 0

    @pytest.mark.asyncio
    async def test_live_lens_no_generation_when_not_confused(
        self, orchestrator, sample_image_bytes, mock_gemini_service
    ):
        """Test that live lens doesn't generate when no confusion detected."""
        mock_gemini_service.analyze_video_frame.return_value = {
            "content_type": "textbook",
            "visible_concepts": ["algebra"],
            "potential_confusion": None,
            "suggested_action": "wait"
        }
        
        result = await orchestrator.live_lens_workflow(
            video_frame=sample_image_bytes,
            audio_transcript="Okay, I see",
            context=[]
        )
        
        # Should provide acknowledgment but not generate image
        assert "explanation" in result

    @pytest.mark.asyncio
    async def test_live_lens_with_context(
        self, orchestrator, sample_image_bytes
    ):
        """Test that live lens uses conversation context."""
        context = [
            {"role": "user", "content": "What is this?"},
            {"role": "assistant", "content": "This is a pulley system."}
        ]
        
        result = await orchestrator.live_lens_workflow(
            video_frame=sample_image_bytes,
            audio_transcript="Can you explain more?",
            context=context
        )
        
        assert "explanation" in result


class TestSubjectDetection:
    """Tests for subject detection helper."""

    def test_detect_physics_subject(self, orchestrator):
        """Test detection of physics concepts."""
        concepts = ["force", "motion", "velocity"]
        subject = orchestrator._detect_subject(concepts)
        assert subject == "physics"

    def test_detect_math_subject(self, orchestrator):
        """Test detection of math concepts."""
        concepts = ["equation", "graph", "function"]
        subject = orchestrator._detect_subject(concepts)
        assert subject == "math"

    def test_detect_chemistry_subject(self, orchestrator):
        """Test detection of chemistry concepts."""
        concepts = ["molecule", "reaction", "element"]
        subject = orchestrator._detect_subject(concepts)
        assert subject == "chemistry"

    def test_detect_unknown_subject(self, orchestrator):
        """Test handling of unknown concepts."""
        concepts = ["random", "words", "here"]
        subject = orchestrator._detect_subject(concepts)
        assert subject == "general"


class TestBatchExplain:
    """Tests for batch explanation processing."""

    @pytest.mark.asyncio
    async def test_batch_explain_multiple_images(
        self, orchestrator, sample_image_bytes
    ):
        """Test processing multiple images in batch."""
        images = [sample_image_bytes, sample_image_bytes]
        annotations = [
            [{"type": "circle", "x": 0.5, "y": 0.5}],
            [{"type": "text", "x": 0.3, "y": 0.3, "text": "?"}]
        ]
        
        results = await orchestrator.batch_explain(images, annotations)
        
        assert len(results) == 2
        assert all("explanation" in r for r in results)

    @pytest.mark.asyncio
    async def test_batch_explain_handles_partial_failure(
        self, orchestrator, sample_image_bytes, mock_gemini_service
    ):
        """Test that batch explain handles individual failures."""
        # Make second call fail
        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise ValueError("Analysis failed")
            return {
                "confusion_concept": "test",
                "difficulty_level": "intermediate",
                "suggested_explanation_type": "schematic",
                "subject": "physics",
                "subtopic": "test"
            }
        
        mock_gemini_service.analyze_annotated_image.side_effect = side_effect
        
        images = [sample_image_bytes, sample_image_bytes]
        annotations = [[], []]
        
        results = await orchestrator.batch_explain(images, annotations)
        
        assert len(results) == 2
        # First should succeed, second should have error
        assert "explanation" in results[0]
        assert "error" in results[1]
