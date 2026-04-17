"""
Unit tests for channel resolver logic.
"""

import pytest
from datetime import time

from app.core.constants import ChannelType, NotificationPriority
from app.db.models.user import User
from app.db.models.notification import Notification
from app.services.channel_resolver import ChannelResolver


class TestChannelResolver:
    """Test cases for ChannelResolver class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ChannelResolver()
    
    def test_resolve_channels_auto_email_user(self):
        """Test channel resolution for user with email only."""
        user = User(
            email="test@example.com",
            phone=None,
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="Test notification",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.EMAIL]
    
    def test_resolve_channels_auto_sms_user(self):
        """Test channel resolution for user with SMS only."""
        user = User(
            email=None,
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="Test notification",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.SMS]
    
    def test_resolve_channels_auto_webhook_user(self):
        """Test channel resolution for user with no email/phone."""
        user = User(
            email=None,
            phone=None,
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="Test notification",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.WEBHOOK]
    
    def test_resolve_channels_critical_priority(self):
        """Test that critical priority uses all available channels."""
        user = User(
            email="test@example.com",
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Critical Alert",
            body="This is critical!",
            priority=NotificationPriority.CRITICAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert set(channels) == {ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK}
    
    def test_resolve_channels_long_content(self):
        """Test that long content defaults to email."""
        user = User(
            email="test@example.com",
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="This is a very long notification content that exceeds the typical SMS character limit and should therefore be routed to email instead of SMS to ensure proper delivery and readability for the end user who will receive this message.",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.EMAIL]
    
    def test_resolve_channels_html_content(self):
        """Test that HTML content defaults to email."""
        user = User(
            email="test@example.com",
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="<h1>HTML Content</h1><p>This has HTML tags.</p>",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.EMAIL]
    
    def test_resolve_channels_complex_formatting(self):
        """Test that complex formatting defaults to email."""
        user = User(
            email="test@example.com",
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="• First item\n• Second item\n• Third item\n\nThis has multiple paragraphs and bullet points.",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == [ChannelType.EMAIL]
    
    def test_resolve_channels_requested_specific(self):
        """Test that specific requested channels are used."""
        user = User(
            email="test@example.com",
            phone="+1234567890",
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="Test notification",
            priority=NotificationPriority.NORMAL
        )
        
        # Request only SMS
        channels = self.resolver.resolve_channels(
            user, notification, [ChannelType.SMS]
        )
        assert channels == [ChannelType.SMS]
    
    def test_resolve_channels_no_available_channels(self):
        """Test that no available channels returns empty list."""
        user = User(
            email=None,
            phone=None,
            timezone="UTC"
        )
        notification = Notification(
            title="Test",
            body="Test notification",
            priority=NotificationPriority.NORMAL
        )
        
        channels = self.resolver.resolve_channels(user, notification)
        assert channels == []
    
    def test_get_primary_channel_single(self):
        """Test primary channel selection with single channel."""
        channels = [ChannelType.EMAIL]
        notification = Notification(
            title="Test",
            body="Test",
            priority=NotificationPriority.NORMAL
        )
        
        primary = self.resolver.get_primary_channel(channels, notification)
        assert primary == ChannelType.EMAIL
    
    def test_get_primary_channel_multiple_normal(self):
        """Test primary channel selection with multiple channels (normal priority)."""
        channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]
        notification = Notification(
            title="Test",
            body="Test",
            priority=NotificationPriority.NORMAL
        )
        
        primary = self.resolver.get_primary_channel(channels, notification)
        assert primary == ChannelType.EMAIL  # First in priority order
    
    def test_get_primary_channel_multiple_critical(self):
        """Test primary channel selection with multiple channels (critical priority)."""
        channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]
        notification = Notification(
            title="Critical Alert",
            body="This is critical!",
            priority=NotificationPriority.CRITICAL
        )
        
        primary = self.resolver.get_primary_channel(channels, notification)
        assert primary == ChannelType.EMAIL  # Email for critical notifications
    
    def test_get_primary_channel_empty_raises_error(self):
        """Test that empty channels list raises error."""
        notification = Notification(
            title="Test",
            body="Test",
            priority=NotificationPriority.NORMAL
        )
        
        with pytest.raises(ValueError, match="No channels available"):
            self.resolver.get_primary_channel([], notification)
    
    def test_validate_channels_valid(self):
        """Test channel validation with valid channels."""
        valid_channels = [ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK]
        assert self.resolver.validate_channels(valid_channels) is True
    
    def test_validate_channels_invalid(self):
        """Test channel validation with invalid channels."""
        invalid_channels = [ChannelType.EMAIL, "invalid_channel", ChannelType.SMS]
        assert self.resolver.validate_channels(invalid_channels) is False
    
    def test_get_channel_priority(self):
        """Test channel priority mapping."""
        assert self.resolver.get_channel_priority(ChannelType.EMAIL) == 1
        assert self.resolver.get_channel_priority(ChannelType.SMS) == 2
        assert self.resolver.get_channel_priority(ChannelType.WEBHOOK) == 3
        assert self.resolver.get_channel_priority("invalid") == 999
    
    def test_is_channel_available_email(self):
        """Test email channel availability check."""
        user_with_email = User(email="test@example.com")
        user_without_email = User(email=None)
        
        assert self.resolver._is_channel_available(user_with_email, ChannelType.EMAIL) is True
        assert self.resolver._is_channel_available(user_without_email, ChannelType.EMAIL) is False
    
    def test_is_channel_available_sms(self):
        """Test SMS channel availability check."""
        user_with_phone = User(phone="+1234567890")
        user_without_phone = User(phone=None)
        
        assert self.resolver._is_channel_available(user_with_phone, ChannelType.SMS) is True
        assert self.resolver._is_channel_available(user_without_phone, ChannelType.SMS) is False
    
    def test_is_channel_available_webhook(self):
        """Test webhook channel availability check."""
        user = User()  # Webhook is always available
        
        assert self.resolver._is_channel_available(user, ChannelType.WEBHOOK) is True
    
    def test_is_long_content_short_text(self):
        """Test long content detection with short text."""
        content = "This is short text."
        assert self.resolver._is_long_content(Notification(body=content)) is False
    
    def test_is_long_content_long_text(self):
        """Test long content detection with long text."""
        content = "This is a very long notification content that definitely exceeds the typical SMS character limit of 160 characters and should therefore be flagged as long content for proper channel selection and routing to ensure the message reaches the recipient in the most appropriate format."
        assert self.resolver._is_long_content(Notification(body=content)) is True
    
    def test_is_long_content_html(self):
        """Test long content detection with HTML."""
        content = "<h1>HTML Content</h1>"
        assert self.resolver._is_long_content(Notification(body=content)) is True
    
    def test_is_long_content_bullets(self):
        """Test long content detection with bullet points."""
        content = "• First item\n• Second item\n• Third item"
        assert self.resolver._is_long_content(Notification(body=content)) is True
    
    def test_contains_html_with_html_tags(self):
        """Test HTML detection with HTML tags."""
        content = "<div>Content</div>"
        assert self.resolver._contains_html(content) is True
    
    def test_contains_html_without_html_tags(self):
        """Test HTML detection without HTML tags."""
        content = "Just plain text content"
        assert self.resolver._contains_html(content) is False
    
    def test_has_complex_formatting_with_bullets(self):
        """Test complex formatting detection with bullet points."""
        content = "• First item\n• Second item"
        assert self.resolver._has_complex_formatting(content) is True
    
    def test_has_complex_formatting_with_numbers(self):
        """Test complex formatting detection with numbered lists."""
        content = "1. First item\n2. Second item"
        assert self.resolver._has_complex_formatting(content) is True
    
    def test_has_complex_formatting_with_paragraphs(self):
        """Test complex formatting detection with multiple paragraphs."""
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        assert self.resolver._has_complex_formatting(content) is True
    
    def test_has_complex_formatting_simple_text(self):
        """Test complex formatting detection with simple text."""
        content = "Just simple text content."
        assert self.resolver._has_complex_formatting(content) is False
