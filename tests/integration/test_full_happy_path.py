"""
End-to-end tests for complete notification workflow.
"""

import pytest
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.api.routes.notifications import router
from app.core.constants import NotificationPriority


class TestFullHappyPath:
    """Test complete notification workflow from send to delivery."""
    
    @pytest.fixture
    def api_client(self, test_client):
        """Create API client for testing."""
        return TestClient(app=router, base_url="http://test")
    
    @pytest.fixture
    def mock_services(self):
        """Mock all external services."""
        with patch.multiple(
            'app.api.routes.notifications.get_current_tenant',
            'app.api.routes.notifications.get_notification_service',
            'app.api.routes.notifications.get_delivery_service',
            'app.api.routes.notifications.get_preference_service',
            'app.api.routes.notifications.get_template_service',
            'app.api.routes.notifications.get_channel_resolver'
        ) as mocks:
            # Configure mocks
            mocks[0].return_value = {
                "id": "test-tenant-id",
                "name": "Test Tenant",
                "is_active": True
            }
            
            # Mock notification service
            mocks[1].send_notification.return_value = AsyncMock(
                id="test-notification-id",
                status="queued",
                resolved_channels=["email"],
                priority=NotificationPriority.NORMAL,
                created_at=datetime.utcnow()
            )
            
            # Mock delivery service
            mocks[2].create_delivery.return_value = AsyncMock(
                id="test-delivery-id",
                channel="email",
                destination="test@example.com",
                status="pending"
            )
            
            # Mock preference service
            mocks[3].get_user_preferences.return_value = {
                "email": True,
                "sms": False,
                "webhook": True
            }
            
            # Mock template service
            mocks[4].get_template.return_value = AsyncMock(
                id="test-template-id",
                slug="test-template",
                email_subject="Test: {{ subject }}",
                email_body="<h1>{{ title }}</h1><p>{{ content }}</p>"
            )
            
            # Mock channel resolver
            mocks[5].resolve_channels.return_value = ["email"]
            mocks[5].get_primary_channel.return_value = "email"
            
            yield mocks
    
    @pytest.mark.asyncio
    async def test_complete_notification_workflow(
        self,
        api_client,
        mock_services
    ):
        """Test complete workflow: send notification → create deliveries → queue tasks."""
        
        # Send notification
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test Notification",
                "body": "This is a test notification.",
                "priority": "normal"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-notification-id"
        assert data["status"] == "queued"
        assert data["resolved_channels"] == ["email"]
        
        # Verify tenant authentication was called
        mock_services[0].assert_called_once()
        
        # Verify notification service was called
        mock_services[1].send_notification.assert_called_once()
        call_args = mock_services[1].send_notification.call_args
        assert call_args[1]["tenant_id"] == "test-tenant-id"
        assert call_args[1]["user_external_id"] == "test-user-123"
        assert call_args[1]["title"] == "Test Notification"
        assert call_args[1]["body"] == "This is a test notification."
        assert call_args[1]["priority"] == "normal"
        
        # Verify preference service was called
        mock_services[3].get_user_preferences.assert_called_once_with("test-user-id")
        
        # Verify channel resolver was called
        mock_services[5].resolve_channels.assert_called_once()
        
        # Verify delivery service was called
        mock_services[2].create_delivery.assert_called_once()
        delivery_call_args = mock_services[2].create_delivery.call_args
        assert delivery_call_args[1]["notification_id"] == "test-notification-id"
        assert delivery_call_args[1]["channel"] == "email"
        assert delivery_call_args[1]["destination"] == "test@example.com"
    
    @pytest.mark.asyncio
    async def test_notification_with_template(
        self,
        api_client,
        mock_services
    ):
        """Test notification sending with template."""
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "template_slug": "test-template",
                "template_variables": {
                    "subject": "Welcome",
                    "title": "Welcome to NotiFlow",
                    "content": "Thanks for joining!"
                },
                "priority": "high"
            }
        )
        
        assert response.status_code == 200
        
        # Verify template service was called
        mock_services[4].get_template.assert_called_once_with("test-tenant-id", "test-template")
        
        # Verify notification service was called with rendered content
        call_args = mock_services[1].send_notification.call_args
        assert call_args[1]["template_slug"] == "test-template"
        assert call_args[1]["template_variables"]["subject"] == "Welcome"
    
    @pytest.mark.asyncio
    async def test_critical_notification_uses_all_channels(
        self,
        api_client,
        mock_services
    ):
        """Test that critical notifications use all available channels."""
        
        # Mock user with all channels enabled
        mock_services[3].get_user_preferences.return_value = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Critical Alert",
                "body": "This is a critical alert!",
                "priority": "critical"
            }
        )
        
        assert response.status_code == 200
        
        # Verify all channels were resolved
        mock_services[5].resolve_channels.assert_called_once()
        resolved_channels = mock_services[5].resolve_channels.return_value
        assert set(resolved_channels) == {"email", "sms", "webhook"}
        
        # Verify deliveries created for all channels
        assert mock_services[2].create_delivery.call_count == 3
    
    @pytest.mark.asyncio
    async def test_batch_notification_sending(
        self,
        api_client,
        mock_services
    ):
        """Test batch notification sending."""
        
        response = await api_client.post(
            "/batch",
            json={
                "user_ids": ["user1", "user2", "user3"],
                "title": "Batch Test",
                "body": "This is a batch notification.",
                "priority": "normal"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["queued"] >= 0
        assert data["failed"] >= 0
        assert "batch_id" in data
    
    @pytest.mark.asyncio
    async def test_scheduled_notification(
        self,
        api_client,
        mock_services
    ):
        """Test scheduled notification handling."""
        
        from datetime import datetime, timedelta
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Scheduled Notification",
                "body": "This is scheduled for later.",
                "scheduled_at": scheduled_time,
                "priority": "normal"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "scheduled_at" in data
        assert data["scheduled_at"] == scheduled_time
    
    @pytest.mark.asyncio
    async def test_notification_bypass_quiet_hours(
        self,
        api_client,
        mock_services
    ):
        """Test notification with quiet hours bypass."""
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Bypass Quiet Hours",
                "body": "This should bypass quiet hours.",
                "bypass_quiet_hours": True,
                "priority": "normal"
            }
        )
        
        assert response.status_code == 200
        
        # Verify bypass flag was passed
        call_args = mock_services[1].send_notification.call_args
        assert call_args[1]["bypass_quiet_hours"] is True
    
    @pytest.mark.asyncio
    async def test_notification_with_metadata(
        self,
        api_client,
        mock_services
    ):
        """Test notification sending with custom metadata."""
        
        metadata = {
            "source": "test-suite",
            "campaign": "e2e-tests",
            "version": "1.0.0",
            "environment": "test"
        }
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test with Metadata",
                "body": "This notification has metadata.",
                "metadata": metadata,
                "priority": "normal"
            }
        )
        
        assert response.status_code == 200
        
        # Verify metadata was passed through
        call_args = mock_services[1].send_notification.call_args
        assert call_args[1]["metadata"] == metadata
    
    @pytest.mark.asyncio
    async def test_notification_error_handling(
        self,
        api_client,
        mock_services
    ):
        """Test error handling in notification sending."""
        
        # Mock service to raise an error
        from app.core.exceptions import NoChannelsAvailableError
        mock_services[1].send_notification.side_effect = NoChannelsAvailableError("test-user-123")
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test Notification",
                "body": "This should fail.",
                "priority": "normal"
            }
        )
        
        # Verify error is handled properly
        assert response.status_code == 400
        data = response.json()
        assert "No channels available" in str(data)
    
    @pytest.mark.asyncio
    async def test_notification_validation_errors(
        self,
        api_client,
        mock_services
    ):
        """Test input validation in notification sending."""
        
        # Test missing required fields
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123"
                # Missing title and body
            }
        )
        
        assert response.status_code == 422
        
        # Test invalid priority
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test",
                "body": "Test",
                "priority": "invalid"
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        api_client,
        mock_services
    ):
        """Test unauthorized access to notification endpoints."""
        
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test",
                "body": "Test"
            }
            # No API key header
        )
        
        assert response.status_code == 401
