"""
Dependency injection for FastAPI endpoints.
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    NotiFlowError,
    UserNotFoundError,
    TenantNotFoundError,
    NoChannelsAvailableError,
    TemplateNotFoundError,
    NotificationNotFoundError,
    DeliveryNotFoundError,
    WebhookConfigNotFoundError
)
from app.core.security import hash_api_key
from app.db.session import get_async_session
from app.db.models.tenant import Tenant
from app.repositories.tenant_repo import TenantRepository
from app.repositories.user_repo import UserRepository
from app.repositories.notification_repo import NotificationRepository
from app.repositories.delivery_repo import DeliveryRepository
from app.repositories.preference_repo import (
    UserPreferenceRepository,
    QuietHoursRepository
)
from app.repositories.template_repo import TemplateRepository
from app.repositories.webhook_config_repo import WebhookConfigRepository
from app.services.preference_service import PreferenceService
from app.services.template_service import TemplateService
from app.services.channel_resolver import ChannelResolver
from app.services.notification_service import NotificationService
from app.services.delivery_service import DeliveryService
from app.services.webhook_config_service import WebhookConfigService
from app.utils.redis_client import redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_async_session():
        yield session


async def get_redis():
    """Get Redis client."""
    await redis_client.connect()
    try:
        yield redis_client
    finally:
        await redis_client.disconnect()


async def get_tenant_repo(db: AsyncSession = Depends(get_db)) -> TenantRepository:
    """Get tenant repository."""
    return TenantRepository(db)


async def get_user_repo(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository."""
    return UserRepository(db)


async def get_notification_repo(db: AsyncSession = Depends(get_db)) -> NotificationRepository:
    """Get notification repository."""
    return NotificationRepository(db)


async def get_delivery_repo(db: AsyncSession = Depends(get_db)) -> DeliveryRepository:
    """Get delivery repository."""
    return DeliveryRepository(db)


async def get_preference_repo(db: AsyncSession = Depends(get_db)) -> UserPreferenceRepository:
    """Get user preference repository."""
    return UserPreferenceRepository(db)


async def get_quiet_hours_repo(db: AsyncSession = Depends(get_db)) -> QuietHoursRepository:
    """Get quiet hours repository."""
    return QuietHoursRepository(db)


async def get_template_repo(db: AsyncSession = Depends(get_db)) -> TemplateRepository:
    """Get template repository."""
    return TemplateRepository(db)


async def get_webhook_config_repo(db: AsyncSession = Depends(get_db)) -> WebhookConfigRepository:
    """Get webhook config repository."""
    return WebhookConfigRepository(db)


async def get_preference_service(
    preference_repo: UserPreferenceRepository = Depends(get_preference_repo),
    quiet_hours_repo: QuietHoursRepository = Depends(get_quiet_hours_repo),
    redis_client = Depends(get_redis)
) -> PreferenceService:
    """Get preference service."""
    return PreferenceService(preference_repo, quiet_hours_repo)


async def get_template_service(
    template_repo: TemplateRepository = Depends(get_template_repo)
) -> TemplateService:
    """Get template service."""
    return TemplateService(template_repo)


async def get_channel_resolver() -> ChannelResolver:
    """Get channel resolver."""
    return ChannelResolver()


async def get_delivery_service(
    delivery_repo: DeliveryRepository = Depends(get_delivery_repo),
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    channel_resolver: ChannelResolver = Depends(get_channel_resolver),
    preference_service: PreferenceService = Depends(get_preference_service),
    template_service: TemplateService = Depends(get_template_service)
) -> DeliveryService:
    """Get delivery service."""
    return DeliveryService(
        delivery_repo=delivery_repo,
        notification_repo=notification_repo,
        user_repo=user_repo,
        tenant_repo=tenant_repo,
        channel_resolver=channel_resolver,
        preference_service=preference_service,
        template_service=template_service
    )


async def get_notification_service(
    notification_repo: NotificationRepository = Depends(get_notification_repo),
    delivery_repo: DeliveryRepository = Depends(get_delivery_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    channel_resolver: ChannelResolver = Depends(get_channel_resolver),
    preference_service: PreferenceService = Depends(get_preference_service),
    template_service: TemplateService = Depends(get_template_service),
    delivery_service: DeliveryService = Depends(get_delivery_service)
) -> NotificationService:
    """Get notification service."""
    return NotificationService(
        notification_repo=notification_repo,
        delivery_repo=delivery_repo,
        user_repo=user_repo,
        tenant_repo=tenant_repo,
        channel_resolver=channel_resolver,
        preference_service=preference_service,
        template_service=template_service,
        delivery_service=delivery_service
    )


async def get_delivery_service(
    delivery_repo: DeliveryRepository = Depends(get_delivery_repo)
) -> DeliveryService:
    """Get delivery service."""
    return DeliveryService(delivery_repo)


async def get_webhook_config_service(
    webhook_config_repo: WebhookConfigRepository = Depends(get_webhook_config_repo)
) -> WebhookConfigService:
    """Get webhook config service."""
    return WebhookConfigService(webhook_config_repo)


async def get_current_tenant(
    api_key: str,
    tenant_repo: TenantRepository = Depends(get_tenant_repo)
) -> Tenant:
    """Get current tenant from API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    
    # Hash the API key for comparison
    api_key_hash = hash_api_key(api_key)
    
    tenant = await tenant_repo.get_by_api_key(api_key_hash)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return tenant


def handle_notiflow_exceptions(func):
    """Decorator to handle NotiFlow exceptions and convert to HTTP responses."""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except NotiFlowError as e:
            # Map specific exceptions to HTTP status codes
            status_code_map = {
                UserNotFoundError: status.HTTP_404_NOT_FOUND,
                TenantNotFoundError: status.HTTP_404_NOT_FOUND,
                NoChannelsAvailableError: status.HTTP_400_BAD_REQUEST,
                TemplateNotFoundError: status.HTTP_404_NOT_FOUND,
                NotificationNotFoundError: status.HTTP_404_NOT_FOUND,
                DeliveryNotFoundError: status.HTTP_404_NOT_FOUND,
                WebhookConfigNotFoundError: status.HTTP_404_NOT_FOUND,
            }
            
            # Get status code or default to 500
            status_code = status_code_map.get(type(e), status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            raise HTTPException(
                status_code=status_code,
                detail=e.message,
                headers={"X-Error-Code": e.code}
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Handle unexpected exceptions
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
                headers={"X-Error-Code": "INTERNAL_ERROR"}
            )
    
    return wrapper
