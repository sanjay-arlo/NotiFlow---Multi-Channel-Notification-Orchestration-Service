"""
Template model for notification templates.
"""

from sqlalchemy import Index, String, Text, JSON, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Template(Base):
    """Notification templates with Jinja2 rendering."""
    
    __tablename__ = "templates"
    
    # Foreign key
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Template identification
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Per-channel templates (Jinja2)
    email_subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email_body: Mapped[str | None] = mapped_column(Text, nullable=True)  # HTML template
    sms_body: Mapped[str | None] = mapped_column(Text, nullable=True)  # plain text, {{variables}} supported
    webhook_payload: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON template
    
    # Variables schema
    variables_schema: Mapped[dict] = mapped_column(JSON, default=list, nullable=False)  # [{"name": "amount", "type": "string", "required": true}]
    
    # Metadata
    category: Mapped[str] = mapped_column(String(50), default="transactional", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="templates")
    notifications = relationship("Notification", back_populates="template")
    
    def __repr__(self) -> str:
        return f"<Template(id={self.id}, slug={self.slug}, category={self.category})>"
    
    def has_email_template(self) -> bool:
        """Check if template has email content."""
        return bool(self.email_subject and self.email_body)
    
    def has_sms_template(self) -> bool:
        """Check if template has SMS content."""
        return bool(self.sms_body)
    
    def has_webhook_template(self) -> bool:
        """Check if template has webhook content."""
        return bool(self.webhook_payload)
    
    def get_required_variables(self) -> list[str]:
        """Get list of required variables from schema."""
        return [
            var["name"] for var in self.variables_schema 
            if var.get("required", False)
        ]
    
    def validate_variables(self, variables: dict) -> tuple[bool, list[str]]:
        """Validate provided variables against schema."""
        missing = []
        for var_def in self.variables_schema:
            var_name = var_def["name"]
            if var_def.get("required", False) and var_name not in variables:
                missing.append(var_name)
        
        return len(missing) == 0, missing


# Constraints and indexes
__table_args__ = (
    UniqueConstraint("tenant_id", "slug", name="uq_templates_tenant_slug"),
    CheckConstraint(
        "category IN ('transactional', 'marketing', 'alert', 'system')",
        name="ck_templates_category"
    ),
    Index("idx_templates_tenant_slug", "tenant_id", "slug"),
)
