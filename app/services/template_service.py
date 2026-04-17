"""
Template rendering and management service.
"""

from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, Template, TemplateError, TemplateSyntaxError

from app.core.exceptions import (
    TemplateNotFoundError,
    TemplateRenderError,
    InvalidTemplateVariablesError
)
from app.db.models.notification import Notification
from app.db.models.template import Template
from app.repositories.template_repo import TemplateRepository


class TemplateService:
    """Service for template rendering and management."""
    
    def __init__(self, template_repo: TemplateRepository):
        self.template_repo = template_repo
        self.jinja_env = Environment(
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
    
    async def render_notification(
        self,
        template: Template,
        variables: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Render notification content for specified channels.
        
        Args:
            template: The template to render
            variables: Variables for template rendering
            channels: Channels to render for (None = all channels)
            
        Returns:
            Dict mapping channel names to rendered content
        """
        # Validate variables against template schema
        is_valid, missing_vars = template.validate_variables(variables)
        if not is_valid:
            raise InvalidTemplateVariablesError(
                f"Missing required variables: {', '.join(missing_vars)}"
            )
        
        # Render for each requested channel
        rendered_content = {}
        channels_to_render = channels or self._get_available_channels(template)
        
        for channel in channels_to_render:
            content = await self._render_channel_content(
                template, channel, variables
            )
            if content:
                rendered_content[channel] = content
        
        return rendered_content
    
    async def render_email(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render email content (subject and body)."""
        if not template.has_email_template():
            return {}
        
        try:
            # Render subject
            subject_template = self.jinja_env.from_string(
                template.email_subject or ""
            )
            subject = subject_template.render(variables)
            
            # Render body
            body_template = self.jinja_env.from_string(
                template.email_body or ""
            )
            body = body_template.render(variables)
            
            return {
                "subject": subject,
                "body": body
            }
        
        except (TemplateError, TemplateSyntaxError) as e:
            raise TemplateRenderError(f"Email template error: {e}")
    
    async def render_sms(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> str:
        """Render SMS content."""
        if not template.has_sms_template():
            return ""
        
        try:
            sms_template = self.jinja_env.from_string(
                template.sms_body or ""
            )
            return sms_template.render(variables)
        
        except (TemplateError, TemplateSyntaxError) as e:
            raise TemplateRenderError(f"SMS template error: {e}")
    
    async def render_webhook(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> str:
        """Render webhook payload."""
        if not template.has_webhook_template():
            return ""
        
        try:
            webhook_template = self.jinja_env.from_string(
                template.webhook_payload or ""
            )
            return webhook_template.render(variables)
        
        except (TemplateError, TemplateSyntaxError) as e:
            raise TemplateRenderError(f"Webhook template error: {e}")
    
    async def get_template(
        self,
        tenant_id: str,
        slug: str
    ) -> Template:
        """Get template by tenant and slug."""
        template = await self.template_repo.get_by_tenant_and_slug(
            tenant_id, slug
        )
        
        if not template:
            raise TemplateNotFoundError(f"Template not found: {slug}")
        
        return template
    
    async def list_templates(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Template]:
        """List templates for tenant."""
        return await self.template_repo.get_multi_by_tenant(
            tenant_id, category, skip, limit
        )
    
    async def validate_template_variables(
        self,
        template: Template,
        variables: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Validate variables against template schema."""
        return template.validate_variables(variables)
    
    async def preview_template(
        self,
        template: Template,
        variables: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """Preview template rendering without saving."""
        return await self.render_notification(
            template, variables, channels
        )
    
    def _get_available_channels(self, template: Template) -> List[str]:
        """Get list of channels available in template."""
        channels = []
        
        if template.has_email_template():
            channels.append("email")
        
        if template.has_sms_template():
            channels.append("sms")
        
        if template.has_webhook_template():
            channels.append("webhook")
        
        return channels
    
    async def _render_channel_content(
        self,
        template: Template,
        channel: str,
        variables: Dict[str, Any]
    ) -> Optional[str]:
        """Render content for specific channel."""
        if channel == "email":
            # For email, we return both subject and body
            result = await self.render_email(template, variables)
            if result:
                # Return body as main content, subject in metadata
                return result.get("body", "")
        
        elif channel == "sms":
            return await self.render_sms(template, variables)
        
        elif channel == "webhook":
            return await self.render_webhook(template, variables)
        
        return None
    
    def _validate_jinja_syntax(self, template_content: str) -> bool:
        """Validate Jinja2 syntax of template content."""
        try:
            self.jinja_env.from_string(template_content)
            return True
        except TemplateSyntaxError:
            return False
    
    async def create_template_variables_schema(
        self,
        template_content: str,
        required_vars: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze template content to extract variables and create schema.
        
        This is a simple implementation - in production you might want
        more sophisticated variable extraction.
        """
        import re
        
        # Find all {{ variable }} patterns
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        matches = re.findall(pattern, template_content)
        
        # Extract unique variable names
        variables = set()
        for match in matches:
            var_name = match.strip()
            # Remove filters and complex expressions
            if '|' in var_name:
                var_name = var_name.split('|')[0].strip()
            if '.' in var_name:
                var_name = var_name.split('.')[0].strip()
            variables.add(var_name)
        
        # Create schema
        schema = []
        for var in sorted(variables):
            schema.append({
                "name": var,
                "type": "string",
                "required": var in (required_vars or []),
                "description": f"Variable: {var}"
            })
        
        return schema
    
    def get_template_summary(self, template: Template) -> Dict[str, Any]:
        """Get summary of template capabilities."""
        return {
            "id": str(template.id),
            "name": template.name,
            "slug": template.slug,
            "category": template.category,
            "description": template.description,
            "channels": self._get_available_channels(template),
            "variables": template.variables_schema,
            "required_variables": template.get_required_variables(),
            "is_active": template.is_active,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
