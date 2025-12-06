"""
Gemini 3.0 Pro integration service for Visual Tutor App.

This module provides a robust interface to Google's Gemini API for
image analysis, prompt generation, and educational explanation generation.
"""

import logging
import base64
import json
import asyncio
from typing import Any, Optional, TypedDict, Literal
from dataclasses import dataclass
from enum import Enum
import httpx

from utils.prompt_engineering import (
    get_analysis_prompt,
    get_nanobananapro_prompt_template,
    get_explanation_prompt,
    get_concept_template,
)
from utils.exceptions import GeminiError, RateLimitError
from utils.cache import prompt_cache, explanation_cache


logger = logging.getLogger(__name__)


class DifficultyLevel(str, Enum):
    """Student difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class ExplanationType(str, Enum):
    """Types of visual explanations."""
    SCHEMATIC = "schematic"
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    MINIMALIST = "minimalist"
    GAMIFIED = "gamified"


class SubjectArea(str, Enum):
    """Supported subject areas."""
    MATH = "math"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    GENERAL = "general"


class ConfusionAnalysis(TypedDict):
    """Type definition for confusion analysis result."""
    confusion_concept: str
    difficulty_level: str
    suggested_explanation_type: str
    subject: str
    subtopic: str
    key_elements: list[str]
    reasoning: str


class VideoFrameAnalysis(TypedDict):
    """Type definition for video frame analysis result."""
    content_type: str
    visible_concepts: list[str]
    potential_confusion: Optional[str]
    suggested_action: Literal["wait", "explain", "generate_diagram"]


@dataclass
class GeminiConfig:
    """Configuration for Gemini service."""
    api_key: str
    timeout: float = 30.0
    max_retries: int = 3
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    model: str = "gemini-1.5-pro"
    temperature_analysis: float = 0.3
    temperature_generation: float = 0.7
    temperature_explanation: float = 0.5
    max_output_tokens_analysis: int = 1024
    max_output_tokens_generation: int = 1024
    max_output_tokens_explanation: int = 2048


class GeminiService:
    """
    Service for interacting with Gemini 3.0 Pro API.
    
    Provides methods for:
    - Analyzing annotated images to identify student confusion
    - Generating detailed prompts for image generation
    - Creating verbal explanations of generated diagrams
    - Analyzing video frames for live tutoring
    
    Features:
    - Automatic retry with exponential backoff
    - Response caching for identical requests
    - Comprehensive error handling with custom exceptions
    - Type-safe interfaces with dataclasses and TypedDicts
    """

    def __init__(self, api_key: str, config: Optional[GeminiConfig] = None):
        """
        Initialize the Gemini service.
        
        Args:
            api_key: Gemini API key
            config: Optional configuration object
        """
        self.config = config or GeminiConfig(api_key=api_key)
        if api_key:
            self.config.api_key = api_key
        
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._last_request_time = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with lazy initialization."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return self._client

    async def _make_request(
        self,
        request_body: dict[str, Any],
        operation: str = "request"
    ) -> dict[str, Any]:
        """
        Make a request to the Gemini API with retry logic.
        
        Args:
            request_body: The request payload
            operation: Description of the operation for logging
            
        Returns:
            API response as dictionary
            
        Raises:
            GeminiError: If the request fails after all retries
            RateLimitError: If rate limited and retries exhausted
        """
        client = await self._get_client()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await client.post(
                    f"{self.config.base_url}/models/{self.config.model}:generateContent",
                    params={"key": self.config.api_key},
                    json=request_body
                )
                
                if response.status_code == 429:
                    wait_time = (2 ** attempt) * 2
                    logger.warning(
                        f"Gemini rate limited during {operation}, "
                        f"waiting {wait_time}s (attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code == 400:
                    error_detail = response.json().get("error", {}).get("message", "Bad request")
                    raise GeminiError(f"Invalid request: {error_detail}")
                
                response.raise_for_status()
                self._request_count += 1
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"Gemini HTTP error during {operation}: {e.response.status_code} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except httpx.RequestError as e:
                last_error = e
                logger.warning(
                    f"Gemini request error during {operation}: {e} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise GeminiError(
            f"Failed to complete {operation} after {self.config.max_retries} attempts: {last_error}"
        )

    def _extract_text_content(self, response: dict[str, Any]) -> str:
        """Extract text content from Gemini API response."""
        try:
            return (
                response.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
        except (IndexError, KeyError, TypeError):
            return ""

    def _parse_json_response(
        self,
        text: str,
        defaults: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Parse JSON from response text with fallback to defaults.
        
        Args:
            text: Response text that may contain JSON
            defaults: Default values if parsing fails
            
        Returns:
            Parsed dictionary or defaults
        """
        # Try to extract JSON from markdown code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                text = text[start:end].strip()
        
        try:
            result = json.loads(text)
            # Merge with defaults to ensure all keys exist
            for key, value in defaults.items():
                result.setdefault(key, value)
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse Gemini response as JSON, using defaults")
            return defaults

    async def analyze_annotated_image(
        self,
        image: bytes,
        annotations: list[dict[str, Any]],
        student_question: Optional[str] = None
    ) -> ConfusionAnalysis:
        """
        Analyze an annotated image to identify student confusion.
        
        This method sends the image and annotations to Gemini for analysis,
        identifying what concept the student is struggling with and
        recommending an appropriate explanation approach.
        
        Args:
            image: Image bytes (JPEG or PNG)
            annotations: List of annotation dictionaries with type, position, etc.
            student_question: Optional explicit question from the student
            
        Returns:
            ConfusionAnalysis containing:
            - confusion_concept: The concept the student is confused about
            - difficulty_level: Estimated difficulty (beginner/intermediate/advanced)
            - suggested_explanation_type: Type of visual explanation recommended
            - subject: Detected subject area
            - subtopic: Specific subtopic within the subject
            - key_elements: List of key elements to explain
            - reasoning: Brief explanation of the analysis
            
        Raises:
            GeminiError: If the API call fails
        """
        logger.info(
            "Analyzing annotated image",
            extra={"annotation_count": len(annotations), "has_question": bool(student_question)}
        )
        
        # Build the analysis prompt
        prompt = get_analysis_prompt(annotations, student_question)
        
        # Encode image to base64
        image_b64 = base64.b64encode(image).decode("utf-8")
        
        # Detect image MIME type
        mime_type = "image/jpeg"
        if image[:8] == b'\x89PNG\r\n\x1a\n':
            mime_type = "image/png"
        elif image[:4] == b'GIF8':
            mime_type = "image/gif"
        elif image[:4] == b'RIFF' and image[8:12] == b'WEBP':
            mime_type = "image/webp"
        
        request_body = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64
                        }
                    },
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": self.config.temperature_analysis,
                "maxOutputTokens": self.config.max_output_tokens_analysis,
                "responseMimeType": "application/json"
            }
        }
        
        result = await self._make_request(request_body, "image analysis")
        text_content = self._extract_text_content(result)
        
        defaults: ConfusionAnalysis = {
            "confusion_concept": "unknown concept",
            "difficulty_level": "intermediate",
            "suggested_explanation_type": "schematic",
            "subject": "general",
            "subtopic": "general",
            "key_elements": [],
            "reasoning": "Unable to determine specific confusion point"
        }
        
        analysis = self._parse_json_response(text_content, defaults)
        
        logger.info(
            f"Image analysis complete",
            extra={
                "confusion_concept": analysis.get("confusion_concept"),
                "subject": analysis.get("subject"),
                "difficulty": analysis.get("difficulty_level")
            }
        )
        
        return analysis  # type: ignore

    async def generate_nanobananapro_prompt(
        self,
        analysis: ConfusionAnalysis,
        style: str = "educational",
        use_cache: bool = True
    ) -> str:
        """
        Generate a detailed prompt for Nano Banana Pro image generation.
        
        This method takes the confusion analysis and generates a comprehensive,
        spatially-precise prompt that will create an effective educational diagram.
        
        Args:
            analysis: Analysis result from analyze_annotated_image
            style: Visual style for the diagram
            use_cache: Whether to use cached prompts for identical requests
            
        Returns:
            Detailed prompt string optimized for Nano Banana Pro
            
        Raises:
            GeminiError: If prompt generation fails
        """
        concept = analysis.get("confusion_concept", "")
        logger.info(f"Generating Nano Banana Pro prompt for: {concept}")
        
        # Check cache
        if use_cache:
            cached = await prompt_cache.get_prompt(analysis)
            if cached:
                logger.info(f"Using cached prompt for: {concept}")
                return cached
        
        # Check for pre-made concept template
        concept_template = get_concept_template(concept)
        
        # Get the base template
        template = get_nanobananapro_prompt_template(
            concept=concept,
            subject=analysis.get("subject", "general"),
            style=style,
            difficulty=analysis.get("difficulty_level", "intermediate")
        )
        
        # Build enhancement prompt
        key_elements = analysis.get("key_elements", [])
        elements_text = f"\nKey elements to include: {', '.join(key_elements)}" if key_elements else ""
        
        enhancement_prompt = f"""
You are a visual education expert specializing in creating effective educational diagrams.
Your task is to enhance this image generation prompt to create the most effective educational diagram.

Base template:
{template}

{f"Reference template for this concept:{chr(10)}{concept_template}" if concept_template else ""}

Student Confusion Analysis:
- Concept: {analysis.get("confusion_concept")}
- Subject: {analysis.get("subject")}
- Difficulty level: {analysis.get("difficulty_level")}
- Reasoning: {analysis.get("reasoning", "")}
{elements_text}

Create a detailed, spatially-precise prompt for an AI image generator. Your enhanced prompt MUST include:

1. SPATIAL LAYOUT
   - Exact placement of elements using terms like "top-left quadrant", "center", "bottom-right corner"
   - Specify spacing and proportions (e.g., "occupying 40% of the image width")

2. TEXT LABELS
   - Specific text labels that MUST appear in the image
   - Font size relative descriptions (e.g., "large title", "small annotations")
   - Ensure all text is readable and well-positioned

3. COLOR CODING
   - Explicit color assignments for different elements
   - Reasoning for color choices (e.g., "use red for warning/important, blue for process flow")
   - Ensure high contrast for accessibility

4. VISUAL CONNECTIONS
   - Arrows with directions and meanings
   - Lines connecting related concepts
   - Flow indicators for processes

5. ANALOGIES (if applicable)
   - Familiar objects or scenarios that relate to the concept
   - Visual metaphors that aid understanding

Return ONLY the enhanced prompt text, nothing else. Make it comprehensive but focused.
"""
        
        request_body = {
            "contents": [{
                "parts": [{"text": enhancement_prompt}]
            }],
            "generationConfig": {
                "temperature": self.config.temperature_generation,
                "maxOutputTokens": self.config.max_output_tokens_generation
            }
        }
        
        try:
            result = await self._make_request(request_body, "prompt generation")
            enhanced_prompt = self._extract_text_content(result)
            
            if not enhanced_prompt.strip():
                logger.warning("Empty prompt generated, using template")
                enhanced_prompt = template
            
            # Cache the result
            if use_cache:
                await prompt_cache.store_prompt(analysis, enhanced_prompt.strip())
            
            logger.info("Enhanced prompt generated successfully")
            return enhanced_prompt.strip()
            
        except GeminiError:
            logger.warning("Failed to enhance prompt, using template")
            return template

    async def explain_generated_image(
        self,
        original_image: bytes,
        generated_image: bytes,
        analysis: ConfusionAnalysis
    ) -> str:
        """
        Generate a verbal explanation of the generated educational diagram.
        
        This creates a conversational explanation that references specific
        elements in the generated diagram, helping the student understand
        the visual content.
        
        Args:
            original_image: The student's original image
            generated_image: The AI-generated explanation image
            analysis: Analysis result from analyze_annotated_image
            
        Returns:
            Verbal explanation text suitable for text-to-speech
        """
        logger.info("Generating verbal explanation for generated image")
        
        prompt = get_explanation_prompt(analysis)
        
        # Encode both images
        original_b64 = base64.b64encode(original_image).decode("utf-8")
        generated_b64 = base64.b64encode(generated_image).decode("utf-8")
        
        request_body = {
            "contents": [{
                "parts": [
                    {"text": "Original image the student was studying:"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": original_b64
                        }
                    },
                    {"text": "\nGenerated explanation diagram:"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": generated_b64
                        }
                    },
                    {"text": f"\n{prompt}"}
                ]
            }],
            "generationConfig": {
                "temperature": self.config.temperature_explanation,
                "maxOutputTokens": self.config.max_output_tokens_explanation
            }
        }
        
        try:
            result = await self._make_request(request_body, "explanation generation")
            explanation = self._extract_text_content(result)
            
            logger.info("Verbal explanation generated successfully")
            return explanation.strip()
            
        except GeminiError as e:
            logger.error(f"Failed to generate explanation: {e}")
            concept = analysis.get('confusion_concept', 'this concept')
            return (
                f"I've created a diagram to help explain {concept}. "
                "Please examine the generated image for a visual breakdown of the key elements. "
                "The diagram highlights the important components and their relationships."
            )

    async def analyze_video_frame(
        self,
        frame: bytes,
        context: list[dict[str, Any]],
        transcript: Optional[str] = None
    ) -> VideoFrameAnalysis:
        """
        Analyze a video frame from live streaming.
        
        Used in Live Lens mode to continuously analyze what the student
        is looking at and detect when they might need help.
        
        Args:
            frame: Video frame bytes (JPEG)
            context: Recent conversation/analysis context
            transcript: Optional audio transcript from the student
            
        Returns:
            VideoFrameAnalysis containing content type, concepts, and suggested action
        """
        # Build context string from recent history
        context_text = ""
        if context:
            recent = context[-5:]  # Last 5 context items
            context_text = "\n".join([
                f"- {item.get('role', 'unknown')}: {item.get('content', '')[:100]}"
                for item in recent
            ])
        
        prompt = f"""
Analyze this video frame from a student's live learning session.

{f"Recent audio from student: {transcript}" if transcript else ""}

{f"Previous context:{chr(10)}{context_text}" if context_text else "No previous context available."}

Your task is to identify:
1. What type of educational content is visible (textbook page, whiteboard, worksheet, digital screen, etc.)
2. Specific concepts or topics being studied (list the main ones you can identify)
3. Any signs of confusion or areas that might need clarification
4. Whether the student might benefit from a visual explanation right now

Return a JSON object with:
{{
    "content_type": "type of content visible (textbook/whiteboard/worksheet/digital/other)",
    "visible_concepts": ["list", "of", "concepts", "seen"],
    "potential_confusion": "specific point that might be confusing, or null if none detected",
    "suggested_action": "wait|explain|generate_diagram"
}}

Guidelines for suggested_action:
- "wait": Content is clear or student appears to be working fine
- "explain": Offer a brief verbal explanation of what's visible
- "generate_diagram": Create a visual explanation for a complex concept
"""
        
        frame_b64 = base64.b64encode(frame).decode("utf-8")
        
        request_body = {
            "contents": [{
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": frame_b64
                        }
                    },
                    {"text": prompt}
                ]
            }],
            "generationConfig": {
                "temperature": self.config.temperature_analysis,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json"
            }
        }
        
        defaults: VideoFrameAnalysis = {
            "content_type": "unknown",
            "visible_concepts": [],
            "potential_confusion": None,
            "suggested_action": "wait"
        }
        
        try:
            result = await self._make_request(request_body, "video frame analysis")
            text_content = self._extract_text_content(result)
            return self._parse_json_response(text_content, defaults)  # type: ignore
            
        except GeminiError as e:
            logger.error(f"Video frame analysis failed: {e}")
            return defaults

    async def generate_step_by_step_explanation(
        self,
        concept: str,
        subject: str,
        difficulty: str = "intermediate",
        max_steps: int = 5
    ) -> list[dict[str, str]]:
        """
        Generate a step-by-step explanation for a concept.
        
        Creates a structured breakdown of a concept into digestible steps,
        each with its own explanation and visual description.
        
        Args:
            concept: The concept to explain
            subject: Subject area
            difficulty: Student difficulty level
            max_steps: Maximum number of steps to generate
            
        Returns:
            List of step dictionaries with 'title', 'explanation', and 'visual_description'
        """
        prompt = f"""
Create a step-by-step explanation for teaching: {concept}
Subject area: {subject}
Student level: {difficulty}

Break this down into {max_steps} or fewer clear, logical steps.

For each step, provide:
1. A short, clear title
2. A 2-3 sentence explanation appropriate for the difficulty level
3. A description of a visual that would help illustrate this step

Return as a JSON array:
[
    {{
        "step_number": 1,
        "title": "Step title",
        "explanation": "Clear explanation text",
        "visual_description": "Description of helpful visual"
    }},
    ...
]
"""
        
        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            result = await self._make_request(request_body, "step-by-step generation")
            text_content = self._extract_text_content(result)
            
            steps = json.loads(text_content)
            if isinstance(steps, list):
                return steps[:max_steps]
            return []
            
        except (GeminiError, json.JSONDecodeError) as e:
            logger.error(f"Failed to generate step-by-step explanation: {e}")
            return [{
                "step_number": 1,
                "title": f"Understanding {concept}",
                "explanation": f"Let's explore {concept} in {subject}.",
                "visual_description": f"A clear diagram showing the main elements of {concept}."
            }]

    async def generate_analogies(
        self,
        concept: str,
        subject: str,
        count: int = 3
    ) -> list[dict[str, Any]]:
        """
        Generate relatable analogies for a concept.
        
        Args:
            concept: The concept to create analogies for
            subject: Subject area
            count: Number of analogies to generate
            
        Returns:
            List of analogy dictionaries with 'analogy', 'mapping', and 'explanation'
        """
        prompt = f"""
Create {count} relatable analogies to help understand: {concept} (in {subject})

For each analogy, provide:
1. A familiar everyday scenario or object
2. A mapping showing how elements of the analogy relate to the concept
3. A brief explanation of why this analogy works

Return as a JSON array:
[
    {{
        "analogy": "Everyday scenario/object",
        "mapping": {{"analogy_element": "concept_element", ...}},
        "explanation": "Why this helps understand the concept"
    }},
    ...
]
"""
        
        request_body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 1024,
                "responseMimeType": "application/json"
            }
        }
        
        try:
            result = await self._make_request(request_body, "analogy generation")
            text_content = self._extract_text_content(result)
            
            analogies = json.loads(text_content)
            if isinstance(analogies, list):
                return analogies[:count]
            return []
            
        except (GeminiError, json.JSONDecodeError) as e:
            logger.error(f"Failed to generate analogies: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "request_count": self._request_count,
            "model": self.config.model,
            "client_active": self._client is not None and not self._client.is_closed
        }

    async def close(self):
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("Gemini service closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
