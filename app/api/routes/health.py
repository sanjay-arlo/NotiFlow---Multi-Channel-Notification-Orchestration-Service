"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Basic health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "service": "notiflow-api"
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check with dependencies."""
    health_status = {
        "status": "ready",
        "checks": {}
    }
    
    # Check database
    try:
        await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["checks"]["database"] = f"error: {str(e)}"
        health_status["status"] = "not_ready"
    
    # Check Redis (would be injected via deps)
    try:
        from app.api.deps import get_redis
        redis_client = await get_redis()
        await redis_client.client.ping()
        health_status["checks"]["redis"] = "ok"
    except Exception as e:
        health_status["checks"]["redis"] = f"error: {str(e)}"
        health_status["status"] = "not_ready"
    
    return health_status


@router.get("/queues")
async def queue_health_check(db: AsyncSession = Depends(get_db)):
    """Queue depth health check."""
    # This would typically query Celery for queue depths
    # For now, return mock data
    return {
        "queues": {
            "critical": {"depth": 0, "workers": 1},
            "high": {"depth": 5, "workers": 1},
            "email": {"depth": 23, "workers": 2},
            "sms": {"depth": 0, "workers": 1},
            "webhook": {"depth": 2, "workers": 1},
            "default": {"depth": 10, "workers": 2}
        }
    }
