"""
Email channel implementation using aiosmtplib.
"""

import re
from typing import Any, Dict, Optional

import aiosmtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.channels.base import BaseChannel, SendResult
from app.core.config import settings
from app.core.exceptions import TransientChannelError, PermanentChannelError
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery


class EmailChannel(BaseChannel):
    """Email notification channel using SMTP."""
    
    channel_type = "email"
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from_email = settings.smtp_from_email
        self.smtp_from_name = settings.smtp_from_name
        self.smtp_use_tls = settings.smtp_use_tls
        self.smtp_timeout = settings.smtp_timeout
    
    async def send(self, notification: Notification, delivery: Delivery) -> SendResult:
        """Send email notification."""
        try:
            # Create email message
            message = self._create_email_message(notification, delivery)
            
            # Connect to SMTP server and send
            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                timeout=self.smtp_timeout,
            )
            
            try:
                if self.smtp_use_tls:
                    await smtp.starttls()
                
                if self.smtp_user and self.smtp_password:
                    await smtp.login(self.smtp_user, self.smtp_password)
                
                response = await smtp.send_message(message)
                
                # Parse response for provider ID
                provider_id = self._extract_provider_id(response)
                
                return SendResult(
                    success=True,
                    provider_id=provider_id,
                    raw_response={"response": str(response)},
                )
            
            finally:
                await smtp.quit()
        
        except aiosmtplib.SMTPConnectError as e:
            raise TransientChannelError(
                f"SMTP connection failed: {e}",
                "connection_timeout",
            )
        
        except aiosmtplib.SMTPServerDisconnected as e:
            raise TransientChannelError(
                f"SMTP server disconnected: {e}",
                "connection_refused",
            )
        
        except aiosmtplib.SMTPResponseException as e:
            if self._is_retryable_smtp_error(e.smtp_code):
                raise TransientChannelError(
                    f"SMTP temporary error: {e.smtp_error.decode()}",
                    f"smtp_{e.smtp_code}",
                )
            else:
                raise PermanentChannelError(
                    f"SMTP permanent error: {e.smtp_error.decode()}",
                    f"smtp_{e.smtp_code}",
                )
        
        except aiosmtplib.SMTPException as e:
            raise TransientChannelError(
                f"SMTP error: {e}",
                "smtp_error",
            )
        
        except Exception as e:
            raise TransientChannelError(
                f"Unexpected error: {e}",
                "unknown_error",
            )
    
    async def validate_destination(self, destination: str) -> bool:
        """Validate email address format."""
        if not destination or "@" not in destination:
            return False
        
        # Basic email regex
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, destination))
    
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts for email."""
        return 4
    
    def get_timeout(self) -> int:
        """Get timeout in seconds for email."""
        return self.smtp_timeout
    
    def supports_delivery_receipts(self) -> bool:
        """Check if email supports delivery receipts."""
        return True
    
    def _create_email_message(self, notification: Notification, delivery: Delivery) -> EmailMessage:
        """Create email message from notification."""
        # Determine content type
        if self._is_html_content(notification.body):
            message = MIMEMultipart("alternative")
            message.attach(MIMEText(notification.body, "plain", "utf-8"))
            message.attach(MIMEText(notification.body, "html", "utf-8"))
        else:
            message = EmailMessage()
            message.set_content(notification.body)
        
        # Set headers
        message["Subject"] = notification.title
        message["From"] = f"{self.smtp_from_name} <{self.smtp_from_email}>"
        message["To"] = delivery.destination
        message["X-Notification-ID"] = str(notification.id)
        message["X-Delivery-ID"] = str(delivery.id)
        
        return message
    
    def _is_html_content(self, content: str) -> bool:
        """Check if content contains HTML."""
        html_tags = ["<html>", "<div>", "<p>", "<br>", "<a href="]
        return any(tag in content.lower() for tag in html_tags)
    
    def _extract_provider_id(self, response: Any) -> Optional[str]:
        """Extract provider ID from SMTP response."""
        # SMTP servers typically return a message ID
        if hasattr(response, "message_id"):
            return response.message_id
        elif isinstance(response, str):
            # Try to extract message ID from response string
            import re
            match = re.search(r"Message-ID: <([^>]+)>", response, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _is_retryable_smtp_error(self, smtp_code: int) -> bool:
        """Check if SMTP error code is retryable."""
        retryable_codes = {
            421,  # Service not available
            450,  # Requested mail action not taken: mailbox unavailable
            451,  # Requested action aborted: error in processing
            452,  # Requested action not taken: insufficient system storage
            454,  # Temporary authentication failure
        }
        return smtp_code in retryable_codes
