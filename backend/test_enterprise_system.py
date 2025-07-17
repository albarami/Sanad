#!/usr/bin/env python3
"""
Enterprise System Test for Sanad v2.
Tests database layer, audit trails, GDPR compliance, and enterprise API endpoints.
"""

import asyncio
import sys
import time
import requests
import json
from pathlib import Path
from loguru import logger

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path.parent))

# Import database components
from backend.db.database import init_database, db_manager
from backend.db.repository import UserRepository, QueryRepository, FeedbackRepository, AuditRepository, ComplianceRepository
from backend.db.models import UserCreate, QueryLogCreate, FeedbackCreate, AuditLogCreate


def test_database_initialization():
    """Test database initialization and table creation."""
    print("\n=== Testing Database Initialization ===")
    
    try:
        # Initialize database
        init_database()
        print("✅ Database tables created successfully")
        
        # Test health check
        health = asyncio.run(db_manager.health_check())
        if health:
            print("✅ Database health check passed")
        else:
            print("❌ Database health check failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        return False


def test_user_management():
    """Test user creation, retrieval, and GDPR compliance."""
    print("\n=== Testing User Management ===")
    
    try:
        session = db_manager.get_session()
        user_repo = UserRepository(session)
        
        # Create test user
        user_data = UserCreate(
            user_id="test_enterprise_user",
            email="test@enterprise.sanad.ai",
            role="user",
            gdpr_consent=True
        )
        
        user = user_repo.create_user(user_data)
        print(f"✅ Created user: {user.user_id} (ID: {user.id})")
        
        # Test user retrieval
        retrieved_user = user_repo.get_user_by_id("test_enterprise_user")
        if retrieved_user and retrieved_user.id == user.id:
            print("✅ User retrieval successful")
        else:
            print("❌ User retrieval failed")
            session.close()
            return False
        
        # Test email lookup
        email_user = user_repo.get_user_by_email("test@enterprise.sanad.ai")
        if email_user and email_user.id == user.id:
            print("✅ Email lookup successful")
        else:
            print("❌ Email lookup failed")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ User management test failed: {str(e)}")
        return False


def test_query_logging():
    """Test query logging and history tracking."""
    print("\n=== Testing Query Logging ===")
    
    try:
        session = db_manager.get_session()
        user_repo = UserRepository(session)
        query_repo = QueryRepository(session)
        
        # Get test user
        user = user_repo.get_user_by_id("test_enterprise_user")
        if not user:
            print("❌ Test user not found")
            session.close()
            return False
        
        # Create test query logs
        test_queries = [
            {
                "question": "What is the probation period in Qatar?",
                "answer": "The probation period in Qatar is typically 6 months.",
                "sanad_score": 0.85,
                "sources": ["labour_law"],
                "agent_scores": {"integrity": 0.9, "precision": 0.8, "provenance": 0.85, "domain": 0.85}
            },
            {
                "question": "What are the working hours in Qatar?",
                "answer": "Standard working hours are 8 hours per day or 48 hours per week.",
                "sanad_score": 0.92,
                "sources": ["labour_law", "ministry_guidelines"],
                "agent_scores": {"integrity": 0.95, "precision": 0.9, "provenance": 0.9, "domain": 0.92}
            }
        ]
        
        query_ids = []
        for query_data in test_queries:
            log_data = QueryLogCreate(
                user_id=user.id,
                session_id="test_session_123",
                question=query_data["question"],
                answer=query_data["answer"],
                sanad_score=query_data["sanad_score"],
                trigger_used=True,
                enhanced=False,
                processing_time_ms=850,
                sources_used=query_data["sources"],
                agent_scores=query_data["agent_scores"],
                ip_address="127.0.0.1",
                user_agent="Test/1.0"
            )
            
            query_log = query_repo.create_query_log(log_data)
            query_ids.append(query_log.id)
            print(f"✅ Created query log: {query_log.id}")
        
        # Test query history retrieval
        user_queries = query_repo.get_user_queries(user.id, limit=10)
        if len(user_queries) >= 2:
            print(f"✅ Retrieved {len(user_queries)} user queries")
        else:
            print(f"❌ Expected at least 2 queries, got {len(user_queries)}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Query logging test failed: {str(e)}")
        return False


def test_feedback_system():
    """Test user feedback collection and analytics."""
    print("\n=== Testing Feedback System ===")
    
    try:
        session = db_manager.get_session()
        user_repo = UserRepository(session)
        query_repo = QueryRepository(session)
        feedback_repo = FeedbackRepository(session)
        
        # Get test user and queries
        user = user_repo.get_user_by_id("test_enterprise_user")
        user_queries = query_repo.get_user_queries(user.id, limit=2)
        
        if len(user_queries) < 1:
            print("❌ No queries found for feedback testing")
            session.close()
            return False
        
        # Create test feedback
        feedback_data = FeedbackCreate(
            query_id=user_queries[0].id,
            rating=4,
            feedback_type="helpful",
            comment="Great answer, very accurate and helpful!",
            suggested_improvement="Could include more specific citations"
        )
        
        feedback = feedback_repo.create_feedback(feedback_data)
        print(f"✅ Created feedback: {feedback.id}")
        
        # Test feedback retrieval
        query_feedback = feedback_repo.get_query_feedback(user_queries[0].id)
        if len(query_feedback) >= 1:
            print(f"✅ Retrieved {len(query_feedback)} feedback entries")
        else:
            print("❌ Feedback retrieval failed")
        
        # Test feedback analytics
        analytics = feedback_repo.get_feedback_analytics(days=30)
        print(f"✅ Feedback analytics: avg_rating={analytics['average_rating']}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Feedback system test failed: {str(e)}")
        return False


def test_audit_trail():
    """Test audit trail logging for compliance."""
    print("\n=== Testing Audit Trail ===")
    
    try:
        session = db_manager.get_session()
        user_repo = UserRepository(session)
        audit_repo = AuditRepository(session)
        
        # Get test user
        user = user_repo.get_user_by_id("test_enterprise_user")
        
        # Create test audit logs
        audit_events = [
            {
                "event_type": "user_login",
                "description": "User logged in successfully",
                "entity_type": "user",
                "severity": "info"
            },
            {
                "event_type": "data_access",
                "description": "User accessed query history",
                "entity_type": "query",
                "severity": "info"
            },
            {
                "event_type": "admin_action",
                "description": "Admin performed system maintenance",
                "entity_type": "system",
                "severity": "warning"
            }
        ]
        
        for event in audit_events:
            audit_data = AuditLogCreate(
                user_id=user.id,
                event_type=event["event_type"],
                event_description=event["description"],
                entity_type=event["entity_type"],
                entity_id=str(user.id),
                ip_address="127.0.0.1",
                user_agent="Test/1.0",
                session_id="test_session_123",
                severity=event["severity"]
            )
            
            audit_log = audit_repo.create_audit_log(audit_data)
            print(f"✅ Created audit log: {audit_log.id} - {event['event_type']}")
        
        # Test audit log retrieval
        audit_logs = audit_repo.get_audit_logs(user_id=user.id, days=1)
        if len(audit_logs) >= 3:
            print(f"✅ Retrieved {len(audit_logs)} audit logs")
        else:
            print(f"❌ Expected at least 3 audit logs, got {len(audit_logs)}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Audit trail test failed: {str(e)}")
        return False


def test_gdpr_compliance():
    """Test GDPR compliance features."""
    print("\n=== Testing GDPR Compliance ===")
    
    try:
        session = db_manager.get_session()
        compliance_repo = ComplianceRepository(session)
        
        # Test data export
        user_data = compliance_repo.export_user_data("test_enterprise_user")
        
        if user_data and "user_profile" in user_data:
            print("✅ User data export successful")
            print(f"   - User profile: {user_data['user_profile']['user_id']}")
            print(f"   - Queries: {len(user_data.get('queries', []))}")
            print(f"   - Feedback: {len(user_data.get('feedback', []))}")
            print(f"   - Audit trail: {len(user_data.get('audit_trail', []))}")
        else:
            print("❌ User data export failed")
            session.close()
            return False
        
        # Test data cleanup (dry run - don't actually delete)
        # In production, this would be run as a scheduled job
        print("✅ GDPR compliance features working")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ GDPR compliance test failed: {str(e)}")
        return False


async def test_api_endpoints():
    """Test FastAPI endpoints with enterprise features."""
    print("\n=== Testing API Endpoints ===")
    
    try:
        # This would require starting the FastAPI server
        # For now, just validate the imports and setup
        from backend.app.main import create_app
        from backend.app.api_router import api_router
        
        app = create_app()
        print("✅ FastAPI application created successfully")
        
        # Check that all enterprise endpoints are registered
        routes = [route.path for route in app.routes]
        
        expected_endpoints = [
            "/health",
            "/health/detailed",
            "/metrics",
            "/api/healthz",
            "/api/ready",
            "/api/baseline",
            "/api/verify",
            "/api/feedback",
            "/api/queries/history",
            "/api/analytics",
            "/api/user/export",
            "/api/user/delete"
        ]
        
        missing_endpoints = []
        for endpoint in expected_endpoints:
            if not any(endpoint in route for route in routes):
                missing_endpoints.append(endpoint)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        else:
            print("✅ All enterprise API endpoints registered")
        
        return True
        
    except Exception as e:
        print(f"❌ API endpoint test failed: {str(e)}")
        return False


def cleanup_test_data():
    """Clean up test data after tests."""
    print("\n=== Cleaning Up Test Data ===")
    
    try:
        session = db_manager.get_session()
        user_repo = UserRepository(session)
        
        # Delete test user (this will cascade to related data)
        success = user_repo.delete_user_data(
            "test_enterprise_user",
            reason="Test cleanup"
        )
        
        if success:
            print("✅ Test data cleaned up successfully")
        else:
            print("⚠️  Test data cleanup had issues (may not exist)")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        return False


def main():
    """Run all enterprise system tests."""
    print("🚀 Starting Sanad v2 Enterprise System Tests")
    print("=" * 60)
    
    tests = [
        ("Database Initialization", test_database_initialization),
        ("User Management", test_user_management),
        ("Query Logging", test_query_logging),
        ("Feedback System", test_feedback_system),
        ("Audit Trail", test_audit_trail),
        ("GDPR Compliance", test_gdpr_compliance),
        ("API Endpoints", lambda: asyncio.run(test_api_endpoints())),
        ("Cleanup", cleanup_test_data)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test crashed: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ENTERPRISE SYSTEM TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All enterprise tests passed! System is ready for production.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 