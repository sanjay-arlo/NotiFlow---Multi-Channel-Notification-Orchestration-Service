"""
Template management endpoints.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_current_tenant,
    get_template_service,
    handle_notiflow_exceptions
)
from app.schemas.common import PaginatedResponse

router = APIRouter()


class TemplateCreateRequest(BaseModel):
    """Request schema for creating template."""
    name: str = Field(..., max_length=255, description="Template name")
    slug: str = Field(..., max_length=255, description="Template slug")
    email_subject: Optional[str] = Field(None, max_length=500, description="Email subject template")
    email_body: Optional[str] = Field(None, description="Email body template (HTML)")
    sms_body: Optional[str] = Field(None, description="SMS body template")
    webhook_payload: Optional[str] = Field(None, description="Webhook payload template (JSON)")
    variables_schema: List[Dict[str, any]] = Field(default_factory=list, description="Variables schema")
    category: str = Field("transactional", description="Template category")
    description: Optional[str] = Field(None, description="Template description")


class TemplateUpdateRequest(BaseModel):
    """Request schema for updating template."""
    name: Optional[str] = Field(None, max_length=255, description="Template name")
    email_subject: Optional[str] = Field(None, max_length=500, description="Email subject template")
    email_body: Optional[str] = Field(None, description="Email body template (HTML)")
    sms_body: Optional[str] = Field(None, description="SMS body template")
    webhook_payload: Optional[str] = Field(None, description="Webhook payload template (JSON)")
    variables_schema: Optional[List[Dict[str, any]]] = Field(None, description="Variables schema")
    category: Optional[str] = Field(None, description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    is_active: Optional[bool] = Field(None, description="Whether template is active")


class TemplateResponse(BaseModel):
    """Response schema for template."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    slug: str = Field(..., description="Template slug")
    email_subject: Optional[str] = Field(None, description="Email subject template")
    email_body: Optional[str] = Field(None, description="Email body template")
    sms_body: Optional[str] = Field(None, description="SMS body template")
    webhook_payload: Optional[str] = Field(None, description="Webhook payload template")
    variables_schema: List[Dict[str, any]] = Field(..., description="Variables schema")
    category: str = Field(..., description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    is_active: bool = Field(..., description="Whether template is active")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")


class TemplatePreviewRequest(BaseModel):
    """Request schema for template preview."""
    template_slug: str = Field(..., description="Template slug")
    variables: Dict[str, any] = Field(..., description="Variables for rendering")


@router.post("/", response_model=TemplateResponse)
@handle_notiflow_exceptions
async def create_template(
    request: TemplateCreateRequest,
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service)
) -> TemplateResponse:
    """Create a new template."""
    from app.db.models.template import Template
    from app.utils.id_utils import generate_template_id
    
    template_data = request.dict()
    template_data["id"] = generate_template_id()
    template_data["tenant_id"] = tenant.id
    
    template = await template_service.template_repo.create(template_data)
    
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        slug=template.slug,
        email_subject=template.email_subject,
        email_body=template.email_body,
        sms_body=template.sms_body,
        webhook_payload=template.webhook_payload,
        variables_schema=template.variables_schema,
        category=template.category,
        description=template.description,
        is_active=template.is_active,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.get("/", response_model=PaginatedResponse[TemplateResponse])
@handle_notiflow_exceptions
async def list_templates(
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service),
    category: Optional[str] = Query(None, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
) -> PaginatedResponse[TemplateResponse]:
    """List templates for tenant."""
    templates = await template_service.list_templates(
        str(tenant.id), category, skip=(page-1)*per_page, limit=per_page
    )
    
    template_responses = [
        TemplateResponse(
            id=str(template.id),
            name=template.name,
            slug=template.slug,
            email_subject=template.email_subject,
            email_body=template.email_body,
            sms_body=template.sms_body,
            webhook_payload=template.webhook_payload,
            variables_schema=template.variables_schema,
            category=template.category,
            description=template.description,
            is_active=template.is_active,
            created_at=template.created_at.isoformat(),
            updated_at=template.updated_at.isoformat()
        )
        for template in templates
    ]
    
    return PaginatedResponse(
        items=template_responses,
        page=page,
        per_page=per_page,
        total=len(template_responses),
        pages=(len(template_responses) + per_page - 1) // per_page
    )


@router.get("/{template_slug}", response_model=TemplateResponse)
@handle_notiflow_exceptions
async def get_template(
    template_slug: str,
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service)
) -> TemplateResponse:
    """Get template by slug."""
    template = await template_service.get_template(str(tenant.id), template_slug)
    
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        slug=template.slug,
        email_subject=template.email_subject,
        email_body=template.email_body,
        sms_body=template.sms_body,
        webhook_payload=template.webhook_payload,
        variables_schema=template.variables_schema,
        category=template.category,
        description=template.description,
        is_active=template.is_active,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat()
    )


@router.put("/{template_slug}", response_model=TemplateResponse)
@handle_notiflow_exceptions
async def update_template(
    template_slug: str,
    request: TemplateUpdateRequest,
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service)
) -> TemplateResponse:
    """Update template."""
    template = await template_service.get_template(str(tenant.id), template_slug)
    
    update_data = request.dict(exclude_unset=True)
    updated_template = await template_service.template_repo.update(template, update_data)
    
    return TemplateResponse(
        id=str(updated_template.id),
        name=updated_template.name,
        slug=updated_template.slug,
        email_subject=updated_template.email_subject,
        email_body=updated_template.email_body,
        sms_body=updated_template.sms_body,
        webhook_payload=updated_template.webhook_payload,
        variables_schema=updated_template.variables_schema,
        category=updated_template.category,
        description=updated_template.description,
        is_active=updated_template.is_active,
        created_at=updated_template.created_at.isoformat(),
        updated_at=updated_template.updated_at.isoformat()
    )


@router.delete("/{template_slug}")
@handle_notiflow_exceptions
async def delete_template(
    template_slug: str,
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service)
) -> Dict[str, str]:
    """Delete template."""
    template = await template_service.get_template(str(tenant.id), template_slug)
    await template_service.template_repo.deactivate_template(template.id)
    
    return {
        "id": str(template.id),
        "message": "Template deactivated successfully"
    }


@router.post("/{template_slug}/preview")
@handle_notiflow_exceptions
async def preview_template(
    template_slug: str,
    request: TemplatePreviewRequest,
    tenant = Depends(get_current_tenant),
    template_service = Depends(get_template_service)
) -> Dict[str, str]:
    """Preview template rendering."""
    template = await template_service.get_template(str(tenant.id), template_slug)
    
    rendered_content = await template_service.preview_template(
        template, request.variables
    )
    
    return {
        "template_id": str(template.id),
        "rendered_content": rendered_content
    }
