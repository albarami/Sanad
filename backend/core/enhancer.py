"""
Response Enhancement Module for Sanad v2.
Enhances draft answers when Sanad score falls below threshold using LLM and agent feedback.
"""

import asyncio
import random
import re
import time
from typing import Dict, List, Optional, Pattern
from loguru import logger

# Optional Prometheus metrics (graceful degradation if not available)
try:
    from prometheus_client import Counter, Histogram
    ENHANCEMENT_ATTEMPTS = Counter('sanad_enhancement_attempts_total', 'Total enhancement attempts', ['status'])
    ENHANCEMENT_DURATION = Histogram('sanad_enhancement_duration_seconds', 'Enhancement processing time')
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.warning("Prometheus metrics not available - install prometheus_client for production monitoring")

from core.config import get_config, Config
from agents.base import AgentScore, Passage
from core.baseline_llm import BaselineLLM
from pydantic import BaseModel, Field
from typing import Any


class EnhancementRequest(BaseModel):
    """Request for answer enhancement."""
    question: str
    draft_answer: str
    passages: List[Passage]
    agent_scores: Dict[str, AgentScore]
    sanad_score: float = Field(ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EnhancementResponse(BaseModel):
    """Response from answer enhancement."""
    enhanced_answer: str
    enhancement_applied: bool
    processing_time_ms: int
    enhancement_reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    sources_used: List[str] = Field(default_factory=list)


class ResponseEnhancer:
    """
    Enhances draft answers using LLM when Sanad score is below threshold.
    
    This class implements the enhancement logic that was previously embedded
    in the orchestrator, providing a cleaner separation of concerns.
    """
    
    def __init__(self, config: Optional[Config] = None, llm: Optional[BaselineLLM] = None):
        """Initialize the ResponseEnhancer with configuration and LLM.
        
        Args:
            config: Optional config injection to avoid per-call YAML parsing
            llm: Optional LLM client injection for testing/mocking
        """
        self.config = config or get_config()
        self.enhancement_threshold = self.config.thresholds.enhancement_threshold
        self.baseline_llm = llm or BaselineLLM()
        
        # Compile regex patterns for domain keywords (performance optimization)
        self._compiled_keywords: List[Pattern] = []
        if self.config.domain.keywords:
            self._compiled_keywords = [
                re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                for keyword in self.config.domain.keywords
            ]
        
        logger.info(f"Initialized ResponseEnhancer with threshold: {self.enhancement_threshold}")
    
    def reload_config(self, config: Optional[Config] = None) -> None:
        """Reload configuration and recompile regex patterns.
        
        Args:
            config: Optional new config, otherwise reloads from file
        """
        self.config = config or get_config()
        self.enhancement_threshold = self.config.thresholds.enhancement_threshold
        
        # Recompile regex patterns for domain keywords
        self._compiled_keywords = []
        if self.config.domain.keywords:
            self._compiled_keywords = [
                re.compile(rf"\b{re.escape(keyword)}\b", re.IGNORECASE)
                for keyword in self.config.domain.keywords
            ]
        
        logger.info(f"Reloaded ResponseEnhancer config with {len(self._compiled_keywords)} keywords")
    
    async def enhance(self, request: EnhancementRequest) -> EnhancementResponse:
        """
        Enhance the draft answer if needed based on Sanad score and agent feedback.
        
        Args:
            request: Enhancement request with context
            
        Returns:
            Enhanced response with metadata
        """
        start_time = time.time()
        
        # Track enhancement attempts
        if METRICS_AVAILABLE:
            timer = ENHANCEMENT_DURATION.time()
        
        try:
            # Check if enhancement is needed
            if not self._should_enhance(request):
                logger.info(f"Enhancement not needed - Sanad score {request.sanad_score:.3f} >= threshold {self.enhancement_threshold}")
                if METRICS_AVAILABLE:
                    ENHANCEMENT_ATTEMPTS.labels(status="skipped").inc()
                return EnhancementResponse(
                    enhanced_answer=request.draft_answer,
                    enhancement_applied=False,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    enhancement_reason="Score above threshold",
                    confidence=request.sanad_score,
                    sources_used=[]
                )
            
            # Perform enhancement
            logger.info(f"Enhancing answer - Sanad score {request.sanad_score:.3f} < threshold {self.enhancement_threshold}")
            enhanced_answer, enhancement_success = await self._perform_enhancement(request)
            
            # Extract sources used
            sources_used = [passage.doc_id for passage in request.passages[:5]]
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Track successful enhancement
            if METRICS_AVAILABLE:
                status = "success" if enhancement_success else "failed"
                ENHANCEMENT_ATTEMPTS.labels(status=status).inc()
            
            return EnhancementResponse(
                enhanced_answer=enhanced_answer,
                enhancement_applied=enhancement_success,
                processing_time_ms=processing_time,
                enhancement_reason=f"Sanad score {request.sanad_score:.3f} below threshold" if enhancement_success else "Enhancement failed",
                confidence=min(request.sanad_score + 0.1, 1.0) if enhancement_success else request.sanad_score,
                sources_used=sources_used if enhancement_success else []
            )
            
        except Exception as e:
            logger.error(f"Enhancement failed: {str(e)}")
            processing_time = int((time.time() - start_time) * 1000)
            
            # Track exception
            if METRICS_AVAILABLE:
                ENHANCEMENT_ATTEMPTS.labels(status="error").inc()
            
            return EnhancementResponse(
                enhanced_answer=request.draft_answer,
                enhancement_applied=False,
                processing_time_ms=processing_time,
                enhancement_reason=f"Enhancement failed: {str(e)}",
                confidence=request.sanad_score,
                sources_used=[]
            )
        finally:
            # Record timing
            if METRICS_AVAILABLE:
                timer.stop()
    
    def _should_enhance(self, request: EnhancementRequest) -> bool:
        """
        Determine if enhancement should be applied based on score and context.
        
        Args:
            request: Enhancement request
            
        Returns:
            True if enhancement should be applied
        """
        # Primary criterion: Sanad score below threshold
        if request.sanad_score >= self.enhancement_threshold:
            return False
        
        # Additional criteria for enhancement
        enhancement_needed = True
        
        # Check if we have sufficient passages for enhancement
        if not request.passages or len(request.passages) < 2:
            logger.warning("Insufficient passages for meaningful enhancement")
            enhancement_needed = False
        
        # Check if agent scores indicate specific issues (case-insensitive, safe)
        low_precision = any(
            score.agent_name.lower() == "precision" and score.score < 0.6
            for score in request.agent_scores.values()
            if hasattr(score, 'agent_name') and score.agent_name
        )
        
        low_provenance = any(
            score.agent_name.lower() == "provenance" and score.score < 0.5
            for score in request.agent_scores.values()
            if hasattr(score, 'agent_name') and score.agent_name
        )
        
        # Prioritize enhancement for precision and provenance issues
        if low_precision or low_provenance:
            logger.info("Enhancement prioritized due to precision/provenance issues")
            enhancement_needed = True
        
        return enhancement_needed
    
    async def _perform_enhancement(self, request: EnhancementRequest) -> tuple[str, bool]:
        """
        Perform the actual enhancement using the baseline LLM.
        
        Args:
            request: Enhancement request with context
            
        Returns:
            Tuple of (enhanced_answer, success_flag)
        """
        # Build enhancement prompt
        enhancement_prompt = self._build_enhancement_prompt(request)
        
        # Call LLM for enhancement with timeout and retry
        logger.info("Calling LLM for answer enhancement")
        
        max_retries = self.config.thresholds.max_retries
        base_delay = self.config.thresholds.base_delay
        
        for attempt in range(max_retries):
            try:
                enhanced_response = await asyncio.wait_for(
                    self.baseline_llm.draft(enhancement_prompt),
                    timeout=self.config.llm.openai.timeout
                )
                
                return enhanced_response.answer, True
                
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    logger.error("LLM enhancement timed out after retries")
                    return request.draft_answer, False
                else:
                    # Add jitter to prevent thundering herd under load
                    delay = base_delay * (2 ** attempt) * (1 + random.uniform(-0.2, 0.2))
                    logger.warning(f"LLM timeout, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"LLM enhancement failed after retries: {str(e)}")
                    return request.draft_answer, False
                else:
                    # Add jitter to prevent thundering herd under load
                    delay = base_delay * (2 ** attempt) * (1 + random.uniform(-0.2, 0.2))
                    logger.warning(f"LLM error: {str(e)}, retrying in {delay:.2f}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
        
        return request.draft_answer, False
    
    def _build_enhancement_prompt(self, request: EnhancementRequest) -> str:
        """
        Build the enhancement prompt for the LLM based on agent feedback.
        
        Args:
            request: Enhancement request with context
            
        Returns:
            Enhanced prompt string
        """
        # Build context from passages with token budgeting
        context_passages = "\n\n".join([
            f"Passage {i+1} (from {passage.doc_id}):\n{self._truncate_passage(passage.text)}"
            for i, passage in enumerate(request.passages[:5])
        ])
        
        # Build agent feedback with specific guidance
        agent_feedback = []
        for score in request.agent_scores.values():
            if score.explanation:
                agent_feedback.append(f"- {score.agent_name.title()}: {score.explanation}")
        
        agent_feedback_text = "\n".join(agent_feedback) if agent_feedback else "No specific agent feedback available."
        
        # Determine enhancement focus based on lowest scoring agents
        lowest_agents = sorted(
            request.agent_scores.values(),
            key=lambda x: x.score
        )[:2]
        
        focus_areas = []
        for agent_score in lowest_agents:
            if agent_score.agent_name.lower() == "precision":
                focus_areas.append("factual accuracy and specificity")
            elif agent_score.agent_name.lower() == "provenance":
                focus_areas.append("source citations and attribution")
            elif agent_score.agent_name.lower() == "domain":
                focus_areas.append("domain-specific terminology and context")
            elif agent_score.agent_name.lower() == "integrity":
                focus_areas.append("logical consistency and completeness")
        
        focus_text = ", ".join(focus_areas) if focus_areas else "overall quality"
        
        # Add domain-specific instructions if this is a domain-relevant query
        domain_instructions = ""
        if (self.config.domain.enhancement_instructions and 
            self.config.domain.enhancement_instructions.strip() and 
            self._is_domain_relevant(request.question)):
            domain_instructions = f"\n{self.config.domain.enhancement_instructions.strip()}"
        
        prompt = f"""Using only the provided passages below, improve this answer based on the agent feedback.

QUESTION: {request.question}

PASSAGES:
{context_passages}

ORIGINAL ANSWER:
{request.draft_answer}

AGENT FEEDBACK:
{agent_feedback_text}

ENHANCEMENT FOCUS: Pay special attention to {focus_text}

IMPROVEMENT GUIDELINES:
1. Address the specific issues mentioned in the agent feedback
2. Use information from the passages to strengthen weak areas
3. Maintain accuracy - only use information explicitly provided in the passages
4. Keep the same general structure and tone
5. Limit response to 250 tokens maximum{domain_instructions}

If the passages don't provide sufficient information to improve the answer, acknowledge this limitation clearly.

IMPROVED ANSWER:"""
        
        return prompt
    
    def _is_domain_relevant(self, question: str) -> bool:
        """
        Check if question contains domain-specific keywords using compiled regex patterns.
        
        Args:
            question: User question to check
            
        Returns:
            True if question is domain-relevant
        """
        # Check current config keywords (handles dynamic changes in tests)
        if not self.config.domain.keywords:
            return False
        
        # Use compiled patterns if available, otherwise fall back to simple matching
        if self._compiled_keywords and len(self._compiled_keywords) == len(self.config.domain.keywords):
            return any(pattern.search(question) for pattern in self._compiled_keywords)
        else:
            # Fallback for dynamic keyword changes (mainly for tests)
            return any(
                re.search(rf"\b{re.escape(keyword)}\b", question, re.IGNORECASE)
                for keyword in self.config.domain.keywords
            )
    
    def _truncate_passage(self, text: str, max_chars: int = 512) -> str:
        """
        Truncate passage text to prevent token limit issues.
        
        Args:
            text: Original passage text
            max_chars: Maximum characters to keep
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rsplit(' ', 1)[0] + "..."
    
    def get_enhancement_stats(self) -> Dict[str, Any]:
        """
        Get statistics about enhancement usage.
        
        Returns:
            Dictionary with enhancement statistics
        """
        return {
            "enhancement_threshold": self.enhancement_threshold,
            "llm_provider": self.config.llm.primary_provider,
            "llm_model": self.config.llm.openai.model,
            "max_tokens": self.config.llm.openai.max_tokens,
            "timeout_seconds": self.config.llm.openai.timeout
        }


# Convenience function for direct usage
async def enhance_response(
    question: str,
    draft_answer: str,
    passages: List[Passage],
    agent_scores: Dict[str, AgentScore],
    sanad_score: float,
    metadata: Optional[Dict[str, Any]] = None
) -> EnhancementResponse:
    """
    Convenience function to enhance a response.
    
    Args:
        question: Original question
        draft_answer: Draft answer to enhance
        passages: Retrieved passages for context
        agent_scores: Scores from verification agents
        sanad_score: Composite Sanad score
        metadata: Additional metadata
        
    Returns:
        EnhancementResponse with enhanced answer
    """
    enhancer = ResponseEnhancer()
    request = EnhancementRequest(
        question=question,
        draft_answer=draft_answer,
        passages=passages,
        agent_scores=agent_scores,
        sanad_score=sanad_score,
        metadata=metadata or {}
    )
    
    return await enhancer.enhance(request)
