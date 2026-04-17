"""
Channel registry for managing notification channels.
"""

from typing import Dict, Type

from app.channels.base import BaseChannel
from app.channels.email_channel import EmailChannel
from app.channels.sms_channel import SMSChannel
from app.channels.webhook_channel import WebhookChannel


class ChannelRegistry:
    """Registry for notification channels."""
    
    def __init__(self):
        self._channels: Dict[str, Type[BaseChannel]] = {}
        self._instances: Dict[str, BaseChannel] = {}
        
        # Register built-in channels
        self.register("email", EmailChannel)
        self.register("sms", SMSChannel)
        self.register("webhook", WebhookChannel)
    
    def register(self, name: str, channel_class: Type[BaseChannel]) -> None:
        """Register a channel class."""
        self._channels[name] = channel_class
    
    def get_channel_class(self, name: str) -> Type[BaseChannel]:
        """Get channel class by name."""
        if name not in self._channels:
            raise ValueError(f"Unknown channel: {name}")
        return self._channels[name]
    
    def get_channel(self, name: str, **kwargs) -> BaseChannel:
        """Get channel instance by name."""
        channel_class = self.get_channel_class(name)
        
        # Cache instances for stateless channels
        if name not in self._instances:
            self._instances[name] = channel_class(**kwargs)
        
        return self._instances[name]
    
    def list_channels(self) -> list[str]:
        """List all registered channel names."""
        return list(self._channels.keys())
    
    def is_channel_supported(self, name: str) -> bool:
        """Check if channel is supported."""
        return name in self._channels


# Global registry instance
channel_registry = ChannelRegistry()


def get_channel(name: str, **kwargs) -> BaseChannel:
    """Get channel instance from global registry."""
    return channel_registry.get_channel(name, **kwargs)


def get_channel_class(name: str) -> Type[BaseChannel]:
    """Get channel class from global registry."""
    return channel_registry.get_channel_class(name)


def list_available_channels() -> list[str]:
    """List all available channels."""
    return channel_registry.list_channels()


def is_channel_supported(name: str) -> bool:
    """Check if channel is supported."""
    return channel_registry.is_channel_supported(name)
