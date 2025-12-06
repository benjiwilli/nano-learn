"""
Nano Banana Pro image generation service for Visual Tutor App.

This module provides comprehensive image generation capabilities using
the Nano Banana Pro model, specifically optimized for educational diagrams.
"""

import logging
import base64
import asyncio
import hashlib
from typing import Optional, Any, TypedDict, Literal
from dataclasses import dataclass, field
from datetime import datetime
import httpx

from utils.exceptions import NanoBananaProError, RateLimitError
from utils.cache import explanation_cache


logger = logging.getLogger(__name__)


class GenerationResult(TypedDict):
    """Type definition for image generation result."""
    image_bytes: bytes
    image_url: str
    prompt_used: str
    generation_time_ms: int
    style: str


class StyleConfig(TypedDict):
    """Configuration for a visual style."""
    modifier: str
    aspect_ratio: str
    color_scheme: str


@dataclass
class NanoBananaProConfig:
    """Configuration for Nano Banana Pro service."""
    api_key: str
    base_url: str = "https://api.genspark.ai/v1"
    timeout: float = 120.0  # Extended timeout for image generation
    max_retries: int = 3
    default_aspect_ratio: str = "1:1"
    max_reference_images: int = 4
    rate_limit_delay: float = 2.0
    enable_prompt_enhancement: bool = True


STYLE_CONFIGS: dict[str, StyleConfig] = {
    "educational": {
        "modifier": "Clear educational diagram with labeled components, clean layout, "
                   "easy-to-read text, professional appearance, high contrast for readability.",
        "aspect_ratio": "1:1",
        "color_scheme": "professional academic colors with high contrast"
    },
    "schematic": {
        "modifier": "Technical schematic diagram with precise geometric lines, clear labels, "
                   "professional blueprint-like appearance, grid structure.",
        "aspect_ratio": "16:9",
        "color_scheme": "technical blue and gray palette"
    },
    "cartoon": {
        "modifier": "Friendly cartoon-style educational illustration with engaging characters, "
                   "colorful elements, rounded shapes, approachable aesthetic.",
        "aspect_ratio": "4:3",
        "color_scheme": "bright, engaging primary colors"
    },
    "realistic": {
        "modifier": "Realistic educational illustration with accurate proportions, detailed "
                   "representations, naturalistic colors, textbook quality.",
        "aspect_ratio": "16:9",
        "color_scheme": "naturalistic, realistic colors"
    },
    "minimalist": {
        "modifier": "Clean minimalist diagram with essential elements only, plenty of whitespace, "
                   "simple shapes, limited color palette, maximum clarity.",
        "aspect_ratio": "1:1",
        "color_scheme": "limited palette: black, white, one accent color"
    },
    "gamified": {
        "modifier": "Game-inspired educational visual with familiar gaming elements, achievement "
                   "indicators, bright colors, interactive-looking components.",
        "aspect_ratio": "16:9",
        "color_scheme": "vibrant gaming colors with progress indicators"
    },
    "infographic": {
        "modifier": "Modern infographic style with data visualization elements, icons, "
                   "clear information hierarchy, engaging layout.",
        "aspect_ratio": "9:16",
        "color_scheme": "modern infographic palette with accent colors"
    },
    "comparison": {
        "modifier": "Side-by-side comparison layout with clear differentiation, "
                   "labels for each side, visual balance.",
        "aspect_ratio": "16:9",
        "color_scheme": "contrasting colors for comparison (red/blue, green/red)"
    }
}


