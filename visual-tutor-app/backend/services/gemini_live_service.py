"""Gemini Live streaming service for real-time video analysis."""

import logging
import asyncio
from typing import Any, AsyncGenerator, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from .gemini_service import GeminiService


logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    """Event from the Gemini Live stream."""
    type: str  # 'analysis', 'transcript', 'function_call', 'error'
    data: dict
    timestamp: datetime


class GeminiLiveService:
    """Service for handling Gemini Live real-time streaming."""

    def __init__(self, gemini_service: GeminiService):
        """
        Initialize the Gemini Live service.
        
        Args:
            gemini_service: Gemini service instance for API calls
        """
        self.gemini = gemini_service
        self._active_sessions: dict[str, dict] = {}

    async def start_session(
        self,
        session_id: str,
        on_event: Optional[Callable[[StreamEvent], None]] = None
    ) -> dict:
        """
        Start a new live streaming session.
        
        Args:
            session_id: Unique session identifier
            on_event: Callback for stream events
            
        Returns:
            Session information
        """
        logger.info(f"Starting live session: {session_id}")
        
        session = {
            "id": session_id,
            "started_at": datetime.utcnow(),
            "context": [],
            "frame_count": 0,
            "on_event": on_event,
            "active": True
        }
        
        self._active_sessions[session_id] = session
        
        return {
            "session_id": session_id,
            "status": "active",
            "started_at": session["started_at"].isoformat()
        }

    async def process_frame(
        self,
        session_id: str,
        frame: bytes,
        timestamp_ms: int
    ) -> dict:
        """
        Process a video frame from the stream.
        
        Args:
            session_id: Session identifier
            frame: Video frame bytes
            timestamp_ms: Frame timestamp in milliseconds
            
        Returns:
            Frame analysis result
        """
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        session["frame_count"] += 1
        
        # Only analyze every Nth frame to reduce API calls
        # At 2fps, this means analyzing every second
        if session["frame_count"] % 2 != 0:
            return {"status": "skipped", "reason": "frame_skip"}
        
        # Analyze the frame
        analysis = await self.gemini.analyze_video_frame(
            frame=frame,
            context=session["context"],
            transcript=None
        )
        
        # Emit event if callback registered
        if session["on_event"]:
            event = StreamEvent(
                type="analysis",
                data=analysis,
                timestamp=datetime.utcnow()
            )
            session["on_event"](event)
        
        return analysis

    async def process_audio(
        self,
        session_id: str,
        transcript: str,
        current_frame: Optional[bytes] = None
    ) -> dict:
        """
        Process transcribed audio from the stream.
        
        Args:
            session_id: Session identifier
            transcript: Transcribed audio text
            current_frame: Optional current video frame
            
        Returns:
            Audio analysis result with potential trigger for image generation
        """
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        # Add to context
        session["context"].append({
            "role": "user",
            "content": transcript,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep context manageable
        if len(session["context"]) > 20:
            session["context"] = session["context"][-20:]
        
        # Analyze if we should trigger visual explanation
        should_generate = self._should_generate_visual(transcript)
        
        result = {
            "transcript": transcript,
            "should_generate_visual": should_generate,
            "trigger_reason": None
        }
        
        if should_generate:
            result["trigger_reason"] = self._get_trigger_reason(transcript)
            
            if session["on_event"]:
                event = StreamEvent(
                    type="function_call",
                    data={
                        "function": "generate_explanation_image",
                        "trigger": result["trigger_reason"]
                    },
                    timestamp=datetime.utcnow()
                )
                session["on_event"](event)
        
        return result

    def _should_generate_visual(self, transcript: str) -> bool:
        """Determine if the transcript indicates need for visual explanation."""
        confusion_indicators = [
            "what is", "what's", "don't understand", "don't get",
            "confused", "confusing", "explain", "help me",
            "show me", "how does", "how do", "why does", "why do",
            "what does", "can you", "could you", "please explain",
            "i'm lost", "makes no sense", "doesn't make sense"
        ]
        
        question_indicators = ["?"]
        
        transcript_lower = transcript.lower()
        
        # Check for confusion indicators
        has_confusion = any(ind in transcript_lower for ind in confusion_indicators)
        
        # Check for questions
        has_question = any(ind in transcript for ind in question_indicators)
        
        return has_confusion or has_question

    def _get_trigger_reason(self, transcript: str) -> str:
        """Identify the specific reason for triggering visual generation."""
        transcript_lower = transcript.lower()
        
        if "what is" in transcript_lower or "what's" in transcript_lower:
            return "definition_request"
        elif "how does" in transcript_lower or "how do" in transcript_lower:
            return "process_explanation"
        elif "why" in transcript_lower:
            return "reasoning_explanation"
        elif "show me" in transcript_lower:
            return "visual_request"
        elif "don't understand" in transcript_lower or "confused" in transcript_lower:
            return "confusion_detected"
        elif "?" in transcript:
            return "question_asked"
        else:
            return "general_inquiry"

    async def end_session(self, session_id: str) -> dict:
        """
        End a live streaming session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary
        """
        session = self._active_sessions.pop(session_id, None)
        
        if not session:
            return {"status": "not_found"}
        
        session["active"] = False
        duration = (datetime.utcnow() - session["started_at"]).total_seconds()
        
        logger.info(f"Ending live session: {session_id}, duration: {duration}s")
        
        return {
            "session_id": session_id,
            "status": "ended",
            "duration_seconds": duration,
            "total_frames": session["frame_count"],
            "context_messages": len(session["context"])
        }

    def get_session_status(self, session_id: str) -> dict:
        """Get the current status of a session."""
        session = self._active_sessions.get(session_id)
        
        if not session:
            return {"status": "not_found"}
        
        return {
            "session_id": session_id,
            "status": "active" if session["active"] else "ended",
            "frame_count": session["frame_count"],
            "context_size": len(session["context"]),
            "started_at": session["started_at"].isoformat()
        }

    async def stream_analyze(
        self,
        session_id: str,
        frame_generator: AsyncGenerator[bytes, None]
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream analysis of video frames.
        
        Args:
            session_id: Session identifier
            frame_generator: Async generator yielding video frames
            
        Yields:
            StreamEvent objects with analysis results
        """
        session = self._active_sessions.get(session_id)
        if not session:
            yield StreamEvent(
                type="error",
                data={"message": "Session not found"},
                timestamp=datetime.utcnow()
            )
            return
        
        async for frame in frame_generator:
            if not session["active"]:
                break
            
            try:
                analysis = await self.process_frame(
                    session_id=session_id,
                    frame=frame,
                    timestamp_ms=int(datetime.utcnow().timestamp() * 1000)
                )
                
                if analysis.get("status") != "skipped":
                    yield StreamEvent(
                        type="analysis",
                        data=analysis,
                        timestamp=datetime.utcnow()
                    )
                    
            except Exception as e:
                logger.error(f"Frame analysis error: {e}")
                yield StreamEvent(
                    type="error",
                    data={"message": str(e)},
                    timestamp=datetime.utcnow()
                )
            
            # Small delay to prevent overwhelming the API
            await asyncio.sleep(0.1)

    @property
    def active_session_count(self) -> int:
        """Get the number of active sessions."""
        return sum(1 for s in self._active_sessions.values() if s["active"])
