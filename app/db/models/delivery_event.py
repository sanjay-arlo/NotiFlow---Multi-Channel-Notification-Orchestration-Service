"""
Delivery event model for audit trail of status changes.
"""

from sqlalchemy import Index, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DeliveryEvent(Base):
    """Audit trail of delivery status changes."""
    
    __tablename__ = "delivery_events"
    
    # Foreign keys
    delivery_id: Mapped[str] = mapped_column(
        ForeignKey("deliveries.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Event details
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Relationships
    delivery = relationship("Delivery", back_populates="events")
    notification = relationship("Notification")
    
    def __repr__(self) -> str:
        return (
            f"<DeliveryEvent(delivery_id={self.delivery_id}, "
            f"event_type={self.event_type}, to_status={self.to_status})>"
        )


# Indexes
__table_args__ = (
    Index("idx_events_delivery", "delivery_id"),
    Index("idx_events_notification", "notification_id"),
    Index("idx_events_created", "created_at"),
)