class NanoBananaProService:
    """
    Service for generating educational images using Nano Banana Pro.
    
    Features:
    - Multiple style presets optimized for education
    - Automatic prompt enhancement for educational clarity
    - Reference image support for context-aware generation
    - Built-in retry logic with exponential backoff
    - Specialized methods for different diagram types
    - Comprehensive error handling
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.genspark.ai/v1",
        config: Optional[NanoBananaProConfig] = None
    ):
        """
        Initialize the Nano Banana Pro service.
        
        Args:
            api_key: GenSpark API key
            base_url: Base URL for the API
            config: Optional configuration object
        """
        self.config = config or NanoBananaProConfig(api_key=api_key, base_url=base_url)
        if api_key:
            self.config.api_key = api_key
        if base_url:
            self.config.base_url = base_url
        
        self._client: Optional[httpx.AsyncClient] = None
        self._request_count = 0
        self._total_generation_time_ms = 0

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with lazy initialization."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.config.timeout,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json"
                },
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2)
            )
        return self._client

    def _enhance_prompt_for_education(
        self,
        prompt: str,
        style: str,
        additional_requirements: Optional[list[str]] = None
    ) -> str:
        """
        Enhance the prompt to ensure educational clarity.
        
        Args:
            prompt: Original prompt
            style: Visual style
            additional_requirements: Extra requirements to add
            
        Returns:
            Enhanced prompt optimized for educational content
        """
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["educational"])
        modifier = style_config["modifier"]
        color_scheme = style_config["color_scheme"]
        
        # Build requirements list
        requirements = [
            "All text labels must be clearly readable and properly positioned",
            "Use consistent color coding throughout the diagram",
            "Include arrows or lines to show relationships between elements",
            "Ensure high contrast for accessibility",
            "Keep the layout clean and organized",
            "Avoid cluttered or overlapping elements"
        ]
        
        if additional_requirements:
            requirements.extend(additional_requirements)
        
        requirements_text = "\n".join(f"- {req}" for req in requirements)
        
        enhanced = f"""
{modifier}

Color scheme: {color_scheme}

{prompt}

IMPORTANT REQUIREMENTS:
{requirements_text}
"""
        
        return enhanced.strip()

    def _generate_cache_key(self, prompt: str, style: str, aspect_ratio: str) -> str:
        """Generate a cache key for a generation request."""
        key_data = f"{prompt}:{style}:{aspect_ratio}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    async def generate_explanation_image(
        self,
        prompt: str,
        style: str = "educational",
        aspect_ratio: Optional[str] = None,
        reference_images: Optional[list[bytes]] = None,
        enhance_prompt: bool = True,
        additional_requirements: Optional[list[str]] = None
    ) -> GenerationResult:
        """
        Generate an educational diagram using Nano Banana Pro.
        
        Args:
            prompt: Detailed prompt for image generation
            style: Visual style (educational, schematic, cartoon, etc.)
            aspect_ratio: Image aspect ratio (defaults based on style)
            reference_images: Optional reference images for context
            enhance_prompt: Whether to apply automatic prompt enhancement
            additional_requirements: Extra requirements to add to the prompt
            
        Returns:
            GenerationResult containing image bytes, URL, and metadata
            
        Raises:
            NanoBananaProError: If generation fails after all retries
        """
        import time
        start_time = time.time()
        
        logger.info(
            f"Generating educational image",
            extra={"style": style, "has_references": bool(reference_images)}
        )
        
        # Get style-specific configuration
        style_config = STYLE_CONFIGS.get(style, STYLE_CONFIGS["educational"])
        final_aspect_ratio = aspect_ratio or style_config.get("aspect_ratio", "1:1")
        
        # Enhance prompt if enabled
        if enhance_prompt and self.config.enable_prompt_enhancement:
            enhanced_prompt = self._enhance_prompt_for_education(
                prompt, style, additional_requirements
            )
        else:
            enhanced_prompt = prompt
        
        # Prepare request body
        request_body: dict[str, Any] = {
            "model": "nano-banana-pro",
            "prompt": enhanced_prompt,
            "aspect_ratio": final_aspect_ratio,
            "image_size": "auto"
        }
        
        # Add reference images if provided
        if reference_images:
            image_urls = []
            for img_bytes in reference_images[:self.config.max_reference_images]:
                img_b64 = base64.b64encode(img_bytes).decode("utf-8")
                image_urls.append(f"data:image/jpeg;base64,{img_b64}")
            request_body["image_urls"] = image_urls
        
        # Execute with retry logic
        client = await self._get_client()
        last_error: Optional[Exception] = None
        
        for attempt in range(self.config.max_retries):
            try:
                response = await client.post(
                    f"{self.config.base_url}/images/generations",
                    json=request_body
                )
                
                if response.status_code == 429:
                    wait_time = self.config.rate_limit_delay * (2 ** attempt)
                    logger.warning(
                        f"Rate limited, waiting {wait_time}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                
                if response.status_code == 400:
                    error_detail = response.json().get("error", {}).get("message", "Bad request")
                    raise NanoBananaProError(f"Invalid request: {error_detail}")
                
                response.raise_for_status()
                result = response.json()
                
                # Extract image URL from response
                image_url = ""
                if "data" in result and len(result["data"]) > 0:
                    image_url = result["data"][0].get("url", "")
                elif "url" in result:
                    image_url = result["url"]
                
                # Download the image if URL provided
                image_bytes = b""
                if image_url and not image_url.startswith("data:"):
                    try:
                        img_response = await client.get(image_url)
                        img_response.raise_for_status()
                        image_bytes = img_response.content
                    except Exception as e:
                        logger.warning(f"Failed to download generated image: {e}")
                
                generation_time_ms = int((time.time() - start_time) * 1000)
                self._request_count += 1
                self._total_generation_time_ms += generation_time_ms
                
                logger.info(
                    f"Image generation completed",
                    extra={
                        "generation_time_ms": generation_time_ms,
                        "has_image_bytes": bool(image_bytes),
                        "style": style
                    }
                )
                
                return GenerationResult(
                    image_bytes=image_bytes,
                    image_url=image_url,
                    prompt_used=enhanced_prompt,
                    generation_time_ms=generation_time_ms,
                    style=style
                )
                
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(
                    f"Generation attempt {attempt + 1} failed: {e.response.status_code}"
                )
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    
            except httpx.RequestError as e:
                last_error = e
                logger.warning(f"Generation request error: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        raise NanoBananaProError(
            f"Image generation failed after {self.config.max_retries} attempts: {last_error}"
        )

    async def generate_comparison_image(
        self,
        concept: str,
        before_description: str,
        after_description: str,
        style: str = "comparison"
    ) -> GenerationResult:
        """
        Generate a before/after comparison image.
        
        Ideal for showing transformations, misconceptions vs correct understanding,
        or process changes.
        
        Args:
            concept: The concept being explained
            before_description: Description of the "before" state
            after_description: Description of the "after" state
            style: Visual style (defaults to comparison)
            
        Returns:
            Generated image result
        """
        prompt = f"""
