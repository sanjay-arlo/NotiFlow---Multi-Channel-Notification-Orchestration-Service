"""
Unit tests for template service.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.services.template_service import TemplateService
from app.db.models.template import Template
from app.core.constants import TemplateCategory


class TestTemplateService:
    """Test cases for TemplateService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.template_repo = AsyncMock()
        self.service = TemplateService(self.template_repo)
    
    @pytest.mark.asyncio
    async def test_get_template_success(self):
        """Test successful template retrieval."""
        tenant_id = "test-tenant"
        slug = "welcome-email"
        
        mock_template = Template(
            id="test-template-id",
            tenant_id=tenant_id,
            name="Welcome Email",
            slug=slug,
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1><p>Thanks for joining.</p>",
            sms_body="Welcome {{ name }}!",
            variables_schema=[
                {"name": "name", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        self.template_repo.get_by_slug.return_value = mock_template
        
        result = await self.service.get_template(tenant_id, slug)
        
        assert result == mock_template
        self.template_repo.get_by_slug.assert_called_once_with(tenant_id, slug)
    
    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test template retrieval when not found."""
        tenant_id = "test-tenant"
        slug = "non-existent"
        
        self.template_repo.get_by_slug.return_value = None
        
        result = await self.service.get_template(tenant_id, slug)
        
        assert result is None
        self.template_repo.get_by_slug.assert_called_once_with(tenant_id, slug)
    
    @pytest.mark.asyncio
    async def test_render_template_email_success(self):
        """Test successful email template rendering."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Welcome Email",
            slug="welcome-email",
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1><p>Company: {{ company }}</p>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True},
                {"name": "company", "type": "string", "required": False}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {"name": "John Doe", "company": "Acme Corp"}
        
        result = await self.service.render_template(template, variables, "email")
        
        assert result["subject"] == "Welcome John Doe!"
        assert "<h1>Welcome John Doe!</h1>" in result["body"]
        assert "Company: Acme Corp" in result["body"]
        assert result["is_valid"] is True
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_render_template_sms_success(self):
        """Test successful SMS template rendering."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Welcome SMS",
            slug="welcome-sms",
            sms_body="Welcome {{ name }}! Your code: {{ code }}",
            variables_schema=[
                {"name": "name", "type": "string", "required": True},
                {"name": "code", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {"name": "Alice", "code": "123456"}
        
        result = await self.service.render_template(template, variables, "sms")
        
        assert result["body"] == "Welcome Alice! Your code: 123456"
        assert result["is_valid"] is True
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_render_template_webhook_success(self):
        """Test successful webhook template rendering."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Webhook Event",
            slug="webhook-event",
            webhook_payload='{"event": "{{ event_type }}", "user": "{{ user_id }}", "data": {{ data | tojson}}}',
            variables_schema=[
                {"name": "event_type", "type": "string", "required": True},
                {"name": "user_id", "type": "string", "required": True},
                {"name": "data", "type": "object", "required": False}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {
            "event_type": "user_signup",
            "user_id": "12345",
            "data": {"email": "user@example.com"}
        }
        
        result = await self.service.render_template(template, variables, "webhook")
        
        import json
        payload = json.loads(result["body"])
        assert payload["event"] == "user_signup"
        assert payload["user"] == "12345"
        assert payload["data"]["email"] == "user@example.com"
        assert result["is_valid"] is True
        assert result["errors"] == []
    
    @pytest.mark.asyncio
    async def test_render_template_missing_required_variable(self):
        """Test template rendering with missing required variable."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Welcome Email",
            slug="welcome-email",
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {}  # Missing required 'name' variable
        
        result = await self.service.render_template(template, variables, "email")
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "name" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_render_template_invalid_jinja_syntax(self):
        """Test template rendering with invalid Jinja syntax."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Invalid Template",
            slug="invalid-template",
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1>{{ invalid syntax }}",
            variables_schema=[
                {"name": "name", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {"name": "John Doe"}
        
        result = await self.service.render_template(template, variables, "email")
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_render_template_with_filters(self):
        """Test template rendering with Jinja filters."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Filtered Template",
            slug="filtered-template",
            email_subject="Welcome {{ name | upper }}!",
            email_body="<h1>{{ message | title }}</h1>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True},
                {"name": "message", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {"name": "john doe", "message": "hello world"}
        
        result = await self.service.render_template(template, variables, "email")
        
        assert result["subject"] == "Welcome JOHN DOE!"
        assert "<h1>Hello World</h1>" in result["body"]
        assert result["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_render_template_with_conditionals(self):
        """Test template rendering with conditionals."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Conditional Template",
            slug="conditional-template",
            email_body="{% if is_premium %}<h1>Premium User</h1>{% else %}<h1>Regular User</h1>{% endif %}",
            variables_schema=[
                {"name": "is_premium", "type": "boolean", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        # Test with premium user
        variables = {"is_premium": True}
        result = await self.service.render_template(template, variables, "email")
        assert "<h1>Premium User</h1>" in result["body"]
        assert result["is_valid"] is True
        
        # Test with regular user
        variables = {"is_premium": False}
        result = await self.service.render_template(template, variables, "email")
        assert "<h1>Regular User</h1>" in result["body"]
        assert result["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_render_template_with_loops(self):
        """Test template rendering with loops."""
        template = Template(
            id="test-template-id",
            tenant_id="test-tenant",
            name="Loop Template",
            slug="loop-template",
            email_body="<ul>{% for item in items %}<li>{{ item }}</li>{% endfor %}</ul>",
            variables_schema=[
                {"name": "items", "type": "array", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        variables = {"items": ["item1", "item2", "item3"]}
        
        result = await self.service.render_template(template, variables, "email")
        
        assert "<li>item1</li>" in result["body"]
        assert "<li>item2</li>" in result["body"]
        assert "<li>item3</li>" in result["body"]
        assert result["is_valid"] is True
    
    @pytest.mark.asyncio
    async def test_validate_template_success(self):
        """Test successful template validation."""
        template_data = {
            "name": "Test Template",
            "slug": "test-template",
            "email_subject": "Test: {{ subject }}",
            "email_body": "<h1>{{ title }}</h1><p>{{ content }}</p>",
            "variables_schema": [
                {"name": "subject", "type": "string", "required": True},
                {"name": "title", "type": "string", "required": True},
                {"name": "content", "type": "string", "required": True}
            ]
        }
        
        result = await self.service.validate_template(template_data)
        
        assert result["is_valid"] is True
        assert result["errors"] == []
        assert result["warnings"] == []
    
    @pytest.mark.asyncio
    async def test_validate_template_invalid_syntax(self):
        """Test template validation with invalid syntax."""
        template_data = {
            "name": "Invalid Template",
            "slug": "invalid-template",
            "email_subject": "Test: {{ subject }}",
            "email_body": "<h1>{{ title }}</h1>{{ invalid syntax }}",
            "variables_schema": [
                {"name": "subject", "type": "string", "required": True},
                {"name": "title", "type": "string", "required": True}
            ]
        }
        
        result = await self.service.validate_template(template_data)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
    
    @pytest.mark.asyncio
    async def test_validate_template_undefined_variables(self):
        """Test template validation with undefined variables."""
        template_data = {
            "name": "Undefined Variables Template",
            "slug": "undefined-template",
            "email_subject": "Test: {{ subject }}",
            "email_body": "<h1>{{ title }}</h1><p>{{ content }}</p>",
            "variables_schema": [
                {"name": "subject", "type": "string", "required": True}
                # Missing title and content
            ]
        }
        
        result = await self.service.validate_template(template_data)
        
        assert result["is_valid"] is False
        assert "title" in str(result["errors"])
        assert "content" in str(result["errors"])
    
    @pytest.mark.asyncio
    async def test_validate_template_unused_variables(self):
        """Test template validation with unused variables."""
        template_data = {
            "name": "Unused Variables Template",
            "slug": "unused-template",
            "email_subject": "Test: {{ subject }}",
            "email_body": "<h1>{{ title }}</h1>",
            "variables_schema": [
                {"name": "subject", "type": "string", "required": True},
                {"name": "title", "type": "string", "required": True},
                {"name": "unused_var", "type": "string", "required": False}
            ]
        }
        
        result = await self.service.validate_template(template_data)
        
        assert result["is_valid"] is True
        assert "unused_var" in str(result["warnings"])
    
    @pytest.mark.asyncio
    async def test_create_template_success(self):
        """Test successful template creation."""
        tenant_id = "test-tenant"
        template_data = {
            "name": "New Template",
            "slug": "new-template",
            "email_subject": "Welcome {{ name }}!",
            "email_body": "<h1>Welcome {{ name }}!</h1>",
            "variables_schema": [
                {"name": "name", "type": "string", "required": True}
            ],
            "category": TemplateCategory.TRANSACTIONAL
        }
        
        mock_template = Template(
            id="new-template-id",
            tenant_id=tenant_id,
            **template_data
        )
        
        self.template_repo.create.return_value = mock_template
        
        result = await self.service.create_template(tenant_id, template_data)
        
        assert result == mock_template
        self.template_repo.create.assert_called_once_with(tenant_id, template_data)
    
    @pytest.mark.asyncio
    async def test_update_template_success(self):
        """Test successful template update."""
        template_id = "test-template-id"
        update_data = {
            "name": "Updated Template",
            "email_subject": "Updated: {{ subject }}",
            "is_active": False
        }
        
        mock_template = Template(
            id=template_id,
            tenant_id="test-tenant",
            name="Updated Template",
            slug="test-template",
            email_subject="Updated: {{ subject }}",
            is_active=False
        )
        
        self.template_repo.update.return_value = mock_template
        
        result = await self.service.update_template(template_id, update_data)
        
        assert result == mock_template
        self.template_repo.update.assert_called_once_with(template_id, update_data)
    
    @pytest.mark.asyncio
    async def test_delete_template_success(self):
        """Test successful template deletion."""
        template_id = "test-template-id"
        
        self.template_repo.delete.return_value = True
        
        result = await self.service.delete_template(template_id)
        
        assert result is True
        self.template_repo.delete.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_list_templates_success(self):
        """Test successful template listing."""
        tenant_id = "test-tenant"
        filters = {"category": TemplateCategory.TRANSACTIONAL, "is_active": True}
        
        mock_templates = [
            Template(
                id="template-1",
                tenant_id=tenant_id,
                name="Template 1",
                slug="template-1",
                category=TemplateCategory.TRANSACTIONAL,
                is_active=True
            ),
            Template(
                id="template-2",
                tenant_id=tenant_id,
                name="Template 2",
                slug="template-2",
                category=TemplateCategory.TRANSACTIONAL,
                is_active=True
            )
        ]
        
        self.template_repo.list.return_value = mock_templates
        
        result = await self.service.list_templates(tenant_id, filters)
        
        assert result == mock_templates
        self.template_repo.list.assert_called_once_with(tenant_id, filters)
    
    @pytest.mark.asyncio
    async def test_preview_template_success(self):
        """Test successful template preview."""
        tenant_id = "test-tenant"
        slug = "welcome-email"
        variables = {"name": "John Doe", "company": "Acme Corp"}
        
        mock_template = Template(
            id="test-template-id",
            tenant_id=tenant_id,
            name="Welcome Email",
            slug=slug,
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1><p>Company: {{ company }}</p>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True},
                {"name": "company", "type": "string", "required": False}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        self.template_repo.get_by_slug.return_value = mock_template
        
        result = await self.service.preview_template(tenant_id, slug, variables)
        
        assert result["template_id"] == "test-template-id"
        assert result["rendered_email_subject"] == "Welcome John Doe!"
        assert "<h1>Welcome John Doe!</h1>" in result["rendered_email_body"]
        assert result["is_valid"] is True
        assert result["validation_errors"] == []
    
    @pytest.mark.asyncio
    async def test_preview_template_not_found(self):
        """Test template preview when template not found."""
        tenant_id = "test-tenant"
        slug = "non-existent"
        variables = {"name": "John Doe"}
        
        self.template_repo.get_by_slug.return_value = None
        
        with pytest.raises(ValueError, match="Template not found"):
            await self.service.preview_template(tenant_id, slug, variables)
    
    @pytest.mark.asyncio
    async def test_get_template_by_id_success(self):
        """Test successful template retrieval by ID."""
        template_id = "test-template-id"
        
        mock_template = Template(
            id=template_id,
            tenant_id="test-tenant",
            name="Test Template",
            slug="test-template",
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        self.template_repo.get_by_id.return_value = mock_template
        
        result = await self.service.get_template_by_id(template_id)
        
        assert result == mock_template
        self.template_repo.get_by_id.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_get_template_by_id_not_found(self):
        """Test template retrieval by ID when not found."""
        template_id = "non-existent-id"
        
        self.template_repo.get_by_id.return_value = None
        
        result = await self.service.get_template_by_id(template_id)
        
        assert result is None
        self.template_repo.get_by_id.assert_called_once_with(template_id)
    
    @pytest.mark.asyncio
    async def test_search_templates_success(self):
        """Test successful template search."""
        tenant_id = "test-tenant"
        query = "welcome"
        
        mock_templates = [
            Template(
                id="template-1",
                tenant_id=tenant_id,
                name="Welcome Email",
                slug="welcome-email",
                category=TemplateCategory.TRANSACTIONAL,
                is_active=True
            )
        ]
        
        self.template_repo.search.return_value = mock_templates
        
        result = await self.service.search_templates(tenant_id, query)
        
        assert result == mock_templates
        self.template_repo.search.assert_called_once_with(tenant_id, query)
    
    @pytest.mark.asyncio
    async def test_duplicate_template_success(self):
        """Test successful template duplication."""
        source_template_id = "source-template-id"
        new_template_data = {
            "name": "Duplicated Template",
            "slug": "duplicated-template"
        }
        
        mock_source_template = Template(
            id=source_template_id,
            tenant_id="test-tenant",
            name="Source Template",
            slug="source-template",
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        mock_duplicated_template = Template(
            id="duplicated-template-id",
            tenant_id="test-tenant",
            name="Duplicated Template",
            slug="duplicated-template",
            email_subject="Welcome {{ name }}!",
            email_body="<h1>Welcome {{ name }}!</h1>",
            variables_schema=[
                {"name": "name", "type": "string", "required": True}
            ],
            category=TemplateCategory.TRANSACTIONAL,
            is_active=True
        )
        
        self.template_repo.get_by_id.return_value = mock_source_template
        self.template_repo.create.return_value = mock_duplicated_template
        
        result = await self.service.duplicate_template(source_template_id, new_template_data)
        
        assert result == mock_duplicated_template
        self.template_repo.get_by_id.assert_called_once_with(source_template_id)
        self.template_repo.create.assert_called_once()
