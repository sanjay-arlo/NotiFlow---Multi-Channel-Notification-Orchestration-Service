"""
Integration tests for quiet hours bypass functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, time, timezone, timedelta

from app.services.notification_service import NotificationService
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.db.models.quiet_hours import QuietHours
from app.core.constants import NotificationPriority, DeliveryStatus, ChannelType


class TestQuietHoursBypass:
    """Integration tests for quiet hours bypass functionality."""
    
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
    async def test_critical_notification_bypasses_quiet_hours(self):
        """Test that critical notifications bypass quiet hours."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Critical Alert",
            body="System critical alert",
            priority=NotificationPriority.CRITICAL
        )
        
        # Mock quiet hours rule (22:00-08:00)
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,  # Sunday
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "admin@example.com",
            "phone": "+1234567890",
            "timezone": "America/New_York"
        }
        
        # Current time during quiet hours (11 PM New York = 3 AM UTC Monday)
        current_time = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)  # Monday 3 AM UTC
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
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
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send critical notification
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="Critical Alert",
                            body="System critical alert",
                            priority=NotificationPriority.CRITICAL,
                            bypass_quiet_hours=False
                        )
                        
                        assert result.success is True
                        assert len(result.deliveries) == 3  # All channels due to critical priority
                        
                        # Verify quiet hours check was called with critical priority
                        mock_quiet_check.assert_called()
                        call_args = mock_quiet_check.call_args
                        assert call_args[0][1] == NotificationPriority.CRITICAL
    
    @pytest.mark.asyncio
    async def test_bypass_flag_overrides_quiet_hours(self):
        """Test that bypass flag overrides quiet hours for normal priority."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Bypass Test",
            body="This should bypass quiet hours",
            priority=NotificationPriority.NORMAL
        )
        
        # Mock quiet hours rule
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": False,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        # Current time during quiet hours
        current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)  # Sunday 11 PM UTC
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    with patch('app.workers.tasks.get_channel') as mock_get_channel:
                        mock_channel = AsyncMock()
                        mock_result = AsyncMock()
                        mock_result.success = True
                        mock_result.provider_id = "smtp-bypass"
                        mock_channel.send.return_value = mock_result
                        mock_get_channel.return_value = mock_channel
                        
                        # Mock repositories
                        notification_repo = AsyncMock()
                        delivery_repo = AsyncMock()
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send notification with bypass flag
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="Bypass Test",
                            body="This should bypass quiet hours",
                            priority=NotificationPriority.NORMAL,
                            bypass_quiet_hours=True
                        )
                        
                        assert result.success is True
                        assert len(result.deliveries) == 2  # email and webhook (sms disabled)
                        
                        # Verify quiet hours check was called with bypass flag
                        mock_quiet_check.assert_called()
                        call_args = mock_quiet_check.call_args
                        assert call_args[0][2] is True  # bypass_quiet_hours = True
    
    @pytest.mark.asyncio
    async def test_normal_notification_respects_quiet_hours(self):
        """Test that normal notifications respect quiet hours without bypass."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Normal Test",
            body="This should respect quiet hours",
            priority=NotificationPriority.NORMAL
        )
        
        # Mock quiet hours rule
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        # Current time during quiet hours
        current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)  # Sunday 11 PM UTC
        resume_time = datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc)  # Monday 8 AM UTC
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (True, resume_time)  # In quiet hours
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    # Mock repositories
                    notification_repo = AsyncMock()
                    delivery_repo = AsyncMock()
                    
                    service = NotificationService(
                        notification_repo=notification_repo,
                        delivery_repo=delivery_repo,
                        user_repo=AsyncMock(),
                        preference_service=AsyncMock(),
                        template_service=AsyncMock(),
                        channel_resolver=AsyncMock()
                    )
                    
                    # Send normal notification without bypass
                    result = await service.send_notification(
                        tenant_id="test-tenant",
                        user_external_id="test-user-123",
                        title="Normal Test",
                        body="This should respect quiet hours",
                        priority=NotificationPriority.NORMAL,
                        bypass_quiet_hours=False
                    )
                    
                    assert result.success is True
                    assert result.scheduled_at == resume_time
                    assert len(result.deliveries) == 0  # No immediate deliveries during quiet hours
                    
                    # Verify notification was scheduled
                    notification_repo.update.assert_called()
                    update_args = notification_repo.update.call_args[0][1]
                    assert update_args["scheduled_at"] == resume_time
    
    @pytest.mark.asyncio
    async def test_high_priority_partial_bypass(self):
        """Test high priority notifications with partial channel bypass."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="High Priority",
            body="High priority notification",
            priority=NotificationPriority.HIGH
        )
        
        # Mock quiet hours rule
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences (only email enabled for high priority)
        user_preferences = {
            "email": True,
            "sms": False,  # Disabled
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        # Current time during quiet hours
        current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to high priority
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    with patch('app.workers.tasks.get_channel') as mock_get_channel:
                        mock_channel = AsyncMock()
                        mock_result = AsyncMock()
                        mock_result.success = True
                        mock_result.provider_id = "smtp-high"
                        mock_channel.send.return_value = mock_result
                        mock_get_channel.return_value = mock_channel
                        
                        # Mock repositories
                        notification_repo = AsyncMock()
                        delivery_repo = AsyncMock()
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send high priority notification
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="High Priority",
                            body="High priority notification",
                            priority=NotificationPriority.HIGH,
                            bypass_quiet_hours=False
                        )
                        
                        assert result.success is True
                        assert len(result.deliveries) == 2  # email and webhook (sms disabled)
                        
                        # Verify quiet hours check was called with high priority
                        mock_quiet_check.assert_called()
                        call_args = mock_quiet_check.call_args
                        assert call_args[0][1] == NotificationPriority.HIGH
    
    @pytest.mark.asyncio
    async def test_quiet_hours_bypass_with_multiple_rules(self):
        """Test quiet hours bypass with multiple quiet hours rules."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Critical Multi-Rule",
            body="Critical with multiple quiet hours rules",
            priority=NotificationPriority.CRITICAL
        )
        
        # Mock multiple quiet hours rules
        weekday_rule = QuietHours(
            user_id="test-user",
            day_of_week=1,  # Monday
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        weekend_rule = QuietHours(
            user_id="test-user",
            day_of_week=6,  # Saturday
            start_time=time(23, 0),
            end_time(time(9, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        # Current time during Monday quiet hours
        current_time = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)  # Monday 11 PM UTC
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    with patch('app.workers.tasks.get_channel') as mock_get_channel:
                        mock_channel = AsyncMock()
                        mock_result = AsyncMock()
                        mock_result.success = True
                        mock_result.provider_id = "smtp-multi"
                        mock_channel.send.return_value = mock_result
                        mock_get_channel.return_value = mock_channel
                        
                        # Mock repositories
                        notification_repo = AsyncMock()
                        delivery_repo = AsyncMock()
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send critical notification
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="Critical Multi-Rule",
                            body="Critical with multiple quiet hours rules",
                            priority=NotificationPriority.CRITICAL,
                            bypass_quiet_hours=False
                        )
                        
                        assert result.success is True
                        assert len(result.deliveries) == 3  # All channels due to critical priority
    
    @pytest.mark.asyncio
    async def test_quiet_hours_bypass_with_timezone(self):
        """Test quiet hours bypass with different timezones."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Critical Timezone",
            body="Critical with timezone handling",
            priority=NotificationPriority.CRITICAL
        )
        
        # Mock quiet hours rule in New York timezone
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,  # Sunday
            start_time=time(22, 0),  # 10 PM New York
            end_time=time(8, 0),     # 8 AM New York
            timezone="America/New_York",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data with New York timezone
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "America/New_York"
        }
        
        # Current time: 3 AM UTC = 10 PM New York (during quiet hours)
        current_time = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)  # Monday 3 AM UTC
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    with patch('app.workers.tasks.get_channel') as mock_get_channel:
                        mock_channel = AsyncMock()
                        mock_result = AsyncMock()
                        mock_result.success = True
                        mock_result.provider_id = "smtp-timezone"
                        mock_channel.send.return_value = mock_result
                        mock_get_channel.return_value = mock_channel
                        
                        # Mock repositories
                        notification_repo = AsyncMock()
                        delivery_repo = AsyncMock()
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send critical notification
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="Critical Timezone",
                            body="Critical with timezone handling",
                            priority=NotificationPriority.CRITICAL,
                            bypass_quiet_hours=False
                        )
                        
                        assert result.success is True
                        assert len(result.deliveries) == 3  # All channels due to critical priority
                        
                        # Verify quiet hours check was called with correct timezone
                        mock_quiet_check.assert_called()
                        call_args = mock_quiet_check.call_args
                        assert call_args[0][3] == "America/New_York"  # timezone parameter
    
    @pytest.mark.asyncio
    async def test_quiet_hours_bypass_delivery_failure(self):
        """Test delivery failure during quiet hours bypass."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Critical Failed",
            body="Critical that fails delivery",
            priority=NotificationPriority.CRITICAL
        )
        
        # Mock quiet hours rule
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        # Current time during quiet hours
        current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    with patch('app.workers.tasks.get_channel') as mock_get_channel:
                        mock_channel = AsyncMock()
                        mock_result = AsyncMock()
                        mock_result.success = False
                        mock_result.error = Exception("SMTP connection failed")
                        mock_channel.send.return_value = mock_result
                        mock_get_channel.return_value = mock_channel
                        
                        # Mock repositories
                        notification_repo = AsyncMock()
                        delivery_repo = AsyncMock()
                        
                        service = NotificationService(
                            notification_repo=notification_repo,
                            delivery_repo=delivery_repo,
                            user_repo=AsyncMock(),
                            preference_service=AsyncMock(),
                            template_service=AsyncMock(),
                            channel_resolver=AsyncMock()
                        )
                        
                        # Send critical notification that fails
                        result = await service.send_notification(
                            tenant_id="test-tenant",
                            user_external_id="test-user-123",
                            title="Critical Failed",
                            body="Critical that fails delivery",
                            priority=NotificationPriority.CRITICAL,
                            bypass_quiet_hours=False
                        )
                        
                        assert result.success is False
                        assert len(result.deliveries) == 0  # No successful deliveries
                        
                        # Verify deliveries were created but failed
                        assert delivery_repo.create.call_count == 3  # One for each channel
    
    @pytest.mark.asyncio
    async def test_quiet_hours_bypass_with_scheduled_notification(self):
        """Test scheduled notification during quiet hours with bypass."""
        notification = Notification(
            id="test-notification",
            tenant_id="test-tenant",
            user_id="test-user",
            title="Scheduled Critical",
            body="Scheduled critical notification",
            priority=NotificationPriority.CRITICAL,
            scheduled_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        # Mock quiet hours rule
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Mock user preferences
        user_preferences = {
            "email": True,
            "sms": True,
            "webhook": True
        }
        
        # Mock user data
        user_data = {
            "id": "test-user",
            "external_id": "test-user-123",
            "email": "user@example.com",
            "phone": "+1234567890",
            "timezone": "UTC"
        }
        
        with patch('app.services.preference_service.PreferenceService.check_quiet_hours') as mock_quiet_check:
            mock_quiet_check.return_value = (False, None)  # Not in quiet hours due to bypass
            
            with patch('app.services.preference_service.PreferenceService.get_user_preferences') as mock_prefs:
                mock_prefs.return_value = user_preferences
                
                with patch('app.services.notification_service.NotificationService._get_user_data') as mock_user_data:
                    mock_user_data.return_value = user_data
                    
                    # Mock repositories
                    notification_repo = AsyncMock()
                    delivery_repo = AsyncMock()
                    
                    service = NotificationService(
                        notification_repo=notification_repo,
                        delivery_repo=delivery_repo,
                        user_repo=AsyncMock(),
                        preference_service=AsyncMock(),
                        template_service=AsyncMock(),
                        channel_resolver=AsyncMock()
                    )
                    
                    # Send scheduled critical notification
                    result = await service.send_notification(
                        tenant_id="test-tenant",
                        user_external_id="test-user-123",
                        title="Scheduled Critical",
                        body="Scheduled critical notification",
                        priority=NotificationPriority.CRITICAL,
                        scheduled_at=datetime.utcnow() + timedelta(hours=1),
                        bypass_quiet_hours=False
                    )
                    
                    assert result.success is True
                    assert result.scheduled_at is not None  # Should still be scheduled for future
                    assert len(result.deliveries) == 0  # No immediate deliveries for scheduled notification
