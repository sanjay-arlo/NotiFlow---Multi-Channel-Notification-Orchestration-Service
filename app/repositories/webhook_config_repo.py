"""
Webhook configuration repository with specialized queries.
"""

from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.webhook_config import WebhookConfig
from app.repositories.base import BaseRepository


class WebhookConfigRepository(BaseRepository[WebhookConfig, dict, dict]):
    """Repository for webhook configuration operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(WebhookConfig, db)
    
    async def get_by_tenant_and_name(
        self,
        tenant_id: str,
        name: str
    ) -> Optional[WebhookConfig]:
        """Get webhook config by tenant and name."""
        stmt = select(WebhookConfig).where(
            and_(
                WebhookConfig.tenant_id == tenant_id,
                WebhookConfig.name == name
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi_by_tenant(
        self,
        tenant_id: str,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get webhook configs for a tenant."""
        conditions = [WebhookConfig.tenant_id == tenant_id]
        
        if active_only:
            conditions.append(WebhookConfig.is_active == True)
        
        stmt = (
            select(WebhookConfig)
            .where(and_(*conditions))
            .order_by(WebhookConfig.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_webhook_configs(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Search webhook configs by name or URL."""
        conditions = [
            or_(
                WebhookConfig.name.ilike(f"%{query}%"),
                WebhookConfig.url.ilike(f"%{query}%")
            )
        ]
        
        if tenant_id:
            conditions.append(WebhookConfig.tenant_id == tenant_id)
        
        stmt = (
            select(WebhookConfig)
            .where(and_(*conditions))
            .order_by(WebhookConfig.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_healthy_webhooks(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get healthy webhook configs."""
        conditions = [WebhookConfig.is_active == True]
        
        if tenant_id:
            conditions.append(WebhookConfig.tenant_id == tenant_id)
        
        # Consider healthy if failure count < 5
        stmt = (
            select(WebhookConfig)
            .where(and_(*conditions))
            .where(WebhookConfig.failure_count < 5)
            .order_by(WebhookConfig.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_unhealthy_webhooks(
        self,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get unhealthy webhook configs."""
        conditions = [WebhookConfig.is_active == True]
        
        if tenant_id:
            conditions.append(WebhookConfig.tenant_id == tenant_id)
        
        # Consider unhealthy if failure count >= 5
        stmt = (
            select(WebhookConfig)
            .where(and_(*conditions))
            .where(WebhookConfig.failure_count >= 5)
            .order_by(WebhookConfig.failure_count.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_tenant(
        self,
        tenant_id: str,
        active_only: bool = True
    ) -> int:
        """Count webhook configs for a tenant."""
        conditions = [WebhookConfig.tenant_id == tenant_id]
        
        if active_only:
            conditions.append(WebhookConfig.is_active == True)
        
        stmt = select(WebhookConfig).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def record_success(self, id: str) -> Optional[WebhookConfig]:
        """Record successful webhook delivery."""
        webhook_config = await self.get(id)
        if webhook_config:
            webhook_config.record_success()
            await self.db.flush()
            await self.db.refresh(webhook_config)
        return webhook_config
    
    async def record_failure(self, id: str) -> Optional[WebhookConfig]:
        """Record failed webhook delivery."""
        webhook_config = await self.get(id)
        if webhook_config:
            webhook_config.record_failure()
            await self.db.flush()
            await self.db.refresh(webhook_config)
        return webhook_config
    
    async def reset_failure_count(self, id: str) -> Optional[WebhookConfig]:
        """Reset failure count for webhook config."""
        return await self.update_by_id(id, {"failure_count": 0})
    
    async def deactivate_webhook(self, id: str) -> Optional[WebhookConfig]:
        """Deactivate webhook config."""
        return await self.update_by_id(id, {"is_active": False})
    
    async def activate_webhook(self, id: str) -> Optional[WebhookConfig]:
        """Activate webhook config."""
        return await self.update_by_id(id, {"is_active": True})
    
    async def update_config(
        self,
        id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        secret: Optional[str] = None,
        headers: Optional[dict] = None,
        max_retries: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Optional[WebhookConfig]:
        """Update webhook configuration."""
        update_data = {}
        
        if name is not None:
            update_data["name"] = name
        if url is not None:
            update_data["url"] = url
        if secret is not None:
            update_data["secret"] = secret
        if headers is not None:
            update_data["headers"] = headers
        if max_retries is not None:
            update_data["max_retries"] = max_retries
        if timeout_seconds is not None:
            update_data["timeout_seconds"] = timeout_seconds
        
        return await self.update_by_id(id, update_data)
