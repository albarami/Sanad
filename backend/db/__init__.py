"""
Database module for Sanad v2 enterprise system.
Provides enterprise-grade data persistence, audit trails, and GDPR compliance.
"""

from .models import (
    Base,
    User,
    QueryLog,
    SourceDocument,
    UserFeedback,
    SystemMetrics,
    AuditLog,
    DataRetentionPolicy,
    UserCreate,
    UserResponse,
    QueryLogCreate,
    QueryLogResponse,
    FeedbackCreate,
    AuditLogCreate
)

from .database import (
    DatabaseManager,
    db_manager,
    get_db,
    get_async_db,
    init_database,
    close_database
)

from .repository import (
    BaseRepository,
    UserRepository,
    QueryRepository,
    FeedbackRepository,
    AuditRepository,
    ComplianceRepository
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
    "ComplianceRepository"
] 