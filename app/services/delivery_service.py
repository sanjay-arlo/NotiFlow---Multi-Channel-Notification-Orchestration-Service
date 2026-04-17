"""
Delivery management service.
"""

from datetime import datetime
from typing import Dict, List, Optional

from app.core.exceptions import DeliveryNotFoundError
from app.db.models.delivery import Delivery
from app.db.models.delivery_event import DeliveryEvent
from app.db.models.notification import Notification
from app.repositories.delivery_repo import DeliveryRepository
from app.utils.redis_client import redis_client
from app.core.constants import (
    REDIS_CHANNEL_RATE_LIMIT_TTL,
    EventType
)


class DeliveryService:
    """Service for managing delivery operations and events."""
    
    def __init__(self, delivery_repo: DeliveryRepository):
        self.delivery_repo = delivery_repo
    
    async def create_delivery(
        self,
        notification_id: str,
        channel: str,
        destination: str,
        max_attempts: Optional[int] = None
    ) -> Delivery:
        """Create a new delivery record."""
        from app.core.constants import CHANNEL_RETRY_CONFIG
        
        # Get max attempts from channel config
        if max_attempts is None:
            config = CHANNEL_RETRY_CONFIG.get(channel, {})
            max_attempts = config.get("max_attempts", 3)
        else:
            max_attempts = max_attempts
        
        delivery_data = {
            "notification_id": notification_id,
            "channel": channel,
            "destination": destination,
            "status": "pending",
            "max_attempts": max_attempts,
            "attempt_count": 0
        }
        
        return await self.delivery_repo.create(delivery_data)
    
    async def get_delivery(
        self,
        delivery_id: str,
        include_events: bool = True
    ) -> Optional[Delivery]:
        """Get delivery with optional events."""
        if include_events:
            return await self.delivery_repo.get_with_events(delivery_id)
        else:
            return await self.delivery_repo.get(delivery_id)
    
    async def update_delivery_status(
        self,
        delivery_id: str,
        status: str,
        provider_id: Optional[str] = None,
        provider_response: Optional[Dict] = None,
        error: Optional[str] = None,
        next_retry_at: Optional[datetime] = None
    ) -> Optional[Delivery]:
        """Update delivery status and create event."""
        from app.core.constants import DeliveryStatus
        
        # Get current delivery
        delivery = await self.delivery_repo.get(delivery_id)
        if not delivery:
            raise DeliveryNotFoundError(delivery_id)
        
        old_status = delivery.status
        
        # Update delivery based on status
        if status == DeliveryStatus.PROCESSING:
            delivery = await self.delivery_repo.mark_as_processing(delivery_id)
        
        elif status == DeliveryStatus.SENT:
            if not provider_id:
                raise ValueError("provider_id required for sent status")
            delivery = await self.delivery_repo.mark_as_sent(
                delivery_id, provider_id, provider_response
            )
        
        elif status == DeliveryStatus.DELIVERED:
            delivery = await self.delivery_repo.mark_as_delivered(delivery_id)
        
        elif status == DeliveryStatus.FAILED:
            if not error:
                raise ValueError("error message required for failed status")
            delivery = await self.delivery_repo.mark_as_failed(
                delivery_id, error, next_retry_at
            )
        
        elif status == DeliveryStatus.BOUNCED:
            if not error:
                raise ValueError("bounce reason required for bounced status")
            delivery = await self.delivery_repo.mark_as_bounced(delivery_id, error)
        
        elif status == DeliveryStatus.CANCELLED:
            delivery = await self.delivery_repo.mark_as_cancelled(delivery_id)
        
        # Create delivery event
        await self._create_delivery_event(
            delivery_id,
            old_status,
            status,
            EventType.STATUS_CHANGE,
            {
                "provider_id": provider_id,
                "error": error,
                "next_retry_at": next_retry_at.isoformat() if next_retry_at else None
            }
        )
        
        return delivery
    
    async def process_delivery_result(
        self,
        delivery_id: str,
        result: "SendResult"
    ) -> Delivery:
        """Process delivery attempt result."""
        if result.success:
            return await self.update_delivery_status(
                delivery_id,
                "sent",
                provider_id=result.provider_id,
                provider_response=result.raw_response
            )
        else:
            from app.utils.retry import calculate_next_retry_at
            from app.channels.registry import get_channel_class
            
            # Calculate next retry time
            channel_class = get_channel_class(result.channel_type)
            next_retry_at = calculate_next_retry_at(
                attempt_number=0,  # Will be updated in repo
                channel_type=result.channel_type,
                retry_after=result.retry_after
            )
            
            return await self.update_delivery_status(
                delivery_id,
                "failed",
                error=result.error,
                next_retry_at=next_retry_at
            )
    
    async def cancel_pending_deliveries(
        self,
        notification_id: str
    ) -> List[Delivery]:
        """Cancel all pending deliveries for a notification."""
        pending_deliveries = await self.delivery_repo.get_by_notification(
            notification_id
        )
        
        cancelled_deliveries = []
        for delivery in pending_deliveries:
            if delivery.status == "pending":
                cancelled_delivery = await self.update_delivery_status(
                    delivery.id, "cancelled"
                )
                cancelled_deliveries.append(cancelled_delivery)
        
        return cancelled_deliveries
    
    async def get_deliveries_for_retry(
        self,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries that should be retried now."""
        return await self.delivery_repo.get_failed_deliveries_for_retry(limit)
    
    async def get_stuck_deliveries(
        self,
        minutes: int = 5,
        limit: int = 100
    ) -> List[Delivery]:
        """Get deliveries stuck in processing state."""
        return await self.delivery_repo.get_stuck_deliveries(minutes, limit)
    
    async def get_delivery_stats(
        self,
        tenant_id: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict:
        """Get comprehensive delivery statistics."""
        return await self.delivery_repo.get_delivery_stats(
            from_date, to_date, tenant_id
        )
    
    async def check_rate_limit(
        self,
        user_id: str,
        channel: str
    ) -> bool:
        """Check if user has exceeded rate limit for channel."""
        try:
            # Get current count from Redis sorted set
            now_timestamp = int(datetime.utcnow().timestamp() * 1000)
            one_hour_ago = now_timestamp - (3600 * 1000)  # 1 hour ago
            
            # Remove old entries
            await redis_client.zremrangebyscore(
                f"channel:ratelimit:{user_id}:{channel}",
                0,
                one_hour_ago
            )
            
            # Get current count
            count = await redis_client.zcard(
                f"channel:ratelimit:{user_id}:{channel}"
            )
            
            # Rate limits per channel (configurable)
            rate_limits = {
                "email": 20,    # 20 emails per hour
                "sms": 10,      # 10 SMS per hour
                "webhook": 100   # 100 webhooks per hour
            }
            
            max_requests = rate_limits.get(channel, 100)
            return count >= max_requests
        
        except Exception:
            # If Redis fails, allow the request
            return False
    
    async def record_rate_limit_request(
        self,
        user_id: str,
        channel: str
    ) -> None:
        """Record a delivery attempt for rate limiting."""
        try:
            now_timestamp = int(datetime.utcnow().timestamp() * 1000)
            await redis_client.zadd(
                f"channel:ratelimit:{user_id}:{channel}",
                {str(now_timestamp): now_timestamp}
            )
            
            # Set TTL to expire old entries
            await redis_client.delete(f"channel:ratelimit:{user_id}:{channel}")
            # Re-add with TTL (this is a workaround for Redis zadd with TTL)
            await redis_client.zadd(
                f"channel:ratelimit:{user_id}:{channel}",
                {str(now_timestamp): now_timestamp}
            )
        except Exception:
            pass  # Rate limiting failures shouldn't break functionality
    
    async def queue_delivery_task(self, delivery_id: str) -> None:
        """Queue Celery task for delivery processing."""
        from app.workers.tasks import deliver_notification
        
        # Get delivery to determine queue
        delivery = await self.delivery_repo.get(delivery_id)
        if not delivery:
            return
        
        # Get notification to determine priority
        notification = await self.delivery_repo.db.execute(
            f"SELECT priority, channel FROM notifications WHERE id = '{delivery.notification_id}'"
        )
        notification_data = notification.fetchone()
        
        if not notification_data:
            return
        
        # Determine queue based on priority and channel
        queue_name = self._get_queue_name(
            notification_data.priority, delivery.channel
        )
        
        # Queue task
        deliver_notification.apply_async(
            args=[str(delivery_id)],
            queue=queue_name
        )
    
    def _get_queue_name(self, priority: str, channel: str) -> str:
        """Get Celery queue name based on priority and channel."""
        from app.core.constants import PRIORITY_QUEUE_ROUTING
        
        # Check specific routing first
        key = (priority, channel)
        if key in PRIORITY_QUEUE_ROUTING:
            return PRIORITY_QUEUE_ROUTING[key]
        
        # Check wildcard routing
        key = (priority, "*")
        if key in PRIORITY_QUEUE_ROUTING:
            return PRIORITY_QUEUE_ROUTING[key]
        
        return "default"
    
    async def _create_delivery_event(
        self,
        delivery_id: str,
        from_status: Optional[str],
        to_status: str,
        event_type: str,
        details: Optional[Dict] = None
    ) -> DeliveryEvent:
        """Create a delivery event record."""
        event_data = {
            "delivery_id": delivery_id,
            "notification_id": delivery_id,  # Will be updated in DB
            "from_status": from_status,
            "to_status": to_status,
            "event_type": event_type,
            "details": details or {}
        }
        
        return await self.delivery_repo.db.execute(
            "INSERT INTO delivery_events (delivery_id, notification_id, from_status, to_status, event_type, details, created_at) VALUES (:delivery_id, :notification_id, :from_status, :to_status, :event_type, :details, NOW())",
            event_data
        )
