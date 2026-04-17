"""
User management endpoints.
"""

from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_tenant,
    get_user_repo,
    get_preference_service,
    handle_notiflow_exceptions
)
from app.core.constants import ChannelType
from app.schemas.common import PaginatedResponse
from app.db.models.user import User

router = APIRouter()


class UserUpsertRequest(BaseModel):
    """Request schema for user upsert."""
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number (E.164)")
    timezone: str = Field("UTC", description="User timezone")
    display_name: Optional[str] = Field(None, description="Display name")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class UserResponse(BaseModel):
    """Response schema for user."""
    id: str = Field(..., description="User ID")
    external_id: str = Field(..., description="External user ID")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    timezone: str = Field(..., description="User timezone")
    display_name: Optional[str] = Field(None, description="Display name")
    metadata: Dict[str, Any] = Field(..., description="User metadata")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")


@router.put("/{user_external_id}", response_model=UserResponse)
@handle_notiflow_exceptions
async def upsert_user(
    user_external_id: str,
    request: UserUpsertRequest,
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo)
) -> UserResponse:
    """Create or update a user."""
    user = await user_repo.upsert_user(
        tenant_id=str(tenant.id),
        external_id=user_external_id,
        user_data=request.dict()
    )
    
    return UserResponse(
        id=str(user.id),
        external_id=user.external_id,
        email=user.email,
        phone=user.phone,
        timezone=user.timezone,
        display_name=user.display_name,
        metadata=user.user_metadata,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat()
    )


@router.get("/{user_external_id}", response_model=UserResponse)
@handle_notiflow_exceptions
async def get_user(
    user_external_id: str,
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo)
) -> UserResponse:
    """Get user by external ID."""
    user = await user_repo.get_by_tenant_and_external(
        str(tenant.id), user_external_id
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        external_id=user.external_id,
        email=user.email,
        phone=user.phone,
        timezone=user.timezone,
        display_name=user.display_name,
        metadata=user.user_metadata,
        created_at=user.created_at.isoformat(),
        updated_at=user.updated_at.isoformat()
    )


@router.get("/")
@handle_notiflow_exceptions
async def list_users(
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[UserResponse]:
    """List users for tenant."""
    skip = (page - 1) * per_page
    
    users = await user_repo.get_multi_by_tenant(
        str(tenant.id), skip=skip, limit=per_page
    )
    
    user_responses = [
        UserResponse(
            id=str(user.id),
            external_id=user.external_id,
            email=user.email,
            phone=user.phone,
            timezone=user.timezone,
            display_name=user.display_name,
            metadata=user.user_metadata,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        for user in users
    ]
    
    return PaginatedResponse(
        items=user_responses,
        page=page,
        per_page=per_page,
        total=len(user_responses),
        pages=(len(user_responses) + per_page - 1) // per_page
    )


@router.get("/search")
@handle_notiflow_exceptions
async def search_users(
    query: str = Query(..., min_length=2, description="Search query"),
    tenant = Depends(get_current_tenant),
    user_repo = Depends(get_user_repo),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[UserResponse]:
    """Search users."""
    skip = (page - 1) * per_page
    
    users = await user_repo.search_users(
        query, str(tenant.id), skip=skip, limit=per_page
    )
    
    user_responses = [
        UserResponse(
            id=str(user.id),
            external_id=user.external_id,
            email=user.email,
            phone=user.phone,
            timezone=user.timezone,
            display_name=user.display_name,
            metadata=user.user_metadata,
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat()
        )
        for user in users
    ]
    
    return PaginatedResponse(
        items=user_responses,
        page=page,
        per_page=per_page,
        total=len(user_responses),
        pages=(len(user_responses) + per_page - 1) // per_page
    )
