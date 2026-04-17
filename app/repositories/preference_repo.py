"""
User preference repository with specialized queries.
"""

from typing import List, Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_preference import UserChannelPreference
from app.db.models.quiet_hours import QuietHours
from app.repositories.base import BaseRepository


class UserPreferenceRepository(BaseRepository[UserChannelPreference, dict, dict]):
    """Repository for user channel preferences."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(UserChannelPreference, db)
    
    async def get_by_user(self, user_id: str) -> List[UserChannelPreference]:
        """Get all preferences for a user."""
        stmt = select(UserChannelPreference).where(
            UserChannelPreference.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_user_and_channel(
        self,
        user_id: str,
        channel: str
    ) -> Optional[UserChannelPreference]:
        """Get user preference for specific channel."""
        stmt = select(UserChannelPreference).where(
            and_(
                UserChannelPreference.user_id == user_id,
                UserChannelPreference.channel == channel
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert_preference(
        self,
        user_id: str,
        channel: str,
        is_enabled: bool
    ) -> UserChannelPreference:
        """Create or update user channel preference."""
        existing = await self.get_by_user_and_channel(user_id, channel)
        
        if existing:
            return await self.update(existing, {"is_enabled": is_enabled})
        else:
            return await self.create({
                "user_id": user_id,
                "channel": channel,
                "is_enabled": is_enabled
            })
    
    async def get_enabled_channels(self, user_id: str) -> List[str]:
        """Get list of enabled channels for user."""
        stmt = select(UserChannelPreference.channel).where(
            and_(
                UserChannelPreference.user_id == user_id,
                UserChannelPreference.is_enabled == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all preferences for a user."""
        stmt = select(UserChannelPreference).where(
            UserChannelPreference.user_id == user_id
        )
        result = await self.db.execute(stmt)
        preferences = result.scalars().all()
        
        for pref in preferences:
            await self.db.delete(pref)
        
        await self.db.flush()
        return len(preferences)


class QuietHoursRepository(BaseRepository[QuietHours, dict, dict]):
    """Repository for quiet hours rules."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(QuietHours, db)
    
    async def get_by_user(self, user_id: str) -> List[QuietHours]:
        """Get all quiet hours rules for a user."""
        stmt = select(QuietHours).where(
            and_(
                QuietHours.user_id == user_id,
                QuietHours.is_active == True
            )
        ).order_by(QuietHours.day_of_week.asc())
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def get_by_user_and_day(
        self,
        user_id: str,
        day_of_week: int
    ) -> Optional[QuietHours]:
        """Get quiet hours rule for specific day."""
        stmt = select(QuietHours).where(
            and_(
                QuietHours.user_id == user_id,
                QuietHours.day_of_week == day_of_week,
                QuietHours.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def upsert_rule(
        self,
        user_id: str,
        day_of_week: int,
        start_time,
        end_time,
        timezone: str = "UTC",
        is_active: bool = True
    ) -> QuietHours:
        """Create or update quiet hours rule."""
        existing = await self.get_by_user_and_day(user_id, day_of_week)
        
        rule_data = {
            "user_id": user_id,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
            "timezone": timezone,
            "is_active": is_active
        }
        
        if existing:
            return await self.update(existing, rule_data)
        else:
            return await self.create(rule_data)
    
    async def upsert_multiple_rules(
        self,
        user_id: str,
        rules: List[dict]
    ) -> List[QuietHours]:
        """Create or update multiple quiet hours rules."""
        created_rules = []
        
        for rule in rules:
            created_rule = await self.upsert_rule(
                user_id=user_id,
                day_of_week=rule["day_of_week"],
                start_time=rule["start_time"],
                end_time=rule["end_time"],
                timezone=rule.get("timezone", "UTC"),
                is_active=rule.get("is_active", True)
            )
            created_rules.append(created_rule)
        
        return created_rules
    
    async def delete_by_user(self, user_id: str) -> int:
        """Delete all quiet hours rules for a user."""
        stmt = select(QuietHours).where(
            QuietHours.user_id == user_id
        )
        result = await self.db.execute(stmt)
        rules = result.scalars().all()
        
        for rule in rules:
            await self.db.delete(rule)
        
        await self.db.flush()
        return len(rules)
    
    async def is_quiet_hours_active(
        self,
        user_id: str,
        current_time,
        current_day: int
    ) -> bool:
        """Check if quiet hours are currently active for user."""
        rule = await self.get_by_user_and_day(user_id, current_day)
        
        if not rule:
            return False
        
        from app.utils.time_utils import is_time_in_range
        return is_time_in_range(current_time, rule.start_time, rule.end_time)
