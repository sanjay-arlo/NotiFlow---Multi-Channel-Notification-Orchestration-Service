"""
Factory-boy factories for testing NotiFlow components.
"""

import factory
from datetime import datetime, timedelta
from uuid import uuid4

from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.db.models.template import Template
from app.db.models.webhook_config import WebhookConfig
from app.core.constants import NotificationPriority, DeliveryStatus, ChannelType, TemplateCategory


class TenantFactory(factory.Factory):
    """Factory for creating Tenant instances."""
    
    class Meta:
        model = Tenant
    
    name = factory.Faker('company')
    api_key_hash = factory.Faker('sha256')
    api_key_prefix = "nf_live_"
    is_active = True
    rate_limit = 1000
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class UserFactory(factory.Factory):
    """Factory for creating User instances."""
    
    class Meta:
        model = User
    
    tenant_id = factory.LazyFunction(lambda: str(uuid4()))
    external_id = factory.Faker('uuid4')
    email = factory.Faker('email')
    phone = factory.Faker('phone_number')
    timezone = "UTC"
    display_name = factory.Faker('name')
    metadata = factory.LazyFunction(lambda: {"department": "Engineering"})
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class NotificationFactory(factory.Factory):
    """Factory for creating Notification instances."""
    
    class Meta:
        model = Notification
    
    tenant_id = factory.LazyFunction(lambda: str(uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid4()))
    title = factory.Faker('sentence', nb_words=4)
    body = factory.Faker('paragraph', nb_sentences=2)
    priority = NotificationPriority.NORMAL
    metadata = factory.LazyFunction(lambda: {"source": "test"})
    resolved_channels = [ChannelType.EMAIL]
    status = "queued"
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class DeliveryFactory(factory.Factory):
    """Factory for creating Delivery instances."""
    
    class Meta:
        model = Delivery
    
    notification_id = factory.LazyFunction(lambda: str(uuid4()))
    channel = ChannelType.EMAIL
    destination = factory.Faker('email')
    status = DeliveryStatus.PENDING
    attempt_count = 0
    max_attempts = 3
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class TemplateFactory(factory.Factory):
    """Factory for creating Template instances."""
    
    class Meta:
        model = Template
    
    tenant_id = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.Faker('sentence', nb_words=3)
    slug = factory.Faker('slug')
    email_subject = "Test: {{ subject }}"
    email_body = "<h1>{{ title }}</h1><p>{{ content }}</p>"
    sms_body = "{{ title }}: {{ content }}"
    webhook_payload = '{"event": "{{ event_type }}", "data": {{ data | tojson }}}'
    variables_schema = [
        {"name": "title", "type": "string", "required": True},
        {"name": "content", "type": "string", "required": True}
    ]
    category = TemplateCategory.TRANSACTIONAL
    description = factory.Faker('sentence')
    is_active = True
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class WebhookConfigFactory(factory.Factory):
    """Factory for creating WebhookConfig instances."""
    
    class Meta:
        model = WebhookConfig
    
    tenant_id = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.Faker('sentence', nb_words=3)
    url = factory.Faker('url')
    secret = factory.Faker('password', length=32)
    headers = {"Content-Type": "application/json"}
    max_retries = 3
    timeout_seconds = 10
    is_active = True
    failure_count = 0
    created_at = factory.LazyFunction(datetime.utcnow)
    updated_at = factory.LazyFunction(datetime.utcnow)


class CriticalNotificationFactory(NotificationFactory):
    """Factory for creating critical priority notifications."""
    
    priority = NotificationPriority.CRITICAL
    resolved_channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]


class FailedDeliveryFactory(DeliveryFactory):
    """Factory for creating failed deliveries."""
    
    status = DeliveryStatus.FAILED
    attempt_count = 3
    max_attempts = 3
    error_message = "Delivery failed after maximum retries"
    error_code = "MAX_RETRIES_EXCEEDED"
    failed_at = factory.LazyFunction(datetime.utcnow)


