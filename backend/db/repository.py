"""
Repository layer for database operations in Sanad v2.
Implements enterprise-grade CRUD operations, audit trails, and GDPR compliance.
"""

import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from .models import (AuditLog, AuditLogCreate, DataRetentionPolicy,
                     FeedbackCreate, QueryLog, QueryLogCreate, SourceDocument,
                     SystemMetrics, User, UserCreate, UserFeedback)


class BaseRepository:
    """Base repository with common database operations."""

    def __init__(self, session: Session):
        """Initialize repository with database session."""
        self.session = session

    def commit(self) -> None:
        """Commit current transaction."""
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.error(f"Database commit failed: {str(e)}")
            raise

    def rollback(self) -> None:
        """Rollback current transaction."""
        self.session.rollback()


class UserRepository(BaseRepository):
    """Repository for user management operations."""

    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user with GDPR compliance tracking.

        Args:
            user_data: User creation data

        Returns:
            Created user object
        """
        # Set data retention based on GDPR (default 180 days)
        retention_date = datetime.utcnow() + timedelta(days=180)

        user = User(
            user_id=user_data.user_id,
            email=user_data.email,
            role=user_data.role,
            gdpr_consent=user_data.gdpr_consent,
            data_retention_until=retention_date,
            created_at=datetime.utcnow(),
        )

        self.session.add(user)
        self.commit()

        # Create audit log
        self._create_audit_log(
            user_id=user.id,
            event_type="user_created",
            event_description=f"User {user.user_id} created with role {user.role}",
            entity_type="user",
            entity_id=str(user.id),
        )

        logger.info(f"Created user: {user.user_id} with role: {user.role}")
        return user

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by external user ID."""
        return self.session.query(User).filter(User.user_id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        return self.session.query(User).filter(User.email == email).first()

    def update_last_seen(self, user_id: str) -> None:
        """Update user's last seen timestamp."""
        user = self.get_user_by_id(user_id)
        if user:
            user.last_seen = datetime.utcnow()
            self.commit()

    def delete_user_data(self, user_id: str, reason: str = "user_request") -> bool:
        """
        Delete user data for GDPR compliance.

        Args:
            user_id: User identifier
            reason: Reason for deletion (GDPR compliance)

        Returns:
            True if successful, False otherwise
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False

            # Create audit log before deletion
            self._create_audit_log(
                user_id=user.id,
                event_type="user_data_deleted",
                event_description=f"User data deleted: {reason}",
                entity_type="user",
                entity_id=str(user.id),
                compliance_reason=reason,
            )

            # Anonymize query logs instead of deleting (for system learning)
            self.session.query(QueryLog).filter(QueryLog.user_id == user.id).update(
                {
                    QueryLog.question: "[ANONYMIZED]",
                    QueryLog.answer: "[ANONYMIZED]",
                    QueryLog.ip_address: None,
                    QueryLog.user_agent: None,
                }
            )

            # Delete user record
            self.session.delete(user)
            self.commit()

            logger.info(f"Deleted user data for: {user_id}, reason: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete user data: {str(e)}")
            self.rollback()
            return False

    def _create_audit_log(self, **kwargs) -> None:
        """Create audit log entry."""
        audit_log = AuditLog(**kwargs, created_at=datetime.utcnow())
        self.session.add(audit_log)


class QueryRepository(BaseRepository):
    """Repository for query and response management."""

    def create_query_log(self, query_data: QueryLogCreate) -> QueryLog:
        """
        Create a new query log entry with audit trail.

        Args:
            query_data: Query log creation data

        Returns:
            Created query log object
        """
        # Generate question hash for deduplication
        question_hash = hashlib.sha256(query_data.question.encode()).hexdigest()

        query_log = QueryLog(
            user_id=query_data.user_id,
            session_id=query_data.session_id,
            question=query_data.question,
            question_hash=question_hash,
            category=query_data.category,
            answer=query_data.answer,
            sanad_score=query_data.sanad_score,
            trigger_used=query_data.trigger_used,
            enhanced=query_data.enhanced,
            processing_time_ms=query_data.processing_time_ms,
            sources_used=query_data.sources_used,
            agent_scores=query_data.agent_scores,
            ip_address=query_data.ip_address,
            user_agent=query_data.user_agent,
            api_version="v2.0",
            created_at=datetime.utcnow(),
        )

        self.session.add(query_log)
        self.commit()

        logger.info(f"Created query log: {query_log.id} for user: {query_data.user_id}")
        return query_log

    def get_user_queries(
        self, user_id: int, limit: int = 50, offset: int = 0
    ) -> List[QueryLog]:
        """Get user's query history with pagination."""
        return (
            self.session.query(QueryLog)
            .filter(QueryLog.user_id == user_id)
            .order_by(desc(QueryLog.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_query_by_id(self, query_id: int) -> Optional[QueryLog]:
        """Get specific query by ID."""
        return self.session.query(QueryLog).filter(QueryLog.id == query_id).first()

    def get_similar_queries(self, question_hash: str, limit: int = 5) -> List[QueryLog]:
        """Find similar queries by hash for caching/reuse."""
        return (
            self.session.query(QueryLog)
            .filter(QueryLog.question_hash == question_hash)
            .order_by(desc(QueryLog.created_at))
            .limit(limit)
            .all()
        )

    def get_system_metrics(
        self, metric_names: List[str], hours: int = 24
    ) -> List[SystemMetrics]:
        """Get system metrics for monitoring."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.session.query(SystemMetrics)
            .filter(
                and_(
                    SystemMetrics.metric_name.in_(metric_names),
                    SystemMetrics.timestamp >= since,
                )
            )
            .order_by(desc(SystemMetrics.timestamp))
            .all()
        )


class FeedbackRepository(BaseRepository):
    """Repository for user feedback management."""

    def create_feedback(self, feedback_data: FeedbackCreate) -> UserFeedback:
        """
        Create user feedback entry.

        Args:
            feedback_data: Feedback creation data

        Returns:
            Created feedback object
        """
        feedback = UserFeedback(
            query_id=feedback_data.query_id,
            rating=feedback_data.rating,
            feedback_type=feedback_data.feedback_type,
            comment=feedback_data.comment,
            suggested_improvement=feedback_data.suggested_improvement,
            created_at=datetime.utcnow(),
        )

        self.session.add(feedback)
        self.commit()

        logger.info(f"Created feedback for query: {feedback_data.query_id}")
        return feedback

    def get_query_feedback(self, query_id: int) -> List[UserFeedback]:
        """Get all feedback for a specific query."""
        return (
            self.session.query(UserFeedback)
            .filter(UserFeedback.query_id == query_id)
            .order_by(desc(UserFeedback.created_at))
            .all()
        )

    def get_feedback_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback analytics for system improvement."""
        since = datetime.utcnow() - timedelta(days=days)

        # Average rating
        avg_rating = (
            self.session.query(func.avg(UserFeedback.rating))
            .filter(UserFeedback.created_at >= since)
            .scalar()
        )

        # Feedback type distribution
        feedback_types = (
            self.session.query(UserFeedback.feedback_type, func.count(UserFeedback.id))
            .filter(UserFeedback.created_at >= since)
            .group_by(UserFeedback.feedback_type)
            .all()
        )

        return {
            "average_rating": float(avg_rating) if avg_rating else 0.0,
            "total_feedback": len(feedback_types),
            "feedback_distribution": dict(feedback_types),
        }


class AuditRepository(BaseRepository):
    """Repository for audit trail management."""

    def create_audit_log(self, audit_data: AuditLogCreate) -> AuditLog:
        """
        Create audit log entry for compliance tracking.

        Args:
            audit_data: Audit log creation data

        Returns:
            Created audit log object
        """
        audit_log = AuditLog(
            user_id=audit_data.user_id,
            event_type=audit_data.event_type,
            event_description=audit_data.event_description,
            entity_type=audit_data.entity_type,
            entity_id=audit_data.entity_id,
            old_values=audit_data.old_values,
            new_values=audit_data.new_values,
            ip_address=audit_data.ip_address,
            user_agent=audit_data.user_agent,
            session_id=audit_data.session_id,
            compliance_reason=audit_data.compliance_reason,
            severity=audit_data.severity,
            created_at=datetime.utcnow(),
        )

        self.session.add(audit_log)
        self.commit()

        return audit_log

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        event_type: Optional[str] = None,
        days: int = 30,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs with filtering."""
        since = datetime.utcnow() - timedelta(days=days)

        query = self.session.query(AuditLog).filter(AuditLog.created_at >= since)

        if user_id:
            query = query.filter(AuditLog.user_id == user_id)

        if event_type:
            query = query.filter(AuditLog.event_type == event_type)

        return query.order_by(desc(AuditLog.created_at)).limit(limit).all()


class ComplianceRepository(BaseRepository):
    """Repository for GDPR and regulatory compliance operations."""

    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        Clean up expired data according to retention policies.

        Returns:
            Dictionary with cleanup statistics
        """
        now = datetime.utcnow()
        stats = {}

        try:
            # Clean up expired user data
            expired_users = (
                self.session.query(User).filter(User.data_retention_until < now).all()
            )

            for user in expired_users:
                # Anonymize instead of delete for audit trail preservation
                user.email = None
                user.is_active = False

                # Anonymize related query logs
                self.session.query(QueryLog).filter(QueryLog.user_id == user.id).update(
                    {
                        QueryLog.question: "[EXPIRED]",
                        QueryLog.answer: "[EXPIRED]",
                        QueryLog.ip_address: None,
                        QueryLog.user_agent: None,
                    }
                )

            stats["anonymized_users"] = len(expired_users)

            # Clean up old metrics (keep only 90 days)
            metrics_cutoff = now - timedelta(days=90)
            deleted_metrics = (
                self.session.query(SystemMetrics)
                .filter(SystemMetrics.timestamp < metrics_cutoff)
                .delete()
            )
            stats["deleted_metrics"] = deleted_metrics

            self.commit()
            logger.info(f"Data cleanup completed: {stats}")

        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
            self.rollback()
            stats["error"] = str(e)

        return stats

    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Export all user data for GDPR compliance.

        Args:
            user_id: User identifier

        Returns:
            Dictionary containing all user data
        """
        user = self.session.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {}

        # Get all related data
        queries = self.session.query(QueryLog).filter(QueryLog.user_id == user.id).all()

        feedback = (
            self.session.query(UserFeedback)
            .join(QueryLog)
            .filter(QueryLog.user_id == user.id)
            .all()
        )

        audit_logs = (
            self.session.query(AuditLog).filter(AuditLog.user_id == user.id).all()
        )

        return {
            "user_profile": {
                "user_id": user.user_id,
                "email": user.email,
                "role": user.role,
                "created_at": user.created_at.isoformat(),
                "last_seen": user.last_seen.isoformat() if user.last_seen else None,
            },
            "queries": [
                {
                    "id": q.id,
                    "question": q.question,
                    "answer": q.answer,
                    "sanad_score": q.sanad_score,
                    "created_at": q.created_at.isoformat(),
                }
                for q in queries
            ],
            "feedback": [
                {
                    "query_id": f.query_id,
                    "rating": f.rating,
                    "comment": f.comment,
                    "created_at": f.created_at.isoformat(),
                }
                for f in feedback
            ],
            "audit_trail": [
                {
                    "event_type": a.event_type,
                    "event_description": a.event_description,
                    "created_at": a.created_at.isoformat(),
                }
                for a in audit_logs
            ],
        }
