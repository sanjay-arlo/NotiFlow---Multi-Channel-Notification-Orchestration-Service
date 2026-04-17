"""
Notification model for main notification records.
"""

from datetime import datetime
from sqlalchemy import (
    Index, String, Text, JSON, ARRAY, DateTime, 
    CheckConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Notification(Base):
    """Main notification record."""
    
    __tablename__ = "notifications"
    
    # Foreign keys
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[str | None] = mapped_column(ForeignKey("templates.id"), nullable=True)
    
    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Routing
    requested_channels: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    resolved_channels: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    primary_channel: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Priority & Scheduling
    priority: Mapped[str] = mapped_column(String(10), default="normal", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    
    # Quiet hours
    suppressed_by_quiet_hours: Mapped[bool] = mapped_column(default=False, nullable=False)
    bypass_quiet_hours: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Tracking
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="notifications")
    user = relationship("User", back_populates="notifications")
    template = relationship("Template", back_populates="notifications")
    deliveries = relationship("Delivery", back_populates="notification", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return (
            f"<Notification(id={self.id}, status={self.status}, "
            f"priority={self.priority}, channels={self.resolved_channels})>"
        )
    
    def is_critical(self) -> bool:
        """Check if notification is critical priority."""
        return self.priority == "critical"
    
    def is_scheduled(self) -> bool:
        """Check if notification is scheduled for future delivery."""
        return self.scheduled_at is not None and self.scheduled_at > datetime.utcnow()
    
    def should_bypass_quiet_hours(self) -> bool:
        """Check if notification should bypass quiet hours."""
        return self.bypass_quiet_hours or self.is_critical()


# Constraints and indexes
__table_args__ = (
    CheckConstraint("priority IN ('critical', 'high', 'normal', 'low')", name="ck_notifications_priority"),
    CheckConstraint(
        "status IN ('queued', 'processing', 'sent', 'delivered', 'failed', 'partial', 'cancelled')",
        name="ck_notifications_status"
    ),
    Index("idx_notifs_tenant", "tenant_id"),
    Index("idx_notifs_user", "user_id"),
    Index("idx_notifs_status", "status"),
    Index("idx_notifs_created", "created_at"),
    Index("idx_notifs_scheduled", "scheduled_at", postgresql_where="scheduled_at IS NOT NULL"),
    Index(
        "idx_notifs_priority_status", 
        "priority", "status", 
        postgresql_where="status IN ('queued', 'processing')"
    ),
)
