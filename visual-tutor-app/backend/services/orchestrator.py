"""
Orchestrator service for coordinating multi-agent workflows.

This is the critical agentic component that coordinates the entire
Visual Tutor pipeline, managing the flow between analysis, generation,
and explanation services.
"""

import logging
import asyncio
import time
from typing import Any, Optional, TypedDict, Literal
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .gemini_service import GeminiService, ConfusionAnalysis
from .nanobananapro_service import NanoBananaProService, GenerationResult
from utils.cache import explanation_cache
from utils.exceptions import (
    VisualTutorError,
    AnalysisError,
    GeminiError,
    NanoBananaProError
)


logger = logging.getLogger(__name__)


class WorkflowStep(str, Enum):
    """Workflow step identifiers."""
    ANALYSIS = "analysis"
    PROMPT_GENERATION = "prompt_generation"
    IMAGE_GENERATION = "image_generation"
    EXPLANATION = "explanation"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(TypedDict):
    """Status information for a workflow execution."""
    step: str
    progress: float
    message: str
    started_at: str
    elapsed_ms: int


class SnapAndExplainResult(TypedDict):
    """Result type for snap-and-explain workflow."""
    generated_image_url: str
    generated_image_bytes: bytes
    explanation: str
    confusion_analysis: dict[str, Any]
    prompt_used: str
    generation_time_ms: int
    workflow_steps: list[dict[str, Any]]


class LiveLensResult(TypedDict):
    """Result type for live lens workflow."""
    generated_image_url: str
    explanation: str
    concept: str
    audio_url: str
    frame_analysis: dict[str, Any]
    triggered_generation: bool


@dataclass
class WorkflowMetrics:
    """Metrics collected during workflow execution."""
    analysis_time_ms: int = 0
    prompt_generation_time_ms: int = 0
    image_generation_time_ms: int = 0
    explanation_time_ms: int = 0
    total_time_ms: int = 0
    cache_hits: int = 0
    retry_count: int = 0


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""
    enable_caching: bool = True
    enable_fallbacks: bool = True
    max_concurrent_tasks: int = 3
    workflow_timeout_seconds: float = 120.0
    enable_step_tracking: bool = True


