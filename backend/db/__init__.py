"""
Database module for Sanad v2 enterprise system.
Provides enterprise-grade data persistence, audit trails, and GDPR compliance.
"""

from .database import (
    DatabaseManager,
    close_database,
    db_manager,
    get_async_db,
    get_db,
    init_database,
)
from .models import (
    AuditLog,
    AuditLogCreate,
    Base,
    DataRetentionPolicy,
    FeedbackCreate,
    QueryLog,
    QueryLogCreate,
    QueryLogResponse,
    SourceDocument,
    SystemMetrics,
    User,
    UserCreate,
    UserFeedback,
    UserResponse,
)
from .repository import (
    AuditRepository,
    BaseRepository,
    ComplianceRepository,
    FeedbackRepository,
    QueryRepository,
    UserRepository,
)

__all__ = [
    # Models
    "Base",
    "User",
    "QueryLog",
    "SourceDocument",
    "UserFeedback",
    "SystemMetrics",
    "AuditLog",
    "DataRetentionPolicy",
    "UserCreate",
    "UserResponse",
    "QueryLogCreate",
    "QueryLogResponse",
    "FeedbackCreate",
    "AuditLogCreate",
    # Database management
    "DatabaseManager",
    "db_manager",
    "get_db",
    "get_async_db",
    "init_database",
    "close_database",
    # Repositories
    "BaseRepository",
    "UserRepository",
    "QueryRepository",
    "FeedbackRepository",
    "AuditRepository",
    "ComplianceRepository",
]
