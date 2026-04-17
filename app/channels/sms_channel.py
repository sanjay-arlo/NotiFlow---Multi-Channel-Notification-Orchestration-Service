"""
SMS channel implementation using Twilio.
"""

import re
from typing import Any, Dict, Optional

import httpx
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioClient

from app.channels.base import BaseChannel, SendResult
from app.core.config import settings
from app.core.exceptions import TransientChannelError, PermanentChannelError
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery


class SMSChannel(BaseChannel):
    """SMS notification channel using Twilio."""
    
    channel_type = "sms"
    
    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_from_number
        self.timeout = settings.twilio_timeout
        
        # Initialize Twilio client
        self._client: Optional[TwilioClient] = None
    
    @property
    def client(self) -> TwilioClient:
        """Get Twilio client, initializing if necessary."""
        if self._client is None:
            if not self.account_sid or not self.auth_token:
                raise PermanentChannelError(
                    "Twilio credentials not configured",
                    "missing_credentials"
                )
            self._client = TwilioClient(self.account_sid, self.auth_token)
        return self._client
    
    async def send(self, notification: Notification, delivery: Delivery) -> SendResult:
        """Send SMS notification."""
        try:
            # Use synchronous Twilio client in async context
            message = self.client.messages.create(
                body=notification.body,
                from_=self.from_number,
                to=delivery.destination,
            )
            
            return SendResult(
                success=True,
                provider_id=message.sid,
                raw_response={
                    "sid": message.sid,
                    "status": message.status,
                    "direction": message.direction,
                },
            )
        
        except TwilioRestException as e:
            error_code = str(e.code) if e.code else "unknown"
            error_message = str(e.msg) if e.msg else "Unknown Twilio error"
            
            if self._is_retryable_twilio_error(error_code):
                retry_after = self._extract_retry_after(e)
                raise TransientChannelError(
                    f"Twilio temporary error: {error_message}",
                    f"twilio_{error_code}",
                    retry_after=retry_after,
                )
            else:
                raise PermanentChannelError(
                    f"Twilio permanent error: {error_message}",
                    f"twilio_{error_code}",
                )
        
        except Exception as e:
            raise TransientChannelError(
                f"Unexpected error: {e}",
                "unknown_error",
            )
    
    async def validate_destination(self, destination: str) -> bool:
        """Validate phone number in E.164 format."""
        if not destination:
            return False
        
        # Basic E.164 format validation
        e164_pattern = r'^\+[1-9]\d{1,14}$'
        return bool(re.match(e164_pattern, destination))
    
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts for SMS."""
        return 3
    
    def get_timeout(self) -> int:
        """Get timeout in seconds for SMS."""
        return self.timeout
    
    def supports_delivery_receipts(self) -> bool:
        """Check if SMS supports delivery receipts."""
        return True
    
    def get_rate_limit_window(self) -> int:
        """Get rate limit window in seconds for SMS."""
        return 60
    
    def get_rate_limit_count(self) -> int:
        """Get rate limit count per window for SMS."""
        return 10  # Twilio typical rate limit
    
    def _is_retryable_twilio_error(self, error_code: str) -> bool:
        """Check if Twilio error code is retryable."""
        retryable_codes = {
            "21614",  # 'To' number is not a valid mobile number
            "21612",  # The 'To' phone number is not currently reachable
            "21610",  # Attempt to send to unsubscribed recipient
            "30001",  # Queue overflow
            "30002",  # Account suspended
            "30003",  # Unreachable destination handset
            "30004",  # Message blocked
            "30005",  # Unknown destination handset
            "30006",  # Landline or unreachable carrier
            "30007",  # Carrier violation
            "30008",  # Unknown error
        }
        
        # Check for rate limiting
        if error_code in ["21629", "21630"]:  # Message rate limit exceeded
            return True
        
        # Check for temporary carrier issues
        if error_code.startswith("3") and error_code not in ["30007"]:
            return True
        
        return error_code in retryable_codes
    
    def _extract_retry_after(self, exception: TwilioRestException) -> Optional[int]:
        """Extract retry-after from Twilio exception."""
        # Twilio may include retry-after in URI or headers
        if hasattr(exception, 'uri') and 'retry-after' in str(exception.uri):
            try:
                # Extract retry-after from URI
                import re
                match = re.search(r'retry-after=(\d+)', str(exception.uri))
                if match:
                    return int(match.group(1))
            except (ValueError, AttributeError):
                pass
        
        # Default retry after for rate limiting
        return 60