Create a side-by-side comparison educational diagram for: "{concept}"

LEFT SIDE (Before/Confusing/Wrong):
{before_description}
- Label this side clearly as "BEFORE" or "Misconception"
- Use muted, cooler colors (grays, muted reds)
- Show crossed-out or unclear elements where appropriate

RIGHT SIDE (After/Clear/Correct):
{after_description}
- Label this side clearly as "AFTER" or "Correct Understanding"
- Use bright, warm colors (greens, bright blues)
- Show checkmarks or highlighted correct elements

LAYOUT:
- Clear vertical dividing line between the two sides
- Matching elements should be at the same vertical position
- Large arrow pointing from left to right labeled "Understanding" or "Learning"
- Title at top: "Understanding {concept}"

Ensure the visual contrast clearly shows the improvement/clarification.
"""
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio="16:9",
            additional_requirements=[
                "Maintain clear visual separation between left and right sides",
                "Use consistent element positioning across both sides",
                "Make the transformation/improvement obvious at a glance"
            ]
        )

    async def generate_step_by_step_image(
        self,
        concept: str,
        steps: list[str],
        style: str = "educational"
    ) -> GenerationResult:
        """
        Generate a step-by-step process diagram.
        
        Creates a visual showing a sequential process or procedure.
        
        Args:
            concept: The concept being explained
            steps: List of step descriptions
            style: Visual style
            
        Returns:
            Generated image result
        """
        steps_text = "\n".join([
            f"Step {i+1}: {step}" 
            for i, step in enumerate(steps[:8])  # Limit to 8 steps
        ])
        
        layout = "horizontal flow" if len(steps) <= 4 else "vertical flow or grid"
        
        prompt = f"""
