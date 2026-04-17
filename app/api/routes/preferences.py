"""
User preference management endpoints.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from app.api.deps import (
    get_current_tenant,
    get_user_repo,
    get_preference_service,
    handle_notiflow_exceptions
)
from app.core.constants import ChannelType
from app.schemas.common import PaginatedResponse

router = APIRouter()


class ChannelPreferenceRequest(BaseModel):
    """Request schema for channel preference."""
    channel: str = Field(..., description="Channel name")
    is_enabled: bool = Field(..., description="Whether channel is enabled")
    
    @validator('channel')
    def validate_channel(cls, v):
        valid_channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]
        if v not in valid_channels:
            raise ValueError(f"Channel must be one of: {valid_channels}")
        return v


class ChannelPreferenceResponse(BaseModel):
    """Response schema for channel preference."""
    channel: str = Field(..., description="Channel name")
    is_enabled: bool = Field(..., description="Whether channel is enabled")
    updated_at: str = Field(..., description="Last update timestamp")


class QuietHoursRule(BaseModel):
    """Schema for quiet hours rule."""
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Sunday)")
    start_time: str = Field(..., description="Start time (HH:MM)")
    end_time: str = Field(..., description="End time (HH:MM)")
    timezone: str = Field("UTC", description="Timezone for rule")
    is_active: bool = Field(True, description="Whether rule is active")


class QuietHoursResponse(BaseModel):
    """Response schema for quiet hours."""
    rules: List[QuietHoursRule] = Field(..., description="Quiet hours rules")


@router.get("/{user_external_id}/preferences")
@handle_notiflow_exceptions
async def get_user_preferences(
    user_external_id: str,
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    preference_service = Depends(get_preference_service)
) -> Dict[str, ChannelPreferenceResponse]:
    """Get user's channel preferences."""
    user = await user_repo.get_by_tenant_and_external(
        str(tenant.id), user_external_id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    preferences = await preference_service.get_user_preferences(user.id)
    
    response = {}
    for channel, is_enabled in preferences.items():
        response[channel] = ChannelPreferenceResponse(
            channel=channel,
            is_enabled=is_enabled,
            updated_at=""  # Would come from DB
        )
    
    return response


@router.put("/{user_external_id}/preferences")
@handle_notiflow_exceptions
async def update_user_preferences(
    user_external_id: str,
    preferences: Dict[str, ChannelPreferenceRequest],
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    preference_service = Depends(get_preference_service)
) -> Dict[str, str]:
    """Update user's channel preferences."""
    user = await user_repo.get_by_tenant_and_external(
        str(tenant.id), user_external_id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    updated_preferences = {}
    for channel, pref_request in preferences.items():
        updated_pref = await preference_service.update_channel_preference(
            user.id, channel, pref_request.is_enabled
        )
        updated_preferences[channel] = ChannelPreferenceResponse(
            channel=channel,
            is_enabled=updated_pref.is_enabled,
            updated_at=updated_pref.updated_at.isoformat()
        )
    
    return {
        "message": "Preferences updated successfully",
        "preferences": updated_preferences
    }


@router.get("/{user_external_id}/quiet-hours")
@handle_notiflow_exceptions
async def get_quiet_hours(
    user_external_id: str,
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    preference_service = Depends(get_preference_service)
) -> QuietHoursResponse:
    """Get user's quiet hours rules."""
    user = await user_repo.get_by_tenant_and_external(
        str(tenant.id), user_external_id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    rules = await preference_service.get_quiet_hours(user.id)
    
    rule_responses = []
    for rule in rules:
        rule_responses.append(QuietHoursRule(
            day_of_week=rule.day_of_week,
            start_time=rule.start_time.strftime("%H:%M"),
            end_time=rule.end_time.strftime("%H:%M"),
            timezone=rule.timezone,
            is_active=rule.is_active
        ))
    
    return QuietHoursResponse(rules=rule_responses)


@router.put("/{user_external_id}/quiet-hours")
@handle_notiflow_exceptions
async def update_quiet_hours(
    user_external_id: str,
    request: QuietHoursResponse,
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    preference_service = Depends(get_preference_service)
) -> Dict[str, str]:
    """Update user's quiet hours rules."""
    user = await user_repo.get_by_tenant_and_external(
        str(tenant.id), user_external_id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Convert to dict format for service
    rules_data = []
    for rule in request.rules:
        rules_data.append({
            "day_of_week": rule.day_of_week,
            "start_time": rule.start_time,
            "end_time": rule.end_time,
            "timezone": rule.timezone,
            "is_active": rule.is_active
        })
    
    updated_rules = await preference_service.update_quiet_hours(
        user.id, rules_data
    )
    
    return {
        "message": "Quiet hours updated successfully",
        "rules_count": len(updated_rules)
    }
