"""
User repository with specialized queries.
"""

from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.user_preference import UserChannelPreference
from app.db.models.quiet_hours import QuietHours
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User, dict, dict]):
    """Repository for user operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_tenant_and_external(
        self,
        tenant_id: str,
        external_id: str
    ) -> Optional[User]:
        """Get user by tenant and external ID."""
        stmt = select(User).where(
            and_(
                User.tenant_id == tenant_id,
                User.external_id == external_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, phone: str) -> Optional[User]:
        """Get user by phone number."""
        stmt = select(User).where(User.phone == phone)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_contact(
        self,
        contact: str
    ) -> Optional[User]:
        """Get user by email or phone."""
        stmt = select(User).where(
            or_(
                User.email == contact,
                User.phone == contact,
                User.external_id == contact
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get multiple users for a tenant."""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def search_users(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Search users by display name, email, or external ID."""
        conditions = [
            or_(
                User.display_name.ilike(f"%{query}%"),
                User.email.ilike(f"%{query}%"),
                User.external_id.ilike(f"%{query}%")
            )
        ]
        
        if tenant_id:
            conditions.append(User.tenant_id == tenant_id)
        
        stmt = (
            select(User)
            .where(and_(*conditions))
            .order_by(User.display_name.asc(), User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_users_with_channel(
        self,
        channel: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """Get users who have a specific channel enabled."""
        stmt = (
            select(User)
            .join(User.channel_preferences)
            .where(
                and_(
                    UserChannelPreference.channel == channel,
                    UserChannelPreference.is_enabled == True
                )
            )
        )
        
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        
        stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def upsert_user(
        self,
        tenant_id: str,
        external_id: str,
        user_data: dict
    ) -> User:
        """Create or update a user."""
        # Try to find existing user
        existing_user = await self.get_by_tenant_and_external(
            tenant_id, external_id
        )
        
        if existing_user:
            # Update existing user
            return await self.update(existing_user, user_data)
        else:
            # Create new user
            user_data["tenant_id"] = tenant_id
            user_data["external_id"] = external_id
            return await self.create(user_data)
    
    async def count_by_tenant(self, tenant_id: str) -> int:
        """Count users for a tenant."""
        stmt = select(User).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
    
    async def get_active_users_count(
        self,
        tenant_id: Optional[str] = None
    ) -> int:
        """Count users with at least one enabled channel."""
        stmt = (
            select(User)
            .join(User.channel_preferences)
            .where(UserChannelPreference.is_enabled == True)
            .distinct()
        )
        
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
