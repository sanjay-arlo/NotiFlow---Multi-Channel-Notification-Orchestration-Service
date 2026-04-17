"""
Integration tests for preferences API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.api.routes.preferences import router
from app.core.constants import ChannelType


class TestPreferencesAPI:
    """Integration tests for preferences API endpoints."""
    
    @pytest.fixture
    def api_client(self, test_client):
        """Create API client for testing."""
        return TestClient(app=router, base_url="http://test")
    
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
    def mock_user(self):
        """Mock user for testing."""
        return {
            "id": "test-user-id",
            "external_id": "test-user-123",
            "email": "test@example.com",
            "phone": "+1234567890",
            "timezone": "UTC",
            "display_name": "Test User"
        }
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful user preferences retrieval."""
        mock_preferences = {
            "email": True,
            "sms": False,
            "webhook": True
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.get_user_preferences.return_value = mock_preferences
                
                response = await api_client.get("/test-user-123/preferences")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["channels"] == mock_preferences
        assert data["timezone"] == "UTC"
        
        # Verify service calls
        mock_service.get_user_by_external_id.assert_called_once_with("test-tenant-id", "test-user-123")
        mock_service.preference_service.get_user_preferences.assert_called_once_with("test-user-id")
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_user_not_found(
        self,
        api_client,
        mock_tenant
    ):
        """Test preferences retrieval when user not found."""
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = None
                
                response = await api_client.get("/non-existent-user/preferences")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_channel_preferences_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful channel preferences update."""
        update_data = {
            "channels": {
                "email": True,
                "sms": True,
                "webhook": False
            }
        }
        
        updated_preferences = {
            "email": True,
            "sms": True,
            "webhook": False
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.update_channel_preference.return_value = AsyncMock()
                mock_service.preference_service.get_user_preferences.return_value = updated_preferences
                
                response = await api_client.put("/test-user-123/preferences", json=update_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["channels"] == updated_preferences
        assert data["user_id"] == "test-user-123"
    
    @pytest.mark.asyncio
    async def test_update_channel_preferences_invalid_channel(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test channel preferences update with invalid channel."""
        update_data = {
            "channels": {
                "email": True,
                "invalid_channel": True
            }
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                
                response = await api_client.put("/test-user-123/preferences", json=update_data)
        
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_get_quiet_hours_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful quiet hours retrieval."""
        mock_quiet_hours = [
            {
                "id": "quiet-1",
                "user_id": "test-user-id",
                "day_of_week": 0,
                "start_time": "22:00",
                "end_time": "08:00",
                "timezone": "America/New_York",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.get_quiet_hours.return_value = mock_quiet_hours
                
                response = await api_client.get("/test-user-123/quiet-hours")
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["quiet_hours"]) == 1
        assert data["quiet_hours"][0]["day_of_week"] == 0
        assert data["quiet_hours"][0]["start_time"] == "22:00"
        assert data["quiet_hours"][0]["end_time"] == "08:00"
    
    @pytest.mark.asyncio
    async def test_get_quiet_hours_no_rules(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test quiet hours retrieval when no rules exist."""
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.get_quiet_hours.return_value = []
                
                response = await api_client.get("/test-user-123/quiet-hours")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["quiet_hours"] == []
    
    @pytest.mark.asyncio
    async def test_update_quiet_hours_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful quiet hours update."""
        update_data = {
            "quiet_hours": [
                {
                    "day_of_week": 0,
                    "start_time": "22:00",
                    "end_time": "08:00",
                    "timezone": "America/New_York",
                    "is_active": True
                },
                {
                    "day_of_week": 6,
                    "start_time": "23:00",
                    "end_time": "09:00",
                    "timezone": "America/New_York",
                    "is_active": True
                }
            ]
        }
        
        updated_quiet_hours = [
            {
                "id": "quiet-1",
                "user_id": "test-user-id",
                "day_of_week": 0,
                "start_time": "22:00",
                "end_time": "08:00",
                "timezone": "America/New_York",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            },
            {
                "id": "quiet-2",
                "user_id": "test-user-id",
                "day_of_week": 6,
                "start_time": "23:00",
                "end_time": "09:00",
                "timezone": "America/New_York",
                "is_active": True,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z"
            }
        ]
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.update_quiet_hours.return_value = updated_quiet_hours
                
                response = await api_client.put("/test-user-123/quiet-hours", json=update_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["quiet_hours"]) == 2
        assert data["quiet_hours"][0]["day_of_week"] == 0
        assert data["quiet_hours"][1]["day_of_week"] == 6
    
    @pytest.mark.asyncio
    async def test_update_quiet_hours_invalid_time_format(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test quiet hours update with invalid time format."""
        update_data = {
            "quiet_hours": [
                {
                    "day_of_week": 0,
                    "start_time": "25:00",  # Invalid time
                    "end_time": "08:00",
                    "timezone": "America/New_York",
                    "is_active": True
                }
            ]
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                
                response = await api_client.put("/test-user-123/quiet-hours", json=update_data)
        
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_update_quiet_hours_invalid_day(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test quiet hours update with invalid day."""
        update_data = {
            "quiet_hours": [
                {
                    "day_of_week": 8,  # Invalid day (0-6)
                    "start_time": "22:00",
                    "end_time": "08:00",
                    "timezone": "America/New_York",
                    "is_active": True
                }
            ]
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                
                response = await api_client.put("/test-user-123/quiet-hours", json=update_data)
        
        assert response.status_code == 422  # Validation error
        
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_check_preferences_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful preference check."""
        check_data = {
            "user_id": "test-user-123",
            "channel": "email",
            "priority": "normal",
            "bypass_quiet_hours": False
        }
        
        mock_result = {
            "can_send": True,
            "channel_enabled": True,
            "is_quiet_hours": False,
            "quiet_hours_active": False,
            "reason": "Channel enabled and not in quiet hours"
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.check_can_send_notification.return_value = mock_result
                
                response = await api_client.post("/test-user-123/check", json=check_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_send"] is True
        assert data["channel_enabled"] is True
        assert data["is_quiet_hours"] is False
    
    @pytest.mark.asyncio
    async def test_check_preferences_during_quiet_hours(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test preference check during quiet hours."""
        check_data = {
            "user_id": "test-user-123",
            "channel": "email",
            "priority": "normal",
            "bypass_quiet_hours": False
        }
        
        mock_result = {
            "can_send": False,
            "channel_enabled": True,
            "is_quiet_hours": True,
            "quiet_hours_active": True,
            "resume_at": "2024-01-15T08:00:00Z",
            "reason": "User is in quiet hours"
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.check_can_send_notification.return_value = mock_result
                
                response = await api_client.post("/test-user-123/check", json=check_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_send"] is False
        assert data["is_quiet_hours"] is True
        assert data["resume_at"] is not None
    
    @pytest.mark.asyncio
    async def test_check_preferences_critical_bypass(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test preference check with critical priority bypass."""
        check_data = {
            "user_id": "test-user-123",
            "channel": "email",
            "priority": "critical",
            "bypass_quiet_hours": False
        }
        
        mock_result = {
            "can_send": True,
            "channel_enabled": True,
            "is_quiet_hours": True,
            "quiet_hours_active": True,
            "reason": "Critical priority bypasses quiet hours"
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.check_can_send_notification.return_value = mock_result
                
                response = await api_client.post("/test-user-123/check", json=check_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_send"] is True
        assert data["reason"] == "Critical priority bypasses quiet hours"
    
    @pytest.mark.asyncio
    async def test_check_preferences_channel_disabled(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test preference check when channel is disabled."""
        check_data = {
            "user_id": "test-user-123",
            "channel": "sms",
            "priority": "normal",
            "bypass_quiet_hours": False
        }
        
        mock_result = {
            "can_send": False,
            "channel_enabled": False,
            "is_quiet_hours": False,
            "quiet_hours_active": False,
            "reason": "SMS channel is disabled for user"
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.check_can_send_notification.return_value = mock_result
                
                response = await api_client.post("/test-user-123/check", json=check_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["can_send"] is False
        assert data["channel_enabled"] is False
    
    @pytest.mark.asyncio
    async def test_bulk_update_preferences_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful bulk preferences update."""
        update_data = {
            "preferences": {
                "email": True,
                "sms": True,
                "webhook": False
            }
        }
        
        updated_preferences = {
            "email": True,
            "sms": True,
            "webhook": False
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.bulk_update_preferences.return_value = updated_preferences
                
                response = await api_client.post("/test-user-123/preferences/bulk", json=update_data)
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["preferences"] == updated_preferences
    
    @pytest.mark.asyncio
    async def test_get_preference_summary_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful preference summary retrieval."""
        mock_summary = {
            "user_id": "test-user-123",
            "enabled_channels": ["email", "webhook"],
            "disabled_channels": ["sms"],
            "quiet_hours_count": 2,
            "quiet_hours_active": False,
            "timezone": "UTC"
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.get_preference_summary.return_value = mock_summary
                
                response = await api_client.get("/test-user-123/summary")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["user_id"] == "test-user-123"
        assert data["enabled_channels"] == ["email", "webhook"]
        assert data["disabled_channels"] == ["sms"]
    
    @pytest.mark.asyncio
    async def test_reset_preferences_success(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test successful preferences reset."""
        reset_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                mock_service.preference_service.reset_preferences.return_value = reset_preferences
                
                response = await api_client.post("/test-user-123/preferences/reset")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["preferences"] == reset_preferences
        assert data["message"] == "Preferences reset to defaults"
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        api_client
    ):
        """Test unauthorized access to preferences endpoints."""
        response = await api_client.get("/test-user-123/preferences")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_invalid_channel_type(
        self,
        api_client,
        mock_tenant,
        mock_user
    ):
        """Test preference check with invalid channel type."""
        check_data = {
            "user_id": "test-user-123",
            "channel": "invalid_channel",
            "priority": "normal",
            "bypass_quiet_hours": False
        }
        
        with patch('app.api.routes.preferences.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.preferences.get_user_service') as mock_service:
                mock_service.get_user_by_external_id.return_value = mock_user
                
                response = await api_client.post("/test-user-123/check", json=check_data)
        
        assert response.status_code == 422  # Validation error
