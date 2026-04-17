"""
Delivery repository with specialized queries.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.delivery import Delivery
from app.db.models.delivery_event import DeliveryEvent
from app.repositories.base import BaseRepository


class DeliveryRepository(BaseRepository[Delivery, dict, dict]):
    """Repository for delivery operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Delivery, db)
    
    async def get_with_events(self, id: str) -> Optional[Delivery]:
        """Get delivery with its events."""
        stmt = (
            select(Delivery)
            .options(selectinload(Delivery.events))
            .where(Delivery.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_notification(self, notification_id: str) -> List[Delivery]:
        """Get all deliveries for a notification."""
        stmt = (
            select(Delivery)
            .where(Delivery.notification_id == notification_id)
            .order_by(Delivery.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_pending_deliveries(
        self,
        channel: Optional[str] = None,
        limit: int = 100
    ) -> List[Delivery]:
        """Get pending deliveries for processing."""
        conditions = [Delivery.status == "pending"]
        
        if channel:
            conditions.append(Delivery.channel == channel)
        
        stmt = (
            select(Delivery)
            .where(and_(*conditions))
            .order_by(Delivery.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_failed_deliveries_for_retry(
        self,
        limit: int = 100
    ) -> List[Delivery]:
        """Get failed deliveries that should be retried now."""
        stmt = (
            select(Delivery)
            .where(
                and_(
                    Delivery.status == "failed",
                    Delivery.next_retry_at <= datetime.utcnow(),
                    Delivery.attempt_count < Delivery.max_attempts
                )
            )
            .order_by(Delivery.next_retry_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_stuck_deliveries(
        self,
        minutes: int = 5,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries stuck in processing state."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        stmt = (
            select(Delivery)
            .where(
                and_(
                    Delivery.status == "processing",
                    Delivery.last_attempt_at <= cutoff_time
                )
            )
            .order_by(Delivery.last_attempt_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_status(
        self,
        status: str,
        channel: Optional[str] = None,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries by status."""
        conditions = [Delivery.status == status]
        
        if channel:
            conditions.append(Delivery.channel == channel)
        
        if tenant_id:
            # Join with notification to filter by tenant
            stmt = (
                select(Delivery)
                .join(Delivery.notification)
                .where(and_(*conditions))
                .where(Delivery.notification.has(tenant_id=tenant_id))
                .order_by(Delivery.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        else:
            stmt = (
                select(Delivery)
                .where(and_(*conditions))
                .order_by(Delivery.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_channel(
        self,
        channel: str,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries by channel."""
        conditions = [Delivery.channel == channel]
        
        if status:
            conditions.append(Delivery.status == status)
        
        stmt = (
            select(Delivery)
            .where(and_(*conditions))
            .order_by(Delivery.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_deliveries_by_date_range(
        self,
        from_date: datetime,
        to_date: datetime,
        channel: Optional[str] = None,
        tenant_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries within date range."""
        conditions = [
            Delivery.created_at >= from_date,
            Delivery.created_at <= to_date
        ]
        
        if channel:
            conditions.append(Delivery.channel == channel)
        
        if tenant_id:
            conditions.append(Delivery.notification.has(tenant_id=tenant_id))
        
        stmt = (
            select(Delivery)
            .where(and_(*conditions))
            .order_by(Delivery.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def count_by_status(
        self,
        tenant_id: Optional[str] = None
    ) -> dict[str, int]:
        """Count deliveries grouped by status."""
        stmt = select(
            Delivery.status,
            func.count(Delivery.id).label("count")
        )
        
        if tenant_id:
            stmt = stmt.where(Delivery.notification.has(tenant_id=tenant_id))
        
        stmt = stmt.group_by(Delivery.status)
        result = await self.db.execute(stmt)
        return {row.status: row.count for row in result}
    
    async def count_by_channel(
        self,
        tenant_id: Optional[str] = None
    ) -> dict[str, int]:
        """Count deliveries grouped by channel."""
        stmt = select(
            Delivery.channel,
            func.count(Delivery.id).label("count")
        )
        
        if tenant_id:
            stmt = stmt.where(Delivery.notification.has(tenant_id=tenant_id))
        
        stmt = stmt.group_by(Delivery.channel)
        result = await self.db.execute(stmt)
        return {row.channel: row.count for row in result}
    
    async def get_delivery_stats(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        tenant_id: Optional[str] = None
    ) -> dict:
        """Get comprehensive delivery statistics."""
        conditions = []
        
        if from_date:
            conditions.append(Delivery.created_at >= from_date)
        
        if to_date:
            conditions.append(Delivery.created_at <= to_date)
        
        if tenant_id:
            conditions.append(Delivery.notification.has(tenant_id=tenant_id))
        
        # Get counts by status and channel
        stmt = select(
            Delivery.channel,
            Delivery.status,
            func.count(Delivery.id).label("count")
        )
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.group_by(Delivery.channel, Delivery.status)
        result = await self.db.execute(stmt)
        
        # Organize stats
        stats = {
            "by_channel": {},
            "by_status": {},
            "total": 0
        }
        
        for row in result:
            channel = row.channel
            status = row.status
            count = row.count
            
            # Update channel stats
            if channel not in stats["by_channel"]:
                stats["by_channel"][channel] = {
                    "total": 0,
                    "delivered": 0,
                    "failed": 0,
                    "pending": 0,
                    "processing": 0
                }
            
            stats["by_channel"][channel]["total"] += count
            stats["by_channel"][channel][status] = (
                stats["by_channel"][channel].get(status, 0) + count
            )
            
            # Update status stats
            if status not in stats["by_status"]:
                stats["by_status"][status] = 0
            stats["by_status"][status] += count
            
            # Update total
            stats["total"] += count
        
        return stats
    
    async def update_status(
        self,
        id: str,
        status: str,
        **kwargs
    ) -> Optional[Delivery]:
        """Update delivery status and additional fields."""
        update_data = {"status": status}
        update_data.update(kwargs)
        
        return await self.update_by_id(id, update_data)
    
    async def mark_as_processing(self, id: str) -> Optional[Delivery]:
        """Mark delivery as being processed."""
        return await self.update_status(
            id, "processing",
            last_attempt_at=datetime.utcnow()
        )
    
    async def mark_as_sent(
        self,
        id: str,
        provider_id: str,
        provider_response: Optional[dict] = None
    ) -> Optional[Delivery]:
        """Mark delivery as sent."""
        return await self.update_status(
            id, "sent",
            provider_id=provider_id,
            provider_response=provider_response,
            sent_at=datetime.utcnow(),
            attempt_count=Delivery.attempt_count + 1,
            last_attempt_at=datetime.utcnow()
        )
    
    async def mark_as_delivered(self, id: str) -> Optional[Delivery]:
        """Mark delivery as delivered."""
        return await self.update_status(
            id, "delivered",
            delivered_at=datetime.utcnow()
        )
    
    async def mark_as_failed(
        self,
        id: str,
        error: str,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[Delivery]:
        """Mark delivery as failed."""
        return await self.update_status(
            id, "failed",
            last_error=error,
            next_retry_at=next_retry_at,
            attempt_count=Delivery.attempt_count + 1,
            last_attempt_at=datetime.utcnow()
        )
    
    async def mark_as_bounced(
        self,
        id: str,
        reason: str
    ) -> Optional[Delivery]:
        """Mark delivery as bounced."""
        return await self.update_status(
            id, "bounced",
            bounce_reason=reason,
            bounced_at=datetime.utcnow(),
            next_retry_at=None
        )
    
    async def mark_as_cancelled(self, id: str) -> Optional[Delivery]:
        """Mark delivery as cancelled."""
        return await self.update_status(id, "cancelled")
