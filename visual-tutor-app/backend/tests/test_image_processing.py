"""Tests for image processing utilities."""

import pytest
import io
import base64
from PIL import Image

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.image_processing import (
    validate_image,
    decode_base64_image,
    encode_image_to_base64,
    compress_image,
    get_image_dimensions,
    extract_annotation_region,
    overlay_annotations,
    create_comparison_image,
)


@pytest.fixture
def sample_jpeg_bytes():
    """Create a sample JPEG image."""
    img = Image.new("RGB", (200, 200), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.fixture
def sample_png_bytes():
    """Create a sample PNG image."""
    img = Image.new("RGBA", (200, 200), color=(0, 255, 0, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def large_image_bytes():
    """Create a large image."""
    img = Image.new("RGB", (4000, 3000), color="blue")
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


class TestValidateImage:
    """Tests for validate_image function."""

    def test_valid_jpeg(self, sample_jpeg_bytes):
        """Test validation of valid JPEG."""
        assert validate_image(sample_jpeg_bytes) is True

    def test_valid_png(self, sample_png_bytes):
        """Test validation of valid PNG."""
        assert validate_image(sample_png_bytes) is True

    def test_invalid_data(self):
        """Test validation of invalid data."""
        assert validate_image(b"not an image") is False

    def test_size_limit(self, large_image_bytes):
        """Test size limit enforcement."""
        # Should fail with 0.1MB limit
        assert validate_image(large_image_bytes, max_size_mb=0.1) is False
        # Should pass with larger limit
        assert validate_image(large_image_bytes, max_size_mb=50) is True

    def test_format_restriction(self, sample_jpeg_bytes):
        """Test format restriction."""
        assert validate_image(sample_jpeg_bytes, allowed_formats=["PNG"]) is False
        assert validate_image(sample_jpeg_bytes, allowed_formats=["JPEG"]) is True


class TestBase64Operations:
    """Tests for base64 encode/decode functions."""

    def test_encode_decode_roundtrip(self, sample_jpeg_bytes):
        """Test encoding and decoding produces same bytes."""
        encoded = encode_image_to_base64(sample_jpeg_bytes)
        decoded = decode_base64_image(encoded)
        assert decoded == sample_jpeg_bytes

    def test_decode_with_data_uri(self, sample_jpeg_bytes):
        """Test decoding base64 with data URI prefix."""
        encoded = encode_image_to_base64(sample_jpeg_bytes)
        data_uri = f"data:image/jpeg;base64,{encoded}"
        decoded = decode_base64_image(data_uri)
        assert decoded == sample_jpeg_bytes

    def test_decode_invalid_base64(self):
        """Test decoding invalid base64 raises error."""
        with pytest.raises(ValueError, match="Invalid base64"):
            decode_base64_image("not valid base64!!!")


class TestCompressImage:
    """Tests for compress_image function."""

    def test_compression_reduces_size(self, large_image_bytes):
        """Test that compression reduces image size."""
        compressed = compress_image(large_image_bytes, max_size=(800, 600), quality=60)
        assert len(compressed) < len(large_image_bytes)

    def test_compression_respects_max_dimensions(self, large_image_bytes):
        """Test that compression respects max dimensions."""
        compressed = compress_image(large_image_bytes, max_size=(800, 600))
        with Image.open(io.BytesIO(compressed)) as img:
            assert img.width <= 800
            assert img.height <= 600

    def test_compression_handles_rgba(self, sample_png_bytes):
        """Test that RGBA is converted for JPEG output."""
        compressed = compress_image(sample_png_bytes, format="JPEG")
        with Image.open(io.BytesIO(compressed)) as img:
            assert img.mode == "RGB"


class TestGetImageDimensions:
    """Tests for get_image_dimensions function."""

    def test_get_dimensions(self, sample_jpeg_bytes):
        """Test getting image dimensions."""
        width, height = get_image_dimensions(sample_jpeg_bytes)
        assert width == 200
        assert height == 200

    def test_get_dimensions_large_image(self, large_image_bytes):
        """Test getting dimensions of large image."""
        width, height = get_image_dimensions(large_image_bytes)
        assert width == 4000
        assert height == 3000


class TestExtractAnnotationRegion:
    """Tests for extract_annotation_region function."""

    def test_extract_center_region(self, sample_jpeg_bytes):
        """Test extracting center region."""
        region = extract_annotation_region(
            sample_jpeg_bytes,
            x=0.4, y=0.4,
            width=0.2, height=0.2,
            padding=0.05
        )
        
        with Image.open(io.BytesIO(region)) as img:
            # Should be smaller than original
            assert img.width < 200
            assert img.height < 200

    def test_extract_corner_region(self, sample_jpeg_bytes):
        """Test extracting corner region (edge case)."""
        region = extract_annotation_region(
            sample_jpeg_bytes,
            x=0.0, y=0.0,
            width=0.2, height=0.2,
            padding=0.1
        )
        
        # Should not raise error even at edge
        assert len(region) > 0


class TestOverlayAnnotations:
    """Tests for overlay_annotations function."""

    def test_overlay_circle(self, sample_jpeg_bytes):
        """Test overlaying circle annotation."""
        annotations = [
            {"type": "circle", "x": 0.5, "y": 0.5, "radius": 0.1, "color": "#FF0000"}
        ]
        
        result = overlay_annotations(sample_jpeg_bytes, annotations)
        
        # Result should be valid image
        with Image.open(io.BytesIO(result)) as img:
            assert img.width == 200
            assert img.height == 200

    def test_overlay_arrow(self, sample_jpeg_bytes):
        """Test overlaying arrow annotation."""
        annotations = [
            {
                "type": "arrow",
                "x": 0.2, "y": 0.2,
                "end_x": 0.8, "end_y": 0.8,
                "color": "#00FF00"
            }
        ]
        
        result = overlay_annotations(sample_jpeg_bytes, annotations)
        assert len(result) > 0

    def test_overlay_text(self, sample_jpeg_bytes):
        """Test overlaying text annotation."""
        annotations = [
            {"type": "text", "x": 0.5, "y": 0.5, "text": "Hello!", "color": "#0000FF"}
        ]
        
        result = overlay_annotations(sample_jpeg_bytes, annotations)
        assert len(result) > 0

    def test_overlay_rectangle(self, sample_jpeg_bytes):
        """Test overlaying rectangle annotation."""
        annotations = [
            {
                "type": "rectangle",
                "x": 0.2, "y": 0.2,
                "width": 0.3, "height": 0.3,
                "color": "#FFFF00"
            }
        ]
        
        result = overlay_annotations(sample_jpeg_bytes, annotations)
        assert len(result) > 0

    def test_overlay_multiple_annotations(self, sample_jpeg_bytes):
        """Test overlaying multiple annotations."""
        annotations = [
            {"type": "circle", "x": 0.3, "y": 0.3, "radius": 0.1, "color": "#FF0000"},
            {"type": "text", "x": 0.5, "y": 0.5, "text": "?", "color": "#0000FF"},
            {"type": "arrow", "x": 0.6, "y": 0.6, "end_x": 0.8, "end_y": 0.8, "color": "#00FF00"},
        ]
        
        result = overlay_annotations(sample_jpeg_bytes, annotations)
        assert len(result) > 0


class TestCreateComparisonImage:
    """Tests for create_comparison_image function."""

    def test_create_comparison(self, sample_jpeg_bytes, sample_png_bytes):
        """Test creating comparison image."""
        result = create_comparison_image(sample_jpeg_bytes, sample_png_bytes)
        
        with Image.open(io.BytesIO(result)) as img:
            # Width should be combined widths plus separator
            assert img.width > 200  # Combined width
            assert img.height == 200  # Same height

    def test_comparison_with_different_sizes(self):
        """Test comparison with different sized images."""
        # Create images of different sizes
        img1 = Image.new("RGB", (100, 150), color="red")
        buf1 = io.BytesIO()
        img1.save(buf1, format="JPEG")
        
        img2 = Image.new("RGB", (200, 100), color="blue")
        buf2 = io.BytesIO()
        img2.save(buf2, format="JPEG")
        
        result = create_comparison_image(buf1.getvalue(), buf2.getvalue())
        
        with Image.open(io.BytesIO(result)) as img:
            # Height should be max of both
            assert img.height == 150
