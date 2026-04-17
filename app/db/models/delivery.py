"""
Delivery model for per-channel delivery attempts.
"""

from datetime import datetime
from sqlalchemy import (
    Index, String, Text, JSON, DateTime, 
    CheckConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Delivery(Base):
    """Per-channel delivery attempt record."""
    
    __tablename__ = "deliveries"
    
    # Foreign key
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Delivery details
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    destination: Mapped[str] = mapped_column(String(500), nullable=False)  # email, phone, URL
    
    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    
    # Provider response
    provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)  # SendGrid msg ID, Twilio SID
    provider_code: Mapped[str | None] = mapped_column(String(50), nullable=True)  # provider-specific status
    provider_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # full provider response
    
    # Retry tracking
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(default=3, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Timing
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    bounce_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relationships
    notification = relationship("Notification", back_populates="deliveries")
    events = relationship("DeliveryEvent", back_populates="delivery", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return (
            f"<Delivery(id={self.id}, channel={self.channel}, "
            f"status={self.status}, attempts={self.attempt_count})>"
        )
    
    def is_retryable(self) -> bool:
        """Check if delivery can be retried."""
        return (
            self.status in ("failed",) and 
            self.attempt_count < self.max_attempts and
            self.next_retry_at is not None
        )
    
    def should_retry(self) -> bool:
        """Check if delivery should be retried now."""
        return (
            self.is_retryable() and 
            self.next_retry_at is not None and 
            self.next_retry_at <= datetime.utcnow()
        )
    
    def is_completed(self) -> bool:
        """Check if delivery is completed (delivered, failed, bounced, or cancelled)."""
        return self.status in ("delivered", "failed", "bounced", "cancelled")
    
    def is_pending(self) -> bool:
        """Check if delivery is pending processing."""
        return self.status == "pending"
    
    def is_processing(self) -> bool:
        """Check if delivery is currently being processed."""
        return self.status == "processing"
    
    def mark_as_processing(self) -> None:
        """Mark delivery as being processed."""
        self.status = "processing"
        self.last_attempt_at = datetime.utcnow()
    
    def mark_as_sent(self, provider_id: str, provider_response: dict | None = None) -> None:
        """Mark delivery as sent."""
        self.status = "sent"
        self.provider_id = provider_id
        self.provider_response = provider_response
        self.sent_at = datetime.utcnow()
        self.attempt_count += 1
        self.last_attempt_at = datetime.utcnow()
    
    def mark_as_delivered(self) -> None:
        """Mark delivery as delivered."""
        self.status = "delivered"
        self.delivered_at = datetime.utcnow()
    
    def mark_as_failed(self, error: str, next_retry_at: datetime | None = None) -> None:
        """Mark delivery as failed."""
        self.status = "failed"
        self.last_error = error
        self.attempt_count += 1
        self.last_attempt_at = datetime.utcnow()
        
        if self.attempt_count >= self.max_attempts:
            self.failed_at = datetime.utcnow()
            self.next_retry_at = None
        else:
            self.next_retry_at = next_retry_at
    
    def mark_as_bounced(self, reason: str) -> None:
        """Mark delivery as bounced."""
        self.status = "bounced"
        self.bounced_at = datetime.utcnow()
        self.bounce_reason = reason
        self.next_retry_at = None


# Constraints and indexes
__table_args__ = (
    CheckConstraint("channel IN ('email', 'sms', 'webhook')", name="ck_deliveries_channel"),
    CheckConstraint(
        "status IN ('pending', 'processing', 'sent', 'delivered', 'failed', 'bounced', 'cancelled')",
        name="ck_deliveries_status"
    ),
    Index("idx_deliveries_notif", "notification_id"),
    Index("idx_deliveries_status", "status"),
    Index(
        "idx_deliveries_retry", 
        "status", "next_retry_at", 
        postgresql_where="status = 'failed' AND next_retry_at IS NOT NULL"
    ),
    Index("idx_deliveries_provider_id", "provider_id", postgresql_where="provider_id IS NOT NULL"),
)
