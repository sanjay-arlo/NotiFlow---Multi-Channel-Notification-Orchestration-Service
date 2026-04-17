"""
User preference management service.
"""

from datetime import datetime, time
from typing import List, Optional, Tuple

from app.core.constants import ChannelType
from app.core.exceptions import NoChannelsAvailableError, QuietHoursActiveError
from app.db.models.user import User
from app.db.models.user_preference import UserChannelPreference
from app.db.models.quiet_hours import QuietHours
from app.repositories.preference_repo import (
    UserPreferenceRepository,
    QuietHoursRepository
)
from app.utils.redis_client import redis_client
from app.utils.time_utils import (
    now_in_timezone,
    time_in_timezone,
    calculate_resume_time,
    get_day_of_week
)
from app.core.constants import (
    REDIS_PREFS_TTL,
    REDIS_QUIET_HOURS_TTL
)


class PreferenceService:
    """Service for managing user preferences and quiet hours."""
    
    def __init__(
        self,
        preference_repo: UserPreferenceRepository,
        quiet_hours_repo: QuietHoursRepository
    ):
        self.preference_repo = preference_repo
        self.quiet_hours_repo = quiet_hours_repo
    
    async def get_user_preferences(
        self,
        user_id: str,
        use_cache: bool = True
    ) -> dict[str, bool]:
        """Get user's channel preferences."""
        if use_cache:
            cached_prefs = await self._get_cached_preferences(user_id)
            if cached_prefs:
                return cached_prefs
        
        # Get from database
        preferences = await self.preference_repo.get_by_user(user_id)
        
        # Build preference dict
        pref_dict = {}
        for pref in preferences:
            pref_dict[pref.channel] = pref.is_enabled
        
        # Set defaults for missing channels
        for channel in [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]:
            if channel not in pref_dict:
                pref_dict[channel] = True  # Enable by default
        
        # Cache the result
        await self._cache_preferences(user_id, pref_dict)
        
        return pref_dict
    
    async def update_channel_preference(
        self,
        user_id: str,
        channel: str,
        is_enabled: bool
    ) -> UserChannelPreference:
        """Update user's channel preference."""
        preference = await self.preference_repo.upsert_preference(
            user_id, channel, is_enabled
        )
        
        # Invalidate cache
        await self._invalidate_preferences_cache(user_id)
        
        return preference
    
    async def get_quiet_hours(
        self,
        user_id: str,
        use_cache: bool = True
    ) -> List[QuietHours]:
        """Get user's quiet hours rules."""
        if use_cache:
            cached_rules = await self._get_cached_quiet_hours(user_id)
            if cached_rules:
                return cached_rules
        
        # Get from database
        rules = await self.quiet_hours_repo.get_by_user(user_id)
        
        # Cache the result
        await self._cache_quiet_hours(user_id, rules)
        
        return rules
    
    async def update_quiet_hours(
        self,
        user_id: str,
        rules: List[dict]
    ) -> List[QuietHours]:
        """Update user's quiet hours rules."""
        # Clear existing rules
        await self.quiet_hours_repo.delete_by_user(user_id)
        
        # Create new rules
        created_rules = await self.quiet_hours_repo.upsert_multiple_rules(
            user_id, rules
        )
        
        # Invalidate cache
        await self._invalidate_quiet_hours_cache(user_id)
        
        return created_rules
    
    async def check_quiet_hours(
        self,
        user: User,
        notification_priority: str,
        bypass_quiet_hours: bool = False
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Check if quiet hours are currently active.
        
        Returns:
            (is_quiet, resume_at) tuple
        """
        # Critical notifications always bypass quiet hours
        if bypass_quiet_hours or notification_priority == "critical":
            return False, None
        
        # Get quiet hours rules
        rules = await self.get_quiet_hours(user.id)
        
        if not rules:
            return False, None
        
        # Get current time in user's timezone
        current_time = now_in_timezone(user.timezone)
        current_day = get_day_of_week(current_time)
        current_time_only = current_time.time()
        
        # Find rule for current day
        current_rule = None
        for rule in rules:
            if rule.day_of_week == current_day:
                current_rule = rule
                break
        
        if not current_rule or not current_rule.is_active:
            return False, None
        
        # Check if current time is within quiet hours
        from app.utils.time_utils import is_time_in_range
        is_quiet = is_time_in_range(
            current_time_only,
            current_rule.start_time,
            current_rule.end_time
        )
        
        if is_quiet:
            # Calculate resume time
            resume_at = calculate_resume_time(
                current_time,
                current_rule.end_time,
                user.timezone
            )
            return True, resume_at
        
        return False, None
    
    async def get_enabled_channels(
        self,
        user: User,
        use_cache: bool = True
    ) -> List[str]:
        """Get list of enabled channels for user."""
        preferences = await self.get_user_preferences(user.id, use_cache)
        
        enabled_channels = []
        for channel, is_enabled in preferences.items():
            if is_enabled and self._is_channel_available(user, channel):
                enabled_channels.append(channel)
        
        return enabled_channels
    
    async def is_channel_enabled(
        self,
        user: User,
        channel: str,
        use_cache: bool = True
    ) -> bool:
        """Check if specific channel is enabled for user."""
        preferences = await self.get_user_preferences(user.id, use_cache)
        return preferences.get(channel, False)
    
    def _is_channel_available(self, user: User, channel: str) -> bool:
        """Check if channel is available for user."""
        if channel == ChannelType.EMAIL:
            return user.has_email()
        elif channel == ChannelType.SMS:
            return user.has_phone()
        elif channel == ChannelType.WEBHOOK:
            return True  # Webhook is always available if configured
        return False
    
    async def _get_cached_preferences(self, user_id: str) -> Optional[dict[str, bool]]:
        """Get cached user preferences."""
        try:
            return await redis_client.json_get(f"prefs:{user_id}")
        except Exception:
            return None
    
    async def _cache_preferences(self, user_id: str, preferences: dict[str, bool]) -> None:
        """Cache user preferences."""
        try:
            await redis_client.json_set(
                f"prefs:{user_id}",
                preferences,
                REDIS_PREFS_TTL
            )
        except Exception:
            pass  # Cache failures shouldn't break functionality
    
    async def _invalidate_preferences_cache(self, user_id: str) -> None:
        """Invalidate cached user preferences."""
        try:
            await redis_client.delete(f"prefs:{user_id}")
        except Exception:
            pass
    
    async def _get_cached_quiet_hours(self, user_id: str) -> Optional[List[QuietHours]]:
        """Get cached quiet hours rules."""
        try:
            return await redis_client.json_get(f"quiet:{user_id}")
        except Exception:
            return None
    
    async def _cache_quiet_hours(self, user_id: str, rules: List[QuietHours]) -> None:
        """Cache quiet hours rules."""
        try:
            # Convert to dict for JSON serialization
            rules_dict = []
            for rule in rules:
                rules_dict.append({
                    "day_of_week": rule.day_of_week,
                    "start_time": rule.start_time.isoformat(),
                    "end_time": rule.end_time.isoformat(),
                    "timezone": rule.timezone,
                    "is_active": rule.is_active
                })
            
            await redis_client.json_set(
                f"quiet:{user_id}",
                rules_dict,
                REDIS_QUIET_HOURS_TTL
            )
        except Exception:
            pass
    
    async def _invalidate_quiet_hours_cache(self, user_id: str) -> None:
        """Invalidate cached quiet hours."""
        try:
            await redis_client.delete(f"quiet:{user_id}")
        except Exception:
            pass
