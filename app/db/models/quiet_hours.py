"""
Quiet hours model for user notification preferences.
"""

from datetime import time
from sqlalchemy import Index, String, Time, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuietHours(Base):
    """Quiet hours rules for users."""
    
    __tablename__ = "quiet_hours"
    
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(nullable=False)  # 0=Sunday, 1=Monday, ... 6=Saturday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)  # e.g., 22:00
    end_time: Mapped[time] = mapped_column(Time, nullable=False)    # e.g., 08:00
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="quiet_hours")
    
    def __repr__(self) -> str:
        return (
            f"<QuietHours(user_id={self.user_id}, day={self.day_of_week}, "
            f"start={self.start_time}, end={self.end_time})>"
        )
    
    def is_quiet_now(self, current_time: time, current_day: int) -> bool:
        """Check if current time is within quiet hours."""
        if not self.is_active or current_day != self.day_of_week:
            return False
        
        if self.start_time <= self.end_time:
            # Same-day quiet hours (e.g., 14:00-16:00)
            return self.start_time <= current_time < self.end_time
        else:
            # Overnight quiet hours (e.g., 22:00-08:00)
            return current_time >= self.start_time or current_time < self.end_time


# Constraints and indexes
__table_args__ = (
    UniqueConstraint("user_id", "day_of_week", name="uq_quiet_hours_user_day"),
    CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_quiet_hours_day"),
    Index("idx_quiet_hours_user", "user_id"),
)
