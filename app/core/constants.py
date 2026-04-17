"""
Constants and enums for NotiFlow.
"""

from enum import Enum
from typing import List


class ChannelType(str, Enum):
    """Notification channel types."""
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationPriority(str, Enum):
    """Notification priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class NotificationStatus(str, Enum):
    """Notification status values."""
    QUEUED = "queued"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class DeliveryStatus(str, Enum):
    """Delivery status values."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    CANCELLED = "cancelled"


class TemplateCategory(str, Enum):
    """Template categories."""
    TRANSACTIONAL = "transactional"
    MARKETING = "marketing"
    ALERT = "alert"
    SYSTEM = "system"


class EventType(str, Enum):
    """Delivery event types."""
    STATUS_CHANGE = "status_change"
    RETRY_SCHEDULED = "retry_scheduled"
    BOUNCE = "bounce"
    DELIVERY_RECEIPT = "delivery_receipt"


# Valid values
VALID_CHANNELS: List[str] = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]
VALID_PRIORITIES: List[str] = [
    NotificationPriority.CRITICAL,
    NotificationPriority.HIGH,
    NotificationPriority.NORMAL,
    NotificationPriority.LOW,
]
VALID_NOTIFICATION_STATUSES: List[str] = [
    NotificationStatus.QUEUED,
    NotificationStatus.PROCESSING,
    NotificationStatus.SENT,
    NotificationStatus.DELIVERED,
    NotificationStatus.FAILED,
    NotificationStatus.PARTIAL,
    NotificationStatus.CANCELLED,
]
VALID_DELIVERY_STATUSES: List[str] = [
    DeliveryStatus.PENDING,
    DeliveryStatus.PROCESSING,
    DeliveryStatus.SENT,
    DeliveryStatus.DELIVERED,
    DeliveryStatus.FAILED,
    DeliveryStatus.BOUNCED,
    DeliveryStatus.CANCELLED,
]
VALID_TEMPLATE_CATEGORIES: List[str] = [
    TemplateCategory.TRANSACTIONAL,
    TemplateCategory.MARKETING,
    TemplateCategory.ALERT,
    TemplateCategory.SYSTEM,
]

# Channel retry configurations
CHANNEL_RETRY_CONFIG = {
    ChannelType.EMAIL: {
        "max_attempts": 4,
        "base_delay_seconds": 60,
        "multiplier": 2,
        "max_delay_seconds": 3600,
        "jitter_factor": 0.1,
        "retryable_errors": [
            "connection_timeout",
            "connection_refused",
            "temporarily_unavailable",
            "rate_limited",
            "mailbox_full",
        ],
    },
    ChannelType.SMS: {
        "max_attempts": 3,
        "base_delay_seconds": 30,
        "multiplier": 2,
        "max_delay_seconds": 600,
        "jitter_factor": 0.1,
        "retryable_errors": [
            "connection_timeout",
            "rate_limited",
            "temporarily_unavailable",
            "invalid_phone_format_soft",
        ],
    },
    ChannelType.WEBHOOK: {
        "max_attempts": 5,
        "base_delay_seconds": 10,
        "multiplier": 2,
        "max_delay_seconds": 300,
        "jitter_factor": 0.2,
        "retryable_errors": [
            "connection_timeout",
            "connection_refused",
            "5xx",
            "rate_limited",
        ],
        "non_retryable_status_codes": [400, 401, 403, 404, 410, 422],
    },
}

# Priority queue routing
PRIORITY_QUEUE_ROUTING = {
    (NotificationPriority.CRITICAL, "*"): "critical",
    (NotificationPriority.HIGH, ChannelType.EMAIL): "high",
    (NotificationPriority.HIGH, ChannelType.SMS): "high",
    (NotificationPriority.HIGH, ChannelType.WEBHOOK): "high",
    (NotificationPriority.NORMAL, ChannelType.EMAIL): "email",
    (NotificationPriority.NORMAL, ChannelType.SMS): "sms",
    (NotificationPriority.NORMAL, ChannelType.WEBHOOK): "webhook",
    (NotificationPriority.LOW, "*"): "default",
}

# Status priority for aggregation (higher number = higher priority)
STATUS_PRIORITY = {
    DeliveryStatus.PROCESSING: 5,
    DeliveryStatus.PENDING: 4,
    DeliveryStatus.SENT: 3,
    DeliveryStatus.BOUNCED: 2,
    DeliveryStatus.FAILED: 2,
    DeliveryStatus.DELIVERED: 1,
    DeliveryStatus.CANCELLED: 0,
}

# API key prefix
API_KEY_PREFIX = "nf_live_"

# Default values
DEFAULT_TIMEZONE = "UTC"
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Redis TTL values (seconds)
REDIS_PREFS_TTL = 300  # 5 minutes
REDIS_QUIET_HOURS_TTL = 300  # 5 minutes
REDIS_RATE_LIMIT_TTL = 60  # 1 minute
REDIS_NOTIFICATION_STATUS_TTL = 3600  # 1 hour
REDIS_CHANNEL_RATE_LIMIT_TTL = 3600  # 1 hour

# Celery queue configurations
CELERY_QUEUES = [
    "critical",
    "high",
    "email",
    "sms",
    "webhook",
    "default",
]

# Webhook signature
WEBHOOK_SIGNATURE_HEADER = "X-Signature"
WEBHOOK_TIMESTAMP_HEADER = "X-Timestamp"
WEBHOOK_TOLERANCE_SECONDS = 300  # 5 minutes

# Content limits
MAX_TITLE_LENGTH = 500
MAX_BODY_LENGTH = 10000
MAX_EMAIL_SUBJECT_LENGTH = 500
MAX_SMS_BODY_LENGTH = 1600
MAX_WEBHOOK_PAYLOAD_SIZE = 1024 * 1024  # 1MB

# Time formats
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
