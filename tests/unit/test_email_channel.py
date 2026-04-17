"""
Unit tests for email channel implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from app.channels.email_channel import EmailChannel
from app.db.models.notification import Notification
from app.db.models.delivery import Delivery
from app.core.constants import DeliveryStatus


class TestEmailChannel:
    """Test cases for EmailChannel class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "password",
            "smtp_from_email": "noreply@example.com",
            "smtp_use_tls": True
        }
        self.channel = EmailChannel(self.config)
    
    @pytest.mark.asyncio
    async def test_send_email_success(self):
        """Test successful email sending."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        # Mock SMTP client
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-123"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-123"
            assert "raw_response" in result.__dict__
            
            # Verify SMTP was called
            mock_smtp_instance.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_email_with_template(self):
        """Test email sending with template content."""
        notification = Notification(
            id="test-notification",
            title="Welcome Email",
            body="<h1>Welcome {{ name }}!</h1><p>Thanks for joining.</p>",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="user@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-456"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-456"
    
    @pytest.mark.asyncio
    async def test_send_email_smtp_error(self):
        """Test email sending with SMTP error."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.side_effect = Exception("SMTP connection failed")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "SMTP connection failed" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_email_authentication_error(self):
        """Test email sending with authentication error."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.side_effect = Exception("Authentication failed")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Authentication failed" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_email_connection_timeout(self):
        """Test email sending with connection timeout."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.side_effect = TimeoutError("Connection timeout")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Connection timeout" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_email_with_reply_to(self):
        """Test email sending with reply-to header."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal",
            metadata={"reply_to": "support@example.com"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-789"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-789"
            
            # Verify message was constructed with reply-to
            call_args = mock_smtp_instance.send_message.call_args
            message = call_args[0][0]
            assert "Reply-To: support@example.com" in str(message)
    
    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self):
        """Test email sending with attachments."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal",
            metadata={
                "attachments": [
                    {"filename": "test.pdf", "content": "base64content", "content_type": "application/pdf"}
                ]
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-101"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-101"
    
    @pytest.mark.asyncio
    async def test_send_email_html_content(self):
        """Test email sending with HTML content."""
        notification = Notification(
            id="test-notification",
            title="HTML Email",
            body="<h1>HTML Content</h1><p>This is <strong>HTML</strong> content.</p>",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-html"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-html"
    
    @pytest.mark.asyncio
    async def test_send_email_plain_text_content(self):
        """Test email sending with plain text content."""
        notification = Notification(
            id="test-notification",
            title="Plain Text Email",
            body="This is plain text content.\n\nWith multiple lines.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-text"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-text"
    
    @pytest.mark.asyncio
    async def test_send_email_with_custom_headers(self):
        """Test email sending with custom headers."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal",
            metadata={
                "headers": {
                    "X-Priority": "1",
                    "X-Mailer": "NotiFlow"
                }
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-headers"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-headers"
            
            # Verify custom headers were included
            call_args = mock_smtp_instance.send_message.call_args
            message = call_args[0][0]
            assert "X-Priority: 1" in str(message)
            assert "X-Mailer: NotiFlow" in str(message)
    
    @pytest.mark.asyncio
    async def test_send_email_with_bounce_address(self):
        """Test email sending with bounce address."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal",
            metadata={"bounce_address": "bounce@example.com"}
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-bounce"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-bounce"
    
    @pytest.mark.asyncio
    async def test_send_email_rate_limit_error(self):
        """Test email sending with rate limit error."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="recipient@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.side_effect = Exception("Rate limit exceeded")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Rate limit exceeded" in str(result.error)
    
    @pytest.mark.asyncio
    async def test_send_email_invalid_destination(self):
        """Test email sending with invalid destination."""
        notification = Notification(
            id="test-notification",
            title="Test Email",
            body="This is a test email.",
            priority="normal"
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="invalid-email",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.side_effect = Exception("Invalid email address")
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is False
            assert "Invalid email address" in str(result.error)
    
    def test_email_channel_configuration(self):
        """Test email channel configuration."""
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_port": 465,
            "smtp_user": "user@test.com",
            "smtp_password": "secret",
            "smtp_from_email": "from@test.com",
            "smtp_use_tls": False
        }
        
        channel = EmailChannel(config)
        
        assert channel.config["smtp_host"] == "smtp.test.com"
        assert channel.config["smtp_port"] == 465
        assert channel.config["smtp_use_tls"] is False
    
    def test_email_channel_default_configuration(self):
        """Test email channel default configuration."""
        config = {
            "smtp_host": "smtp.test.com",
            "smtp_user": "user@test.com",
            "smtp_password": "secret"
        }
        
        channel = EmailChannel(config)
        
        # Check default values
        assert channel.config["smtp_port"] == 587
        assert channel.config["smtp_use_tls"] is True
    
    @pytest.mark.asyncio
    async def test_send_email_with_priority(self):
        """Test email sending with different priorities."""
        for priority in ["low", "normal", "high", "critical"]:
            notification = Notification(
                id=f"test-notification-{priority}",
                title=f"Test Email - {priority}",
                body=f"This is a {priority} priority email.",
                priority=priority
            )
            
            delivery = Delivery(
                id=f"test-delivery-{priority}",
                notification_id=f"test-notification-{priority}",
                channel="email",
                destination="recipient@example.com",
                status="pending"
            )
            
            with patch('app.channels.email_channel.SMTP') as mock_smtp:
                mock_smtp_instance = AsyncMock()
                mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
                mock_smtp_instance.send_message.return_value = {"id": f"smtp-{priority}"}
                
                result = await self.channel.send(notification, delivery)
                
                assert result.success is True
                assert result.provider_id == f"smtp-{priority}"
    
    @pytest.mark.asyncio
    async def test_send_email_with_template_variables(self):
        """Test email sending with template variables."""
        notification = Notification(
            id="test-notification",
            title="Welcome {{ name }}",
            body="Hello {{ name }},\n\nWelcome to {{ company }}!",
            priority="normal",
            metadata={
                "template_variables": {
                    "name": "John Doe",
                    "company": "Acme Corp"
                }
            }
        )
        
        delivery = Delivery(
            id="test-delivery",
            notification_id="test-notification",
            channel="email",
            destination="user@example.com",
            status="pending"
        )
        
        with patch('app.channels.email_channel.SMTP') as mock_smtp:
            mock_smtp_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_smtp_instance
            mock_smtp_instance.send_message.return_value = {"id": "smtp-template"}
            
            result = await self.channel.send(notification, delivery)
            
            assert result.success is True
            assert result.provider_id == "smtp-template"
