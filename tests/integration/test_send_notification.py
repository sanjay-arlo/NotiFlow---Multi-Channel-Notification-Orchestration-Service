"""
Integration tests for notification sending API.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.api.routes.notifications import router
from app.core.constants import NotificationPriority


class TestSendNotificationAPI:
    """Integration tests for notification sending endpoints."""
    
    @pytest.fixture
    def api_client(self, test_client):
        """Create API client for testing."""
        return AsyncClient(app=router, base_url="http://test")
    
    @pytest.fixture
    def mock_tenant(self):
        """Mock tenant for API key authentication."""
        return {
            "id": "test-tenant-id",
            "name": "Test Tenant",
            "api_key_hash": "test-hash",
            "is_active": True
        }
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service."""
        with patch('app.api.routes.notifications.notification_service') as mock_service:
            mock_service.send_notification.return_value = AsyncMock(
                id="test-notification-id",
                status="queued",
                resolved_channels=["email"],
                priority=NotificationPriority.NORMAL,
                created_at="2024-01-15T10:00:00Z"
            )
            yield mock_service
    
    @pytest.mark.asyncio
    async def test_send_notification_success(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test successful notification sending."""
        # Mock tenant authentication
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "title": "Test Notification",
                    "body": "This is a test notification.",
                    "priority": "normal"
                }
            )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test-notification-id"
        assert data["status"] == "queued"
        assert data["resolved_channels"] == ["email"]
        assert data["priority"] == "normal"
        
        # Verify service was called correctly
        mock_notification_service.send_notification.assert_called_once()
        call_args = mock_notification_service.send_notification.call_args
        assert call_args[1]["tenant_id"] == str(mock_tenant["id"])
        assert call_args[1]["user_external_id"] == "test-user-123"
        assert call_args[1]["title"] == "Test Notification"
        assert call_args[1]["body"] == "This is a test notification."
    
    @pytest.mark.asyncio
    async def test_send_notification_with_template(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification sending with template."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "template_slug": "welcome-email",
                    "template_variables": {
                        "name": "Test User",
                        "email": "test@example.com"
                    },
                    "priority": "high"
                }
            )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test-notification-id"
        
        # Verify service was called with template data
        call_args = mock_notification_service.send_notification.call_args
        assert call_args[1]["template_slug"] == "welcome-email"
        assert call_args[1]["template_variables"]["name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_send_notification_with_channels(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification sending with specific channels."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "title": "Test Notification",
                    "body": "This is a test notification.",
                    "channels": ["email", "sms"],
                    "priority": "normal"
                }
            )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["resolved_channels"] == ["email", "sms"]
    
    @pytest.mark.asyncio
    async def test_send_notification_critical_priority(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test critical priority notification."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "title": "Critical Alert",
                    "body": "This is a critical notification!",
                    "priority": "critical"
                }
            )
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["priority"] == "critical"
    
    @pytest.mark.asyncio
    async def test_send_notification_with_scheduled_time(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification with scheduled delivery."""
        from datetime import datetime, timedelta
        
        scheduled_time = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
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
    
    @pytest.mark.asyncio
    async def test_send_notification_bypass_quiet_hours(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification with quiet hours bypass."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
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
        
        # Verify service was called with bypass flag
        call_args = mock_notification_service.send_notification.call_args
        assert call_args[1]["bypass_quiet_hours"] is True
    
    @pytest.mark.asyncio
    async def test_send_notification_invalid_priority(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification with invalid priority."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "title": "Test Notification",
                    "body": "This is a test notification.",
                    "priority": "invalid"
                }
            )
        
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
        assert "priority" in str(data["detail"])
    
    @pytest.mark.asyncio
    async def test_send_notification_missing_required_fields(
        self,
        api_client,
        mock_tenant
    ):
        """Test notification with missing required fields."""
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123"
                    # Missing title and body
                }
            )
        
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_send_notification_unauthorized(
        self,
        api_client
    ):
        """Test notification without API key."""
        response = await api_client.post(
            "/send",
            json={
                "user_id": "test-user-123",
                "title": "Test Notification",
                "body": "This is a test notification."
            }
        )
        
        assert response.status_code == 401  # Unauthorized
    
    @pytest.mark.asyncio
    async def test_send_notification_service_error(
        self,
        api_client,
        mock_tenant,
        mock_notification_service
    ):
        """Test notification sending when service throws error."""
        from app.core.exceptions import NoChannelsAvailableError
        
        mock_notification_service.send_notification.side_effect = NoChannelsAvailableError("test-user-123")
        
        with patch('app.api.routes.notifications.get_current_tenant', return_value=mock_tenant):
            response = await api_client.post(
                "/send",
                json={
                    "user_id": "test-user-123",
                    "title": "Test Notification",
                    "body": "This is a test notification."
                }
            )
        
        assert response.status_code == 400  # Bad Request
        
        data = response.json()
        assert "No channels available" in data["detail"]
