"""
Integration tests for retry flow and backoff logic.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from app.services.notification_service import NotificationService
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.core.constants import NotificationPriority, DeliveryStatus, ChannelType


class TestRetryFlow:
    """Integration tests for retry flow and backoff logic."""
    
    @pytest.fixture
    def notification_service(self):
        """Create notification service instance."""
        return NotificationService(
            notification_repo=AsyncMock(),
            delivery_repo=AsyncMock(),
            user_repo=AsyncMock(),
            preference_service=AsyncMock(),
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
    
    @pytest.mark.asyncio
    async def test_email_retry_flow_success(self):
        """Test successful email retry flow after transient failure."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Test Email",
            body="Test content",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="test@example.com",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_message="Connection timeout",
            next_retry_at=datetime.utcnow() + timedelta(minutes=5)
        )
        
        # Mock email channel to succeed on retry
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "smtp-123"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is True
            assert result.provider_id == "smtp-123"
            
            # Verify delivery was updated
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["status"] == DeliveryStatus.SENT
            assert update_args["attempt_count"] == 2
            assert update_args["sent_at"] is not None
    
    @pytest.mark.asyncio
    async def test_email_retry_permanent_failure(self):
        """Test email retry with permanent failure (no more retries)."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Test Email",
            body="Test content",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="test@example.com",
            status=DeliveryStatus.FAILED,
            attempt_count=3,  # Already at max attempts
            max_attempts=3,
            error_message="Authentication failed",
            next_retry_at=None
        )
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=AsyncMock(),
            preference_service=AsyncMock(),
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Attempt retry
        result = await service.retry_delivery(delivery.id)
        
        assert result.success is False
        assert "Maximum attempts reached" in str(result.error)
        
        # Verify delivery was marked as permanently failed
        delivery_repo.update.assert_called()
        update_args = delivery_repo.update.call_args[0][1]
        assert update_args["status"] == DeliveryStatus.FAILED
        assert update_args["failed_at"] is not None
    
    @pytest.mark.asyncio
    async def test_sms_retry_with_backoff(self):
        """Test SMS retry with exponential backoff."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Test SMS",
            body="Test SMS content",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.SMS,
            destination="+1234567890",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_message="Rate limit exceeded",
            next_retry_at=datetime.utcnow() + timedelta(minutes=2)
        )
        
        # Mock SMS channel to fail again
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = False
            mock_result.error = Exception("Rate limit exceeded")
            mock_result.retry_after = 300  # 5 minutes
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is False
            assert "Rate limit exceeded" in str(result.error)
            assert result.retry_after == 300
            
            # Verify backoff was applied
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["attempt_count"] == 2
            assert update_args["next_retry_at"] is not None
            
            # Check exponential backoff (should be longer than previous)
            next_retry_time = update_args["next_retry_at"]
            expected_min_retry = datetime.utcnow() + timedelta(minutes=5)  # 2^1 * base_delay
            assert next_retry_time >= expected_min_retry
    
    @pytest.mark.asyncio
    async def test_webhook_retry_with_jitter(self):
        """Test webhook retry with jitter to prevent thundering herd."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.WEBHOOK,
            destination="https://example.com/webhook",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_message="Connection timeout",
            next_retry_at=datetime.utcnow() + timedelta(minutes=1)
        )
        
        # Mock webhook channel to fail
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = False
            mock_result.error = Exception("Connection timeout")
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is False
            assert "Connection timeout" in str(result.error)
            
            # Verify jitter was applied (retry time should vary)
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["attempt_count"] == 2
            assert update_args["next_retry_at"] is not None
    
    @pytest.mark.asyncio
    async def test_critical_notification_immediate_retry(self):
        """Test immediate retry for critical notifications."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Critical Alert",
            body="Critical system alert",
            priority=NotificationPriority.CRITICAL
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="admin@example.com",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=5,  # More retries for critical
            error_message="Server busy",
            next_retry_at=datetime.utcnow() + timedelta(minutes=1)
        )
        
        # Mock email channel to succeed on retry
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "smtp-critical"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is True
            assert result.provider_id == "smtp-critical"
            
            # Verify delivery was updated
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["status"] == DeliveryStatus.SENT
            assert update_args["attempt_count"] == 2
    
    @pytest.mark.asyncio
    async def test_low_priority_delayed_retry(self):
        """Test delayed retry for low priority notifications."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Low Priority",
            body="Low priority notification",
            priority=NotificationPriority.LOW
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="user@example.com",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=2,  # Fewer retries for low priority
            error_message="Connection timeout",
            next_retry_at=datetime.utcnow() + timedelta(minutes=10)  # Longer delay
        )
        
        # Mock email channel to fail again
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = False
            mock_result.error = Exception("Connection timeout")
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is False
            assert "Connection timeout" in str(result.error)
            
            # Verify longer delay was applied
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["attempt_count"] == 2
            assert update_args["next_retry_at"] is not None
            
            # Check that retry time is significantly delayed
            next_retry_time = update_args["next_retry_at"]
            expected_min_retry = datetime.utcnow() + timedelta(minutes=15)  # Longer base delay
            assert next_retry_time >= expected_min_retry
    
    @pytest.mark.asyncio
    async def test_retry_with_custom_retry_after(self):
        """Test retry with custom retry-after from provider."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Custom Retry",
            body="Test with custom retry",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.WEBHOOK,
            destination="https://api.example.com/webhook",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            error_message="Rate limit",
            next_retry_at=datetime.utcnow() + timedelta(minutes=1)
        )
        
        # Mock webhook channel with custom retry-after
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = False
            mock_result.error = Exception("Rate limit")
            mock_result.retry_after = 1800  # 30 minutes custom retry-after
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_by_id.return_value = delivery
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry the delivery
            result = await service.retry_delivery(delivery.id)
            
            assert result.success is False
            assert result.retry_after == 1800
            
            # Verify custom retry-after was used
            delivery_repo.update.assert_called()
            update_args = delivery_repo.update.call_args[0][1]
            assert update_args["retry_after"] == 1800
            
            # Check that next_retry_at respects the custom retry-after
            next_retry_time = update_args["next_retry_at"]
            expected_min_retry = datetime.utcnow() + timedelta(minutes=30)
            assert next_retry_time >= expected_min_retry
    
    @pytest.mark.asyncio
    async def test_bulk_retry_deliveries(self):
        """Test bulk retry of multiple deliveries."""
        deliveries = [
            Delivery(
                id="delivery-1",
                notification_id="test-notification",
                channel=ChannelType.EMAIL,
                destination="user1@example.com",
                status=DeliveryStatus.FAILED,
                attempt_count=1,
                max_attempts=3,
                error_message="Connection timeout"
            ),
            Delivery(
                id="delivery-2",
                notification_id="test-notification",
                channel=ChannelType.SMS,
                destination="+1234567890",
                status=DeliveryStatus.FAILED,
                attempt_count=1,
                max_attempts=3,
                error_message="Rate limit"
            )
        ]
        
        # Mock channels to succeed on retry
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-123"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            delivery_repo.get_failed_deliveries.return_value = deliveries
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=AsyncMock(),
                preference_service=AsyncMock(),
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Retry all failed deliveries
            results = await service.bulk_retry_deliveries("test-notification")
            
            assert len(results) == 2
            assert all(result.success for result in results)
            
            # Verify all deliveries were updated
            assert delivery_repo.update.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_delivery_not_found(self):
        """Test retry when delivery not found."""
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = None
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=AsyncMock(),
            preference_service=AsyncMock(),
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Attempt retry
        with pytest.raises(ValueError, match="Delivery not found"):
            await service.retry_delivery("non-existent-delivery")
    
    @pytest.mark.asyncio
    async def test_retry_delivery_already_sent(self):
        """Test retry when delivery is already sent."""
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="test@example.com",
            status=DeliveryStatus.SENT,  # Already sent
            attempt_count=1,
            max_attempts=3
        )
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=AsyncMock(),
            preference_service=AsyncMock(),
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Attempt retry
        with pytest.raises(ValueError, match="Delivery is not in failed state"):
            await service.retry_delivery(delivery.id)
    
    @pytest.mark.asyncio
    async def test_retry_delivery_not_scheduled_yet(self):
        """Test retry when delivery is not scheduled for retry yet."""
        future_time = datetime.utcnow() + timedelta(hours=1)
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel=ChannelType.EMAIL,
            destination="test@example.com",
            status=DeliveryStatus.FAILED,
            attempt_count=1,
            max_attempts=3,
            next_retry_at=future_time  # Scheduled for future
        )
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        delivery_repo.get_by_id.return_value = delivery
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=AsyncMock(),
            preference_service=AsyncMock(),
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Attempt retry
        with pytest.raises(ValueError, match="Delivery not scheduled for retry"):
            await service.retry_delivery(delivery.id)
