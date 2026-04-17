"""
User model for notification recipients.
"""

from sqlalchemy import Index, String, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """User represents a notification recipient."""
    
    __tablename__ = "users"
    
    # Tenant and external identifier
    tenant_id: Mapped[str] = mapped_column(nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Contact information
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)  # E.164 format
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Additional metadata
    user_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    channel_preferences = relationship("UserChannelPreference", back_populates="user", cascade="all, delete-orphan")
    quiet_hours = relationship("QuietHours", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, external_id={self.external_id}, email={self.email})>"
    
    def has_email(self) -> bool:
        """Check if user has a valid email address."""
        return bool(self.email and "@" in self.email)
    
    def has_phone(self) -> bool:
        """Check if user has a valid phone number."""
        return bool(self.phone and self.phone.startswith("+"))
    
    def get_display_name(self) -> str:
        """Get the best display name for the user."""
        return self.display_name or self.email or self.external_id


# Constraints and indexes
__table_args__ = (
    UniqueConstraint("tenant_id", "external_id", name="uq_users_tenant_external"),
    Index("idx_users_tenant_external", "tenant_id", "external_id"),
    Index("idx_users_email", "email", postgresql_where="email IS NOT NULL"),
    Index("idx_users_phone", "phone", postgresql_where="phone IS NOT NULL"),
)
