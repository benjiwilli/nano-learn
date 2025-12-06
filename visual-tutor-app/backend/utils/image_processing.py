"""Image processing utilities for Visual Tutor App."""

import io
import base64
import logging
from typing import Optional, Tuple

from PIL import Image


logger = logging.getLogger(__name__)


def validate_image(
    image_bytes: bytes,
    max_size_mb: int = 10,
    allowed_formats: Optional[list[str]] = None
) -> bool:
    """
    Validate image data.
    
    Args:
        image_bytes: Raw image bytes
        max_size_mb: Maximum allowed size in megabytes
        allowed_formats: List of allowed formats (default: JPEG, PNG, WEBP)
        
    Returns:
        True if valid, False otherwise
    """
    if allowed_formats is None:
        allowed_formats = ["JPEG", "PNG", "WEBP", "GIF"]
    
    # Check size
    size_mb = len(image_bytes) / (1024 * 1024)
    if size_mb > max_size_mb:
        logger.warning(f"Image too large: {size_mb:.2f}MB > {max_size_mb}MB")
        return False
    
    # Check if it's a valid image
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            if img.format not in allowed_formats:
                logger.warning(f"Invalid format: {img.format}")
                return False
            # Try to load to verify integrity
            img.verify()
        return True
    except Exception as e:
        logger.warning(f"Image validation failed: {e}")
        return False


def decode_base64_image(base64_string: str) -> bytes:
    """
    Decode a base64-encoded image.
    
    Args:
        base64_string: Base64-encoded image string (may include data URI prefix)
        
    Returns:
        Raw image bytes
        
    Raises:
        ValueError: If the string is not valid base64
    """
    # Remove data URI prefix if present
    if "," in base64_string:
        base64_string = base64_string.split(",", 1)[1]
    
    # Remove whitespace
    base64_string = base64_string.strip()
    
    try:
        return base64.b64decode(base64_string)
    except Exception as e:
        raise ValueError(f"Invalid base64 image data: {e}")


def encode_image_to_base64(image_bytes: bytes) -> str:
    """
    Encode image bytes to base64 string.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Base64-encoded string
    """
    return base64.b64encode(image_bytes).decode("utf-8")


def compress_image(
    image_bytes: bytes,
    max_size: Tuple[int, int] = (1920, 1080),
    quality: int = 85,
    format: str = "JPEG"
) -> bytes:
    """
    Compress an image to reduce size.
    
    Args:
        image_bytes: Raw image bytes
        max_size: Maximum dimensions (width, height)
        quality: JPEG quality (1-100)
        format: Output format (JPEG, PNG, WEBP)
        
    Returns:
        Compressed image bytes
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert RGBA to RGB for JPEG
            if format == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Resize if necessary
            if img.width > max_size[0] or img.height > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format=format, quality=quality, optimize=True)
            return output.getvalue()
            
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
        return image_bytes  # Return original if compression fails


def get_image_dimensions(image_bytes: bytes) -> Tuple[int, int]:
    """
    Get image dimensions.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        Tuple of (width, height)
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        return img.size