Create a step-by-step educational diagram for: "{concept}"

STEPS TO SHOW:
{steps_text}

LAYOUT REQUIREMENTS:
- Arrange steps in a clear {layout}
- Number each step prominently (1, 2, 3, ...)
- Use arrows to show progression between steps
- Each step should have:
  * A number indicator
  * A brief text label
  * A small illustrative icon or mini-diagram
- Use consistent colors for each step
- Include a title at the top: "How to {concept}" or "{concept} Process"

VISUAL DESIGN:
- Steps should be visually distinct but connected
- Use a color gradient or progression to show flow
- Ensure all text is readable
- Add small visual aids for each step where appropriate
"""
        
        # Adjust aspect ratio based on number of steps and layout
        aspect_ratio = "16:9" if len(steps) <= 4 else "9:16"
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio=aspect_ratio,
            additional_requirements=[
                "Steps must be clearly numbered and sequential",
                "Arrow flow must be obvious and unambiguous",
                "Each step must be visually distinct"
            ]
        )

    async def generate_analogy_image(
        self,
        concept: str,
        analogy: str,
        mapping: dict[str, str],
        style: str = "cartoon"
    ) -> GenerationResult:
        """
        Generate an image using a familiar analogy.
        
        Shows the relationship between an abstract concept and
        a familiar everyday scenario or object.
        
        Args:
            concept: The abstract concept to explain
            analogy: The familiar analogy
            mapping: Dictionary mapping concept elements to analogy elements
            style: Visual style (cartoon works well for analogies)
            
        Returns:
            Generated image result
        """
        mapping_text = "\n".join([
            f"- {analogy_elem} = {concept_elem}" 
            for analogy_elem, concept_elem in mapping.items()
        ])
        
        prompt = f"""
Create an educational diagram explaining "{concept}" using the analogy of "{analogy}".

ELEMENT MAPPING (Analogy = Concept):
{mapping_text}

LAYOUT (two-part visual):

TOP SECTION: "{analogy}" (The Familiar)
- Show the {analogy} with all its relevant elements
- Label each element that maps to the concept
- Make it immediately recognizable and relatable

BOTTOM SECTION: "{concept}" (The Abstract)
- Show the concept with corresponding elements
- Use matching positions for mapped elements
- Use more technical/academic representation

CONNECTIONS:
- Draw connecting lines between corresponding elements
- Use matching colors for paired elements
- Add labels explaining the relationship

TITLE: "{concept} is like {analogy}"

The analogy should make the abstract concept immediately understandable.
"""
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio="4:3",
            additional_requirements=[
                "Analogy elements must be clearly connected to concept elements",
                "The familiar scenario should be instantly recognizable",
                "Mapping should be visually obvious without reading all labels"
            ]
        )

    async def generate_concept_map(
        self,
        central_concept: str,
        related_concepts: list[str],
        relationships: Optional[dict[str, str]] = None,
        style: str = "schematic"
    ) -> GenerationResult:
        """
        Generate a concept map showing relationships.
        
        Args:
            central_concept: The main concept in the center
            related_concepts: List of related concepts
            relationships: Optional dict mapping concept pairs to relationship labels
            style: Visual style
            
        Returns:
            Generated image result
        """
        concepts_text = "\n".join([f"- {c}" for c in related_concepts[:8]])
        
        relationships_text = ""
        if relationships:
            relationships_text = "Relationships:\n" + "\n".join([
                f"- {pair}: {label}" 
                for pair, label in list(relationships.items())[:10]
            ])
        
        prompt = f"""
Create a concept map diagram centered on: "{central_concept}"

CENTRAL CONCEPT (in the middle):
{central_concept}
- Make this the largest, most prominent element
- Use a distinctive shape (large circle or rounded rectangle)
- Use a bold, eye-catching color

RELATED CONCEPTS (surrounding the center):
{concepts_text}
- Arrange these around the central concept
- Use consistent shapes for all related concepts
- Size should indicate importance/relevance

