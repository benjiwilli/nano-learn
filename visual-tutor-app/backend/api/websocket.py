"""WebSocket endpoints for Gemini Live real-time streaming."""

import logging
import json
import asyncio
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from services.gemini_live_service import GeminiLiveService
from services.orchestrator import Orchestrator
from services.gemini_service import GeminiService
from services.nanobananapro_service import NanoBananaProService
from config import settings


logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manage WebSocket connections for Live Lens sessions."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.session_contexts: dict[str, list] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_contexts[session_id] = []
        logger.info(f"WebSocket connected: {session_id}")

    def disconnect(self, session_id: str):
        """Remove a disconnected WebSocket."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_contexts:
            del self.session_contexts[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")

    async def send_message(self, session_id: str, message: dict):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)

    def get_context(self, session_id: str) -> list:
        """Get conversation context for a session."""
        return self.session_contexts.get(session_id, [])

    def update_context(self, session_id: str, message: dict):
        """Add a message to session context."""
        if session_id in self.session_contexts:
            self.session_contexts[session_id].append(message)
            # Keep only last 20 messages for context
            if len(self.session_contexts[session_id]) > 20:
                self.session_contexts[session_id] = self.session_contexts[session_id][-20:]


manager = ConnectionManager()


@router.websocket("/live-lens")
async def live_lens_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for Live Lens real-time video streaming and analysis.
    
    Client messages:
    - {type: 'video_frame', data: base64_image}
    - {type: 'audio', transcript: str}
    - {type: 'request_explanation', concept: str}
    - {type: 'ping'}
    
    Server messages:
    - {type: 'analysis', text: str, timestamp: float}
    - {type: 'image_generated', image_url: str, concept: str}
    - {type: 'explanation', text: str, audio_url: str}
    - {type: 'error', message: str}
    - {type: 'pong'}
    - {type: 'connected', session_id: str}
    """
    session_id = str(uuid4())
    
    await manager.connect(websocket, session_id)
    
    # Initialize services
    gemini_service = GeminiService(api_key=settings.gemini_api_key)
    nano_service = NanoBananaProService(
        api_key=settings.genspark_api_key,
        base_url=settings.genspark_base_url
    )
    orchestrator = Orchestrator(gemini_service=gemini_service, nano_service=nano_service)
    live_service = GeminiLiveService(gemini_service=gemini_service)
    
    # Send connection confirmation
    await manager.send_message(session_id, {
        "type": "connected",
        "session_id": session_id
    })
    
    try:
        # Variables for frame processing
        last_frame: Optional[bytes] = None
        processing_frame = False
        
        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_message(session_id, {"type": "ping"})
                continue
            
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.send_message(session_id, {"type": "pong"})
                
            elif message_type == "video_frame":
                # Store the latest frame
                frame_data = data.get("data", "")
                if frame_data:
                    import base64
                    try:
                        last_frame = base64.b64decode(frame_data)
                    except Exception as e:
                        logger.warning(f"Failed to decode video frame: {e}")
                
            elif message_type == "audio":
                # Process audio transcript
                transcript = data.get("transcript", "")
                if transcript:
                    manager.update_context(session_id, {
                        "role": "user",
                        "content": transcript
                    })
                    
                    # Check for confusion indicators
                    confusion_indicators = [
                        "what is", "don't understand", "confused", "explain",
                        "help", "show me", "?", "how does", "why"
                    ]
                    
                    is_confused = any(
                        indicator in transcript.lower() 
                        for indicator in confusion_indicators
                    )
                    
                    if is_confused and last_frame:
                        # Trigger explanation workflow
                        await manager.send_message(session_id, {
                            "type": "status",
                            "message": "Analyzing your question..."
                        })
                        
                        try:
                            result = await orchestrator.live_lens_workflow(
                                video_frame=last_frame,
                                audio_transcript=transcript,
                                context=manager.get_context(session_id)
                            )
                            
                            if result.get("generated_image_url"):
                                await manager.send_message(session_id, {
                                    "type": "image_generated",
                                    "image_url": result["generated_image_url"],
                                    "concept": result.get("concept", "")
                                })
                            
                            await manager.send_message(session_id, {
                                "type": "explanation",
                                "text": result.get("explanation", ""),
                                "audio_url": result.get("audio_url", "")
                            })
                            
                            manager.update_context(session_id, {
                                "role": "assistant",
                                "content": result.get("explanation", "")
                            })
                            
                        except Exception as e:
                            logger.error(f"Explanation workflow error: {e}", exc_info=True)
                            await manager.send_message(session_id, {
                                "type": "error",
                                "message": "Failed to generate explanation"
                            })
                    else:
                        # Just acknowledge the audio
                        await manager.send_message(session_id, {
                            "type": "analysis",
                            "text": f"I heard: {transcript}"
                        })
            
            elif message_type == "request_explanation":
                # Explicit request for explanation
                concept = data.get("concept", "")
                if concept and last_frame:
                    await manager.send_message(session_id, {
                        "type": "status",
                        "message": f"Generating explanation for: {concept}"
                    })
                    
                    try:
                        result = await orchestrator.live_lens_workflow(
                            video_frame=last_frame,
                            audio_transcript=f"Please explain {concept}",
                            context=manager.get_context(session_id)
                        )
                        
                        if result.get("generated_image_url"):
                            await manager.send_message(session_id, {
                                "type": "image_generated",
                                "image_url": result["generated_image_url"],
                                "concept": concept
                            })
                        
                        await manager.send_message(session_id, {
                            "type": "explanation",
                            "text": result.get("explanation", "")
                        })
                        
                    except Exception as e:
                        logger.error(f"Request explanation error: {e}", exc_info=True)
                        await manager.send_message(session_id, {
                            "type": "error",
                            "message": "Failed to generate explanation"
                        })
                else:
                    await manager.send_message(session_id, {
                        "type": "error",
                        "message": "No video frame available or concept not specified"
                    })
            
            elif message_type == "disconnect":
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected by client: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await manager.send_message(session_id, {
                "type": "error",
                "message": "Connection error occurred"
            })
        except:
            pass
    finally:
        manager.disconnect(session_id)


@router.get("/live-lens/sessions")
async def get_active_sessions():
    """Get count of active Live Lens sessions (for monitoring)."""
    return {
        "active_sessions": len(manager.active_connections)
    }
