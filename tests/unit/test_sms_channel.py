"""
Unit tests for SMS channel implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.channels.sms_channel import SMSChannel
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.core.constants import DeliveryStatus


class TestSMSChannel:
    """Test cases for SMSChannel class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "twilio_account_sid": "AC12345678901234567890123456789012",
            "twilio_auth_token": "auth12345678901234567890123456789012",
            "twilio_from_number": "+1234567890"
        }
        self.channel = SMSChannel(self.config)
    
    @pytest.mark.asyncio
    async def test_send_sms_success(self):
        """Test successful SMS sending."""
        notification = Notification(
            id="test-notification",
            title="Test SMS",
            body="This is a test SMS message.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        # Mock Twilio client
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM12345678901234567890123456789012"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM12345678901234567890123456789012"
            assert "raw_response" in result.__dict__
            
            # Verify Twilio was called
            mock_client.return_value.messages.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_sms_with_template(self):
        """Test SMS sending with template content."""
        notification = Notification(
            id="test-notification",
            title="Welcome SMS",
            body="Welcome {{ name }}! Your code is {{ code }}.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM98765432109876543210987654321098"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM98765432109876543210987654321098"
    
    @pytest.mark.asyncio
    async def test_send_sms_twilio_error(self):
        """Test SMS sending with Twilio error."""
        notification = Notification(
            id="test-notification",
            title="Test SMS",
            body="This is a test SMS message.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            from twilio.base.exceptions import TwilioRestException
            mock_client.return_value.messages.create.side_effect = TwilioRestException(
                401, "Authentication failed"
            )
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Authentication failed" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_invalid_phone_number(self):
        """Test SMS sending with invalid phone number."""
        notification = Notification(
            id="test-notification",
            title="Test SMS",
            body="This is a test SMS message.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="invalid-phone",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            from twilio.base.exceptions import TwilioRestException
            mock_client.return_value.messages.create.side_effect = TwilioRestException(
                400, "Invalid 'To' phone number"
            )
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Invalid 'To' phone number" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_rate_limit_error(self):
        """Test SMS sending with rate limit error."""
        notification = Notification(
            id="test-notification",
            title="Test SMS",
            body="This is a test SMS message.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            from twilio.base.exceptions import TwilioRestException
            mock_client.return_value.messages.create.side_effect = TwilioRestException(
                429, "Too Many Requests"
            )
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Too Many Requests" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_connection_error(self):
        """Test SMS sending with connection error."""
        notification = Notification(
            id="test-notification",
            title="Test SMS",
            body="This is a test SMS message.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_client.return_value.messages.create.side_effect = ConnectionError("Connection failed")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Connection failed" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_long_message_truncation(self):
        """Test SMS sending with long message truncation."""
        long_body = "This is a very long SMS message that exceeds the typical 160 character limit and should be automatically truncated to fit within the SMS character limits while maintaining the most important information at the beginning of the message."
        
        notification = Notification(
            id="test-notification",
            title="Long SMS",
            body=long_body,
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM11111111111111111111111111111111"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM11111111111111111111111111111111"
            
            # Verify message was truncated
            call_args = mock_client.return_value.messages.create.call_args
            sent_body = call_args[1]["body"]
            assert len(sent_body) <= 160
    
    @pytest.mark.asyncio
    async def test_send_sms_with_unicode_content(self):
        """Test SMS sending with Unicode content."""
        notification = Notification(
            id="test-notification",
            title="Unicode SMS",
            body="Hello world! Ñiño café résumé",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM22222222222222222222222222222222"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM22222222222222222222222222222222"
    
    @pytest.mark.asyncio
    async def test_send_sms_with_media_url(self):
        """Test SMS sending with media URL (MMS)."""
        notification = Notification(
            id="test-notification",
            title="MMS Test",
            body="Check out this image!",
            priority="normal",
            metadata={"media_url": "https://example.com/image.jpg"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM33333333333333333333333333333333"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM33333333333333333333333333333333"
            
            # Verify media URL was included
            call_args = mock_client.return_value.messages.create.call_args
            assert call_args[1]["media_url"] == "https://example.com/image.jpg"
    
    @pytest.mark.asyncio
    async def test_send_sms_with_delivery_callback(self):
        """Test SMS sending with delivery callback URL."""
        notification = Notification(
            id="test-notification",
            title="Callback SMS",
            body="This SMS has a callback.",
            priority="normal",
            metadata={"status_callback": "https://example.com/sms-status"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM44444444444444444444444444444444"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM44444444444444444444444444444444"
            
            # Verify status callback was included
            call_args = mock_client.return_value.messages.create.call_args
            assert call_args[1]["status_callback"] == "https://example.com/sms-status"
    
    @pytest.mark.asyncio
    async def test_send_sms_with_priority(self):
        """Test SMS sending with different priorities."""
        for priority in ["low", "normal", "high", "critical"]:
            notification = Notification(
                id=f"test-notification-{priority}",
                title=f"Test SMS - {priority}",
                body=f"This is a {priority} priority SMS.",
                priority=priority
            )
            
            delivery = Delivery(
                id=f"test-delivery-{priority}",
                notification_id=f"test-notification-{priority}",
                channel="sms",
                destination="+12345678901",
                status="pending"
            )
            
            with patch('app.channels.sms_channel.Client') as mock_client:
                mock_message = AsyncMock()
                mock_message.sid = f"SM{priority}5555555555555555555555555555555"
                mock_message.status = "sent"
                mock_client.return_value.messages.create.return_value = mock_message
                
                result = await self.channel.send(notification, delivery)
                
                assert result.success is True
                assert result.provider_id == f"SM{priority}5555555555555555555555555555555"
    
    @pytest.mark.asyncio
    async def test_send_sms_with_custom_from_number(self):
        """Test SMS sending with custom from number."""
        notification = Notification(
            id="test-notification",
            title="Custom From SMS",
            body="This SMS uses a custom from number.",
            priority="normal",
            metadata={"from_number": "+19876543210"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM66666666666666666666666666666666"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM66666666666666666666666666666666"
            
            # Verify custom from number was used
            call_args = mock_client.return_value.messages.create.call_args
            assert call_args[1]["from_"] == "+19876543210"
    
    def test_sms_channel_configuration(self):
        """Test SMS channel configuration."""
        config = {
            "twilio_account_sid": "AC00000000000000000000000000000000",
            "twilio_auth_token": "auth00000000000000000000000000000000",
            "twilio_from_number": "+15551234567",
            "timeout": 30
        }
        
        channel = SMSChannel(config)
        
        assert channel.config["twilio_account_sid"] == "AC00000000000000000000000000000000"
        assert channel.config["twilio_auth_token"] == "auth00000000000000000000000000000000"
        assert channel.config["twilio_from_number"] == "+15551234567"
        assert channel.config["timeout"] == 30
    
    def test_sms_channel_missing_configuration(self):
        """Test SMS channel with missing configuration."""
        config = {
            "twilio_account_sid": "AC00000000000000000000000000000000",
            # Missing auth_token and from_number
        }
        
        with pytest.raises(KeyError):
            SMSChannel(config)
    
    @pytest.mark.asyncio
    async def test_send_sms_with_template_variables(self):
        """Test SMS sending with template variables."""
        notification = Notification(
            id="test-notification",
            title="Welcome {{ name }}",
            body="Hi {{ name }}, your verification code is {{ code }}.",
            priority="normal",
            metadata={
                "template_variables": {
                    "name": "Alice",
                    "code": "123456"
                }
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM77777777777777777777777777777777"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM77777777777777777777777777777777"
    
    @pytest.mark.asyncio
    async def test_send_sms_with_empty_body(self):
        """Test SMS sending with empty body."""
        notification = Notification(
            id="test-notification",
            title="Empty SMS",
            body="",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        result = await self.channel.send(notification, delivery)
        
        assert result.success is False
        assert "Message body cannot be empty" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_with_whitespace_only_body(self):
        """Test SMS sending with whitespace-only body."""
        notification = Notification(
            id="test-notification",
            title="Whitespace SMS",
            body="   \n\t   ",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        result = await self.channel.send(notification, delivery)
        
        assert result.success is False
        assert "Message body cannot be empty" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_sms_with_multiple_media_urls(self):
        """Test SMS sending with multiple media URLs."""
        notification = Notification(
            id="test-notification",
            title="Multiple Media SMS",
            body="Multiple media files.",
            priority="normal",
            metadata={
                "media_urls": [
                    "https://example.com/image1.jpg",
                    "https://example.com/image2.jpg"
                ]
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="sms",
            destination="+12345678901",
            status="pending"
        )
        
        with patch('app.channels.sms_channel.Client') as mock_client:
            mock_message = AsyncMock()
            mock_message.sid = "SM88888888888888888888888888888888888"
            mock_message.status = "sent"
            mock_client.return_value.messages.create.return_value = mock_message
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "SM88888888888888888888888888888888888"
            
            # Verify multiple media URLs were included
            call_args = mock_client.return_value.messages.create.call_args
            assert len(call_args[1]["media_url"]) == 2
