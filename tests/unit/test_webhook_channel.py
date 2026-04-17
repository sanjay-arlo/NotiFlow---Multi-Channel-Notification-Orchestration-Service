"""
Unit tests for webhook channel implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import json

from app.channels.webhook_channel import WebhookChannel
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.core.constants import DeliveryStatus


class TestWebhookChannel:
    """Test cases for WebhookChannel class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "secret": "webhook-secret-key",
            "headers": {
                "Content-Type": "application/json",
                "User-Agent": "NotiFlow-Webhook/1.0"
            },
            "max_retries": 3,
            "timeout_seconds": 10
        }
        self.channel = WebhookChannel(self.config)
    
    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        """Test successful webhook delivery."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test", "data": "payload"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        # Mock HTTP client
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_response.headers = {"X-Request-ID": "req-123"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "req-123"
            assert "raw_response" in result.__dict__
            
            # Verify HTTP call was made correctly
            mock_client.return_value.post.assert_called_once()
            call_args = mock_client.return_value.post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            assert call_args[0][1]["json"] == {"event": "test", "data": "payload"}
            
            # Verify headers
            headers = call_args[0][1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["X-Notification-ID"] == "test-notification"
            assert headers["X-Delivery-ID"] == "test-delivery"
            
            # Verify signature
            signature = headers["X-Signature"]
            expected_signature = self.channel._generate_signature(
                json.dumps({"event": "test", "data": "payload"}, separators=(",", ":"))
            )
            assert signature == expected_signature
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_template(self):
        """Test webhook sending with template rendering."""
        notification = Notification(
            id="test-notification",
            title="Template Webhook",
            body='{"event": "{{ event_type }}", "user": "{{ user_id }}", "timestamp": "{{ timestamp }}"}',
            priority="normal",
            metadata={
                "template_variables": {
                    "event_type": "user_signup",
                    "user_id": "12345",
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "webhook-456"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "webhook-456"
            
            # Verify rendered payload
            call_args = mock_client.return_value.post.call_args
            sent_payload = call_args[0][1]["json"]
            expected_payload = {
                "event": "user_signup",
                "user": "12345",
                "timestamp": "2024-01-15T10:00:00Z"
            }
            assert sent_payload == expected_payload
    
    @pytest.mark.asyncio
    async def test_send_webhook_http_error(self):
        """Test webhook sending with HTTP error."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            from httpx import HTTPStatusError, Response
            error_response = Response(500, json={"error": "Internal server error"})
            mock_client.return_value.post.side_effect = HTTPStatusError("Server Error", request=error_response)
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "HTTP error" in str(result.error).lower()
            assert result.retry_after is None
    
    @pytest.mark.asyncio
    async def test_send_webhook_rate_limit_error(self):
        """Test webhook sending with rate limit error."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            from httpx import HTTPStatusError, Response
            error_response = Response(429, headers={"Retry-After": "60"})
            mock_client.return_value.post.side_effect = HTTPStatusError("Rate limit", request=error_response)
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "rate limit" in str(result.error).lower()
            assert result.retry_after == 60
    
    @pytest.mark.asyncio
    async def test_send_webhook_timeout_error(self):
        """Test webhook sending with timeout error."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            from httpx import ConnectTimeout
            mock_client.return_value.post.side_effect = ConnectTimeout("Request timeout")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "timeout" in str(result.error).lower()
    
    @pytest.mark.asyncio
    async def test_send_webhook_connection_error(self):
        """Test webhook sending with connection error."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            from httpx import ConnectError
            mock_client.return_value.post.side_effect = ConnectError("Connection failed")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "connection" in str(result.error).lower()
    
    @pytest.mark.asyncio
    async def test_send_webhook_without_secret(self):
        """Test webhook sending without signing secret."""
        config = self.config.copy()
        config["secret"] = None
        channel = WebhookChannel(config)
        
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify no signature header
            call_args = mock_client.return_value.post.call_args
            headers = call_args[0][1]["headers"]
            assert "X-Signature" not in headers
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_custom_headers(self):
        """Test webhook sending with custom headers."""
        config = self.config.copy()
        config["headers"].update({
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value"
        })
        channel = WebhookChannel(config)
        
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify custom headers were included
            call_args = mock_client.return_value.post.call_args
            headers = call_args[0][1]["headers"]
            assert headers["Authorization"] == "Bearer token123"
            assert headers["X-Custom-Header"] == "custom-value"
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_large_payload(self):
        """Test webhook sending with large payload."""
        large_data = {"data": "x" * 10000}  # 10KB of data
        notification = Notification(
            id="test-notification",
            title="Large Webhook",
            body=json.dumps(large_data),
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify large payload was handled
            call_args = mock_client.return_value.post.call_args
            sent_payload = call_args[0][1]["json"]
            assert len(json.dumps(sent_payload)) > 10000
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_priority(self):
        """Test webhook sending with different priorities."""
        for priority in ["low", "normal", "high", "critical"]:
            notification = Notification(
                id=f"test-notification-{priority}",
                title=f"Test Webhook - {priority}",
                body=f'{{"event": "test", "priority": "{priority}"}}',
                priority=priority
            )
            
            delivery = Delivery(
                id=f"test-delivery-{priority}",
                notification_id=f"test-notification-{priority}",
                channel="webhook",
                destination="https://example.com/webhook",
                status="pending"
            )
            
            with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {"status": "ok"}
                mock_client.return_value.post.return_value = mock_response
                
                result = await self.channel.send(notification, delivery)
                
                assert result.success is True
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_retry_after_header(self):
        """Test webhook sending with retry-after header."""
        notification = Notification(
            id="test-notification",
            title="Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            from httpx import HTTPStatusError, Response
            error_response = Response(429, headers={"Retry-After": "300"})
            mock_client.return_value.post.side_effect = HTTPStatusError("Rate limit", request=error_response)
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert result.retry_after == 300
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_invalid_json(self):
        """Test webhook sending with invalid JSON payload."""
        notification = Notification(
            id="test-notification",
            title="Invalid JSON Webhook",
            body='{"event": "test", "invalid": json}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        result = await self.channel.send(notification, delivery)
        
        assert result.success is False
        assert "Invalid JSON" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_empty_payload(self):
        """Test webhook sending with empty payload."""
        notification = Notification(
            id="test-notification",
            title="Empty Webhook",
            body="",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        result = await self.channel.send(notification, delivery)
        
        assert result.success is False
        assert "Payload cannot be empty" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_timestamp_validation(self):
        """Test webhook sending with timestamp validation."""
        config = self.config.copy()
        config["validate_timestamp"] = True
        config["max_timestamp_age"] = 300  # 5 minutes
        channel = WebhookChannel(config)
        
        notification = Notification(
            id="test-notification",
            title="Timestamp Webhook",
            body='{"event": "test", "timestamp": "2024-01-15T10:00:00Z"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify timestamp was added
            call_args = mock_client.return_value.post.call_args
            headers = call_args[0][1]["headers"]
            assert "X-Timestamp" in headers
    
    def test_webhook_channel_configuration(self):
        """Test webhook channel configuration."""
        config = {
            "secret": "test-secret",
            "headers": {"Content-Type": "application/json"},
            "max_retries": 5,
            "timeout_seconds": 30
        }
        
        channel = WebhookChannel(config)
        
        assert channel.config["secret"] == "test-secret"
        assert channel.config["max_retries"] == 5
        assert channel.config["timeout_seconds"] == 30
    
    def test_generate_signature(self):
        """Test HMAC signature generation."""
        payload = '{"event": "test", "data": "payload"}'
        secret = "test-secret"
        
        channel = WebhookChannel({"secret": secret})
        signature = channel._generate_signature(payload)
        
        # Verify signature is not empty and consistent
        assert signature is not None
        assert len(signature) > 0
        
        # Verify same payload produces same signature
        signature2 = channel._generate_signature(payload)
        assert signature == signature2
    
    def test_generate_signature_with_different_payloads(self):
        """Test that different payloads produce different signatures."""
        channel = WebhookChannel({"secret": "test-secret"})
        
        payload1 = '{"event": "test1"}'
        payload2 = '{"event": "test2"}'
        
        signature1 = channel._generate_signature(payload1)
        signature2 = channel._generate_signature(payload2)
        
        assert signature1 != signature2
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_form_data(self):
        """Test webhook sending with form data instead of JSON."""
        notification = Notification(
            id="test-notification",
            title="Form Webhook",
            body="key1=value1&key2=value2",
            priority="normal",
            metadata={"content_type": "application/x-www-form-urlencoded"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify form data was sent
            call_args = mock_client.return_value.post.call_args
            assert "data" in call_args[0][1]
            assert call_args[0][1]["data"] == "key1=value1&key2=value2"
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_multipart_data(self):
        """Test webhook sending with multipart data."""
        notification = Notification(
            id="test-notification",
            title="Multipart Webhook",
            body='{"file": "test.txt", "content": "Hello World"}',
            priority="normal",
            metadata={"content_type": "multipart/form-data"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_send_webhook_with_ssl_verification(self):
        """Test webhook sending with SSL verification settings."""
        config = self.config.copy()
        config["verify_ssl"] = False
        channel = WebhookChannel(config)
        
        notification = Notification(
            id="test-notification",
            title="SSL Test Webhook",
            body='{"event": "test"}',
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="webhook",
            destination="https://example.com/webhook",
            status="pending"
        )
        
        with patch('app.channels.webhook_channel.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            mock_client.return_value.post.return_value = mock_response
            
            result = await channel.send(notification, delivery)
            
            assert result.success is True
            
            # Verify SSL verification setting
            mock_client.assert_called_once_with(verify=False)
