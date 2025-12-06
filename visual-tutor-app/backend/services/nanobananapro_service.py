"""
Nano Banana Pro image generation service for Visual Tutor App.

This module provides image generation capabilities for educational diagrams.
For the prototype, it uses placeholder images with descriptive text overlay
to demonstrate the concept.
"""

import logging
import base64
import asyncio
import hashlib
from typing import Optional, Any, TypedDict, Literal
from dataclasses import dataclass, field
from datetime import datetime
import httpx
from io import BytesIO

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
    base_url: str = "https://www.genspark.ai/api/llm_proxy/v1"
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


def create_placeholder_image(prompt: str, style: str, width: int = 800, height: int = 600) -> bytes:
    """
    Create a placeholder image with text describing the diagram.
    
    This is used for the prototype to demonstrate the concept.
    In production, this would call the actual image generation API.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Style-based colors
        style_colors = {
            "educational": {"bg": "#F0F4F8", "text": "#2D3748", "accent": "#3182CE"},
            "schematic": {"bg": "#1A365D", "text": "#FFFFFF", "accent": "#63B3ED"},
            "cartoon": {"bg": "#FFF5F5", "text": "#2D3748", "accent": "#F56565"},
            "realistic": {"bg": "#FFFFF0", "text": "#2D3748", "accent": "#38A169"},
            "minimalist": {"bg": "#FFFFFF", "text": "#1A202C", "accent": "#718096"},
            "gamified": {"bg": "#2D3748", "text": "#FFFFFF", "accent": "#9F7AEA"},
            "infographic": {"bg": "#EBF8FF", "text": "#2C5282", "accent": "#4299E1"},
            "comparison": {"bg": "#F7FAFC", "text": "#2D3748", "accent": "#E53E3E"},
        }
        
        colors = style_colors.get(style, style_colors["educational"])
        
        # Create image
        img = Image.new("RGB", (width, height), colors["bg"])
        draw = ImageDraw.Draw(img)
        
        # Try to use a font, fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
        
        # Draw header
        header_text = f"Visual Explanation - {style.title()} Style"
        draw.rectangle([0, 0, width, 60], fill=colors["accent"])
        draw.text((20, 15), header_text, fill="#FFFFFF", font=font_large)
        
        # Draw prompt description (word wrap)
        y_pos = 80
        max_width = width - 40
        
        # Simple word wrap
        words = prompt[:500].split()  # Limit prompt length
        lines = []
        current_line = []
        
        for word in words:
            current_line.append(word)
            test_line = " ".join(current_line)
            if len(test_line) > 80:  # Characters per line
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []
        if current_line:
            lines.append(" ".join(current_line))
        
        for line in lines[:15]:  # Limit lines
            draw.text((20, y_pos), line, fill=colors["text"], font=font_medium)
            y_pos += 25
        
        if len(lines) > 15:
            draw.text((20, y_pos), "...", fill=colors["text"], font=font_medium)
        
        # Draw footer
        footer_y = height - 40
        draw.rectangle([0, footer_y, width, height], fill=colors["accent"])
        draw.text((20, footer_y + 10), "AI-Generated Educational Diagram (Prototype)", fill="#FFFFFF", font=font_small)
        
        # Draw decorative elements
        # Border
        draw.rectangle([0, 0, width-1, height-1], outline=colors["accent"], width=3)
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
        
    except ImportError:
        logger.warning("PIL not available, returning minimal placeholder")
        # Return a minimal valid PNG if PIL is not available
        # This is a 1x1 transparent PNG
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )


class NanoBananaProService:
    """
    Service for generating educational images.
    
    For the prototype, this generates placeholder images that describe
    what the actual generated image would contain.
    
    Features:
    - Multiple style presets optimized for education
    - Automatic prompt enhancement for educational clarity
    - Specialized methods for different diagram types
    - Comprehensive error handling
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.genspark.ai/api/llm_proxy/v1",
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
        Generate an educational diagram.
        
        For the prototype, this generates a placeholder image with
        the prompt description. In production, this would call the
        actual image generation API.
        
        Args:
            prompt: Detailed prompt for image generation
            style: Visual style (educational, schematic, cartoon, etc.)
            aspect_ratio: Image aspect ratio (defaults based on style)
            reference_images: Optional reference images for context
            enhance_prompt: Whether to apply automatic prompt enhancement
            additional_requirements: Extra requirements to add to the prompt
            
        Returns:
            GenerationResult containing image bytes, URL, and metadata
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
        
        # Calculate dimensions based on aspect ratio
        ratio_map = {
            "1:1": (800, 800),
            "16:9": (960, 540),
            "9:16": (540, 960),
            "4:3": (800, 600),
            "3:4": (600, 800),
        }
        width, height = ratio_map.get(final_aspect_ratio, (800, 600))
        
        # Generate placeholder image
        try:
            image_bytes = create_placeholder_image(enhanced_prompt, style, width, height)
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            self._request_count += 1
            self._total_generation_time_ms += generation_time_ms
            
            # Create data URL for the image
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            image_url = f"data:image/png;base64,{image_b64}"
            
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
            
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise NanoBananaProError(f"Failed to generate image: {e}")

    async def generate_comparison_image(
        self,
        concept: str,
        before_description: str,
        after_description: str,
        style: str = "comparison"
    ) -> GenerationResult:
        """
        Generate a before/after comparison image.
        """
        prompt = f"""
COMPARISON DIAGRAM: "{concept}"

LEFT SIDE (Before/Misconception):
{before_description}

RIGHT SIDE (After/Correct Understanding):
{after_description}

Layout: Side-by-side with clear dividing line
Title: "Understanding {concept}"
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
        """
        steps_text = "\n".join([
            f"Step {i+1}: {step}" 
            for i, step in enumerate(steps[:8])
        ])
        
        layout = "horizontal flow" if len(steps) <= 4 else "vertical flow or grid"
        
        prompt = f"""
STEP-BY-STEP DIAGRAM: "{concept}"

STEPS:
{steps_text}

Layout: {layout} with numbered steps and arrows showing progression
Title: "How to {concept}" or "{concept} Process"
"""
        
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
        """
        mapping_text = "\n".join([
            f"- {analogy_elem} = {concept_elem}" 
            for analogy_elem, concept_elem in mapping.items()
        ])
        
        prompt = f"""
