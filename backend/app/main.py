"""
Main FastAPI application for Sanad v2 enterprise system.
Implements startup/shutdown lifecycle, database initialization, and health monitoring.
"""

import asyncio
import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

# Prometheus imports with graceful fallback
try:
    from prometheus_client import REGISTRY, make_asgi_app

    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning(
        "prometheus_client not available - metrics endpoint will be disabled"
    )
    PROMETHEUS_AVAILABLE = False

from ..core.config import get_config
from ..db.database import close_database, db_manager, init_database
# Import application components
from .api_router import api_router

# Import enhancer to register Prometheus metrics
if PROMETHEUS_AVAILABLE:
    from ..core import \
        enhancer  # This registers the sanad_enhancement_* metrics
    from ..core.config_hash import compute_config_hash


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for FastAPI application.
    Manages startup and shutdown procedures for enterprise deployment.
    """
    # Startup
    logger.info("🚀 Starting Sanad v2 Enterprise System")

    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()

        # Verify database health
        db_healthy = await db_manager.health_check()
        if not db_healthy:
            logger.error("Database health check failed!")
            raise RuntimeError("Database initialization failed")

        logger.info("✅ Database initialized successfully")

        # Compute config hash for immutability tracking
        if PROMETHEUS_AVAILABLE:
            try:
                config_hash = compute_config_hash()
                logger.info(f"📋 Config hash computed and exported to Prometheus")
            except Exception as e:
                logger.warning(f"Failed to compute config hash: {e}")

        # Future: Initialize other enterprise services
        # - Background tasks (data cleanup, backups)
        # - Rate limiting
        # - Authentication

        logger.info("🎯 Sanad v2 startup completed")

        yield

    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

    finally:
        # Clean up resources on shutdown
        logger.info("🔄 Shutting down Sanad v2 Enterprise System")

        # Close database connections
        if db_manager._initialized:
            await db_manager.close()
            logger.info("✅ Database connections closed")

        logger.info("✅ Sanad v2 shutdown completed")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    config = get_config()

    # Create FastAPI app with enterprise configuration
    app = FastAPI(
        title="Sanad v2 Enterprise Verification System",
        description="AI-powered regulatory content verification with Islamic ʿIlm al-Rijāl methodology",
        version="2.0.0",
        lifespan=lifespan,
        docs_url=(
            "/docs" if config.environment == "development" else None
        ),  # Disable in production
        redoc_url="/redoc" if config.environment == "development" else None,
    )

    # Add enterprise security middleware
    if config.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.sanad.ai", "localhost"],  # Configure for your domain
        )

    # Add CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
        ],  # Vite dev server
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(api_router, prefix="/api")

    # Basic auth for metrics endpoint
    security = HTTPBasic()

    def authenticate_metrics(credentials: HTTPBasicCredentials = Depends(security)):
        """Authenticate metrics endpoint access."""
        metrics_password = os.getenv("SANAD_METRICS_PASSWORD")
        if not metrics_password:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Metrics authentication not configured",
            )

        correct_username = secrets.compare_digest(credentials.username, "metrics")
        correct_password = secrets.compare_digest(
            credentials.password, metrics_password
        )

        if not (correct_username and correct_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid metrics credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        return credentials

    # Add enterprise health check endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "version": "2.0.0"}

    @app.get("/healthz")
    async def healthz():
        """Kubernetes/Nginx health probe endpoint."""
        return {"status": "ok"}

    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with database connectivity."""
        try:
            # Check database health
            db_healthy = await db_manager.health_check()

            # Future: Check other service health
            # - LLM API connectivity
            # - Embedding service
            # - File system access

            if not db_healthy:
                raise HTTPException(status_code=503, detail="Database unhealthy")

            return {
                "status": "healthy",
                "version": "2.0.0",
                "services": {"database": "healthy", "api": "healthy"},
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

    # Prometheus metrics endpoint with basic auth
    if PROMETHEUS_AVAILABLE:
        from fastapi import Response
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        @app.get("/metrics")
        async def metrics_endpoint(
            _: HTTPBasicCredentials = Depends(authenticate_metrics),
        ):
            """Prometheus metrics endpoint with basic authentication."""
            try:
                # Generate Prometheus metrics in the expected format
                metrics_data = generate_latest(REGISTRY)
                return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
            except Exception as e:
                logger.error(f"Failed to generate metrics: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate metrics",
                )

    else:

        @app.get("/metrics")
        async def metrics_disabled():
            """Disabled metrics endpoint when Prometheus not available."""
            return {
                "status": "disabled",
                "message": "Prometheus client not installed - metrics unavailable",
            }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    """
    Run the application directly for development.
    In production, use: uvicorn backend.app.main:app
    """
    config = get_config()

    uvicorn.run(
        "backend.app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.environment == "development",
        log_level=config.log_level.lower(),
    )
