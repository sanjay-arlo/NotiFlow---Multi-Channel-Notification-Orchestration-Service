"""
Custom exceptions for NotiFlow.
"""

from typing import Optional


class NotiFlowError(Exception):
    """Base exception for NotiFlow."""
    
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


class UserNotFoundError(NotiFlowError):
    """Raised when a user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(f"User not found: {user_id}", "USER_NOT_FOUND")


class TenantNotFoundError(NotiFlowError):
    """Raised when a tenant is not found."""
    
    def __init__(self, tenant_id: str):
        super().__init__(f"Tenant not found: {tenant_id}", "TENANT_NOT_FOUND")


class NoChannelsAvailableError(NotiFlowError):
    """Raised when no enabled channels are available for a user."""
    
    def __init__(self, user_id: str):
        super().__init__(
            f"No enabled notification channels for user: {user_id}",
            "NO_CHANNELS_AVAILABLE"
        )


class TemplateNotFoundError(NotiFlowError):
    """Raised when a template is not found."""
    
    def __init__(self, slug: str):
        super().__init__(f"Template not found: {slug}", "TEMPLATE_NOT_FOUND")


class TemplateRenderError(NotiFlowError):
    """Raised when template rendering fails."""
    
    def __init__(self, message: str):
        super().__init__(f"Template render error: {message}", "TEMPLATE_RENDER_ERROR")


class InvalidTemplateVariablesError(NotiFlowError):
    """Raised when template variables are invalid."""
    
    def __init__(self, message: str):
        super().__init__(f"Invalid template variables: {message}", "INVALID_TEMPLATE_VARIABLES")


class NotificationNotFoundError(NotiFlowError):
    """Raised when a notification is not found."""
    
    def __init__(self, notification_id: str):
        super().__init__(f"Notification not found: {notification_id}", "NOTIFICATION_NOT_FOUND")


class DeliveryNotFoundError(NotiFlowError):
    """Raised when a delivery is not found."""
    
    def __init__(self, delivery_id: str):
        super().__init__(f"Delivery not found: {delivery_id}", "DELIVERY_NOT_FOUND")


class WebhookConfigNotFoundError(NotiFlowError):
    """Raised when a webhook config is not found."""
    
    def __init__(self, webhook_id: str):
        super().__init__(f"Webhook config not found: {webhook_id}", "WEBHOOK_CONFIG_NOT_FOUND")


class RateLimitExceededError(NotiFlowError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, limit: int, window: int):
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window} seconds",
            "RATE_LIMIT_EXCEEDED"
        )


class QuietHoursActiveError(NotiFlowError):
    """Raised when quiet hours are active and notification is not critical."""
    
    def __init__(self, resume_at: Optional[str] = None):
        message = "Quiet hours are active"
        if resume_at:
            message += f", will resume at {resume_at}"
        super().__init__(message, "QUIET_HOURS_ACTIVE")


class ChannelNotEnabledError(NotiFlowError):
    """Raised when a requested channel is not enabled for a user."""
    
    def __init__(self, channel: str, user_id: str):
        super().__init__(
            f"Channel '{channel}' is not enabled for user {user_id}",
            "CHANNEL_NOT_ENABLED"
        )


class InvalidChannelError(NotiFlowError):
    """Raised when an invalid channel is specified."""
    
    def __init__(self, channel: str):
        super().__init__(f"Invalid channel: {channel}", "INVALID_CHANNEL")


class InvalidPriorityError(NotiFlowError):
    """Raised when an invalid priority is specified."""
    
    def __init__(self, priority: str):
        super().__init__(f"Invalid priority: {priority}", "INVALID_PRIORITY")


class InvalidStatusError(NotiFlowError):
    """Raised when an invalid status is specified."""
    
    def __init__(self, status: str):
        super().__init__(f"Invalid status: {status}", "INVALID_STATUS")


# Channel-specific errors
class TransientChannelError(Exception):
    """Retryable channel error."""
    
    def __init__(self, message: str, error_code: str, retry_after: Optional[int] = None):
        self.error_code = error_code
        self.retry_after = retry_after
        super().__init__(message)


class PermanentChannelError(Exception):
    """Non-retryable channel error."""
    
    def __init__(self, message: str, error_code: str):
        self.error_code = error_code
        super().__init__(message)


class EmailChannelError(PermanentChannelError):
    """Email channel specific error."""
    pass


class SMSChannelError(PermanentChannelError):
    """SMS channel specific error."""
    pass


class WebhookChannelError(PermanentChannelError):
    """Webhook channel specific error."""
    pass