ANALOGY DIAGRAM: "{concept}" is like "{analogy}"

ELEMENT MAPPING:
{mapping_text}

TOP: Show the familiar analogy ({analogy})
BOTTOM: Show the abstract concept ({concept})
CONNECTIONS: Lines linking corresponding elements

Title: "{concept} is like {analogy}"
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
        """
        concepts_text = "\n".join([f"- {c}" for c in related_concepts[:8]])
        
        relationships_text = ""
        if relationships:
            relationships_text = "Relationships:\n" + "\n".join([
                f"- {pair}: {label}" 
                for pair, label in list(relationships.items())[:10]
            ])
        
        prompt = f"""
CONCEPT MAP: "{central_concept}"

CENTRAL CONCEPT (center, largest):
{central_concept}

RELATED CONCEPTS (surrounding):
{concepts_text}

{relationships_text}

Layout: Radial with central concept in middle, related concepts around it
Connections: Lines with relationship labels
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
        """
        events_text = "\n".join([
            f"- {event.get('date', 'Unknown')}: {event.get('description', '')}"
            for event in events[:10]
        ])
        
        prompt = f"""
TIMELINE DIAGRAM: "{title}"

EVENTS:
{events_text}

Layout: Horizontal timeline from left (earliest) to right (latest)
Each event: Date label + brief description + optional icon
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
        """
        variables_text = "\n".join([
            f"- {var}: {meaning}" 
            for var, meaning in variables.items()
        ])
        
        example_text = f"\nEXAMPLE: {example}" if example else ""
        
        prompt = f"""
FORMULA VISUALIZATION: {formula}

VARIABLES:
{variables_text}
{example_text}

Layout:
- TOP: Formula in large, clear notation
- MIDDLE: Variable breakdown with color coding
- BOTTOM: Visual representation of what the formula calculates
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