def extract_annotation_region(
    image_bytes: bytes,
    x: float,
    y: float,
    width: float,
    height: float,
    padding: float = 0.1
) -> bytes:
    """
    Extract a region around an annotation.
    
    Args:
        image_bytes: Raw image bytes
        x: Relative X position (0-1)
        y: Relative Y position (0-1)
        width: Relative width (0-1)
        height: Relative height (0-1)
        padding: Additional padding around region (0-1)
        
    Returns:
        Cropped region bytes
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        img_width, img_height = img.size
        
        # Calculate absolute coordinates with padding
        left = max(0, int((x - padding) * img_width))
        top = max(0, int((y - padding) * img_height))
        right = min(img_width, int((x + width + padding) * img_width))
        bottom = min(img_height, int((y + height + padding) * img_height))
        
        # Crop
        cropped = img.crop((left, top, right, bottom))
        
        # Save to bytes
        output = io.BytesIO()
        cropped.save(output, format="PNG")
        return output.getvalue()


def overlay_annotations(
    image_bytes: bytes,
    annotations: list[dict]
) -> bytes:
    """
    Overlay annotations onto the image for visualization.
    
    Args:
        image_bytes: Raw image bytes
        annotations: List of annotation dictionaries
        
    Returns:
        Image with annotations overlaid
    """
    from PIL import ImageDraw, ImageFont
    
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert to RGBA for transparency support
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        draw = ImageDraw.Draw(img)
        width, height = img.size
        
        for ann in annotations:
            ann_type = ann.get("type", "")
            color = ann.get("color", "#FF0000")
            x = ann.get("x", 0) * width
            y = ann.get("y", 0) * height
            stroke_width = int(ann.get("stroke_width", 2))
            
            if ann_type == "circle":
                radius = ann.get("radius", 0.05) * min(width, height)
                draw.ellipse(
                    [x - radius, y - radius, x + radius, y + radius],
                    outline=color,
                    width=stroke_width
                )
                
            elif ann_type == "arrow":
                end_x = ann.get("end_x", x + 0.1) * width
                end_y = ann.get("end_y", y + 0.1) * height
                draw.line([x, y, end_x, end_y], fill=color, width=stroke_width)
                # Draw arrowhead
                _draw_arrowhead(draw, x, y, end_x, end_y, color, size=10)
                
            elif ann_type == "rectangle":
                rect_width = ann.get("width", 0.1) * width
                rect_height = ann.get("height", 0.1) * height
                draw.rectangle(
                    [x, y, x + rect_width, y + rect_height],
                    outline=color,
                    width=stroke_width
                )
                
            elif ann_type == "text":
                text = ann.get("text", "")
                if text:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                    except:
                        font = ImageFont.load_default()
                    draw.text((x, y), text, fill=color, font=font)
                    
            elif ann_type == "freehand":
                points = ann.get("points", [])
                if len(points) >= 2:
                    point_coords = [(p["x"] * width, p["y"] * height) for p in points]
                    draw.line(point_coords, fill=color, width=stroke_width)
        
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format="PNG")
        return output.getvalue()


def _draw_arrowhead(draw, x1, y1, x2, y2, color, size=10):
    """Draw an arrowhead at the end of a line."""
    import math
    
    angle = math.atan2(y2 - y1, x2 - x1)
    
    # Calculate arrowhead points
    arrow_angle = math.pi / 6  # 30 degrees
    
    x3 = x2 - size * math.cos(angle - arrow_angle)
    y3 = y2 - size * math.sin(angle - arrow_angle)
    
    x4 = x2 - size * math.cos(angle + arrow_angle)
    y4 = y2 - size * math.sin(angle + arrow_angle)
    
    draw.polygon([(x2, y2), (x3, y3), (x4, y4)], fill=color)


def create_comparison_image(
    original_bytes: bytes,
    generated_bytes: bytes,
    separator_width: int = 10
) -> bytes:
    """
    Create a side-by-side comparison image.
    
    Args:
        original_bytes: Original image bytes
        generated_bytes: Generated image bytes
        separator_width: Width of separator between images
        
    Returns:
        Combined comparison image bytes
    """
    with Image.open(io.BytesIO(original_bytes)) as orig, \
         Image.open(io.BytesIO(generated_bytes)) as gen:
        
        # Ensure same height
        target_height = max(orig.height, gen.height)
        
        # Resize while maintaining aspect ratio
        orig_ratio = orig.width / orig.height
        gen_ratio = gen.width / gen.height
        
        orig_resized = orig.resize(
            (int(target_height * orig_ratio), target_height),
            Image.Resampling.LANCZOS
        )
        gen_resized = gen.resize(
            (int(target_height * gen_ratio), target_height),
            Image.Resampling.LANCZOS
        )
        
        # Create combined image
        total_width = orig_resized.width + separator_width + gen_resized.width
        combined = Image.new("RGB", (total_width, target_height), (255, 255, 255))
        
        # Paste images
        combined.paste(orig_resized, (0, 0))
        combined.paste(gen_resized, (orig_resized.width + separator_width, 0))
        
        # Draw separator
        from PIL import ImageDraw
        draw = ImageDraw.Draw(combined)
        draw.rectangle(
            [orig_resized.width, 0, orig_resized.width + separator_width, target_height],
            fill=(200, 200, 200)
        )
        
        # Save to bytes
        output = io.BytesIO()
        combined.save(output, format="JPEG", quality=90)
        return output.getvalue()
