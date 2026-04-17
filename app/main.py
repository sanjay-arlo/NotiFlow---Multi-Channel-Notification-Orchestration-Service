"""
Main FastAPI application factory.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.db.session import engine
from app.utils.redis_client import redis_client

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting NotiFlow API...")
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise
    
    # Create database tables (for development)
    if settings.debug:
        from app.db.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Created database tables")
    
    yield
    
    # Shutdown
    logger.info("Shutting down NotiFlow API...")
    try:
        await redis_client.disconnect()
        logger.info("Disconnected from Redis")
    except Exception as e:
        logger.error(f"Error disconnecting from Redis: {e}")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Multi-Channel Notification Orchestration Service",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure as needed
    )
    
    # Add request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Add logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s - "
            f"Request-ID: {getattr(request.state, 'request_id', 'unknown')}"
        )
        
        return response
    
    # Include API routes
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    
    # Add exception handlers
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Unhandled exception: {exc}",
            exc_info=True,
            extra={"request_id": getattr(request.state, 'request_id', 'unknown')}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error"
                }
            }
        )
    
    return app


# Create application instance
app = create_app()


@app.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "service": "notiflow-api"
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check with dependencies."""
    health_status = {
        "status": "ready",
        "checks": {}
    }
    
    # Check Redis
    try:
        await redis_client.client.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {e}"
        health_status["status"] = "not_ready"
    
    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {e}"
        health_status["status"] = "not_ready"
    
    return JSONResponse(
        status_code=status.HTTP_200_OK if health_status["status"] == "ready" else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=health_status
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
