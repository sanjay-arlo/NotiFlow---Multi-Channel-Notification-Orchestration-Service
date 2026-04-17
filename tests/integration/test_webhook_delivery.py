"""
Integration tests for webhook delivery functionality.
"""

import pytest
from unittest.mock import AsyncMock, patch
import json

from fastapi.testclient import TestClient

from app.api.routes.webhooks import router
from app.core.security import generate_webhook_signature
from app.db.models.webhook_config import WebhookConfig


class TestWebhookDelivery:
    """Integration tests for webhook delivery."""
    
    @pytest.fixture
    def webhook_config(self):
        """Create sample webhook config for testing."""
        return WebhookConfig(
            id="test-webhook-id",
            name="Test Webhook",
            url="https://httpbin.org/post",
            secret="test-secret",
            headers={"Content-Type": "application/json"},
            max_retries=3,
            timeout_seconds=10,
            is_active=True,
            failure_count=0
        )
    
    @pytest.fixture
    def sample_webhook_payload(self):
        """Create sample webhook payload."""
        return {
            "id": "test-notification-id",
            "delivery_id": "test-delivery-id",
            "title": "Test Notification",
            "body": "This is a test webhook notification.",
            "priority": "normal",
            "status": "sent",
            "created_at": "2024-01-15T10:00:00Z",
            "metadata": {"source": "test"},
            "user": {
                "id": "test-user-id",
                "external_id": "test-user-123",
                "email": "test@example.com",
                "phone": "+1234567890",
                "display_name": "Test User"
            },
            "channels": ["webhook"],
            "primary_channel": "webhook"
        }
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_success(self, webhook_config, sample_webhook_payload):
        """Test successful webhook delivery."""
        # Mock HTTP client
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.headers = {"X-Request-ID": "test-request-id"}
            mock_post.return_value = mock_response
            
            # Mock webhook channel
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                mock_channel.send.return_value = AsyncMock(
                    success=True,
                    provider_id="test-provider-id",
                    raw_response={"status": "ok"}
                )
                
                # Create webhook channel with config
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                # Send webhook
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify success
                assert result.success is True
                assert result.provider_id == "test-provider-id"
                
                # Verify HTTP call was made correctly
                mock_post.assert_called_once()
                call_args = mock_post.call_args
                assert call_args[0][0] == webhook_config.url
                assert call_args[0][1]["json"] == sample_webhook_payload
                
                # Verify headers
                headers = call_args[0][1]["headers"]
                assert headers["Content-Type"] == "application/json"
                assert headers["X-Notification-ID"] == "test-notification-id"
                assert headers["X-Delivery-ID"] == "test-delivery-id"
                
                # Verify signature
                signature = headers["X-Signature"]
                expected_signature = generate_webhook_signature(
                    json.dumps(sample_webhook_payload, separators=(",", ":")),
                    webhook_config.secret
                )
                assert signature == expected_signature
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_with_custom_headers(self, webhook_config, sample_webhook_payload):
        """Test webhook delivery with custom headers."""
        # Add custom headers to webhook config
        webhook_config.headers.update({
            "X-Custom-Header": "custom-value",
            "Authorization": "Bearer token123"
        })
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"received": True}
            mock_post.return_value = mock_response
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                mock_channel.send.return_value = AsyncMock(
                    success=True,
                    provider_id="test-provider-id",
                    raw_response={"received": True}
                )
                
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify custom headers are included
                call_args = mock_post.call_args
                headers = call_args[0][1]["headers"]
                assert headers["X-Custom-Header"] == "custom-value"
                assert headers["Authorization"] == "Bearer token123"
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_http_error(self, webhook_config, sample_webhook_payload):
        """Test webhook delivery with HTTP error."""
        with patch('httpx.AsyncClient.post') as mock_post:
            from httpx import HTTPStatusError, Response
            
            error_response = Response(500, json={"error": "Internal server error"})
            mock_post.side_effect = HTTPStatusError("Server Error", request=error_response)
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify error handling
                assert result.success is False
                assert "HTTP error" in str(result.error).lower()
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_timeout(self, webhook_config, sample_webhook_payload):
        """Test webhook delivery with timeout."""
        with patch('httpx.AsyncClient.post') as mock_post:
            from httpx import ConnectTimeout
            
            mock_post.side_effect = ConnectTimeout("Request timeout")
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify timeout handling
                assert result.success is False
                assert "timeout" in str(result.error).lower()
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_retry_logic(self, webhook_config, sample_webhook_payload):
        """Test webhook delivery retry logic."""
        with patch('httpx.AsyncClient.post') as mock_post:
            # First call fails with 429 (rate limit)
            from httpx import HTTPStatusError, Response
            
            retry_response = Response(429, json={"error": "Too many requests"})
            retry_after = 60
            mock_post.side_effect = HTTPStatusError("Rate limit", request=retry_response)
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                from app.channels.webhook_channel import WebhookChannel
                from app.utils.retry import calculate_next_retry_at
                
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify retry logic
                assert result.success is False
                assert result.retry_after == retry_after
                
                # Verify next retry calculation
                next_retry = calculate_next_retry_at(0, "webhook", retry_after)
                expected_retry = next_retry
                assert abs((result.next_retry_at - expected_retry).total_seconds()) < 1
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_without_secret(self, sample_webhook_payload):
        """Test webhook delivery without signing secret."""
        webhook_config = WebhookConfig(
            id="test-webhook-id",
            name="Test Webhook",
            url="https://httpbin.org/post",
            secret=None,  # No secret
            headers={"Content-Type": "application/json"},
            max_retries=3,
            timeout_seconds=10,
            is_active=True,
            failure_count=0
        )
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_post.return_value = mock_response
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                mock_channel.send.return_value = AsyncMock(
                    success=True,
                    provider_id="test-provider-id",
                    raw_response={"status": "ok"}
                )
                
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": None,  # No secret
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify success without signature
                assert result.success is True
                
                # Verify no signature header
                call_args = mock_post.call_args
                headers = call_args[0][1]["headers"]
                assert "X-Signature" not in headers
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_json_payload(self, webhook_config):
        """Test webhook delivery with JSON payload template."""
        # Create notification with webhook template
        from app.db.models.notification import Notification
        from app.db.models.template import Template
        
        template = Template(
            id="test-template-id",
            slug="webhook-template",
            webhook_payload='{"event": "{{ event_type }}", "data": {{ data | tojson }}}'
        )
        
        notification = Notification(
            id="test-notification-id",
            title="Test Event",
            body="Test notification",
            priority="normal",
            template=template,
            metadata={"event_type": "user_signup", "data": {"user_id": "123"}}
        )
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_post.return_value = mock_response
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                mock_channel.send.return_value = AsyncMock(
                    success=True,
                    provider_id="test-provider-id",
                    raw_response={"status": "ok"}
                )
                
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify JSON payload rendering
                assert result.success is True
                
                # Verify rendered payload
                call_args = mock_post.call_args
                sent_payload = json.loads(call_args[0][1]["json"])
                
                expected_payload = {
                    "event": "user_signup",
                    "data": {"user_id": "123"}
                }
                assert sent_payload == expected_payload
    
    @pytest.mark.asyncio
    async def test_webhook_delivery_large_payload(self, webhook_config):
        """Test webhook delivery with large payload."""
        # Create large payload
        large_data = {"data": "x" * 10000}  # 10KB of data
        sample_webhook_payload = {
            "id": "test-notification-id",
            "delivery_id": "test-delivery-id",
            "title": "Test Notification",
            "body": "This is a test notification.",
            "priority": "normal",
            "metadata": large_data
        }
        
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_post.return_value = mock_response
            
            with patch('app.channels.webhook_channel.WebhookChannel') as mock_channel:
                mock_channel.send.return_value = AsyncMock(
                    success=True,
                    provider_id="test-provider-id",
                    raw_response={"status": "ok"}
                )
                
                from app.channels.webhook_channel import WebhookChannel
                channel = WebhookChannel({
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                })
                
                from app.db.models.delivery import Delivery
                from app.db.models.notification import Notification
                
                delivery = Delivery(
                    id="test-delivery-id",
                    notification_id="test-notification-id",
                    channel="webhook",
                    destination=webhook_config.url,
                    status="pending"
                )
                
                notification = Notification(
                    id="test-notification-id",
                    title="Test",
                    body="Test notification",
                    priority="normal"
                )
                
                result = await channel.send(notification, delivery)
                
                # Verify large payload is handled
                assert result.success is True
                
                # Verify payload was sent
                call_args = mock_post.call_args
                sent_payload = json.loads(call_args[0][1]["json"])
                assert len(json.dumps(sent_payload)) > 10000  # Large payload
