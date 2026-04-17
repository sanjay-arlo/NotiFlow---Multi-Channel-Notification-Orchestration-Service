"""
Pydantic schemas for template management.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator

from app.core.constants import TemplateCategory


class TemplateVariable(BaseModel):
    """Schema for template variable definitions."""
    name: str = Field(..., min_length=1, max_length=50)
    type: str = Field(..., regex="^(string|integer|boolean|object|array)$")
    required: bool = True
    description: Optional[str] = None
    default_value: Optional[Any] = None


class TemplateBase(BaseModel):
    """Base schema for templates."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=100, regex="^[a-z0-9-]+$")
    category: TemplateCategory
    description: Optional[str] = None
    is_active: bool = True


class TemplateCreate(TemplateBase):
    """Schema for creating templates."""
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    sms_body: Optional[str] = None
    webhook_payload: Optional[str] = None
    variables_schema: List[TemplateVariable] = []

    @validator('variables_schema')
    def validate_variables(cls, v):
        """Validate that variables schema is not empty for templates with content."""
        return v


class TemplateUpdate(BaseModel):
    """Schema for updating templates."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[TemplateCategory] = None
    description: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    sms_body: Optional[str] = None
    webhook_payload: Optional[str] = None
    variables_schema: Optional[List[TemplateVariable]] = None
    is_active: Optional[bool] = None


class TemplateResponse(TemplateBase):
    """Schema for template responses."""
    id: str
    tenant_id: str
    email_subject: Optional[str]
    email_body: Optional[str]
    sms_body: Optional[str]
    webhook_payload: Optional[str]
    variables_schema: List[TemplateVariable]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class TemplatePreviewRequest(BaseModel):
    """Schema for template preview requests."""
    template_slug: str
    variables: Dict[str, Any] = {}
    channel: Optional[str] = None


class TemplatePreviewResponse(BaseModel):
    """Schema for template preview responses."""
    template_id: str
    template_name: str
    rendered_email_subject: Optional[str]
    rendered_email_body: Optional[str]
    rendered_sms_body: Optional[str]
    rendered_webhook_payload: Optional[str]
    is_valid: bool
    validation_errors: List[str] = []


class TemplateValidationRequest(BaseModel):
    """Schema for template validation requests."""
    template_slug: Optional[str] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    sms_body: Optional[str] = None
    webhook_payload: Optional[str] = None
    variables_schema: List[TemplateVariable] = []


class TemplateValidationResponse(BaseModel):
    """Schema for template validation responses."""
    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    missing_variables: List[str] = []
    unused_variables: List[str] = []


class TemplateListRequest(BaseModel):
    """Schema for template list requests."""
    category: Optional[TemplateCategory] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(None, min_length=1, max_length=100)
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class TemplateUsageStats(BaseModel):
    """Schema for template usage statistics."""
    template_id: str
    template_name: str
    total_sends: int
    successful_deliveries: int
    failed_deliveries: int
    success_rate: float
    last_used: Optional[str] = None


class TemplateDuplicateRequest(BaseModel):
    """Schema for template duplication requests."""
    source_template_slug: str
    new_name: str = Field(..., min_length=1, max_length=100)
    new_slug: str = Field(..., min_length=1, max_length=100, regex="^[a-z0-9-]+$")


class TemplateVersion(BaseModel):
    """Schema for template version history."""
    version: int
    changes: List[str]
    changed_by: str
    changed_at: str


class TemplateWithVersionsResponse(TemplateResponse):
    """Schema for template with version history."""
    versions: List[TemplateVersion] = []


class BulkTemplateUpdate(BaseModel):
    """Schema for bulk template updates."""
    template_ids: List[str]
    updates: TemplateUpdate


class TemplateExportRequest(BaseModel):
    """Schema for template export requests."""
    template_ids: Optional[List[str]] = None
    category: Optional[TemplateCategory] = None
    include_variables: bool = True


class TemplateImportRequest(BaseModel):
    """Schema for template import requests."""
    templates: List[TemplateCreate]
    overwrite_existing: bool = False
    validate_only: bool = False


class TemplateImportResponse(BaseModel):
    """Schema for template import responses."""
    imported: int
    updated: int
    failed: int
    errors: List[str] = []


class TemplateSearchRequest(BaseModel):
    """Schema for template search requests."""
    query: str = Field(..., min_length=1, max_length=100)
    category: Optional[TemplateCategory] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)


class TemplateTestRequest(BaseModel):
    """Schema for template test requests."""
    template_slug: str
    test_variables: Dict[str, Any]
    test_channels: List[str] = ["email", "sms", "webhook"]
    dry_run: bool = True


class TemplateTestResponse(BaseModel):
    """Schema for template test responses."""
    template_id: str
    test_results: Dict[str, Any]
    success: bool
    errors: List[str] = []
