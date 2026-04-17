"""
Webhook channel implementation using httpx.
"""

import json
import re
import time
from typing import Any, Dict, Optional

import httpx

from app.channels.base import BaseChannel, SendResult
from app.core.config import settings
from app.core.exceptions import TransientChannelError, PermanentChannelError
from app.core.security import generate_webhook_signature
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery


class WebhookChannel(BaseChannel):
    """Webhook notification channel using HTTP POST."""
    
    channel_type = "webhook"
    
    def __init__(self, webhook_config: Optional[Dict[str, Any]] = None):
        self.webhook_config = webhook_config or {}
        self.timeout = settings.webhook_default_timeout
        self.signature_algorithm = settings.webhook_signature_algorithm
    
    async def send(self, notification: Notification, delivery: Delivery) -> SendResult:
        """Send webhook notification."""
        try:
            # Prepare webhook payload
            payload = self._create_payload(notification, delivery)
            
            # Prepare headers
            headers = self._create_headers(payload, delivery)
            
            # Send webhook
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    delivery.destination,
                    json=payload,
                    headers=headers,
                )
            
            # Process response
            return self._process_response(response, payload)
        
        except httpx.ConnectTimeout as e:
            raise TransientChannelError(
                f"Webhook connection timeout: {e}",
                "connection_timeout",
            )
        
        except httpx.ConnectError as e:
            raise TransientChannelError(
                f"Webhook connection failed: {e}",
                "connection_refused",
            )
        
        except httpx.TimeoutException as e:
            raise TransientChannelError(
                f"Webhook request timeout: {e}",
                "timeout",
            )
        
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            
            if self._is_retryable_status_code(status_code):
                retry_after = self._extract_retry_after(e.response)
                raise TransientChannelError(
                    f"Webhook HTTP error {status_code}: {e.response.text}",
                    f"http_{status_code}",
                    retry_after=retry_after,
                )
            else:
                raise PermanentChannelError(
                    f"Webhook HTTP error {status_code}: {e.response.text}",
                    f"http_{status_code}",
                )
        
        except httpx.RequestError as e:
            raise TransientChannelError(
                f"Webhook request error: {e}",
                "request_error",
            )
        
        except Exception as e:
            raise TransientChannelError(
                f"Unexpected error: {e}",
                "unknown_error",
            )
    
    async def validate_destination(self, destination: str) -> bool:
        """Validate webhook URL."""
        if not destination:
            return False
        
        # Basic URL validation
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(url_pattern, destination))
    
    def get_max_attempts(self) -> int:
        """Get maximum retry attempts for webhook."""
        return self.webhook_config.get("max_retries", 5)
    
    def get_timeout(self) -> int:
        """Get timeout in seconds for webhook."""
        return self.webhook_config.get("timeout_seconds", self.timeout)
    
    def supports_delivery_receipts(self) -> bool:
        """Check if webhook supports delivery receipts."""
        return False
    
    def _create_payload(self, notification: Notification, delivery: Delivery) -> Dict[str, Any]:
        """Create webhook payload."""
        payload = {
            "id": str(notification.id),
            "delivery_id": str(delivery.id),
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority,
            "status": notification.status,
            "created_at": notification.created_at.isoformat(),
            "notification_metadata": notification.notification_metadata,
            "user": {
                "id": str(notification.user.id),
                "external_id": notification.user.external_id,
                "email": notification.user.email,
                "phone": notification.user.phone,
                "display_name": notification.user.display_name,
            },
            "channels": notification.resolved_channels,
            "primary_channel": notification.primary_channel,
        }
        
        # Add template info if available
        if notification.template:
            payload["template"] = {
                "id": str(notification.template.id),
                "slug": notification.template.slug,
                "category": notification.template.category,
            }
        
        return payload
    
    def _create_headers(self, payload: Dict[str, Any], delivery: Delivery) -> Dict[str, str]:
        """Create HTTP headers for webhook request."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"NotiFlow-Webhook/1.0",
            "X-Notification-ID": str(delivery.notification_id),
            "X-Delivery-ID": str(delivery.id),
        }
        
        # Add custom headers from webhook config
        custom_headers = self.webhook_config.get("headers", {})
        headers.update(custom_headers)
        
        # Add signature if secret is configured
        secret = self.webhook_config.get("secret")
        if secret:
            payload_str = json.dumps(payload, separators=(",", ":"))
            signature = generate_webhook_signature(payload_str, secret)
            headers["X-Signature"] = signature
            headers["X-Timestamp"] = str(int(time.time()))
        
        return headers
    
    def _process_response(self, response: httpx.Response, payload: Dict[str, Any]) -> SendResult:
        """Process webhook response."""
        try:
            response_data = response.json() if response.content else {}
        except json.JSONDecodeError:
            response_data = {"raw_response": response.text}
        
        if 200 <= response.status_code < 300:
            return SendResult(
                success=True,
                provider_id=str(response.headers.get("X-Request-ID", "")),
                raw_response={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_data,
                },
            )
        else:
            return SendResult(
                success=False,
                error=f"HTTP {response.status_code}: {response.text}",
                raw_response={
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "body": response_data,
                },
            )
    
    def _is_retryable_status_code(self, status_code: int) -> bool:
        """Check if HTTP status code is retryable."""
        # 4xx client errors (except 429 rate limit)
        non_retryable_4xx = {400, 401, 403, 404, 405, 406, 408, 410, 413, 414, 415, 422, 429}
        
        # 5xx server errors are retryable
        if 500 <= status_code < 600:
            return True
        
        # 429 Too Many Requests is retryable
        if status_code == 429:
            return True
        
        # Other 4xx errors are not retryable
        return status_code not in non_retryable_4xx
    
    def _extract_retry_after(self, response: httpx.Response) -> Optional[int]:
        """Extract retry-after from HTTP response."""
        # Check Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after)
            except ValueError:
                pass
        
        # Check for rate limit in body
        try:
            data = response.json()
            if "retry_after" in data:
                return int(data["retry_after"])
        except (json.JSONDecodeError, ValueError, KeyError):
            pass
        
        return None
