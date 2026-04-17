"""
Webhook configuration model for outgoing webhooks.
"""

from datetime import datetime
from sqlalchemy import Index, String, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class WebhookConfig(Base):
    """Outgoing webhook endpoint configurations."""
    
    __tablename__ = "webhook_configs"
    
    # Foreign key
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # Configuration
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    
    # Authentication
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)  # HMAC signing secret
    headers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # custom headers to send
    
    # Retry configuration
    max_retries: Mapped[int] = mapped_column(default=3, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(default=10, nullable=False)
    
    # Status tracking
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_success_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failure_count: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="webhook_configs")
    
    def __repr__(self) -> str:
        return f"<WebhookConfig(id={self.id}, name={self.name}, url={self.url})>"
    
    def has_secret(self) -> bool:
        """Check if webhook has a signing secret."""
        return bool(self.secret)
    
    def is_healthy(self) -> bool:
        """Check if webhook appears healthy based on recent failures."""
        # Consider unhealthy if more than 5 consecutive failures
        return self.failure_count < 5
    
    def record_success(self) -> None:
        """Record a successful webhook delivery."""
        self.last_success_at = datetime.utcnow()
        self.failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed webhook delivery."""
        self.last_failure_at = datetime.utcnow()
        self.failure_count += 1


# Indexes
__table_args__ = (
    Index("idx_webhook_tenant", "tenant_id"),
    Index("idx_webhook_active", "tenant_id", "is_active", postgresql_where="is_active = TRUE"),
)
