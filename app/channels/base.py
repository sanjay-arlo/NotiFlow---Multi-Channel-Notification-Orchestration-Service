"""
Base channel interface for notification providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.db.models.notification import Notification
from app.db.models.delivery import Delivery


@dataclass
class SendResult:
    """Result of sending a notification."""
    success: bool
    provider_id: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry


class BaseChannel(ABC):
    """Abstract base class for notification channels."""
    
    channel_type: str  # "email", "sms", "webhook"
    
    @abstractmethod
    async def send(self, notification: Notification, delivery: Delivery) -> SendResult:
        """
        Send notification via this channel.
        
        Args:
            notification: The notification to send
            delivery: The delivery record with destination and metadata
            
        Returns:
            SendResult with success status and provider details
            
        Raises:
            TransientChannelError: For retryable errors
            PermanentChannelError: For non-retryable errors
        """
        pass
    
    @abstractmethod
    async def validate_destination(self, destination: str) -> bool:
        """
        Validate if destination is appropriate for this channel.
        
        Args:
            destination: Email address, phone number, or webhook URL
            
        Returns:
            True if destination is valid for this channel
        """
        pass
    
    @abstractmethod
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts for this channel."""
        pass
    
    def get_timeout(self) -> int:
        """Get timeout in seconds for this channel."""
        return 30
    
    def supports_delivery_receipts(self) -> bool:
        """Check if channel supports delivery receipts."""
        return False
    
    def get_rate_limit_window(self) -> int:
        """Get rate limit window in seconds."""
        return 60
    
    def get_rate_limit_count(self) -> int:
        """Get rate limit count per window."""
        return 100
