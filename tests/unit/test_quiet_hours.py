"""
Unit tests for quiet hours functionality.
"""

import pytest
from datetime import datetime, time, timezone
from unittest.mock import AsyncMock, patch

from app.core.constants import NotificationPriority
from app.db.models.quiet_hours import QuietHours
from app.utils.time_utils import is_in_quiet_hours, calculate_quiet_hours_resume_time


class TestQuietHours:
    """Test cases for quiet hours functionality."""
    
    def test_is_in_quiet_hours_active_rule(self):
        """Test quiet hours check when rule is active."""
        # Create active quiet hours rule (22:00-08:00)
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,  # Sunday
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=True
        )
        
        # Test during quiet hours (23:00)
        test_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)  # Sunday 23:00 UTC
        with patch('app.utils.time_utils.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = test_time
            result = is_in_quiet_hours(quiet_rule, test_time)
            assert result is True
        
        # Test outside quiet hours (09:00)
        test_time = datetime(2024, 1, 14, 9, 0, tzinfo=timezone.utc)  # Sunday 09:00 UTC
        with patch('app.utils.time_utils.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = test_time
            result = is_in_quiet_hours(quiet_rule, test_time)
            assert result is False
    
    def test_is_in_quiet_hours_inactive_rule(self):
        """Test quiet hours check when rule is inactive."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="America/New_York",
            is_active=False  # Inactive rule
        )
        
        test_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
    
    def test_is_in_quiet_hours_cross_midnight(self):
        """Test quiet hours that cross midnight."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test after midnight (01:00)
        test_time = datetime(2024, 1, 15, 1, 0, tzinfo=timezone.utc)  # Monday 01:00
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is True
        
        # Test after end time (09:00)
        test_time = datetime(2024, 1, 15, 9, 0, tzinfo=timezone.utc)  # Monday 09:00
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
    
    def test_is_in_quiet_hours_same_day(self):
        """Test quiet hours within same day."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test during quiet hours (14:00)
        test_time = datetime(2024, 1, 14, 14, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is True
        
        # Test before quiet hours (08:00)
        test_time = datetime(2024, 1, 14, 8, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
        
        # Test after quiet hours (18:00)
        test_time = datetime(2024, 1, 14, 18, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
    
    def test_is_in_quiet_hours_boundary_conditions(self):
        """Test quiet hours boundary conditions."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test exactly at start time (22:00)
        test_time = datetime(2024, 1, 14, 22, 0, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is True
        
        # Test exactly at end time (08:00)
        test_time = datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
    
    def test_is_in_quiet_hours_timezone_handling(self):
        """Test timezone handling in quiet hours."""
        # User in New York (UTC-5 during standard time)
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),  # 10 PM New York time
            end_time=time(8, 0),     # 8 AM New York time
            timezone="America/New_York",
            is_active=True
        )
        
        # Test 3 AM UTC = 10 PM New York time (should be quiet)
        test_time = datetime(2024, 1, 14, 3, 0, tzinfo=timezone.utc)  # Sunday 3 AM UTC
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is True
        
        # Test 14 PM UTC = 9 AM New York time (should not be quiet)
        test_time = datetime(2024, 1, 14, 14, 0, tzinfo=timezone.utc)  # Sunday 2 PM UTC
        result = is_in_quiet_hours(quiet_rule, test_time)
        assert result is False
    
    def test_calculate_quiet_hours_resume_time_same_day(self):
        """Test resume time calculation for same-day quiet hours."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(17, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test during quiet hours
        current_time = datetime(2024, 1, 14, 14, 0, tzinfo=timezone.utc)
        resume_time = calculate_quiet_hours_resume_time(quiet_rule, current_time)
        
        expected_resume = datetime(2024, 1, 14, 17, 0, tzinfo=timezone.utc)
        assert resume_time == expected_resume
    
    def test_calculate_quiet_hours_resume_time_cross_midnight(self):
        """Test resume time calculation for quiet hours crossing midnight."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test during quiet hours (after midnight)
        current_time = datetime(2024, 1, 15, 3, 0, tzinfo=timezone.utc)  # Monday 3 AM
        resume_time = calculate_quiet_hours_resume_time(quiet_rule, current_time)
        
        expected_resume = datetime(2024, 1, 15, 8, 0, tzinfo=timezone.utc)
        assert resume_time == expected_resume
    
    def test_calculate_quiet_hours_resume_time_not_quiet(self):
        """Test resume time calculation when not in quiet hours."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test outside quiet hours
        current_time = datetime(2024, 1, 14, 10, 0, tzinfo=timezone.utc)
        resume_time = calculate_quiet_hours_resume_time(quiet_rule, current_time)
        
        assert resume_time is None
    
    def test_quiet_hours_critical_notification_bypass(self):
        """Test that critical notifications bypass quiet hours."""
        from app.services.preference_service import PreferenceService
        
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        with patch('app.services.preference_service.PreferenceService._get_cached_quiet_hours') as mock_cache:
            mock_cache.return_value = [quiet_rule]
            
            service = PreferenceService(AsyncMock(), AsyncMock())
            
            # Test critical notification
            current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
            is_quiet, resume_at = service.check_quiet_hours(
                None, NotificationPriority.CRITICAL, False, current_time, "UTC"
            )
            
            assert is_quiet is False  # Should bypass
            assert resume_at is None
    
    def test_quiet_hours_bypass_flag(self):
        """Test that bypass flag overrides quiet hours."""
        from app.services.preference_service import PreferenceService
        
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        with patch('app.services.preference_service.PreferenceService._get_cached_quiet_hours') as mock_cache:
            mock_cache.return_value = [quiet_rule]
            
            service = PreferenceService(AsyncMock(), AsyncMock())
            
            # Test with bypass flag
            current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
            is_quiet, resume_at = service.check_quiet_hours(
                None, NotificationPriority.NORMAL, True, current_time, "UTC"
            )
            
            assert is_quiet is False  # Should bypass
            assert resume_at is None
    
    def test_quiet_hours_multiple_rules(self):
        """Test quiet hours with multiple rules."""
        # Weekday rule
        weekday_rule = QuietHours(
            user_id="test-user",
            day_of_week=1,  # Monday
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Weekend rule
        weekend_rule = QuietHours(
            user_id="test-user",
            day_of_week=6,  # Saturday
            start_time=time(23, 0),
            end_time=time(9, 0),
            timezone="UTC",
            is_active=True
        )
        
        with patch('app.services.preference_service.PreferenceService._get_cached_quiet_hours') as mock_cache:
            mock_cache.return_value = [weekday_rule, weekend_rule]
            
            service = PreferenceService(AsyncMock(), AsyncMock())
            
            # Test Monday during quiet hours
            monday_time = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)  # Monday 11 PM
            is_quiet, resume_at = service.check_quiet_hours(
                None, NotificationPriority.NORMAL, False, monday_time, "UTC"
            )
            assert is_quiet is True
            
            # Test Saturday during quiet hours
            saturday_time = datetime(2024, 1, 20, 23, 30, tzinfo=timezone.utc)  # Saturday 11:30 PM
            is_quiet, resume_at = service.check_quiet_hours(
                None, NotificationPriority.NORMAL, False, saturday_time, "UTC"
            )
            assert is_quiet is True
    
    def test_quiet_hours_no_rules(self):
        """Test quiet hours when no rules exist."""
        from app.services.preference_service import PreferenceService
        
        with patch('app.services.preference_service.PreferenceService._get_cached_quiet_hours') as mock_cache:
            mock_cache.return_value = []
            
            service = PreferenceService(AsyncMock(), AsyncMock())
            
            current_time = datetime(2024, 1, 14, 23, 0, tzinfo=timezone.utc)
            is_quiet, resume_at = service.check_quiet_hours(
                None, NotificationPriority.NORMAL, False, current_time, "UTC"
            )
            
            assert is_quiet is False
            assert resume_at is None
    
    def test_quiet_hours_day_mismatch(self):
        """Test quiet hours when current day doesn't match rule."""
        quiet_rule = QuietHours(
            user_id="test-user",
            day_of_week=0,  # Sunday
            start_time=time(22, 0),
            end_time=time(8, 0),
            timezone="UTC",
            is_active=True
        )
        
        # Test on Monday (day 1) with Sunday rule
        monday_time = datetime(2024, 1, 15, 23, 0, tzinfo=timezone.utc)
        result = is_in_quiet_hours(quiet_rule, monday_time)
        assert result is False
    
    def test_quiet_hours_cache_invalidation(self):
        """Test that cache is properly invalidated."""
        from app.services.preference_service import PreferenceService
        
        preference_repo = AsyncMock()
        quiet_repo = AsyncMock()
        service = PreferenceService(preference_repo, quiet_repo)
        
        with patch('app.services.preference_service.PreferenceService._invalidate_quiet_hours_cache') as mock_invalidate:
            service.update_quiet_hours("user-123", [])
            mock_invalidate.assert_called_once_with("user-123")
