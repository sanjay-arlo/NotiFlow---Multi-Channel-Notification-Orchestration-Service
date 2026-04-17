"""
Pydantic schemas for user preferences and quiet hours.
"""

from typing import Dict, List, Optional
from datetime import time
from pydantic import BaseModel, Field, validator

from app.core.constants import ChannelType


class ChannelPreferenceBase(BaseModel):
    """Base schema for channel preferences."""
    channel: ChannelType
    is_enabled: bool = True


class ChannelPreferenceCreate(ChannelPreferenceBase):
    """Schema for creating channel preferences."""
    pass


class ChannelPreferenceUpdate(BaseModel):
    """Schema for updating channel preferences."""
    is_enabled: bool


class ChannelPreferenceResponse(ChannelPreferenceBase):
    """Schema for channel preference responses."""
    id: str
    user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class QuietHoursBase(BaseModel):
    """Base schema for quiet hours."""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Sunday, 6=Saturday)")
    start_time: str = Field(..., regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="Start time in HH:MM format")
    end_time: str = Field(..., regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="End time in HH:MM format")
    timezone: str = Field(default="UTC", description="Timezone for the quiet hours")
    is_active: bool = True

    @validator('end_time')
    def validate_time_range(cls, v, values):
        """Validate that end time is different from start time."""
        if 'start_time' in values:
            start = time.fromisoformat(values['start_time'])
            end = time.fromisoformat(v)
            if start == end:
                raise ValueError('End time must be different from start time')
        return v


class QuietHoursCreate(QuietHoursBase):
    """Schema for creating quiet hours."""
    pass


class QuietHoursUpdate(BaseModel):
    """Schema for updating quiet hours."""
    start_time: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: Optional[str] = Field(None, regex=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class QuietHoursResponse(QuietHoursBase):
    """Schema for quiet hours responses."""
    id: str
    user_id: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class UserPreferencesResponse(BaseModel):
    """Schema for complete user preferences response."""
    user_id: str
    channels: Dict[str, bool]
    quiet_hours: List[QuietHoursResponse]
    timezone: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class BulkChannelPreferenceUpdate(BaseModel):
    """Schema for bulk channel preference updates."""
    preferences: Dict[ChannelType, bool] = Field(..., description="Channel preference mapping")


class PreferenceCheckRequest(BaseModel):
    """Schema for checking if notifications should be sent."""
    user_id: str
    channel: ChannelType
    priority: str = "normal"
    bypass_quiet_hours: bool = False


class PreferenceCheckResponse(BaseModel):
    """Schema for preference check responses."""
    can_send: bool
    channel_enabled: bool
    is_quiet_hours: bool
    quiet_hours_active: bool
    resume_at: Optional[str] = None
    reason: str