class Orchestrator:
    """
    Orchestrates the multi-step workflow for visual explanations.
    
    This is the central coordination component that manages:
    1. Gemini analysis of student confusion
    2. Prompt generation for Nano Banana Pro
    3. Educational image generation
    4. Feedback loop for verbal explanation
    
    Features:
    - Step-by-step workflow tracking
    - Comprehensive error handling with fallbacks
    - Caching integration for performance
    - Concurrent task execution where possible
    - Detailed metrics collection
    """

    def __init__(
        self,
        gemini_service: GeminiService,
        nano_service: NanoBananaProService,
        config: Optional[OrchestratorConfig] = None
    ):
        """
        Initialize the orchestrator with required services.
        
        Args:
            gemini_service: Gemini 3.0 Pro service instance
            nano_service: Nano Banana Pro service instance
            config: Optional configuration
        """
        self.gemini = gemini_service
        self.nano = nano_service
        self.config = config or OrchestratorConfig()
        
        self._active_workflows: dict[str, WorkflowStatus] = {}
        self._workflow_history: list[dict[str, Any]] = []
        self._total_workflows = 0
        self._successful_workflows = 0
        self._failed_workflows = 0

    def _create_workflow_id(self) -> str:
        """Generate a unique workflow ID."""
        import uuid
        return f"wf-{uuid.uuid4().hex[:12]}"

    def _update_workflow_status(
        self,
        workflow_id: str,
        step: WorkflowStep,
        progress: float,
        message: str,
        started_at: datetime
    ):
        """Update the status of an active workflow."""
        if self.config.enable_step_tracking:
            self._active_workflows[workflow_id] = {
                "step": step.value,
                "progress": progress,
                "message": message,
                "started_at": started_at.isoformat(),
                "elapsed_ms": int((datetime.now() - started_at).total_seconds() * 1000)
            }

    async def snap_and_explain_workflow(
        self,
        image: bytes,
        annotations: list[dict[str, Any]],
        student_question: Optional[str] = None,
        preferred_style: Optional[str] = None
    ) -> SnapAndExplainResult:
        """
        Execute the complete snap-and-explain workflow.
        
        This method orchestrates the full educational explanation pipeline:
        1. Analyze the annotated image to identify confusion
        2. Generate a tailored Nano Banana Pro prompt
        3. Create the educational diagram
        4. Generate verbal explanation referencing the diagram
        
        Args:
            image: Original image bytes from student
            annotations: List of annotation objects (circles, arrows, text)
            student_question: Optional explicit question from student
            preferred_style: Optional style preference for the diagram
            
        Returns:
            SnapAndExplainResult containing all generated content and metadata
            
        Raises:
            AnalysisError: If analysis fails and no fallback is possible
        """
        workflow_id = self._create_workflow_id()
        started_at = datetime.now()
        metrics = WorkflowMetrics()
        workflow_steps: list[dict[str, Any]] = []
        
        logger.info(
            f"Starting snap-and-explain workflow",
            extra={
                "workflow_id": workflow_id,
                "annotation_count": len(annotations),
                "has_question": bool(student_question)
            }
        )
        
        self._total_workflows += 1
        
        try:
            # ==================== STEP 1: Analysis ====================
            self._update_workflow_status(
                workflow_id, WorkflowStep.ANALYSIS, 0.1,
                "Analyzing your image and annotations...", started_at
            )
            
            step_start = time.time()
            analysis = await self.gemini.analyze_annotated_image(
                image=image,
                annotations=annotations,
                student_question=student_question
            )
            metrics.analysis_time_ms = int((time.time() - step_start) * 1000)
            
            workflow_steps.append({
                "step": "analysis",
                "status": "completed",
                "duration_ms": metrics.analysis_time_ms,
                "result": {
                    "confusion_concept": analysis.get("confusion_concept"),
                    "subject": analysis.get("subject"),
                    "difficulty": analysis.get("difficulty_level")
                }
            })
            
            logger.info(
                f"Analysis complete",
                extra={
                    "workflow_id": workflow_id,
                    "confusion_concept": analysis.get("confusion_concept"),
                    "analysis_time_ms": metrics.analysis_time_ms
                }
            )
            
            # Check cache for existing explanation
            if self.config.enable_caching:
                cached = await explanation_cache.get_explanation(
                    concept=analysis.get("confusion_concept", ""),
                    subject=analysis.get("subject", "general"),
                    difficulty=analysis.get("difficulty_level", "intermediate"),
                    style=preferred_style or analysis.get("suggested_explanation_type", "educational")
                )
                if cached:
                    logger.info(f"Cache hit for explanation", extra={"workflow_id": workflow_id})
                    metrics.cache_hits += 1
                    self._successful_workflows += 1
                    
                    return SnapAndExplainResult(
                        generated_image_url=cached.get("generated_image_url", ""),
                        generated_image_bytes=cached.get("generated_image_bytes", b""),
                        explanation=cached.get("explanation", ""),
                        confusion_analysis=analysis,
                        prompt_used=cached.get("prompt_used", ""),
                        generation_time_ms=0,
                        workflow_steps=workflow_steps
                    )
            
            # ==================== STEP 2: Prompt Generation ====================
            self._update_workflow_status(
                workflow_id, WorkflowStep.PROMPT_GENERATION, 0.3,
                "Creating a custom explanation approach...", started_at
            )
            
            step_start = time.time()
            style = preferred_style or analysis.get("suggested_explanation_type", "educational")
            
            nano_prompt = await self.gemini.generate_nanobananapro_prompt(
                analysis=analysis,
                style=style,
                use_cache=self.config.enable_caching
            )
            metrics.prompt_generation_time_ms = int((time.time() - step_start) * 1000)
            
            workflow_steps.append({
                "step": "prompt_generation",
                "status": "completed",
                "duration_ms": metrics.prompt_generation_time_ms,
                "result": {"prompt_length": len(nano_prompt), "style": style}
            })
            
            logger.info(
                f"Prompt generated",
                extra={
                    "workflow_id": workflow_id,
                    "prompt_length": len(nano_prompt),
                    "prompt_generation_time_ms": metrics.prompt_generation_time_ms
                }
            )
            
            # ==================== STEP 3: Image Generation ====================
            self._update_workflow_status(
                workflow_id, WorkflowStep.IMAGE_GENERATION, 0.5,
                "Generating your visual explanation...", started_at
            )
            
            step_start = time.time()
            generated_image_url = ""
            generated_image_bytes = b""
            
            try:
                image_result = await self.nano.generate_explanation_image(
                    prompt=nano_prompt,
                    style=style,
                    reference_images=[image] if image else None
                )
                
                generated_image_url = image_result.get("image_url", "")
                generated_image_bytes = image_result.get("image_bytes", b"")
                metrics.image_generation_time_ms = int((time.time() - step_start) * 1000)
                
                workflow_steps.append({
                    "step": "image_generation",
                    "status": "completed",
                    "duration_ms": metrics.image_generation_time_ms,
                    "result": {
                        "has_image": bool(generated_image_bytes),
                        "has_url": bool(generated_image_url)
                    }
                })
                
                logger.info(
                    f"Image generated",
                    extra={
                        "workflow_id": workflow_id,
                        "has_image_bytes": bool(generated_image_bytes),
                        "image_generation_time_ms": metrics.image_generation_time_ms
                    }
                )
                
            except NanoBananaProError as e:
                logger.error(
                    f"Image generation failed",
                    extra={"workflow_id": workflow_id, "error": str(e)}
                )
                
                workflow_steps.append({
                    "step": "image_generation",
                    "status": "failed",
                    "error": str(e)
                })
                
                if not self.config.enable_fallbacks:
                    raise
            
            # ==================== STEP 4: Explanation ====================
            self._update_workflow_status(
                workflow_id, WorkflowStep.EXPLANATION, 0.8,
                "Creating your personalized explanation...", started_at
            )
            
            step_start = time.time()
            
            if generated_image_bytes:
                explanation = await self.gemini.explain_generated_image(
                    original_image=image,
                    generated_image=generated_image_bytes,
                    analysis=analysis
                )
            else:
                # Text-only fallback explanation
                explanation = await self._generate_fallback_explanation(analysis)
            
            metrics.explanation_time_ms = int((time.time() - step_start) * 1000)
            
            workflow_steps.append({
                "step": "explanation",
                "status": "completed",
                "duration_ms": metrics.explanation_time_ms,
                "result": {"explanation_length": len(explanation)}
            })
            
            # ==================== Workflow Complete ====================
            metrics.total_time_ms = int((datetime.now() - started_at).total_seconds() * 1000)
            
            self._update_workflow_status(
                workflow_id, WorkflowStep.COMPLETED, 1.0,
                "Explanation ready!", started_at
            )
            
            # Cache the result
            if self.config.enable_caching and generated_image_url:
                await explanation_cache.store_explanation(
                    concept=analysis.get("confusion_concept", ""),
                    subject=analysis.get("subject", "general"),
                    explanation={
                        "generated_image_url": generated_image_url,
                        "explanation": explanation,
                        "prompt_used": nano_prompt
                    },
                    difficulty=analysis.get("difficulty_level", "intermediate"),
                    style=style
                )
            
            self._successful_workflows += 1
            
            # Clean up active workflow
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
            
            logger.info(
                f"Snap-and-explain workflow completed",
                extra={
                    "workflow_id": workflow_id,
                    "total_time_ms": metrics.total_time_ms,
                    "metrics": {
                        "analysis_ms": metrics.analysis_time_ms,
                        "prompt_ms": metrics.prompt_generation_time_ms,
                        "image_ms": metrics.image_generation_time_ms,
                        "explanation_ms": metrics.explanation_time_ms
                    }
                }
            )
            
            return SnapAndExplainResult(
                generated_image_url=generated_image_url,
                generated_image_bytes=generated_image_bytes,
                explanation=explanation,
                confusion_analysis=analysis,
                prompt_used=nano_prompt,
                generation_time_ms=metrics.total_time_ms,
                workflow_steps=workflow_steps
            )
            
        except Exception as e:
            self._failed_workflows += 1
            
            self._update_workflow_status(
                workflow_id, WorkflowStep.FAILED, 0,
                f"Error: {str(e)[:100]}", started_at
            )
            
            logger.error(
                f"Snap-and-explain workflow failed",
                extra={"workflow_id": workflow_id, "error": str(e)},
                exc_info=True
            )
            
            # Clean up active workflow
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
            
            raise AnalysisError(
                message=f"Workflow failed: {str(e)}",
                details={"workflow_id": workflow_id, "steps_completed": len(workflow_steps)}
            )

    async def live_lens_workflow(
        self,
        video_frame: bytes,
        audio_transcript: str,
        context: list[dict[str, Any]],
        force_generation: bool = False
    ) -> LiveLensResult:
        """
        Execute the live lens workflow for real-time assistance.
        
        This method handles the continuous analysis and on-demand
        generation for live video streaming sessions.
        
        Args:
            video_frame: Current video frame bytes
            audio_transcript: Transcribed audio from student
            context: Conversation history
            force_generation: Force diagram generation regardless of analysis
            
        Returns:
            LiveLensResult containing analysis and any generated content
        """
        logger.info(
            "Starting live lens workflow",
            extra={
                "has_transcript": bool(audio_transcript),
                "context_length": len(context),
                "force_generation": force_generation
            }
        )
        
        # Analyze the current frame with context
        frame_analysis = await self.gemini.analyze_video_frame(
            frame=video_frame,
            context=context,
            transcript=audio_transcript
        )
        
        result = LiveLensResult(
            generated_image_url="",
            explanation="",
            concept="",
            audio_url="",
            frame_analysis=frame_analysis,
            triggered_generation=False
        )
        
        # Determine if we should generate a visual explanation
        should_generate = force_generation or (
            frame_analysis.get("suggested_action") == "generate_diagram" or
            frame_analysis.get("potential_confusion") is not None
        )
        
        if should_generate:
            logger.info("Triggering visual explanation generation in live mode")
            result["triggered_generation"] = True
            
            # Create analysis-like dict for the generation pipeline
            confusion_concept = (
                frame_analysis.get("potential_confusion") or
                (frame_analysis.get("visible_concepts", []) or ["the concept"])[0]
            )
            
            analysis: ConfusionAnalysis = {
                "confusion_concept": confusion_concept,
                "difficulty_level": "intermediate",
                "suggested_explanation_type": "schematic",
                "subject": self._detect_subject(frame_analysis.get("visible_concepts", [])),
                "subtopic": confusion_concept,
                "key_elements": frame_analysis.get("visible_concepts", []),
                "reasoning": f"Live mode detection: {frame_analysis.get('potential_confusion', 'Student request')}"
            }
            
            # Generate the prompt
            nano_prompt = await self.gemini.generate_nanobananapro_prompt(
                analysis=analysis,
                style="educational"
            )
            
            # Generate the image
            try:
                image_result = await self.nano.generate_explanation_image(
                    prompt=nano_prompt,
                    style="educational",
                    reference_images=[video_frame]
                )
                
                result["generated_image_url"] = image_result.get("image_url", "")
                result["concept"] = confusion_concept
                
                # Generate explanation for the image
                if image_result.get("image_bytes"):
                    explanation = await self.gemini.explain_generated_image(
                        original_image=video_frame,
                        generated_image=image_result["image_bytes"],
                        analysis=analysis
                    )
                    result["explanation"] = explanation
                else:
                    result["explanation"] = (
                        f"I've created a diagram to help explain {confusion_concept}. "
                        "Take a look at the visual I generated."
                    )
                    
            except NanoBananaProError as e:
                logger.error(f"Live lens image generation failed: {e}")
                result["explanation"] = (
                    f"I noticed you might be confused about {confusion_concept}. "
                    f"Let me explain: {await self._generate_fallback_explanation(analysis)}"
                )
        else:
            # Just provide contextual feedback
            visible = frame_analysis.get("visible_concepts", [])
            
            if frame_analysis.get("suggested_action") == "explain":
                # Provide a brief explanation without image
                if visible:
                    result["explanation"] = await self._generate_quick_explanation(visible)
                else:
                    result["explanation"] = "I'm here to help! Circle anything confusing or ask me a question."
            elif visible:
                result["explanation"] = (
                    f"I can see you're studying {', '.join(visible[:3])}. "
                    "Let me know if you have any questions!"
                )
            else:
                result["explanation"] = (
                    "I'm watching along. Ask me anything or circle something you find confusing!"
                )
        
        logger.info(
            "Live lens workflow completed",
            extra={
                "triggered_generation": result["triggered_generation"],
                "has_image": bool(result["generated_image_url"])
            }
        )
        
        return result

    async def generate_step_by_step(
        self,
        concept: str,
        subject: str,
        difficulty: str = "intermediate"
    ) -> dict[str, Any]:
        """
        Generate a complete step-by-step explanation with visuals.
        
        Args:
            concept: The concept to explain
            subject: Subject area
            difficulty: Student difficulty level
            
        Returns:
            Dictionary containing steps with explanations and images
        """
        logger.info(f"Generating step-by-step explanation for: {concept}")
        
        # First, generate the step breakdown
        steps = await self.gemini.generate_step_by_step_explanation(
            concept=concept,
            subject=subject,
            difficulty=difficulty
        )
        
        # Generate an overview image
        step_descriptions = [step.get("title", "") for step in steps]
        
        overview_image = await self.nano.generate_step_by_step_image(
            concept=concept,
            steps=step_descriptions,
            style="educational"
        )
        
        return {
            "concept": concept,
            "subject": subject,
            "difficulty": difficulty,
            "steps": steps,
            "overview_image_url": overview_image.get("image_url", ""),
            "total_steps": len(steps)
        }

    async def generate_with_analogy(
        self,
        concept: str,
        subject: str
    ) -> dict[str, Any]:
        """
        Generate an explanation using relatable analogies.
        
        Args:
            concept: The concept to explain
            subject: Subject area
            
        Returns:
            Dictionary containing analogies with visual representations
        """
        logger.info(f"Generating analogy-based explanation for: {concept}")
        
        # Generate analogies
        analogies = await self.gemini.generate_analogies(
            concept=concept,
            subject=subject,
            count=3
        )
        
        # Generate an image for the best analogy
        if analogies:
            best_analogy = analogies[0]
            analogy_image = await self.nano.generate_analogy_image(
                concept=concept,
                analogy=best_analogy.get("analogy", ""),
                mapping=best_analogy.get("mapping", {}),
                style="cartoon"
            )
            
            return {
                "concept": concept,
                "subject": subject,
                "analogies": analogies,
                "featured_analogy": best_analogy,
                "analogy_image_url": analogy_image.get("image_url", "")
            }
        
        return {
            "concept": concept,
            "subject": subject,
            "analogies": [],
            "featured_analogy": None,
            "analogy_image_url": ""
        }

    async def _generate_fallback_explanation(
        self,
        analysis: ConfusionAnalysis
    ) -> str:
        """Generate a text-only fallback explanation when image generation fails."""
        concept = analysis.get("confusion_concept", "this concept")
        subject = analysis.get("subject", "this subject")
        difficulty = analysis.get("difficulty_level", "intermediate")
        
        # Generate a step-by-step text explanation
        steps = await self.gemini.generate_step_by_step_explanation(
            concept=concept,
            subject=subject,
            difficulty=difficulty,
            max_steps=4
        )
        
        if steps:
            step_text = "\n".join([
                f"**{step.get('title', f'Step {i+1}')}**: {step.get('explanation', '')}"
                for i, step in enumerate(steps)
            ])
            
            return f"""
Let me explain {concept} step by step:

{step_text}

Would you like me to try generating a visual diagram, or should I explain any specific part in more detail?
"""
        
        return f"""
Let me explain {concept} for you.

{concept} is a fundamental concept in {subject}. Here's a breakdown:

1. **What it is**: {concept} refers to a key principle that helps us understand how things work in {subject}.

2. **Why it matters**: Understanding {concept} is important because it forms the foundation for more advanced topics.

3. **How to think about it**: Try to visualize {concept} as a process or relationship between elements.

Would you like me to try generating a visual diagram, or should I explain any specific part in more detail?
"""

    async def _generate_quick_explanation(
        self,
        concepts: list[str]
    ) -> str:
        """Generate a quick explanation for visible concepts."""
        if not concepts:
            return "I'm here to help! What would you like me to explain?"
        
        concepts_text = ", ".join(concepts[:5])
        
        return (
            f"I can see you're looking at content related to {concepts_text}. "
            "Would you like me to explain any of these concepts, or generate a visual diagram?"
        )

    def _detect_subject(self, concepts: list[str]) -> str:
        """Detect the subject area from visible concepts."""
        subject_keywords = {
            "math": ["equation", "formula", "graph", "algebra", "geometry", "calculus", 
                    "number", "function", "variable", "derivative", "integral"],
            "physics": ["force", "motion", "energy", "wave", "circuit", "gravity", 
                       "acceleration", "velocity", "momentum", "electricity", "magnetism"],
            "chemistry": ["atom", "molecule", "reaction", "element", "compound", "bond", 
                         "periodic", "ion", "acid", "base", "oxidation"],
            "biology": ["cell", "dna", "organism", "evolution", "photosynthesis", 
                       "genetics", "anatomy", "protein", "enzyme", "bacteria"],
            "history": ["war", "civilization", "empire", "revolution", "century", 
                       "era", "ancient", "medieval", "colony", "democracy"],
            "geography": ["map", "climate", "continent", "ocean", "mountain", 
                         "river", "population", "region", "latitude", "longitude"]
        }
        
        concept_text = " ".join(concepts).lower()
        
        # Count matches for each subject
        scores = {}
        for subject, keywords in subject_keywords.items():
            score = sum(1 for kw in keywords if kw in concept_text)
            if score > 0:
                scores[subject] = score
        
        if scores:
            return max(scores, key=scores.get)
        
        return "general"

    async def batch_explain(
        self,
        items: list[dict[str, Any]],
        max_concurrent: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """
        Process multiple explanation requests in batch.
        
        Args:
            items: List of dicts with 'image' and 'annotations' keys
            max_concurrent: Maximum concurrent workflows (defaults to config)
            
        Returns:
            List of explanation results or error dicts
        """
        max_concurrent = max_concurrent or self.config.max_concurrent_tasks
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_item(item: dict) -> dict:
            async with semaphore:
                try:
                    result = await self.snap_and_explain_workflow(
                        image=item.get("image", b""),
                        annotations=item.get("annotations", []),
                        student_question=item.get("question")
                    )
                    return {"success": True, "result": result}
                except Exception as e:
                    return {"success": False, "error": str(e)}
        
        results = await asyncio.gather(
            *[process_item(item) for item in items],
            return_exceptions=True
        )
        
        return [
            r if isinstance(r, dict) else {"success": False, "error": str(r)}
            for r in results
        ]

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Get the current status of an active workflow."""
        return self._active_workflows.get(workflow_id)

    def get_active_workflows(self) -> dict[str, WorkflowStatus]:
        """Get all active workflows."""
        return self._active_workflows.copy()

    def get_stats(self) -> dict[str, Any]:
        """Get orchestrator statistics."""
        success_rate = (
            self._successful_workflows / self._total_workflows
            if self._total_workflows > 0 else 0
        )
        
        return {
            "total_workflows": self._total_workflows,
            "successful_workflows": self._successful_workflows,
            "failed_workflows": self._failed_workflows,
            "success_rate": success_rate,
            "active_workflows": len(self._active_workflows),
            "config": {
                "caching_enabled": self.config.enable_caching,
                "fallbacks_enabled": self.config.enable_fallbacks,
                "max_concurrent": self.config.max_concurrent_tasks
            }
        }

    async def close(self):
        """Close all service connections."""
        await self.gemini.close()
        await self.nano.close()
        logger.info("Orchestrator services closed")
