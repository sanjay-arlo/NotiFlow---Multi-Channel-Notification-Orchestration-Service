"""
Unit tests for preference service.
"""

import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock

from app.core.constants import ChannelType, NotificationPriority
from app.db.models.user import User
from app.db.models.user_preference import UserChannelPreference
from app.db.models.quiet_hours import QuietHours
from app.services.preference_service import PreferenceService


class TestPreferenceService:
    """Test cases for PreferenceService."""
    
    @pytest.fixture
    def preference_service(self):
        """Create preference service for testing."""
        mock_preference_repo = AsyncMock()
        mock_quiet_hours_repo = AsyncMock()
        return PreferenceService(mock_preference_repo, mock_quiet_hours_repo)
    
    @pytest.fixture
    def sample_user(self):
        """Create sample user for testing."""
        return User(
            id="550e8400-e29b-41d4-a716-446655440001",
            external_id="test_user_123",
            email="test@example.com",
            phone="+1234567890",
            timezone="America/New_York",
            display_name="Test User"
        )
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_cached(self, preference_service, sample_user):
        """Test getting user preferences with caching."""
        # Mock cached preferences
        cached_prefs = {ChannelType.EMAIL: True, ChannelType.SMS: False}
        
        with pytest.patch('app.services.preference_service.PreferenceService._get_cached_preferences') as mock_cache:
            mock_cache.return_value = cached_prefs
            
            result = await preference_service.get_user_preferences(str(sample_user.id), use_cache=True)
            
            assert result == cached_prefs
            mock_cache.assert_called_once_with(str(sample_user.id))
    
    @pytest.mark.asyncio
    async def test_get_user_preferences_from_db(self, preference_service, sample_user):
        """Test getting user preferences from database."""
        # Mock database response
        mock_preferences = [
            UserChannelPreference(
                user_id=sample_user.id,
                channel=ChannelType.EMAIL,
                is_enabled=True
            ),
            UserChannelPreference(
                user_id=sample_user.id,
                channel=ChannelType.SMS,
                is_enabled=False
            )
        ]
        
        preference_service.preference_repo.get_by_user.return_value = mock_preferences
        
        result = await preference_service.get_user_preferences(str(sample_user.id), use_cache=False)
        
        assert result == {
            ChannelType.EMAIL: True,
            ChannelType.SMS: False,
            ChannelType.WEBHOOK: True  # Default enabled
        }
    
    @pytest.mark.asyncio
    async def test_update_channel_preference(self, preference_service, sample_user):
        """Test updating user channel preference."""
        updated_preference = UserChannelPreference(
            user_id=sample_user.id,
            channel=ChannelType.EMAIL,
            is_enabled=False
        )
        
        preference_service.preference_repo.upsert_preference.return_value = updated_preference
        
        result = await preference_service.update_channel_preference(
            str(sample_user.id), ChannelType.EMAIL, False
        )
        
        assert result == updated_preference
        preference_service.preference_repo.upsert_preference.assert_called_once_with(
            str(sample_user.id), ChannelType.EMAIL, False
        )
    
    @pytest.mark.asyncio
    async def test_get_quiet_hours_cached(self, preference_service, sample_user):
        """Test getting quiet hours with caching."""
        # Mock cached quiet hours
        cached_rules = [
            QuietHours(
                user_id=sample_user.id,
                day_of_week=0,  # Sunday
                start_time=time(22, 0),
                end_time=time(8, 0),
                timezone="America/New_York",
                is_active=True
            )
        ]
        
        with pytest.patch('app.services.preference_service.PreferenceService._get_cached_quiet_hours') as mock_cache:
            mock_cache.return_value = cached_rules
            
            result = await preference_service.get_quiet_hours(str(sample_user.id), use_cache=True)
            
            assert result == cached_rules
            mock_cache.assert_called_once_with(str(sample_user.id))
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_active(self, preference_service, sample_user):
        """Test quiet hours check when active."""
        # Mock quiet hours rule for current day
        current_time = time(23, 0)  # 11 PM
        current_day = 6  # Saturday
        
        mock_rule = QuietHours(
            user_id=sample_user.id,
            day_of_week=current_day,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=True
        )
        
        preference_service.quiet_hours_repo.get_by_user_and_day.return_value = mock_rule
        
        is_quiet, resume_at = await preference_service.check_quiet_hours(
            sample_user, NotificationPriority.NORMAL, False
        )
        
        assert is_quiet is True
        assert resume_at is not None
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_inactive(self, preference_service, sample_user):
        """Test quiet hours check when inactive."""
        # Mock no quiet hours rule
        preference_service.quiet_hours_repo.get_by_user_and_day.return_value = None
        
        is_quiet, resume_at = await preference_service.check_quiet_hours(
            sample_user, NotificationPriority.NORMAL, False
        )
        
        assert is_quiet is False
        assert resume_at is None
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_bypass_critical(self, preference_service, sample_user):
        """Test that critical notifications bypass quiet hours."""
        # Mock active quiet hours
        mock_rule = QuietHours(
            user_id=sample_user.id,
            day_of_week=6,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=True
        )
        
        preference_service.quiet_hours_repo.get_by_user_and_day.return_value = mock_rule
        
        is_quiet, resume_at = await preference_service.check_quiet_hours(
            sample_user, NotificationPriority.CRITICAL, False
        )
        
        assert is_quiet is False  # Should bypass
        assert resume_at is None
    
    @pytest.mark.asyncio
    async def test_check_quiet_hours_bypass_flag(self, preference_service, sample_user):
        """Test that bypass flag overrides quiet hours."""
        # Mock active quiet hours
        mock_rule = QuietHours(
            user_id=sample_user.id,
            day_of_week=6,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=True
        )
        
        preference_service.quiet_hours_repo.get_by_user_and_day.return_value = mock_rule
        
        is_quiet, resume_at = await preference_service.check_quiet_hours(
            sample_user, NotificationPriority.NORMAL, True  # Bypass enabled
        )
        
        assert is_quiet is False  # Should bypass
        assert resume_at is None
    
    @pytest.mark.asyncio
    async def test_get_enabled_channels(self, preference_service, sample_user):
        """Test getting enabled channels for user."""
        # Mock user preferences
        mock_preferences = [
            UserChannelPreference(
                user_id=sample_user.id,
                channel=ChannelType.EMAIL,
                is_enabled=True
            ),
            UserChannelPreference(
                user_id=sample_user.id,
                channel=ChannelType.SMS,
                is_enabled=False
            )
        ]
        
        preference_service.preference_repo.get_by_user.return_value = mock_preferences
        
        result = await preference_service.get_enabled_channels(sample_user)
        
        assert ChannelType.EMAIL in result
        assert ChannelType.SMS not in result
        assert ChannelType.WEBHOOK in result  # Default enabled
    
    @pytest.mark.asyncio
    async def test_is_channel_enabled(self, preference_service, sample_user):
        """Test checking if specific channel is enabled."""
        # Mock preferences
        mock_preferences = [
            UserChannelPreference(
                user_id=sample_user.id,
                channel=ChannelType.EMAIL,
                is_enabled=True
            )
        ]
        
        preference_service.preference_repo.get_by_user.return_value = mock_preferences
        
        # Test enabled channel
        assert await preference_service.is_channel_enabled(sample_user, ChannelType.EMAIL) is True
        
        # Test disabled channel
        assert await preference_service.is_channel_enabled(sample_user, ChannelType.SMS) is False
    
    @pytest.mark.asyncio
    async def test_update_quiet_hours(self, preference_service, sample_user):
        """Test updating quiet hours rules."""
        rules_data = [
            {
                "day_of_week": 0,  # Sunday
                "start_time": "22:00",
                "end_time": "08:00",
                "timezone": "America/New_York",
                "is_active": True
            },
            {
                "day_of_week": 6,  # Saturday
                "start_time": "23:00",
                "end_time": "09:00",
                "timezone": "America/New_York",
                "is_active": True
            }
        ]
        
        mock_created_rules = [
            QuietHours(
                user_id=sample_user.id,
                day_of_week=0,
                start_time=time(22, 0),
                end_time=time(8, 0),
                timezone="America/New_York",
                is_active=True
            ),
            QuietHours(
                user_id=sample_user.id,
                day_of_week=6,
                start_time=time(23, 0),
                end_time=time(9, 0),
                timezone="America/New_York",
                is_active=True
            )
        ]
        
        preference_service.quiet_hours_repo.upsert_multiple_rules.return_value = mock_created_rules
        
        result = await preference_service.update_quiet_hours(str(sample_user.id), rules_data)
        
        assert result == mock_created_rules
        preference_service.quiet_hours_repo.upsert_multiple_rules.assert_called_once_with(
            str(sample_user.id), rules_data
        )
    
    @pytest.mark.asyncio
    async def test_cache_invalidation(self, preference_service, sample_user):
        """Test that cache is invalidated on updates."""
        with pytest.patch('app.services.preference_service.PreferenceService._invalidate_preferences_cache') as mock_invalidate:
            await preference_service.update_channel_preference(
                str(sample_user.id), ChannelType.EMAIL, True
            )
            
            mock_invalidate.assert_called_once_with(str(sample_user.id))
        
        with pytest.patch('app.services.preference_service.PreferenceService._invalidate_quiet_hours_cache') as mock_invalidate:
            await preference_service.update_quiet_hours(str(sample_user.id), [])
            
            mock_invalidate.assert_called_once_with(str(sample_user.id))