{relationships_text}

CONNECTIONS:
- Draw lines connecting related concepts
- Add labels on lines showing the relationship type
- Use different line styles for different relationship types
- Arrows should show direction of relationship where relevant

LAYOUT:
- Radial layout with central concept in the middle
- Related concepts distributed evenly around
- No overlapping elements
- Clear visual hierarchy
"""
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio="1:1",
            additional_requirements=[
                "Central concept must be visually dominant",
                "Connections must be clear and labeled",
                "Related concepts should be evenly distributed"
            ]
        )

    async def generate_timeline_image(
        self,
        title: str,
        events: list[dict[str, str]],
        style: str = "infographic"
    ) -> GenerationResult:
        """
        Generate a timeline diagram.
        
        Args:
            title: Timeline title
            events: List of event dicts with 'date' and 'description' keys
            style: Visual style
            
        Returns:
            Generated image result
        """
        events_text = "\n".join([
            f"- {event.get('date', 'Unknown')}: {event.get('description', '')}"
            for event in events[:10]
        ])
        
        prompt = f"""
Create a timeline diagram: "{title}"

EVENTS TO SHOW:
{events_text}

LAYOUT:
- Horizontal timeline with dates/periods marked
- Clear progression from left (earliest) to right (latest)
- Each event should have:
  * A date/period label
  * A brief description
  * An optional small icon or image
- Use a continuous line connecting all events
- Mark major periods or eras if applicable

VISUAL DESIGN:
- Consistent spacing between events
- Clear date labels above or below the line
- Event descriptions should not overlap
- Use color to distinguish different periods or themes
"""
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio="16:9",
            additional_requirements=[
                "Timeline must show clear chronological progression",
                "Events must be evenly spaced and readable",
                "Date labels must be prominent"
            ]
        )

    async def generate_formula_visualization(
        self,
        formula: str,
        variables: dict[str, str],
        example: Optional[str] = None,
        style: str = "schematic"
    ) -> GenerationResult:
        """
        Generate a visualization of a mathematical formula.
        
        Args:
            formula: The formula to visualize
            variables: Dictionary mapping variable names to their meanings
            example: Optional example calculation
            style: Visual style
            
        Returns:
            Generated image result
        """
        variables_text = "\n".join([
            f"- {var}: {meaning}" 
            for var, meaning in variables.items()
        ])
        
        example_text = f"\nEXAMPLE CALCULATION:\n{example}" if example else ""
        
        prompt = f"""
Create a visual explanation of the formula: {formula}

VARIABLE MEANINGS:
{variables_text}

{example_text}

LAYOUT:
- TOP: The complete formula in large, clear mathematical notation
- MIDDLE: Variable breakdown with color-coded elements
  * Each variable in its assigned color
  * Arrow or line connecting to its meaning
- BOTTOM: Visual representation of what the formula calculates
  {f"Include the example calculation showing actual numbers" if example else ""}

COLOR CODING:
- Assign a distinct color to each variable
- Use the same colors consistently throughout
- Highlight the result/output clearly

Make the formula approachable and understandable at a glance.
"""
        
        return await self.generate_explanation_image(
            prompt=prompt,
            style=style,
            aspect_ratio="4:3",
            additional_requirements=[
                "Formula must be clearly readable",
                "Variable colors must be consistent",
                "Visual breakdown must be intuitive"
            ]
        )

    def get_available_styles(self) -> dict[str, StyleConfig]:
        """Get all available style configurations."""
        return STYLE_CONFIGS.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        avg_time = (
            self._total_generation_time_ms / self._request_count 
            if self._request_count > 0 else 0
        )
        
        return {
            "request_count": self._request_count,
            "total_generation_time_ms": self._total_generation_time_ms,
            "average_generation_time_ms": avg_time,
            "available_styles": list(STYLE_CONFIGS.keys()),
            "client_active": self._client is not None and not self._client.is_closed
        }

    async def close(self):
        """Close the HTTP client and release resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        logger.info("Nano Banana Pro service closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
