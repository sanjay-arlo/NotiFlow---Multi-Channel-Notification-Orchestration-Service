"""
Webhook configuration management endpoints.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_tenant,
    get_webhook_config_service,
    handle_notiflow_exceptions
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


class WebhookConfigCreateRequest(BaseModel):
    """Request schema for creating webhook config."""
    name: str = Field(..., max_length=255, description="Webhook name")
    url: str = Field(..., max_length=2000, description="Webhook URL")
    secret: Optional[str] = Field(None, max_length=255, description="HMAC signing secret")
    headers: Dict[str, str] = Field(default_factory=dict, description="Custom headers")
    max_retries: int = Field(3, ge=1, le=10, description="Maximum retry attempts")
    timeout_seconds: int = Field(10, ge=1, le=300, description="Timeout in seconds")


class WebhookConfigUpdateRequest(BaseModel):
    """Request schema for updating webhook config."""
    name: Optional[str] = Field(None, max_length=255, description="Webhook name")
    url: Optional[str] = Field(None, max_length=2000, description="Webhook URL")
    secret: Optional[str] = Field(None, max_length=255, description="HMAC signing secret")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    max_retries: Optional[int] = Field(None, ge=1, le=10, description="Maximum retry attempts")
    timeout_seconds: Optional[int] = Field(None, ge=1, le=300, description="Timeout in seconds")


class WebhookConfigResponse(BaseModel):
    """Response schema for webhook config."""
    id: str = Field(..., description="Webhook config ID")
    name: str = Field(..., description="Webhook name")
    url: str = Field(..., description="Webhook URL")
    has_secret: bool = Field(..., description="Whether secret is configured")
    max_retries: int = Field(..., description="Maximum retry attempts")
    timeout_seconds: int = Field(..., description="Timeout in seconds")
    is_active: bool = Field(..., description="Whether webhook is active")
    is_healthy: bool = Field(..., description="Whether webhook appears healthy")
    failure_count: int = Field(..., description="Consecutive failure count")
    last_success_at: Optional[str] = Field(None, description="Last success timestamp")
    last_failure_at: Optional[str] = Field(None, description="Last failure timestamp")
    headers: Dict[str, str] = Field(..., description="Custom headers")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")


@router.post("/", response_model=WebhookConfigResponse)
@handle_notiflow_exceptions
async def create_webhook_config(
    request: WebhookConfigCreateRequest,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> WebhookConfigResponse:
    """Create a new webhook configuration."""
    webhook_config = await webhook_config_service.create_webhook_config(
        tenant_id=str(tenant.id),
        name=request.name,
        url=request.url,
        secret=request.secret,
        headers=request.headers,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds
    )
    
    return WebhookConfigResponse(
        id=str(webhook_config.id),
        name=webhook_config.name,
        url=webhook_config.url,
        has_secret=webhook_config.has_secret(),
        max_retries=webhook_config.max_retries,
        timeout_seconds=webhook_config.timeout_seconds,
        is_active=webhook_config.is_active,
        is_healthy=webhook_config.is_healthy(),
        failure_count=webhook_config.failure_count,
        last_success_at=webhook_config.last_success_at.isoformat() if webhook_config.last_success_at else None,
        last_failure_at=webhook_config.last_failure_at.isoformat() if webhook_config.last_failure_at else None,
        headers=webhook_config.headers,
        created_at=webhook_config.created_at.isoformat(),
        updated_at=webhook_config.updated_at.isoformat()
    )


@router.get("/", response_model=PaginatedResponse[WebhookConfigResponse])
@handle_notiflow_exceptions
async def list_webhook_configs(
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service),
    active_only: bool = Query(True, description="Filter active webhooks only"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[WebhookConfigResponse]:
    """List webhook configurations for tenant."""
    skip = (page - 1) * per_page
    
    webhook_configs = await webhook_config_service.get_webhook_configs(
        str(tenant.id), active_only, skip, per_page
    )
    
    webhook_responses = [
        WebhookConfigResponse(
            id=str(config.id),
            name=config.name,
            url=config.url,
            has_secret=config.has_secret(),
            max_retries=config.max_retries,
            timeout_seconds=config.timeout_seconds,
            is_active=config.is_active,
            is_healthy=config.is_healthy(),
            failure_count=config.failure_count,
            last_success_at=config.last_success_at.isoformat() if config.last_success_at else None,
            last_failure_at=config.last_failure_at.isoformat() if config.last_failure_at else None,
            headers=config.headers,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat()
        )
        for config in webhook_configs
    ]
    
    return PaginatedResponse(
        items=webhook_responses,
        page=page,
        per_page=per_page,
        total=len(webhook_responses),
        pages=(len(webhook_responses) + per_page - 1) // per_page
    )


@router.get("/{webhook_id}", response_model=WebhookConfigResponse)
@handle_notiflow_exceptions
async def get_webhook_config(
    webhook_id: str,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> WebhookConfigResponse:
    """Get webhook configuration by ID."""
    webhook_config = await webhook_config_service.get_webhook_config(webhook_id)
    
    return WebhookConfigResponse(
        id=str(webhook_config.id),
        name=webhook_config.name,
        url=webhook_config.url,
        has_secret=webhook_config.has_secret(),
        max_retries=webhook_config.max_retries,
        timeout_seconds=webhook_config.timeout_seconds,
        is_active=webhook_config.is_active,
        is_healthy=webhook_config.is_healthy(),
        failure_count=webhook_config.failure_count,
        last_success_at=webhook_config.last_success_at.isoformat() if webhook_config.last_success_at else None,
        last_failure_at=webhook_config.last_failure_at.isoformat() if webhook_config.last_failure_at else None,
        headers=webhook_config.headers,
        created_at=webhook_config.created_at.isoformat(),
        updated_at=webhook_config.updated_at.isoformat()
    )


@router.put("/{webhook_id}", response_model=WebhookConfigResponse)
@handle_notiflow_exceptions
async def update_webhook_config(
    webhook_id: str,
    request: WebhookConfigUpdateRequest,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> WebhookConfigResponse:
    """Update webhook configuration."""
    webhook_config = await webhook_config_service.update_webhook_config(
        webhook_id,
        name=request.name,
        url=request.url,
        secret=request.secret,
        headers=request.headers,
        max_retries=request.max_retries,
        timeout_seconds=request.timeout_seconds
    )
    
    return WebhookConfigResponse(
        id=str(webhook_config.id),
        name=webhook_config.name,
        url=webhook_config.url,
        has_secret=webhook_config.has_secret(),
        max_retries=webhook_config.max_retries,
        timeout_seconds=webhook_config.timeout_seconds,
        is_active=webhook_config.is_active,
        is_healthy=webhook_config.is_healthy(),
        failure_count=webhook_config.failure_count,
        last_success_at=webhook_config.last_success_at.isoformat() if webhook_config.last_success_at else None,
        last_failure_at=webhook_config.last_failure_at.isoformat() if webhook_config.last_failure_at else None,
        headers=webhook_config.headers,
        created_at=webhook_config.created_at.isoformat(),
        updated_at=webhook_config.updated_at.isoformat()
    )


@router.delete("/{webhook_id}")
@handle_notiflow_exceptions
async def delete_webhook_config(
    webhook_id: str,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> Dict[str, str]:
    """Delete webhook configuration."""
    success = await webhook_config_service.delete_webhook_config(webhook_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook configuration not found"
        )
    
    return {
        "id": webhook_id,
        "message": "Webhook configuration deleted successfully"
    }


@router.post("/{webhook_id}/test")
@handle_notiflow_exceptions
async def test_webhook_config(
    webhook_id: str,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> Dict[str, any]:
    """Test webhook configuration."""
    result = await webhook_config_service.test_webhook_config(webhook_id)
    
    return result


@router.post("/{webhook_id}/activate")
@handle_notiflow_exceptions
async def activate_webhook_config(
    webhook_id: str,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> Dict[str, str]:
    """Activate webhook configuration."""
    webhook_config = await webhook_config_service.activate_webhook_config(webhook_id)
    
    return {
        "id": webhook_id,
        "message": "Webhook configuration activated successfully"
    }


@router.post("/{webhook_id}/deactivate")
@handle_notiflow_exceptions
async def deactivate_webhook_config(
    webhook_id: str,
    tenant = Depends(get_current_tenant),
    webhook_config_service = Depends(get_webhook_config_service)
) -> Dict[str, str]:
    """Deactivate webhook configuration."""
    webhook_config = await webhook_config_service.deactivate_webhook_config(webhook_id)
    
    return {
        "id": webhook_id,
        "message": "Webhook configuration deactivated successfully"
    }