class DeliveredDeliveryFactory(DeliveryFactory):
    """Factory for creating successful deliveries."""
    
    status = DeliveryStatus.DELIVERED
    attempt_count = 1
    provider_id = factory.Faker('uuid4')
    sent_at = factory.LazyFunction(datetime.utcnow)
    delivered_at = factory.LazyFunction(datetime.utcnow)


class ScheduledNotificationFactory(NotificationFactory):
    """Factory for creating scheduled notifications."""
    
    scheduled_at = factory.LazyFunction(
        lambda: datetime.utcnow() + timedelta(hours=1)
    )
    status = "scheduled"


class EmailTemplateFactory(TemplateFactory):
    """Factory for creating email-only templates."""
    
    email_subject = factory.Faker('sentence')
    email_body = factory.Faker('paragraph', nb_sentences=3)
    sms_body = None
    webhook_payload = None


class SMSTemplateFactory(TemplateFactory):
    """Factory for creating SMS-only templates."""
    
    email_subject = None
    email_body = None
    sms_body = factory.Faker('sentence', nb_words=10)
    webhook_payload = None


class WebhookTemplateFactory(TemplateFactory):
    """Factory for creating webhook-only templates."""
    
    email_subject = None
    email_body = None
    sms_body = None
    webhook_payload = '{"event": "{{ event }}", "timestamp": "{{ timestamp }}"}'


class UserWithPhoneFactory(UserFactory):
    """Factory for creating users with phone numbers."""
    
    phone = factory.Faker('phone_number')


class UserWithoutPhoneFactory(UserFactory):
    """Factory for creating users without phone numbers."""
    
    phone = None


class UserWithoutEmailFactory(UserFactory):
    """Factory for creating users without email addresses."""
    
    email = None


class HighPriorityNotificationFactory(NotificationFactory):
    """Factory for creating high priority notifications."""
    
    priority = NotificationPriority.HIGH
    resolved_channels = [ChannelType.EMAIL, ChannelType.SMS]


class LowPriorityNotificationFactory(NotificationFactory):
    """Factory for creating low priority notifications."""
    
    priority = NotificationPriority.LOW
    resolved_channels = [ChannelType.EMAIL]


class AlertTemplateFactory(TemplateFactory):
    """Factory for creating alert templates."""
    
    category = TemplateCategory.ALERT
    name = factory.Faker('sentence', nb_words=2) + " Alert"
    email_subject = "Alert: {{ alert_type }}"
    email_body = "<div class='alert'>{{ message }}</div>"
    sms_body = "ALERT: {{ message }}"
    webhook_payload = '{"alert": "{{ alert_type }}", "message": "{{ message }}"}'


class MarketingTemplateFactory(TemplateFactory):
    """Factory for creating marketing templates."""
    
    category = TemplateCategory.MARKETING
    name = factory.Faker('sentence', nb_words=2) + " Campaign"
    email_subject = "{{ campaign_name }}"
    email_body = "<h1>{{ campaign_name }}</h1><p>{{ content }}</p>"
    sms_body = "{{ campaign_name }}: {{ content }}"
    webhook_payload = '{"campaign": "{{ campaign_name }}", "content": "{{ content }}"}'


class DisabledWebhookConfigFactory(WebhookConfigFactory):
    """Factory for creating disabled webhook configurations."""
    
    is_active = False
    failure_count = 5


class FailingWebhookConfigFactory(WebhookConfigFactory):
    """Factory for creating failing webhook configurations."""
    
    failure_count = 10
    last_failure = factory.LazyFunction(datetime.utcnow)
    last_error = "Connection timeout"


class SuccessfulWebhookConfigFactory(WebhookConfigFactory):
    """Factory for creating successful webhook configurations."""
    
    last_success = factory.LazyFunction(datetime.utcnow)
    failure_count = 0
