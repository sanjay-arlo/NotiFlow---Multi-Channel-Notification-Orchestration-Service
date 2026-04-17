"""
Channel resolution logic for determining which channels to use.
"""

from typing import List, Optional

from app.core.constants import ChannelType, NotificationPriority
from app.db.models.user import User
from app.db.models.notification import Notification


class ChannelResolver:
    """Resolves which channels to use for notification delivery."""
    
    def __init__(self):
        pass
    
    def resolve_channels(
        self,
        user: User,
        notification: Notification,
        requested_channels: Optional[List[str]] = None
    ) -> List[str]:
        """
        Resolve which channels to use for notification delivery.
        
        Args:
            user: The notification recipient
            notification: The notification to send
            requested_channels: Specific channels requested (None = auto-resolve)
            
        Returns:
            List of channel names in priority order
        """
        if requested_channels:
            # Use specific requested channels, filtered by user preferences
            return self._filter_requested_channels(user, requested_channels)
        else:
            # Auto-resolve channels based on content and user
            return self._auto_resolve_channels(user, notification)
    
    def _filter_requested_channels(
        self,
        user: User,
        requested_channels: List[str]
    ) -> List[str]:
        """Filter requested channels by user preferences and availability."""
        available_channels = []
        
        for channel in requested_channels:
            if not self._is_channel_available(user, channel):
                continue
            available_channels.append(channel)
        
        return available_channels
    
    def _auto_resolve_channels(
        self,
        user: User,
        notification: Notification
    ) -> List[str]:
        """Automatically resolve channels based on content and user."""
        available_channels = self._get_available_channels(user)
        
        if not available_channels:
            return []
        
        # Critical priority uses ALL enabled channels
        if notification.priority == NotificationPriority.CRITICAL:
            return available_channels
        
        # Long content defaults to email
        if self._is_long_content(notification):
            if ChannelType.EMAIL in available_channels:
                return [ChannelType.EMAIL]
            # Fall back to first available if no email
            return [available_channels[0]]
        
        # Default priority order: email -> sms -> webhook
        channel_priority = [
            ChannelType.EMAIL,
            ChannelType.SMS,
            ChannelType.WEBHOOK
        ]
        
        for channel in channel_priority:
            if channel in available_channels:
                return [channel]
        
        return []
    
    def _get_available_channels(self, user: User) -> List[str]:
        """Get list of channels available for user."""
        available_channels = []
        
        # Check email availability
        if user.has_email():
            available_channels.append(ChannelType.EMAIL)
        
        # Check SMS availability
        if user.has_phone():
            available_channels.append(ChannelType.SMS)
        
        # Webhook is always available if configured
        # (This would need webhook config per user or tenant)
        available_channels.append(ChannelType.WEBHOOK)
        
        return available_channels
    
    def _is_channel_available(self, user: User, channel: str) -> bool:
        """Check if channel is available for user."""
        if channel == ChannelType.EMAIL:
            return user.has_email()
        elif channel == ChannelType.SMS:
            return user.has_phone()
        elif channel == ChannelType.WEBHOOK:
            return True  # Webhook is always available if configured
        else:
            return False
    
    def _is_long_content(self, notification: Notification) -> bool:
        """Check if notification content is better suited for email."""
        # Check body length (SMS limit is ~160 characters)
        if len(notification.body) > 160:
            return True
        
        # Check for HTML content
        if self._contains_html(notification.body):
            return True
        
        # Check for complex formatting
        if self._has_complex_formatting(notification.body):
            return True
        
        return False
    
    def _contains_html(self, content: str) -> bool:
        """Check if content contains HTML tags."""
        html_tags = ["<html>", "<div>", "<p>", "<br>", "<a href="]
        return any(tag in content.lower() for tag in html_tags)
    
    def _has_complex_formatting(self, content: str) -> bool:
        """Check if content has complex formatting."""
        # Check for multiple paragraphs
        if content.count('\n\n') >= 2:
            return True
        
        # Check for bullet points or numbered lists
        lines = content.split('\n')
        bullet_lines = sum(1 for line in lines if line.strip().startswith(('-', '*', '•')))
        numbered_lines = sum(1 for line in lines if line.strip() and line.strip()[0].isdigit())
        
        if bullet_lines >= 2 or numbered_lines >= 2:
            return True
        
        return False
    
    def get_primary_channel(
        self,
        channels: List[str],
        notification: Notification
    ) -> str:
        """Get the primary channel from resolved channels."""
        if not channels:
            raise ValueError("No channels available")
        
        # If only one channel, it's the primary
        if len(channels) == 1:
            return channels[0]
        
        # For critical notifications, use email if available (most reliable)
        if notification.priority == NotificationPriority.CRITICAL:
            if ChannelType.EMAIL in channels:
                return ChannelType.EMAIL
        
        # Use first channel in list (highest priority)
        return channels[0]
    
    def validate_channels(self, channels: List[str]) -> bool:
        """Validate that all channels are supported."""
        supported_channels = {ChannelType.EMAIL, ChannelType.SMS, ChannelType.WEBHOOK}
        return all(channel in supported_channels for channel in channels)
    
    def get_channel_priority(self, channel: str) -> int:
        """Get priority value for channel (lower = higher priority)."""
        priority_map = {
            ChannelType.EMAIL: 1,
            ChannelType.SMS: 2,
            ChannelType.WEBHOOK: 3,
        }
        return priority_map.get(channel, 999)
