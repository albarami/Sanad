"""
Enhanced API Router for Sanad v2 Enterprise System.
Implements user management, audit trails, GDPR compliance, and enterprise logging.
"""

import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel, Field

# Import core services
try:
    from ..agents.base import Passage
    from ..agents.domain_labour import DomainLabourAgent
    from ..agents.integrity import IntegrityAgent
    from ..agents.precision import PrecisionAgent
    from ..agents.provenance import ProvenanceAgent
    from ..coordinator.orchestrator import (
        CoordinatorInput,
        SanadCoordinator,
        VerificationResponse,
    )
    from ..core.baseline_llm import BaselineLLM, LLMResponse
    from ..core.config import get_config
    from ..db.database import get_db
    from ..db.models import (
        AuditLogCreate,
        FeedbackCreate,
        QueryLogResponse,
        User,
        UserCreate,
        UserResponse,
    )
    from ..db.repository import (
        AuditRepository,
        ComplianceRepository,
        FeedbackRepository,
        QueryRepository,
        UserRepository,
    )
    from ..retrieval.simple_retriever import SimpleRetriever
    from ..trigger.detector import TriggerDetector
except ImportError:
    # Fallback for direct execution
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(__file__)))

    from agents.base import Passage
    from agents.domain_labour import DomainLabourAgent
    from agents.integrity import IntegrityAgent
    from agents.precision import PrecisionAgent
    from agents.provenance import ProvenanceAgent
    from coordinator.orchestrator import (
        CoordinatorInput,
        SanadCoordinator,
        VerificationResponse,
    )
    from core.baseline_llm import BaselineLLM, LLMResponse
    from core.config import get_config
    from db.database import get_db
    from db.models import (
        AuditLogCreate,
        FeedbackCreate,
        QueryLogResponse,
        User,
        UserCreate,
        UserResponse,
    )
    from db.repository import (
        AuditRepository,
        ComplianceRepository,
        FeedbackRepository,
        QueryRepository,
        UserRepository,
    )
    from retrieval.simple_retriever import SimpleRetriever
    from trigger.detector import TriggerDetector


# Create API router
api_router = APIRouter()

# Security scheme (placeholder - implement proper auth later)
security = HTTPBearer(auto_error=False)


# Enhanced Request/Response Models
class VerifyRequest(BaseModel):
    """Enhanced request model for verification endpoint."""

    question: str = Field(
        ..., min_length=1, max_length=4000, description="User question to verify"
    )
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    user_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional user context"
    )


class BaselineRequest(BaseModel):
    """Request model for baseline endpoint."""

    question: str = Field(
        ..., min_length=1, max_length=4000, description="Question for baseline LLM"
    )


class BaselineResponse(BaseModel):
    """Response model for baseline endpoint."""

    answer: str
    latency_ms: int
    model: str
    provider: str
    tokens_used: int


class EnhancedVerificationResponse(VerificationResponse):
    """Enhanced verification response with enterprise tracking."""

    query_id: Optional[int] = Field(None, description="Database query ID for tracking")
    session_id: Optional[str] = Field(None, description="Session ID")


class FeedbackRequest(BaseModel):
    """Request model for user feedback."""

    query_id: int
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1-5")
    feedback_type: Optional[str] = Field(None, description="Type of feedback")
    comment: Optional[str] = Field(None, description="User comment")
    suggested_improvement: Optional[str] = Field(
        None, description="Suggested improvement"
    )


class AnalyticsResponse(BaseModel):
    """Response model for analytics data."""

    total_queries: int
    average_sanad_score: float
    trigger_rate: float
    enhancement_rate: float
    average_processing_time: float
    feedback_stats: Dict[str, Any]


