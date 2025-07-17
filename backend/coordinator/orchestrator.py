"""
Coordinator Service for Sanad v2.
Orchestrates agent execution, computes weighted scores, and triggers enhancement.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger

# Import base classes
try:
    from ..agents.base import BaseAgent, AgentInput, AgentScore, Passage
    from ..core.config import get_config
    from ..core.baseline_llm import BaselineLLM, LLMResponse
    from ..core.enhancer import ResponseEnhancer, EnhancementRequest
    from ..db.database import db_manager
    from ..db.repository import QueryRepository, AuditRepository
    from ..db.models import QueryLogCreate, AuditLogCreate
except ImportError:
    from agents.base import BaseAgent, AgentInput, AgentScore, Passage
    from core.config import get_config
    from core.baseline_llm import BaselineLLM, LLMResponse
    from core.enhancer import ResponseEnhancer, EnhancementRequest
    from db.database import db_manager
    from db.repository import QueryRepository, AuditRepository
    from db.models import QueryLogCreate, AuditLogCreate


class VerificationResponse(BaseModel):
    """Response from the verification process."""
    answer: str
    sanad_score: float = Field(ge=0.0, le=1.0)
    sources: List[Passage]
    processing_time_ms: int
    
    # Islamic methodology fields (optional for backward compatibility)
    grade: Optional[str] = None
    certainty: Optional[float] = None
    consensus_level: Optional[int] = None
    scholarly_justification: Optional[str] = None
    conditional_assessments: Optional[List[str]] = None


class CoordinatorInput(BaseModel):
    """Input for the coordinator."""
    question: str
    draft_answer: str
    passages: List[Passage]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SanadCoordinator:
    """
    Main coordinator that orchestrates the Sanad verification process.
    Manages agent execution, score computation, and answer enhancement.
    """
    
    def __init__(self):
        """Initialize the coordinator with configuration and services."""
        self.config = get_config()
        self.baseline_llm = BaselineLLM()
        self.agents: Dict[str, BaseAgent] = {}
        self.enhancer = ResponseEnhancer()
        
        logger.info("Initialized SanadCoordinator with ResponseEnhancer")
    
    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the coordinator.
        
        Args:
            agent: The agent to register
        """
        agent_name = agent.name.lower().replace("agent", "")
        self.agents[agent_name] = agent
        logger.info(f"Registered agent: {agent_name}")
    
    async def verify(self, input_data: CoordinatorInput, user_id: Optional[int] = None, session_id: Optional[str] = None, ip_address: Optional[str] = None) -> VerificationResponse:
        """
        Execute the complete Sanad verification process with enterprise logging.
        
        Args:
            input_data: Input containing question, draft answer, and passages
            user_id: User ID for audit trail (optional)
            session_id: Session ID for tracking (optional)
            ip_address: User IP address for audit (optional)
            
        Returns:
            VerificationResponse with verified answer and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Execute agents in parallel
            agent_scores = await self._execute_agents(input_data)
            
            # Step 2: Compute weighted Sanad score
            sanad_score = self._compute_sanad_score(agent_scores)
            
            # Step 3: Determine if enhancement is needed
            enhancement_threshold = self.config.thresholds.enhancement_threshold
            final_answer = input_data.draft_answer
            enhanced = False
            
            if sanad_score < enhancement_threshold:
                logger.info(f"Score {sanad_score:.3f} below threshold {enhancement_threshold}, enhancing answer")
                final_answer = await self._enhance_answer(input_data, agent_scores, sanad_score)
                enhanced = True
            else:
                logger.info(f"Score {sanad_score:.3f} above threshold, using draft answer")
            
            # Step 4: Build response
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            response = VerificationResponse(
                answer=final_answer,
                sanad_score=sanad_score,
                sources=input_data.passages,
                processing_time_ms=processing_time_ms
            )
            
            # Step 5: Log to database for enterprise audit trail
            await self._log_verification(
                input_data=input_data,
                response=response,
                agent_scores=agent_scores,
                enhanced=enhanced,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error in verification process: {str(e)}")
            # Return graceful fallback
            processing_time_ms = int((time.time() - start_time) * 1000)
            return VerificationResponse(
                answer=input_data.draft_answer,
                sanad_score=0.3,  # Low score to indicate issue
                sources=input_data.passages,
                processing_time_ms=processing_time_ms
            )
    
    async def _execute_agents(self, input_data: CoordinatorInput) -> Dict[str, AgentScore]:
        """
        Execute all registered agents in parallel.
        
        Args:
            input_data: Input data for agents
            
        Returns:
            Dictionary mapping agent names to their scores
        """
        if not self.agents:
            logger.warning("No agents registered, returning empty scores")
            return {}
        
        # Prepare agent input
        agent_input = AgentInput(
            question=input_data.question,
            draft_answer=input_data.draft_answer,
            passages=input_data.passages,
            metadata=input_data.metadata
        )
        
        # Execute agents in parallel
        tasks = []
        for agent_name, agent in self.agents.items():
            task = asyncio.create_task(
                self._safe_agent_execution(agent_name, agent, agent_input)
            )
            tasks.append((agent_name, task))
        
        # Collect results
        agent_scores = {}
        for agent_name, task in tasks:
            try:
                score = await task
                if score:
                    agent_scores[agent_name] = score
                    logger.debug(f"Agent {agent_name}: score={score.score:.3f}")
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {str(e)}")
                # Create default score for failed agent
                agent_scores[agent_name] = AgentScore(
                    score=0.5,
                    explanation=f"Agent failed: {str(e)}",
                    confidence=0.0,
                    agent_name=agent_name
                )
        
        return agent_scores
    
    async def _safe_agent_execution(self, agent_name: str, agent: BaseAgent, input_data: AgentInput) -> Optional[AgentScore]:
        """
        Safely execute an agent with timeout and error handling.
        
        Args:
            agent_name: Name of the agent
            agent: The agent instance
            input_data: Input data for the agent
            
        Returns:
            AgentScore or None if failed
        """
        try:
            # Set timeout (850ms per agent as per latency budget)
            score = await asyncio.wait_for(
                agent.evaluate(input_data),
                timeout=0.85  # 850ms
            )
            return score
        except asyncio.TimeoutError:
            logger.warning(f"Agent {agent_name} timed out")
            return None
        except Exception as e:
            logger.error(f"Agent {agent_name} execution failed: {str(e)}")
            return None
    
    def _compute_sanad_score(self, agent_scores: Dict[str, AgentScore]) -> float:
        """
        Compute weighted Sanad score from agent scores.
        
        Args:
            agent_scores: Dictionary of agent scores
            
        Returns:
            Weighted composite score (0.0 to 1.0)
        """
        if not agent_scores:
            return 0.3  # Default low score when no agents executed
        
        # Get weights from configuration
        weights = self.config.agent_weights
        weight_mapping = {
            "integrity": weights.integrity,
            "precision": weights.precision,
            "provenance": weights.provenance,
            "domain": weights.domain
        }
        
        # Calculate weighted score
        total_score = 0.0
        total_weight = 0.0
        
        for agent_name, agent_score in agent_scores.items():
            if agent_name in weight_mapping:
                weight = weight_mapping[agent_name]
                total_score += agent_score.score * weight
                total_weight += weight
                logger.debug(f"Agent {agent_name}: score={agent_score.score:.3f}, weight={weight}")
        
        # Normalize by total weight (in case some agents failed)
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.3
        
        logger.info(f"Computed Sanad score: {final_score:.3f} (from {len(agent_scores)} agents)")
        return min(max(final_score, 0.0), 1.0)  # Clamp to [0, 1]
    
    async def _enhance_answer(self, input_data: CoordinatorInput, agent_scores: Dict[str, AgentScore], sanad_score: float) -> str:
        """
        Enhance the answer using the ResponseEnhancer module.
        
        Args:
            input_data: Original input data
            agent_scores: Scores from agents for context
            sanad_score: Computed Sanad score
            
        Returns:
            Enhanced answer
        """
        try:
            # Create enhancement request
            enhancement_request = EnhancementRequest(
                question=input_data.question,
                draft_answer=input_data.draft_answer,
                passages=input_data.passages,
                agent_scores=agent_scores,
                sanad_score=sanad_score,
                metadata=input_data.metadata
            )
            
            # Use the enhancer module
            logger.info("Using ResponseEnhancer for answer enhancement")
            enhancement_response = await self.enhancer.enhance(enhancement_request)
            
            return enhancement_response.enhanced_answer
            
        except Exception as e:
            logger.error(f"Enhancement failed: {str(e)}, using original answer")
            return input_data.draft_answer
    
    async def _log_verification(
        self,
        input_data: CoordinatorInput,
        response: VerificationResponse,
        agent_scores: Dict[str, AgentScore],
        enhanced: bool,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log verification request and response to database for enterprise audit trail.
        
        Args:
            input_data: Original input data
            response: Verification response
            agent_scores: Individual agent scores
            enhanced: Whether answer was enhanced
            user_id: User ID for audit trail
            session_id: Session ID for tracking
            ip_address: User IP address for audit
        """
        try:
            # Only log if user_id is provided (enterprise tracking)
            if not user_id:
                return
            
            session = db_manager.get_session()
            query_repo = QueryRepository(session)
            
            # Extract source IDs
            sources_used = [passage.doc_id for passage in input_data.passages] if input_data.passages else []
            
            # Convert agent scores to simple dict
            agent_scores_dict = {
                name: score.score for name, score in agent_scores.items()
            }
            
            # Create query log
            query_log_data = QueryLogCreate(
                user_id=user_id,
                session_id=session_id,
                question=input_data.question,
                category="verification",  # Could be determined by retriever
                answer=response.answer,
                sanad_score=response.sanad_score,
                trigger_used=True,  # Since we're in verification flow
                enhanced=enhanced,
                processing_time_ms=response.processing_time_ms,
                sources_used=sources_used,
                agent_scores=agent_scores_dict,
                ip_address=ip_address
            )
            
            query_log = query_repo.create_query_log(query_log_data)
            logger.info(f"Logged verification to database: query_id={query_log.id}")
            
            session.close()
            
        except Exception as e:
            logger.warning(f"Failed to log verification to database: {str(e)}")
            # Don't raise - logging failure shouldn't break verification
    
    async def _log_error(
        self,
        input_data: CoordinatorInput,
        error: str,
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """
        Log verification errors to audit trail.
        
        Args:
            input_data: Original input data
            error: Error message
            user_id: User ID for audit trail
            session_id: Session ID for tracking
            ip_address: User IP address for audit
        """
        try:
            session = db_manager.get_session()
            audit_repo = AuditRepository(session)
            
            audit_data = AuditLogCreate(
                user_id=user_id,
                event_type="verification_error",
                event_description=f"Verification failed: {error}",
                entity_type="verification",
                entity_id=session_id,
                ip_address=ip_address,
                session_id=session_id,
                severity="error"
            )
            
            audit_repo.create_audit_log(audit_data)
            logger.info(f"Logged verification error to audit trail")
            
            session.close()
            
        except Exception as e:
            logger.warning(f"Failed to log error to audit trail: {str(e)}")
            # Don't raise - audit logging failure shouldn't break error handling 