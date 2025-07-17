"""
Database models for Sanad v2 enterprise system.
Implements audit trails, user management, and GDPR compliance.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model for authentication and session management."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        String(255), unique=True, index=True, nullable=False
    )  # External user ID
    email = Column(String(255), unique=True, index=True)
    role = Column(String(50), default="user")  # user, admin, auditor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime)
    gdpr_consent = Column(Boolean, default=False)
    data_retention_until = Column(DateTime)  # GDPR compliance

    # Relationships
    queries = relationship("QueryLog", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")


class QueryLog(Base):
    """Complete log of all user queries and system responses."""

    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(String(255), index=True)

    # Query data
    question = Column(Text, nullable=False)
    question_hash = Column(String(64), index=True)  # For deduplication
    category = Column(String(50))  # official, research, etc.

    # Response data
    answer = Column(Text)
    sanad_score = Column(Float)
    trigger_used = Column(Boolean, default=False)
    enhanced = Column(Boolean, default=False)

    # Performance metrics
    processing_time_ms = Column(Integer)
    retrieval_time_ms = Column(Integer)
    agent_time_ms = Column(Integer)

    # Sources and provenance
    sources_used = Column(JSON)  # List of source IDs
    agent_scores = Column(JSON)  # Individual agent scores

    # Metadata
    api_version = Column(String(20))
    model_version = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(45))  # IPv6 support
    user_agent = Column(String(500))

    # Relationships
    user = relationship("User", back_populates="queries")
    feedback = relationship("UserFeedback", back_populates="query")


class SourceDocument(Base):
    """Registry of all source documents in the system."""

    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String(255), unique=True, index=True, nullable=False)
    filename = Column(String(500))
    title = Column(String(500))
    category = Column(String(50))  # official, research, academic

    # Document metadata
    language = Column(String(10), default="en")
    publication_date = Column(DateTime)
    last_updated = Column(DateTime)
    version = Column(String(50))
    authority_level = Column(Float)  # 0.0 to 1.0

    # Processing metadata
    chunk_count = Column(Integer)
    embedding_model = Column(String(100))
    processed_at = Column(DateTime)
    file_hash = Column(String(64))  # For integrity checking

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class UserFeedback(Base):
    """User feedback on query responses for system improvement."""

    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    query_id = Column(Integer, ForeignKey("query_logs.id"), nullable=False)

    # Feedback data
    rating = Column(Integer)  # 1-5 scale
    feedback_type = Column(String(50))  # helpful, incorrect, incomplete, etc.
    comment = Column(Text)
    suggested_improvement = Column(Text)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(45))

    # Relationships
    query = relationship("QueryLog", back_populates="feedback")


class SystemMetrics(Base):
    """System performance and operational metrics."""

    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_type = Column(String(50))  # counter, gauge, histogram
    labels = Column(JSON)  # Additional metric labels
    timestamp = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    """Comprehensive audit trail for regulatory compliance."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Audit event data
    event_type = Column(
        String(100), nullable=False
    )  # query, admin_action, data_export, etc.
    event_description = Column(Text)
    entity_type = Column(String(50))  # user, query, document, etc.
    entity_id = Column(String(255))

    # Changes (for update events)
    old_values = Column(JSON)
    new_values = Column(JSON)

    # Context
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(255))

    # Compliance
    compliance_reason = Column(String(200))  # GDPR, audit, investigation
    retention_until = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    severity = Column(String(20), default="info")  # info, warning, critical

    # Relationships
    user = relationship("User", back_populates="audit_logs")


class DataRetentionPolicy(Base):
    """GDPR and regulatory data retention policies."""

    __tablename__ = "data_retention_policies"

    id = Column(Integer, primary_key=True, index=True)
    policy_name = Column(String(100), unique=True, nullable=False)
    data_type = Column(String(50), nullable=False)  # query_logs, user_data, etc.
    retention_days = Column(Integer, nullable=False)
    auto_delete = Column(Boolean, default=True)
    legal_basis = Column(String(200))  # GDPR Article reference

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


# Pydantic models for API serialization
class UserCreate(BaseModel):
    """Schema for creating users."""

    user_id: str
    email: Optional[str] = None
    role: str = "user"
    gdpr_consent: bool = False


class UserResponse(BaseModel):
    """Schema for user API responses."""

    id: int
    user_id: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class QueryLogCreate(BaseModel):
    """Schema for creating query logs."""

    user_id: int
    session_id: Optional[str] = None
    question: str
    category: Optional[str] = None
    answer: Optional[str] = None
    sanad_score: Optional[float] = None
    trigger_used: bool = False
    enhanced: bool = False
    processing_time_ms: Optional[int] = None
    sources_used: Optional[List[str]] = None
    agent_scores: Optional[Dict[str, float]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class QueryLogResponse(BaseModel):
    """Schema for query log API responses."""

    id: int
    question: str
    answer: Optional[str]
    sanad_score: Optional[float]
    trigger_used: bool
    enhanced: bool
    processing_time_ms: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackCreate(BaseModel):
    """Schema for creating user feedback."""

    query_id: int
    rating: Optional[int] = Field(ge=1, le=5)
    feedback_type: Optional[str]
    comment: Optional[str]
    suggested_improvement: Optional[str]


class AuditLogCreate(BaseModel):
    """Schema for creating audit logs."""

    user_id: Optional[int] = None
    event_type: str
    event_description: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    compliance_reason: Optional[str] = None
    severity: str = "info"
