"""
Notification repository with specialized queries.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification, dict, dict]):
    """Repository for notification operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Notification, db)
    
    async def get_with_deliveries(self, id: str) -> Optional[Notification]:
        """Get notification with its deliveries."""
        stmt = (
            select(Notification)
            .options(selectinload(Notification.deliveries))
            .where(Notification.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_tenant_and_external_id(
        self,
        tenant_id: str,
        user_external_id: str
    ) -> List[Notification]:
        """Get notifications for a tenant's user by external ID."""
        stmt = (
            select(Notification)
            .join(Notification.user)
            .where(
                and_(
                    Notification.tenant_id == tenant_id,
                    Notification.user.has(external_id=user_external_id)
                )
            )
            .order_by(Notification.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_pending_notifications(
        self,
        limit: int = 100
    ) -> List[Notification]:
        """Get pending notifications for processing."""
        stmt = (
            select(Notification)
            .where(Notification.status.in_(["queued", "processing"]))
            .order_by(Notification.priority.desc(), Notification.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_scheduled_notifications(
        self,
        before: datetime,
        limit: int = 100
    ) -> List[Notification]:
        """Get scheduled notifications that should be sent now."""
        stmt = (
            select(Notification)
            .where(
                and_(
                    Notification.status == "queued",
                    Notification.scheduled_at <= before,
                    Notification.scheduled_at.is_not(None)
                )
            )
            .order_by(Notification.scheduled_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications by status."""
        stmt = select(Notification).where(Notification.status == status)
        
        if tenant_id:
            stmt = stmt.where(Notification.tenant_id == tenant_id)
        
        stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_priority(
        self,
        priority: str,
        limit: int = 100
    ) -> List[Notification]:
        """Get notifications by priority."""
        stmt = (
            select(Notification)
            .where(Notification.priority == priority)
            .where(Notification.status.in_(["queued", "processing"]))
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_completed_notifications(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Notification]:
        """Get completed notifications within date range."""
        conditions = [
            Notification.status.in_(["delivered", "failed", "cancelled"])
        ]
        
        if from_date:
            conditions.append(Notification.completed_at >= from_date)
        
        if to_date:
            conditions.append(Notification.completed_at <= to_date)
        
        if tenant_id:
            conditions.append(Notification.tenant_id == tenant_id)
        
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.completed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_status(
        self,
        tenant_id: Optional[str] = None
    ) -> dict[str, int]:
        """Count notifications grouped by status."""
        stmt = select(
            Notification.status,
            func.count(Notification.id).label("count")
        )
        
        if tenant_id:
            stmt = stmt.where(Notification.tenant_id == tenant_id)
        
        stmt = stmt.group_by(Notification.status)
        result = await self.db.execute(stmt)
        return {row.status: row.count for row in result}
    
    async def count_by_priority(
        self,
        tenant_id: Optional[str] = None
    ) -> dict[str, int]:
        """Count notifications grouped by priority."""
        stmt = select(
            Notification.priority,
            func.count(Notification.id).label("count")
        )
        
        if tenant_id:
            stmt = stmt.where(Notification.tenant_id == tenant_id)
        
        stmt = stmt.group_by(Notification.priority)
        result = await self.db.execute(stmt)
        return {row.priority: row.count for row in result}
    
    async def update_status(
        self,
        id: str,
        status: str,
        completed_at: Optional[datetime] = None
    ) -> Optional[Notification]:
        """Update notification status."""
        update_data = {"status": status}
        if completed_at:
            update_data["completed_at"] = completed_at
        
        return await self.update_by_id(id, update_data)
    
    async def mark_as_processing(self, id: str) -> Optional[Notification]:
        """Mark notification as being processed."""
        return await self.update_status(id, "processing")
    
    async def mark_as_sent(self, id: str) -> Optional[Notification]:
        """Mark notification as sent."""
        return await self.update_status(id, "sent")
    
    async def mark_as_delivered(self, id: str) -> Optional[Notification]:
        """Mark notification as delivered."""
        return await self.update_status(id, "delivered", datetime.utcnow())
    
    async def mark_as_failed(self, id: str) -> Optional[Notification]:
        """Mark notification as failed."""
        return await self.update_status(id, "failed", datetime.utcnow())
    
    async def mark_as_cancelled(self, id: str) -> Optional[Notification]:
        """Mark notification as cancelled."""
        return await self.update_status(id, "cancelled", datetime.utcnow())
    
    async def search_notifications(
        self,
        query: str,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Notification]:
        """Search notifications by title or body."""
        conditions = [
            or_(
                Notification.title.ilike(f"%{query}%"),
                Notification.body.ilike(f"%{query}%")
            )
        ]
        
        if tenant_id:
            conditions.append(Notification.tenant_id == tenant_id)
        
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(Notification.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
