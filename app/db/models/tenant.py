"""
Tenant model for API key authentication.
"""

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.security import hash_api_key
from app.db.base import Base


class Tenant(Base):
    """Tenant represents an organization using NotiFlow."""
    
    __tablename__ = "tenants"
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    api_key_prefix: Mapped[str] = mapped_column(String(8), nullable=False)  # "nf_live_" prefix for display
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    rate_limit: Mapped[int] = mapped_column(default=1000, nullable=False)  # requests per minute
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="tenant", cascade="all, delete-orphan")
    templates = relationship("Template", back_populates="tenant", cascade="all, delete-orphan")
    webhook_configs = relationship("WebhookConfig", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, active={self.is_active})>"
    
    def set_api_key(self, api_key: str) -> None:
        """Set the API key hash and prefix."""
        self.api_key_hash = hash_api_key(api_key)
        self.api_key_prefix = api_key[:8] if len(api_key) >= 8 else api_key
    
    def verify_api_key(self, api_key: str) -> bool:
        """Verify the provided API key."""
        return hash_api_key(api_key) == self.api_key_hash


# Indexes
__table_args__ = (
    Index("idx_tenants_api_key_prefix", "api_key_prefix"),
    Index("idx_tenants_active", "id", "is_active", postgresql_where="is_active = True"),
)
