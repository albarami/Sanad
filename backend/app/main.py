"""
Main FastAPI application for Sanad v2 enterprise system.
Implements startup/shutdown lifecycle, database initialization, and health monitoring.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger
import uvicorn

# Import application components
from .api_router import api_router
from ..db.database import init_database, close_database, db_manager
from ..core.config import get_config


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
        
        # Future: Initialize other enterprise services
        # - Prometheus metrics
        # - Background tasks (data cleanup, backups)
        # - Rate limiting
        # - Authentication
        
        logger.info("🎯 Sanad v2 startup completed")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    finally:
        # Shutdown
        logger.info("🔄 Shutting down Sanad v2 Enterprise System")
        
        try:
            # Close database connections
            close_database()
            logger.info("✅ Database connections closed")
            
            # Future: Cleanup other enterprise services
            
            logger.info("✅ Sanad v2 shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {str(e)}")


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
        docs_url="/docs" if config.environment == "development" else None,  # Disable in production
        redoc_url="/redoc" if config.environment == "development" else None
    )
    
    # Add enterprise security middleware
    if config.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*.sanad.ai", "localhost"]  # Configure for your domain
        )
    
    # Add CORS middleware for frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Add enterprise health check endpoints
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        return {"status": "healthy", "version": "2.0.0"}
    
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
                "services": {
                    "database": "healthy",
                    "api": "healthy"
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")
    
    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint for monitoring."""
        # Future: Implement Prometheus metrics collection
        # For now, return basic metrics
        return {
            "status": "metrics_placeholder",
            "message": "Prometheus metrics integration coming soon"
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
        log_level=config.log_level.lower()
    ) 