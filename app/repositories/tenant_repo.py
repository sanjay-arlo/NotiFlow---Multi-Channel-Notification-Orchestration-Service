"""
Tenant repository with specialized queries.
"""

from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository[Tenant, dict, dict]):
    """Repository for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Tenant, db)
    
    async def get_by_api_key(self, api_key_hash: str) -> Optional[Tenant]:
        """Get tenant by API key hash."""
        stmt = select(Tenant).where(
            and_(
                Tenant.api_key_hash == api_key_hash,
                Tenant.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_api_key_prefix(self, prefix: str) -> Optional[Tenant]:
        """Get tenant by API key prefix."""
        stmt = select(Tenant).where(
            and_(
                Tenant.api_key_prefix == prefix,
                Tenant.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_tenants(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Get all active tenants."""
        stmt = (
            select(Tenant)
            .where(Tenant.is_active == True)
            .order_by(Tenant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_tenants(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Tenant]:
        """Search tenants by name."""
        stmt = (
            select(Tenant)
            .where(Tenant.name.ilike(f"%{query}%"))
            .order_by(Tenant.name.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_active(self) -> int:
        """Count active tenants."""
        stmt = select(Tenant).where(Tenant.is_active == True)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def update_api_key(self, id: str, api_key: str) -> Optional[Tenant]:
        """Update tenant API key."""
        tenant = await self.get(id)
        if tenant:
            tenant.set_api_key(api_key)
            await self.db.flush()
            await self.db.refresh(tenant)
        return tenant
    
    async def deactivate_tenant(self, id: str) -> Optional[Tenant]:
        """Deactivate a tenant."""
        return await self.update_by_id(id, {"is_active": False})
    
    async def activate_tenant(self, id: str) -> Optional[Tenant]:
        """Activate a tenant."""
        return await self.update_by_id(id, {"is_active": True})
    
    async def update_rate_limit(
        self,
        id: str,
        rate_limit: int
    ) -> Optional[Tenant]:
        """Update tenant rate limit."""
        return await self.update_by_id(id, {"rate_limit": rate_limit})
