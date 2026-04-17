"""
User channel preferences model.
"""

from sqlalchemy import Index, String, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserChannelPreference(Base):
    """User channel preferences for notification delivery."""
    
    __tablename__ = "user_channel_preferences"
    
    user_id: Mapped[str] = mapped_column(nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="channel_preferences")
    
    def __repr__(self) -> str:
        return f"<UserChannelPreference(user_id={self.user_id}, channel={self.channel}, enabled={self.is_enabled})>"


# Constraints and indexes
__table_args__ = (
    UniqueConstraint("user_id", "channel", name="uq_user_prefs_user_channel"),
    CheckConstraint("channel IN ('email', 'sms', 'webhook')", name="ck_user_prefs_channel"),
    Index("idx_prefs_user", "user_id"),
)
