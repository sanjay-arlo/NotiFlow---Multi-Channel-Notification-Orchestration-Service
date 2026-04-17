"""
Integration tests for bulk notification sending functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from app.services.notification_service import NotificationService
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.core.constants import NotificationPriority, DeliveryStatus, ChannelType


class TestBulkSend:
    """Integration tests for bulk notification sending functionality."""
    
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
    async def test_bulk_send_success(self):
        """Test successful bulk notification sending."""
        user_ids = ["user-1", "user-2", "user-3"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            },
            "user-3": {
                "id": "user-3",
                "external_id": "user-3",
                "email": "user3@example.com",
                "phone": "+12345678903",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": False, "webhook": True},
            "user-3": {"email": False, "sms": True, "webhook": True}
        }
        
        # Mock channels
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
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup user repo mock
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"], users_data["user-3"]
            ]
            
            # Setup preference service mock
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Bulk Test",
                body="This is a bulk notification",
                priority=NotificationPriority.NORMAL
            )
            
            assert result.success is True
            assert result.total == 3
            assert result.queued == 3
            assert result.failed == 0
            assert result.batch_id is not None
            
            # Verify user lookup
            user_repo.get_multiple_by_external_ids.assert_called_once_with("test-tenant", user_ids)
            
            # Verify preference lookup
            preference_service.get_multiple_user_preferences.assert_called_once_with(["user-1", "user-2", "user-3"])
            
            # Verify notifications were created
            assert notification_repo.create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_template(self):
        """Test bulk notification sending with template."""
        user_ids = ["user-1", "user-2"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock template
        template = AsyncMock()
        template.email_subject = "Welcome {{ name }}!"
        template.email_body = "<h1>Welcome {{ name }}!</h1><p>{{ message }}</p>"
        template.sms_body = "Welcome {{ name }}! {{ message }}"
        template.webhook_payload = '{"event": "welcome", "name": "{{ name }}", "message": "{{ message }}"}'
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-template"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            template_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            template_service.get_template.return_value = template
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=template_service,
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification with template
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                template_slug="welcome-template",
                template_variables={
                    "name": "John Doe",
                    "message": "Thanks for joining!"
                },
                priority=NotificationPriority.NORMAL
            )
            
            assert result.success is True
            assert result.total == 2
            assert result.queued == 2
            assert result.failed == 0
            
            # Verify template was retrieved
            template_service.get_template.assert_called_once_with("test-tenant", "welcome-template")
    
    @pytest.mark.asyncio
    async def test_bulk_send_partial_failure(self):
        """Test bulk notification sending with partial failures."""
        user_ids = ["user-1", "user-2", "user-3", "user-4"]
        
        # Mock user data (user-3 not found)
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            },
            "user-4": {
                "id": "user-4",
                "external_id": "user-4",
                "email": "user4@example.com",
                "phone": "+12345678904",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True},
            "user-4": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-partial"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"], users_data["user-4"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Bulk Partial",
                body="This is a partial bulk notification",
                priority=NotificationPriority.NORMAL
            )
            
            assert result.success is True
            assert result.total == 4
            assert result.queued == 3
            assert result.failed == 1
            assert len(result.errors) == 1
            assert "user-3" in str(result.errors[0])
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_priority_routing(self):
        """Test bulk notification sending with priority routing."""
        user_ids = ["user-1", "user-2"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "admin@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-critical"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send critical bulk notification
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Critical Bulk",
                body="Critical bulk notification",
                priority=NotificationPriority.CRITICAL
            )
            
            assert result.success is True
            assert result.total == 2
            assert result.queued == 2
            assert result.failed == 0
            
            # Verify critical notifications were created
            for call in notification_repo.create.call_args_list:
                notification_data = call[0][0]
                assert notification_data["priority"] == NotificationPriority.CRITICAL
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_quiet_hours(self):
        """Test bulk notification sending with quiet hours."""
        user_ids = ["user-1", "user-2"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "America/New_York"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "America/New_York"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock quiet hours check (both users in quiet hours)
        resume_time = datetime.utcnow() + timedelta(hours=8)
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        user_repo = AsyncMock()
        preference_service = AsyncMock()
        
        # Setup mocks
        user_repo.get_multiple_by_external_ids.return_value = [
            users_data["user-1"], users_data["user-2"]
        ]
        preference_service.get_multiple_user_preferences.return_value = users_preferences
        preference_service.check_quiet_hours.return_value = (True, resume_time)
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=user_repo,
            preference_service=preference_service,
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Send bulk notification during quiet hours
        result = await service.send_bulk_notification(
            tenant_id="test-tenant",
            user_ids=user_ids,
            title="Quiet Hours Bulk",
            body="Bulk notification during quiet hours",
            priority=NotificationPriority.NORMAL
        )
        
        assert result.success is True
        assert result.total == 2
        assert result.queued == 2  # Scheduled for later
        assert result.failed == 0
        
        # Verify notifications were scheduled
        for call in notification_repo.create.call_args_list:
            notification_data = call[0][0]
            assert notification_data["scheduled_at"] == resume_time
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_bypass_quiet_hours(self):
        """Test bulk notification sending with quiet hours bypass."""
        user_ids = ["user-1", "user-2"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-bypass"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            preference_service.check_quiet_hours.return_value = (False, None)  # Bypass
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification with bypass
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Bypass Bulk",
                body="Bulk notification with quiet hours bypass",
                priority=NotificationPriority.NORMAL,
                bypass_quiet_hours=True
            )
            
            assert result.success is True
            assert result.total == 2
            assert result.queued == 2
            assert result.failed == 0
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_scheduled_delivery(self):
        """Test bulk notification sending with scheduled delivery."""
        user_ids = ["user-1", "user-2"]
        scheduled_time = datetime.utcnow() + timedelta(hours=2)
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        user_repo = AsyncMock()
        preference_service = AsyncMock()
        
        # Setup mocks
        user_repo.get_multiple_by_external_ids.return_value = [
            users_data["user-1"], users_data["user-2"]
        ]
        preference_service.get_multiple_user_preferences.return_value = users_preferences
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=user_repo,
            preference_service=preference_service,
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Send scheduled bulk notification
        result = await service.send_bulk_notification(
            tenant_id="test-tenant",
            user_ids=user_ids,
            title="Scheduled Bulk",
            body="Scheduled bulk notification",
            priority=NotificationPriority.NORMAL,
            scheduled_at=scheduled_time
        )
        
        assert result.success is True
        assert result.total == 2
        assert result.queued == 2
        assert result.failed == 0
        
        # Verify notifications were scheduled
        for call in notification_repo.create.call_args_list:
            notification_data = call[0][0]
            assert notification_data["scheduled_at"] == scheduled_time
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_metadata(self):
        """Test bulk notification sending with metadata."""
        user_ids = ["user-1", "user-2"]
        
        metadata = {
            "campaign": "welcome",
            "source": "bulk-api",
            "version": "1.0.0"
        }
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": "+12345678902",
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": True, "webhook": True}
        }
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-metadata"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification with metadata
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Metadata Bulk",
                body="Bulk notification with metadata",
                priority=NotificationPriority.NORMAL,
                metadata=metadata
            )
            
            assert result.success is True
            assert result.total == 2
            assert result.queued == 2
            assert result.failed == 0
            
            # Verify metadata was included
            for call in notification_repo.create.call_args_list:
                notification_data = call[0][0]
                assert notification_data["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_bulk_send_empty_user_list(self):
        """Test bulk notification sending with empty user list."""
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        user_repo = AsyncMock()
        preference_service = AsyncMock()
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=user_repo,
            preference_service=preference_service,
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Send bulk notification with empty user list
        result = await service.send_bulk_notification(
            tenant_id="test-tenant",
            user_ids=[],
            title="Empty Bulk",
            body="Bulk notification with no users",
            priority=NotificationPriority.NORMAL
        )
        
        assert result.success is True
        assert result.total == 0
        assert result.queued == 0
        assert result.failed == 0
        
        # Verify no notifications were created
        notification_repo.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_bulk_send_all_users_not_found(self):
        """Test bulk notification sending when all users are not found."""
        user_ids = ["user-1", "user-2"]
        
        # Mock repositories
        notification_repo = AsyncMock()
        delivery_repo = AsyncMock()
        user_repo = AsyncMock()
        preference_service = AsyncMock()
        
        # Setup mocks (no users found)
        user_repo.get_multiple_by_external_ids.return_value = []
        
        service = NotificationService(
            notification_repo=notification_repo,
            delivery_repo=delivery_repo,
            user_repo=user_repo,
            preference_service=preference_service,
            template_service=AsyncMock(),
            channel_resolver=AsyncMock()
        )
        
        # Send bulk notification with non-existent users
        result = await service.send_bulk_notification(
            tenant_id="test-tenant",
            user_ids=user_ids,
            title="Not Found Bulk",
            body="Bulk notification with non-existent users",
            priority=NotificationPriority.NORMAL
        )
        
        assert result.success is True
        assert result.total == 2
        assert result.queued == 0
        assert result.failed == 2
        assert len(result.errors) == 2
    
    @pytest.mark.asyncio
    async def test_bulk_send_with_channel_filtering(self):
        """Test bulk notification sending with channel filtering."""
        user_ids = ["user-1", "user-2"]
        
        # Mock user data
        users_data = {
            "user-1": {
                "id": "user-1",
                "external_id": "user-1",
                "email": "user1@example.com",
                "phone": "+12345678901",
                "timezone": "UTC"
            },
            "user-2": {
                "id": "user-2",
                "external_id": "user-2",
                "email": "user2@example.com",
                "phone": None,  # No phone number
                "timezone": "UTC"
            }
        }
        
        # Mock user preferences
        users_preferences = {
            "user-1": {"email": True, "sms": True, "webhook": True},
            "user-2": {"email": True, "sms": False, "webhook": True}
        }
        
        # Mock channels
        with patch('app.workers.tasks.get_channel') as mock_get_channel:
            mock_channel = AsyncMock()
            mock_result = AsyncMock()
            mock_result.success = True
            mock_result.provider_id = "provider-filter"
            mock_channel.send.return_value = mock_result
            mock_get_channel.return_value = mock_channel
            
            # Mock repositories
            notification_repo = AsyncMock()
            delivery_repo = AsyncMock()
            user_repo = AsyncMock()
            preference_service = AsyncMock()
            
            # Setup mocks
            user_repo.get_multiple_by_external_ids.return_value = [
                users_data["user-1"], users_data["user-2"]
            ]
            preference_service.get_multiple_user_preferences.return_value = users_preferences
            
            service = NotificationService(
                notification_repo=notification_repo,
                delivery_repo=delivery_repo,
                user_repo=user_repo,
                preference_service=preference_service,
                template_service=AsyncMock(),
                channel_resolver=AsyncMock()
            )
            
            # Send bulk notification
            result = await service.send_bulk_notification(
                tenant_id="test-tenant",
                user_ids=user_ids,
                title="Channel Filter Bulk",
                body="Bulk notification with channel filtering",
                priority=NotificationPriority.NORMAL
            )
            
            assert result.success is True
            assert result.total == 2
            assert result.queued == 2
            assert result.failed == 0
            
            # Verify channel filtering was applied
            # user-1: email, sms, webhook (3 channels)
            # user-2: email, webhook only (no phone, sms disabled)
            total_deliveries = delivery_repo.create.call_count
            assert total_deliveries == 5  # 3 for user-1 + 2 for user-2