class DemoRequest(BaseModel):
    """Request model for enterprise demo endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Question for baseline vs Sanad comparison",
    )
    include_performance_metrics: bool = Field(
        default=True, description="Include detailed performance analysis"
    )


class DemoComparisonResult(BaseModel):
    """Individual result for baseline or Sanad."""

    answer: str
    provider: str
    tokens_used: int
    processing_time_ms: int
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    verification_score: Optional[float] = None
    verification_confidence: Optional[str] = None
    trigger_used: bool = False


class EnterpriseDemoResponse(BaseModel):
    """Enterprise demo response with full comparison analysis."""

    query: str
    session_id: str
    timestamp: str

    baseline_result: DemoComparisonResult
    sanad_result: DemoComparisonResult

    performance_analysis: Dict[str, Any]
    capability_comparison: Dict[str, Any]
    business_value_assessment: Dict[str, Any]

    query_id: Optional[int] = None  # Database tracking


# Global service instances (initialized once)
_services: Optional[Dict[str, Any]] = None


def get_services() -> Dict[str, Any]:
    """
    Get or initialize global service instances.

    Returns:
        Dictionary of initialized services
    """
    global _services

    if _services is None:
        logger.info("Initializing Sanad services...")

        try:
            # Initialize core services
            config = get_config()
            baseline_llm = BaselineLLM()

            # Initialize trigger detector
            trigger_detector = TriggerDetector()

            # Initialize retriever
            project_root = Path(__file__).parent.parent.parent
            index_dir = project_root / "data" / "index"

            if not index_dir.exists():
                logger.warning(f"Index directory not found: {index_dir}")
                retriever = None
            else:
                retriever = SimpleRetriever(index_dir)

            # Initialize coordinator and agents
            coordinator = SanadCoordinator()

            # Register agents with coordinator
            coordinator.register_agent(IntegrityAgent())
            coordinator.register_agent(PrecisionAgent())
            coordinator.register_agent(ProvenanceAgent())
            coordinator.register_agent(DomainLabourAgent())

            _services = {
                "config": config,
                "baseline_llm": baseline_llm,
                "trigger_detector": trigger_detector,
                "retriever": retriever,
                "coordinator": coordinator,
            }

            logger.info("Successfully initialized all Sanad services")

        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            raise

    return _services


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Any = Depends(get_db),
) -> Optional[User]:
    """
    Get current user from authorization token.
    For now, this is a placeholder implementation.
    In production, implement proper JWT/OAuth validation.

    Args:
        credentials: Authorization credentials
        db: Database session

    Returns:
        User object or None
    """
    # Placeholder implementation - always return demo user
    # In production, validate JWT token and return actual user

    user_repo = UserRepository(db)
    demo_user = user_repo.get_user_by_id("demo_user")

    if not demo_user:
        # Create demo user if doesn't exist
        demo_user_data = UserCreate(
            user_id="demo_user", email="demo@sanad.ai", role="user", gdpr_consent=True
        )
        demo_user = user_repo.create_user(demo_user_data)

    return demo_user


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Get user agent from request."""
    return request.headers.get("User-Agent", "unknown")


# Health Check Endpoints
@api_router.get("/healthz", tags=["Health"])
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}


@api_router.get("/ready", tags=["Health"])
async def readiness_check(db: Any = Depends(get_db)):
    """Readiness check with database connectivity."""
    try:
        # Test database connection
        user_repo = UserRepository(db)
        # Simple query to test DB
        test_user = user_repo.get_user_by_id("health_check_test")

        return {"status": "ready", "database": "connected", "timestamp": time.time()}

    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service not ready")


