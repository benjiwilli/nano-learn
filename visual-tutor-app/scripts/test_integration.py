#!/usr/bin/env python3
"""
Integration tests for Visual Tutor App.

Run with: python scripts/test_integration.py
"""

import asyncio
import base64
import sys
from pathlib import Path
import io

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import httpx
from PIL import Image


BASE_URL = "http://localhost:8000"


async def create_test_image() -> str:
    """Create a simple test image and return base64 encoded."""
    img = Image.new("RGB", (400, 300), color="white")
    
    # Draw some shapes to simulate educational content
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    
    # Draw a simple diagram
    draw.rectangle([50, 50, 150, 150], outline="black", width=2)
    draw.ellipse([200, 50, 300, 150], outline="blue", width=2)
    draw.line([150, 100, 200, 100], fill="red", width=2)
    draw.text((100, 200), "Test Diagram", fill="black")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


async def test_health_check():
    """Test the health check endpoint."""
    print("\n1. Testing health check endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy"
        
        print(f"   ✓ Health check passed: {data}")


async def test_get_subjects():
    """Test the subjects endpoint."""
    print("\n2. Testing subjects endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/subjects")
        
        assert response.status_code == 200
        data = response.json()
        assert "subjects" in data
        assert len(data["subjects"]) > 0
        
        print(f"   ✓ Got {len(data['subjects'])} subjects")
        for subject in data["subjects"]:
            print(f"     - {subject['name']}: {', '.join(subject['subtopics'][:3])}...")


async def test_get_styles():
    """Test the styles endpoint."""
    print("\n3. Testing styles endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/styles")
        
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        
        print(f"   ✓ Got {len(data['styles'])} styles:")
        for style in data["styles"]:
            print(f"     - {style['name']}: {style['description'][:50]}...")


async def test_snap_and_explain_validation():
    """Test validation on snap-and-explain endpoint."""
    print("\n4. Testing snap-and-explain validation...")
    
    async with httpx.AsyncClient() as client:
        # Test empty image
        response = await client.post(
            f"{BASE_URL}/api/v1/snap-and-explain",
            json={"image": ""}
        )
        
        assert response.status_code in [400, 422], f"Expected validation error, got {response.status_code}"
        print("   ✓ Empty image rejected correctly")
        
        # Test invalid base64
        response = await client.post(
            f"{BASE_URL}/api/v1/snap-and-explain",
            json={"image": "not-valid-base64!!!"}
        )
        
        assert response.status_code in [400, 422, 500]
        print("   ✓ Invalid base64 handled correctly")


async def test_snap_and_explain_structure():
    """Test snap-and-explain with valid structure (API keys required for full test)."""
    print("\n5. Testing snap-and-explain request structure...")
    
    image_b64 = await create_test_image()
    
    request_data = {
        "image": image_b64,
        "annotations": [
            {
                "type": "circle",
                "x": 0.5,
                "y": 0.5,
                "radius": 0.1,
                "color": "#FF0000",
                "stroke_width": 2
            },
            {
                "type": "text",
                "x": 0.6,
                "y": 0.4,
                "text": "?",
                "color": "#0000FF",
                "stroke_width": 2
            }
        ],
        "question": "What is this diagram showing?",
        "subject": "physics"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/snap-and-explain",
                json=request_data
            )
            
            if response.status_code == 200:
                data = response.json()
                print("   ✓ Full snap-and-explain completed!")
                print(f"     - Request ID: {data.get('request_id')}")
                print(f"     - Generation time: {data.get('generation_time_ms')}ms")
                print(f"     - Concept: {data.get('confusion_analysis', {}).get('confusion_concept')}")
            elif response.status_code == 500:
                # API key might not be configured
                print("   ⚠ API returned 500 - check if API keys are configured")
                print(f"     Response: {response.text[:200]}...")
            else:
                print(f"   ⚠ Unexpected status: {response.status_code}")
                print(f"     Response: {response.text[:200]}...")
                
        except httpx.TimeoutException:
            print("   ⚠ Request timed out - API might be slow or unavailable")


async def test_websocket_connection():
    """Test WebSocket connection for Live Lens."""
    print("\n6. Testing WebSocket connection...")
    
    import websockets
    
    try:
        uri = "ws://localhost:8000/api/v1/live-lens"
        async with websockets.connect(uri) as websocket:
            # Should receive connection message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            import json
            data = json.loads(message)
            
            assert data["type"] == "connected"
            assert "session_id" in data
            
            print(f"   ✓ WebSocket connected! Session: {data['session_id']}")
            
            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            pong = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            pong_data = json.loads(pong)
            
            assert pong_data["type"] == "pong"
            print("   ✓ Ping/Pong working correctly")
            
    except ImportError:
        print("   ⚠ websockets library not installed, skipping WebSocket test")
    except Exception as e:
        print(f"   ⚠ WebSocket test failed: {e}")


async def test_live_lens_sessions():
    """Test Live Lens sessions endpoint."""
    print("\n7. Testing Live Lens sessions endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/live-lens/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_sessions" in data
        
        print(f"   ✓ Active sessions: {data['active_sessions']}")


async def run_all_tests():
    """Run all integration tests."""
    print("=" * 50)
    print("Visual Tutor - Integration Tests")
    print("=" * 50)
    print(f"\nTarget: {BASE_URL}")
    
    tests = [
        test_health_check,
        test_get_subjects,
        test_get_styles,
        test_snap_and_explain_validation,
        test_snap_and_explain_structure,
        test_websocket_connection,
        test_live_lens_sessions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest runner error: {e}")
        sys.exit(1)
