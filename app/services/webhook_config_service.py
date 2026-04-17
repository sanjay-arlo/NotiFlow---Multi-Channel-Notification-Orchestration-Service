"""
Webhook configuration management service.
"""

from typing import Dict, List, Optional

from app.core.exceptions import WebhookConfigNotFoundError
from app.db.models.webhook_config import WebhookConfig
from app.repositories.webhook_config_repo import WebhookConfigRepository


class WebhookConfigService:
    """Service for managing webhook configurations."""
    
    def __init__(self, webhook_config_repo: WebhookConfigRepository):
        self.webhook_config_repo = webhook_config_repo
    
    async def create_webhook_config(
        self,
        tenant_id: str,
        name: str,
        url: str,
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        timeout_seconds: int = 10
    ) -> WebhookConfig:
        """Create a new webhook configuration."""
        config_data = {
            "tenant_id": tenant_id,
            "name": name,
            "url": url,
            "secret": secret,
            "headers": headers or {},
            "max_retries": max_retries,
            "timeout_seconds": timeout_seconds,
            "is_active": True
        }
        
        return await self.webhook_config_repo.create(config_data)
    
    async def get_webhook_config(
        self,
        webhook_id: str
    ) -> Optional[WebhookConfig]:
        """Get webhook configuration by ID."""
        webhook_config = await self.webhook_config_repo.get(webhook_id)
        if not webhook_config:
            raise WebhookConfigNotFoundError(webhook_id)
        return webhook_config
    
    async def get_webhook_configs(
        self,
        tenant_id: str,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get webhook configurations for a tenant."""
        return await self.webhook_config_repo.get_multi_by_tenant(
            tenant_id, active_only, skip, limit
        )
    
    async def update_webhook_config(
        self,
        webhook_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        max_retries: Optional[int] = None,
        timeout_seconds: Optional[int] = None
    ) -> Optional[WebhookConfig]:
        """Update webhook configuration."""
        return await self.webhook_config_repo.update_config(
            webhook_id, name, url, secret, headers, max_retries, timeout_seconds
        )
    
    async def delete_webhook_config(self, webhook_id: str) -> bool:
        """Delete webhook configuration."""
        webhook_config = await self.webhook_config_repo.delete(webhook_id)
        return webhook_config is not None
    
    async def test_webhook_config(
        self,
        webhook_id: str
    ) -> Dict[str, any]:
        """Test webhook configuration with a test payload."""
        webhook_config = await self.get_webhook_config(webhook_id)
        
        test_payload = {
            "test": True,
            "webhook_id": str(webhook_config.id),
            "name": webhook_config.name,
            "url": webhook_config.url,
            "timestamp": "2024-01-15T10:00:00Z"
        }
        
        try:
            # Import here to avoid circular imports
            from app.channels.registry import get_channel
            
            # Create webhook channel with config
            webhook_channel = get_channel(
                "webhook",
                webhook_config={
                    "secret": webhook_config.secret,
                    "headers": webhook_config.headers,
                    "max_retries": webhook_config.max_retries,
                    "timeout_seconds": webhook_config.timeout_seconds
                }
            )
            
            # Create mock delivery for testing
            from app.db.models.delivery import Delivery
            from app.db.models.notification import Notification
            from app.utils.id_utils import generate_delivery_id, generate_notification_id
            
            mock_notification = Notification(
                id=generate_notification_id(),
                title="Test Webhook",
                body="This is a test webhook notification",
                status="test"
            )
            
            mock_delivery = Delivery(
                id=generate_delivery_id(),
                notification_id=mock_notification.id,
                channel="webhook",
                destination=webhook_config.url,
                status="test"
            )
            
            # Send test webhook
            result = await webhook_channel.send(mock_notification, mock_delivery)
            
            if result.success:
                # Record success
                await self.webhook_config_repo.record_success(webhook_id)
                
                return {
                    "success": True,
                    "message": "Webhook test successful",
                    "provider_id": result.provider_id,
                    "response": result.raw_response
                }
            else:
                # Record failure
                await self.webhook_config_repo.record_failure(webhook_id)
                
                return {
                    "success": False,
                    "message": "Webhook test failed",
                    "error": result.error,
                    "provider_response": result.raw_response
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": "Webhook test error",
                "error": str(e)
            }
    
    async def get_healthy_webhooks(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get healthy webhook configurations."""
        return await self.webhook_config_repo.get_healthy_webhooks(
            tenant_id, skip, limit
        )
    
    async def get_unhealthy_webhooks(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Get unhealthy webhook configurations."""
        return await self.webhook_config_repo.get_unhealthy_webhooks(
            tenant_id, skip, limit
        )
    
    async def activate_webhook_config(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Activate webhook configuration."""
        return await self.webhook_config_repo.activate_webhook(webhook_id)
    
    async def deactivate_webhook_config(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Deactivate webhook configuration."""
        return await self.webhook_config_repo.deactivate_webhook(webhook_id)
    
    async def reset_failure_count(self, webhook_id: str) -> Optional[WebhookConfig]:
        """Reset failure count for webhook configuration."""
        return await self.webhook_config_repo.reset_failure_count(webhook_id)
    
    async def search_webhook_configs(
        self,
        tenant_id: str,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[WebhookConfig]:
        """Search webhook configurations."""
        return await self.webhook_config_repo.search_webhook_configs(
            query, tenant_id, skip, limit
        )
    
    def get_webhook_summary(self, webhook_config: WebhookConfig) -> Dict[str, any]:
        """Get summary of webhook configuration."""
        return {
            "id": str(webhook_config.id),
            "name": webhook_config.name,
            "url": webhook_config.url,
            "has_secret": webhook_config.has_secret(),
            "max_retries": webhook_config.max_retries,
            "timeout_seconds": webhook_config.timeout_seconds,
            "is_active": webhook_config.is_active,
            "is_healthy": webhook_config.is_healthy(),
            "failure_count": webhook_config.failure_count,
            "last_success_at": webhook_config.last_success_at.isoformat() if webhook_config.last_success_at else None,
            "last_failure_at": webhook_config.last_failure_at.isoformat() if webhook_config.last_failure_at else None,
            "headers": webhook_config.headers,
            "created_at": webhook_config.created_at.isoformat(),
            "updated_at": webhook_config.updated_at.isoformat()
        }