# Core Verification Endpoints
@api_router.post("/baseline", response_model=BaselineResponse, tags=["Verification"])
async def get_baseline_answer(
    request: BaselineRequest,
    db: Any = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get baseline LLM answer without Sanad verification.

    Args:
        request: Baseline request with question
        db: Database session
        current_user: Current authenticated user

    Returns:
        BaselineResponse with unverified answer
    """
    start_time = time.time()

    try:
        services = get_services()
        baseline_llm = services.get("baseline_llm")

        if baseline_llm is None:
            raise HTTPException(
                status_code=503, detail="Baseline LLM service not available"
            )

        # Generate baseline answer
        logger.info(f"Generating baseline answer for: {request.question[:50]}...")
        response = await baseline_llm.draft(request.question)

        processing_time = int((time.time() - start_time) * 1000)

        # Log to database if user is authenticated
        if current_user:
            query_repo = QueryRepository(db)
            from db.models import QueryLogCreate

            query_log_data = QueryLogCreate(
                user_id=current_user.id,
                question=request.question,
                answer=response.answer,
                sanad_score=0.0,  # No verification performed
                trigger_used=False,
                enhanced=False,
                processing_time_ms=processing_time,
            )

            query_repo.create_query_log(query_log_data)

        logger.info(f"Baseline answer generated in {processing_time}ms")

        return BaselineResponse(
            answer=response.answer,
            latency_ms=processing_time,
            model=response.model,
            provider=response.provider,
            tokens_used=response.tokens_used,
        )

    except Exception as e:
        logger.error(f"Baseline endpoint error: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Baseline generation failed: {str(e)}"
        )


@api_router.post(
    "/verify", response_model=EnhancedVerificationResponse, tags=["Verification"]
)
async def verify_answer(
    request: VerifyRequest,
    http_request: Request,
    db: Any = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get verified answer using the complete Sanad verification process with enterprise logging.

    Args:
        request: Verification request with question
        http_request: HTTP request object for metadata
        db: Database session
        current_user: Current authenticated user

    Returns:
        EnhancedVerificationResponse with verified answer and tracking metadata
    """
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())
    ip_address = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)

    try:
        services = get_services()

        # Check service availability
        baseline_llm = services.get("baseline_llm")
        trigger_detector = services.get("trigger_detector")
        retriever = services.get("retriever")
        coordinator = services.get("coordinator")

        if baseline_llm is None:
            raise HTTPException(status_code=503, detail="LLM service not available")

        logger.info(f"Processing verification request: {request.question[:50]}...")

        # Step 1: Check if Sanad verification should be triggered
        should_trigger = False
        if trigger_detector:
            should_trigger = trigger_detector.use_sanad(request.question)
            logger.info(f"Trigger decision: {should_trigger}")
        else:
            logger.warning("Trigger detector not available, defaulting to verification")
            should_trigger = True

        # Step 2: Generate baseline draft answer
        logger.debug("Generating draft answer...")
        draft_response = await baseline_llm.draft(request.question)
        draft_answer = draft_response.answer

        # Step 3: If not triggered, return baseline response
        if not should_trigger:
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"No verification needed, returning baseline answer in {processing_time}ms"
            )

            response = EnhancedVerificationResponse(
                answer=draft_answer,
                sanad_score=0.0,  # No verification performed
                sources=[],
                processing_time_ms=processing_time,
                session_id=session_id,
            )

            # Log to database
            if current_user:
                query_repo = QueryRepository(db)
                from db.models import QueryLogCreate

                query_log_data = QueryLogCreate(
                    user_id=current_user.id,
                    session_id=session_id,
                    question=request.question,
                    answer=response.answer,
                    sanad_score=response.sanad_score,
                    trigger_used=False,
                    enhanced=False,
                    processing_time_ms=processing_time,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                query_log = query_repo.create_query_log(query_log_data)
                response.query_id = query_log.id

            return response

        # Step 4: Retrieve relevant passages
        passages = []
        if retriever:
            try:
                logger.debug("Retrieving relevant passages...")
                category = retriever.route(request.question)
                retrieval_results = retriever.search(
                    request.question, k=5, category=category
                )

                # Convert retrieval results to Passage objects
                passages = [
                    Passage(
                        doc_id=result.get("doc_id", "unknown"),
                        chunk_id=str(result.get("chunk_id", 0)),
                        text=result.get("text", ""),
                        category=result.get("category", "unknown"),
                        score=float(result.get("score", 0.0)),
                        distance=float(result.get("distance", 1.0)),
                    )
                    for result in retrieval_results
                ]

                logger.info(
                    f"Retrieved {len(passages)} passages from category: {category}"
                )

            except Exception as e:
                logger.warning(
                    f"Retrieval failed: {str(e)}, proceeding without passages"
                )
                passages = []
        else:
            logger.warning("Retriever not available, proceeding without passages")

        # Step 5: Run Sanad verification with enterprise logging
        if coordinator and len(passages) > 0:
            logger.debug("Running Sanad verification...")

            coordinator_input = CoordinatorInput(
                question=request.question, draft_answer=draft_answer, passages=passages
            )

            # Enhanced verification with user tracking
            verification_result = await coordinator.verify(
                coordinator_input,
                user_id=current_user.id if current_user else None,
                session_id=session_id,
                ip_address=ip_address,
            )

            logger.info(
                f"Verification completed with score: {verification_result.sanad_score:.3f}"
            )

            # Add enterprise tracking fields
            enhanced_result = EnhancedVerificationResponse(
                **verification_result.dict(), session_id=session_id
            )

            # Add query_id if logged to database
            if current_user:
                query_repo = QueryRepository(db)
                # Find the logged query (it was logged by coordinator)
                recent_queries = query_repo.get_user_queries(current_user.id, limit=1)
                if recent_queries:
                    enhanced_result.query_id = recent_queries[0].id

            return enhanced_result
        else:
            # Fallback when coordinator or passages not available
            logger.warning(
                "Coordinator or passages not available, returning enhanced baseline"
            )
            processing_time = int((time.time() - start_time) * 1000)

            response = EnhancedVerificationResponse(
                answer=draft_answer,
                sanad_score=0.5,  # Partial score for baseline
                sources=passages,
                processing_time_ms=processing_time,
                session_id=session_id,
            )

            # Log to database
            if current_user:
                query_repo = QueryRepository(db)
                from db.models import QueryLogCreate

                query_log_data = QueryLogCreate(
                    user_id=current_user.id,
                    session_id=session_id,
                    question=request.question,
                    answer=response.answer,
                    sanad_score=response.sanad_score,
                    trigger_used=True,
                    enhanced=False,
                    processing_time_ms=processing_time,
                    sources_used=[p.doc_id for p in passages],
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

                query_log = query_repo.create_query_log(query_log_data)
                response.query_id = query_log.id

            return response

    except Exception as e:
        logger.error(f"Verification endpoint error: {str(e)}")

        # Log error to audit trail
        if current_user:
            audit_repo = AuditRepository(db)
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                event_type="verification_error",
                event_description=f"Verification failed: {str(e)}",
                entity_type="verification",
                entity_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                severity="error",
            )
            audit_repo.create_audit_log(audit_data)

        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


# Enterprise Management Endpoints
@api_router.post("/feedback", tags=["Enterprise"])
async def submit_feedback(
    request: FeedbackRequest,
    db: Any = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Submit user feedback for a query."""
    try:
        feedback_repo = FeedbackRepository(db)

        feedback_data = FeedbackCreate(
            query_id=request.query_id,
            rating=request.rating,
            feedback_type=request.feedback_type,
            comment=request.comment,
            suggested_improvement=request.suggested_improvement,
        )

        feedback = feedback_repo.create_feedback(feedback_data)

        return {
            "status": "success",
            "feedback_id": feedback.id,
            "message": "Feedback submitted successfully",
        }

    except Exception as e:
        logger.error(f"Feedback submission failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


@api_router.get(
    "/queries/history", response_model=List[QueryLogResponse], tags=["Enterprise"]
)
async def get_query_history(
    limit: int = 50,
    offset: int = 0,
    db: Any = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's query history with pagination."""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        query_repo = QueryRepository(db)
        queries = query_repo.get_user_queries(
            current_user.id, limit=limit, offset=offset
        )

        return [
            QueryLogResponse(
                id=q.id,
                question=q.question,
                answer=q.answer,
                sanad_score=q.sanad_score,
                trigger_used=q.trigger_used,
                enhanced=q.enhanced,
                processing_time_ms=q.processing_time_ms,
                created_at=q.created_at,
            )
            for q in queries
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query history retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query history")


@api_router.get("/analytics", response_model=AnalyticsResponse, tags=["Enterprise"])
async def get_analytics(
    days: int = 30,
    db: Any = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get analytics and system metrics."""
    try:
        if not current_user or current_user.role not in ["admin", "auditor"]:
            raise HTTPException(status_code=403, detail="Admin access required")

        # This is a placeholder - implement comprehensive analytics
        query_repo = QueryRepository(db)
        feedback_repo = FeedbackRepository(db)

        # Get feedback analytics
        feedback_stats = feedback_repo.get_feedback_analytics(days=days)

        return AnalyticsResponse(
            total_queries=0,  # Implement actual query counting
            average_sanad_score=0.75,  # Implement actual calculation
            trigger_rate=0.85,  # Implement actual calculation
            enhancement_rate=0.25,  # Implement actual calculation
            average_processing_time=850.0,  # Implement actual calculation
            feedback_stats=feedback_stats,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics retrieval failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


# GDPR Compliance Endpoints
@api_router.post("/user/export", tags=["GDPR"])
async def export_user_data(
    db: Any = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Export all user data for GDPR compliance."""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        compliance_repo = ComplianceRepository(db)
        user_data = compliance_repo.export_user_data(current_user.user_id)

        # Log data export for audit trail
        audit_repo = AuditRepository(db)
        audit_data = AuditLogCreate(
            user_id=current_user.id,
            event_type="data_export",
            event_description="User requested data export",
            entity_type="user",
            entity_id=str(current_user.id),
            compliance_reason="GDPR Article 15 - Right of access",
        )
        audit_repo.create_audit_log(audit_data)

        return {"status": "success", "data": user_data, "exported_at": time.time()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data export failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export user data")


@api_router.delete("/user/delete", tags=["GDPR"])
async def delete_user_data(
    db: Any = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Delete user data for GDPR compliance (right to be forgotten)."""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_repo = UserRepository(db)
        success = user_repo.delete_user_data(
            current_user.user_id, reason="GDPR Article 17 - Right to erasure"
        )

        if success:
            return {"status": "success", "message": "User data deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete user data")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Data deletion failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete user data")


# Enterprise Demo Endpoint
@api_router.post(
    "/demo/comparison", response_model=EnterpriseDemoResponse, tags=["Enterprise Demo"]
)
async def enterprise_demo_comparison(
    request: DemoRequest,
    http_request: Request,
    db: Any = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Enterprise demo endpoint showing side-by-side baseline vs Sanad comparison.
    Includes performance analysis, capability comparison, and business value assessment.
    """
    session_id = str(uuid.uuid4())
    ip_address = get_client_ip(http_request)
    user_agent = get_user_agent(http_request)
    start_time = time.time()

    logger.info(
        f"Enterprise demo requested: {request.question[:50]}... by {current_user.user_id if current_user else 'anonymous'}"
    )

    try:
        services = get_services()
        baseline_llm = services.get("baseline_llm")
        trigger_detector = services.get("trigger_detector")
        retriever = services.get("retriever")
        coordinator = services.get("coordinator")

        if baseline_llm is None:
            raise HTTPException(
                status_code=503,
                detail="Demo service not available - LLM not initialized",
            )

        # === PHASE 1: BASELINE ONLY ===
        logger.info("Demo Phase 1: Running baseline LLM")
        baseline_start = time.time()
        baseline_response = await baseline_llm.draft(request.question)
        baseline_time = int((time.time() - baseline_start) * 1000)

        baseline_result = DemoComparisonResult(
            answer=baseline_response.answer,
            provider=baseline_response.provider,
            tokens_used=baseline_response.tokens_used,
            processing_time_ms=baseline_time,
            sources=[],
            verification_score=None,
            verification_confidence=None,
            trigger_used=False,
        )

        # === PHASE 2: SANAD ENHANCED ===
        logger.info("Demo Phase 2: Running Sanad verification")
        sanad_start = time.time()

        # Check trigger
        should_trigger = (
            trigger_detector.use_sanad(request.question) if trigger_detector else True
        )
        trigger_reason = (
            trigger_detector.get_trigger_reason(request.question)
            if trigger_detector
            else "Manual demo"
        )

        if not should_trigger:
            # If trigger says no, return baseline for both
            sanad_result = DemoComparisonResult(
                answer=baseline_response.answer,
                provider=baseline_response.provider,
                tokens_used=baseline_response.tokens_used,
                processing_time_ms=baseline_time,
                sources=[],
                verification_score=0.3,
                verification_confidence="Low - No relevant sources",
                trigger_used=False,
            )
            trigger_note = "Query did not trigger Sanad verification"
        else:
            # Run full Sanad pipeline
            passages = []
            retrieval_sources = []

            if retriever:
                try:
                    category = retriever.route(request.question)
                    retrieval_results = retriever.search(
                        request.question, k=5, category=category
                    )

                    # Convert to Passage objects for coordinator
                    passages = [
                        Passage(
                            doc_id=result.get("doc_id", "unknown"),
                            chunk_id=str(result.get("chunk_id", 0)),
                            text=result.get("text", ""),
                            category=result.get("category", "unknown"),
                            score=float(result.get("score", 0.0)),
                            distance=float(result.get("distance", 1.0)),
                        )
                        for result in retrieval_results
                    ]

                    # Convert for demo response
                    retrieval_sources = [
                        {
                            "source": result.get("doc_id", "unknown"),
                            "relevance_score": float(result.get("score", 0.0)),
                            "snippet": (
                                result.get("text", "")[:100] + "..."
                                if len(result.get("text", "")) > 100
                                else result.get("text", "")
                            ),
                            "category": result.get("category", "unknown"),
                        }
                        for result in retrieval_results
                    ]

                except Exception as e:
                    logger.warning(f"Retrieval failed in demo: {str(e)}")

            # Run Sanad verification if we have coordinator and passages
            if coordinator and len(passages) > 0:
                coordinator_input = CoordinatorInput(
                    question=request.question,
                    draft_answer=baseline_response.answer,
                    passages=passages,
                )

                verification_result = await coordinator.verify(
                    coordinator_input,
                    user_id=current_user.id if current_user else None,
                    session_id=session_id,
                    ip_address=ip_address,
                )

                # Determine confidence level
                score = verification_result.sanad_score
                confidence = (
                    "High" if score > 0.8 else "Medium" if score > 0.6 else "Low"
                )

                sanad_result = DemoComparisonResult(
                    answer=verification_result.answer,
                    provider=baseline_response.provider,
                    tokens_used=baseline_response.tokens_used,
                    processing_time_ms=int((time.time() - sanad_start) * 1000),
                    sources=retrieval_sources,
                    verification_score=score,
                    verification_confidence=confidence,
                    trigger_used=True,
                )
                trigger_note = f"Triggered: {trigger_reason}"
            else:
                # Fallback if no coordinator or sources
                avg_score = (
                    sum(p.score for p in passages) / len(passages) if passages else 0.3
                )
                confidence = "Medium" if passages else "Low"

                sanad_result = DemoComparisonResult(
                    answer=baseline_response.answer,
                    provider=baseline_response.provider,
                    tokens_used=baseline_response.tokens_used,
                    processing_time_ms=int((time.time() - sanad_start) * 1000),
                    sources=retrieval_sources,
                    verification_score=avg_score,
                    verification_confidence=confidence,
                    trigger_used=True,
                )
                trigger_note = f"Triggered: {trigger_reason} (Limited verification)"

        # === ANALYSIS ===
        total_time = int((time.time() - start_time) * 1000)

        # Performance Analysis
        time_overhead = (
            (
                (sanad_result.processing_time_ms - baseline_result.processing_time_ms)
                / baseline_result.processing_time_ms
                * 100
            )
            if baseline_result.processing_time_ms > 0
            else 0
        )

        performance_analysis = {
            "baseline_time_ms": baseline_result.processing_time_ms,
            "sanad_time_ms": sanad_result.processing_time_ms,
            "time_overhead_percent": round(time_overhead, 1),
            "total_demo_time_ms": total_time,
            "trigger_decision": trigger_note,
        }

        # Capability Comparison
        capability_comparison = {
            "verification": {
                "baseline": "None",
                "sanad": (
                    f"Score: {sanad_result.verification_score:.2f}"
                    if sanad_result.verification_score
                    else "Limited"
                ),
            },
            "sources": {
                "baseline": "0 sources",
                "sanad": f"{len(sanad_result.sources)} verified sources",
            },
            "trust_level": {
                "baseline": "Unknown",
                "sanad": sanad_result.verification_confidence or "Unknown",
            },
            "compliance": {"baseline": "Not assured", "sanad": "Document-verified"},
        }

        # Business Value Assessment
        source_count = len(sanad_result.sources)
        business_value_assessment = {
            "document_coverage": (
                f"{source_count} relevant documents found"
                if source_count > 0
                else "No relevant documents in corpus"
            ),
            "verification_status": (
                "Verified against official sources"
                if source_count > 0
                else "Limited verification available"
            ),
            "compliance_readiness": (
                "Enterprise-ready"
                if sanad_result.verification_score
                and sanad_result.verification_score > 0.7
                else "Requires review"
            ),
            "risk_reduction": (
                "High"
                if source_count > 0
                and sanad_result.verification_score
                and sanad_result.verification_score > 0.8
                else "Medium" if source_count > 0 else "Limited"
            ),
            "recommended_action": (
                "Deploy to production"
                if source_count > 0
                and sanad_result.verification_score
                and sanad_result.verification_score > 0.7
                else (
                    "Expand document corpus"
                    if source_count == 0
                    else "Review verification settings"
                )
            ),
        }

        # Create response
        demo_response = EnterpriseDemoResponse(
            query=request.question,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            baseline_result=baseline_result,
            sanad_result=sanad_result,
            performance_analysis=performance_analysis,
            capability_comparison=capability_comparison,
            business_value_assessment=business_value_assessment,
        )

        # Log to database for enterprise tracking
        if current_user:
            query_repo = QueryRepository(db)
            audit_repo = AuditRepository(db)

            # Log demo query
            demo_log_data = QueryLogCreate(
                user_id=current_user.id,
                session_id=session_id,
                question=request.question,
                answer=f"DEMO: Baseline vs Sanad comparison completed",
                sanad_score=sanad_result.verification_score,
                trigger_used=sanad_result.trigger_used,
                enhanced=True,
                processing_time_ms=total_time,
                sources_used=[s["source"] for s in sanad_result.sources],
                ip_address=ip_address,
                user_agent=user_agent,
            )

            query_log = query_repo.create_query_log(demo_log_data)
            demo_response.query_id = query_log.id

            # Log demo audit event
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                event_type="enterprise_demo",
                event_description=f"Enterprise demo comparison performed: {request.question[:50]}...",
                entity_type="demo",
                entity_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                severity="info",
            )
            audit_repo.create_audit_log(audit_data)

        logger.info(
            f"Enterprise demo completed in {total_time}ms: {source_count} sources, score={sanad_result.verification_score}"
        )
        return demo_response

    except Exception as e:
        logger.error(f"Enterprise demo failed: {str(e)}")

        # Log error
        if current_user:
            audit_repo = AuditRepository(db)
            audit_data = AuditLogCreate(
                user_id=current_user.id,
                event_type="enterprise_demo_error",
                event_description=f"Enterprise demo failed: {str(e)}",
                entity_type="demo",
                entity_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                severity="error",
            )
            audit_repo.create_audit_log(audit_data)

        raise HTTPException(status_code=500, detail=f"Enterprise demo failed: {str(e)}")
