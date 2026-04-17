"""
Main API router aggregation.
"""

from fastapi import APIRouter

from app.api.routes import notifications, preferences, users, templates, webhooks, deliveries, health

# Create main API router
api_router = APIRouter()

# Include all route modules
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["notifications"]
)

api_router.include_router(
    preferences.router,
    prefix="/users",
    tags=["preferences"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["templates"]
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)

api_router.include_router(
    deliveries.router,
    prefix="/deliveries",
    tags=["deliveries"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)
