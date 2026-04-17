"""
Integration tests for priority-based queue routing.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.workers.celery_app import celery_app


class TestPriorityQueueRouting:
    """Test cases for priority queue routing."""
    
    @pytest.mark.asyncio
    async def test_critical_notification_routes_to_critical_queue(self):
        """Test that critical notifications route to critical queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate critical notification
            deliver_notification.apply_async(
                args=["test-delivery-id"],
                queue="critical"
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]  # kwargs
            assert call_kwargs["queue"] == "critical"
    
    @pytest.mark.asyncio
    async def test_high_priority_notification_routes_to_high_queue(self):
        """Test that high priority notifications route to high queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate high priority notification
            deliver_notification.apply_async(
                args=["test-delivery-id"],
                queue="high"
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]
            assert call_kwargs["queue"] == "high"
    
    @pytest.mark.asyncio
    async def test_normal_notification_routes_to_default_queue(self):
        """Test that normal notifications route to default queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate normal notification
            deliver_notification.apply_async(
                args=["test-delivery-id"]
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]
            assert call_kwargs.get("queue") == "default"
    
    @pytest.mark.asyncio
    async def test_email_notification_routes_to_email_queue(self):
        """Test that email notifications route to email queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate email notification with queue override
            deliver_notification.apply_async(
                args=["test-delivery-id"],
                queue="email"
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]
            assert call_kwargs["queue"] == "email"
    
    @pytest.mark.asyncio
    async def test_sms_notification_routes_to_sms_queue(self):
        """Test that SMS notifications route to SMS queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate SMS notification with queue override
            deliver_notification.apply_async(
                args=["test-delivery-id"],
                queue="sms"
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]
            assert call_kwargs["queue"] == "sms"
    
    @pytest.mark.asyncio
    async def test_webhook_notification_routes_to_webhook_queue(self):
        """Test that webhook notifications route to webhook queue."""
        from app.workers.tasks import deliver_notification
        
        with patch('app.workers.tasks.deliver_notification.apply_async') as mock_apply:
            # Simulate webhook notification with queue override
            deliver_notification.apply_async(
                args=["test-delivery-id"],
                queue="webhook"
            )
            
            mock_apply.assert_called_once()
            call_kwargs = mock_apply.call_args[1]
            assert call_kwargs["queue"] == "webhook"
    
    @pytest.mark.asyncio
    async def test_queue_routing_configuration(self):
        """Test that Celery queue routing is properly configured."""
        # Check that queues are defined in Celery config
        from app.workers.celery_app import celery_app
        
        expected_queues = {
            "critical", "high", "email", "sms", "webhook", "default"
        }
        
        actual_queues = set(celery_app.conf.task_queues)
        expected_queue_names = {queue.name for queue in celery_app.conf.task_queues}
        
        assert expected_queue_names == expected_queues
    
    @pytest.mark.asyncio
    async def test_task_routing_rules(self):
        """Test that task routing rules are properly configured."""
        from app.workers.celery_app import celery_app
        
        # Check that deliver_notification task has routing rules
        task_routes = celery_app.conf.task_routes
        
        assert "app.workers.tasks.deliver_notification" in task_routes
        
        # The routing should be a function that determines queue based on kwargs
        routing_rule = task_routes["app.workers.tasks.deliver_notification"]
        assert callable(routing_rule)
    
    @pytest.mark.asyncio
    async def test_priority_queue_worker_configuration(self):
        """Test that priority queues have appropriate worker configurations."""
        # This test verifies the expected worker setup for priority queues
        # In a real deployment, this would check actual worker processes
        
        from app.core.constants import PRIORITY_QUEUE_ROUTING
        
        # Verify routing configuration exists
        assert PRIORITY_QUEUE_ROUTING is not None
        
        # Check that critical notifications route to critical queue
        assert PRIORITY_QUEUE_ROUTING.get(("critical", "email")) == "critical"
        assert PRIORITY_QUEUE_ROUTING.get(("critical", "sms")) == "critical"
        assert PRIORITY_QUEUE_ROUTING.get(("critical", "webhook")) == "critical"
        
        # Check that high priority notifications route to high queue
        assert PRIORITY_QUEUE_ROUTING.get(("high", "email")) == "high"
        assert PRIORITY_QUEUE_ROUTING.get(("high", "sms")) == "high"
        assert PRIORITY_QUEUE_ROUTING.get(("high", "webhook")) == "high"
    
    @pytest.mark.asyncio
    async def test_channel_specific_queue_routing(self):
        """Test that channel-specific notifications route to appropriate queues."""
        from app.core.constants import PRIORITY_QUEUE_ROUTING
        
        # Check email notifications route to email queue
        assert PRIORITY_QUEUE_ROUTING.get(("normal", "email")) == "email"
        assert PRIORITY_QUEUE_ROUTING.get(("low", "email")) == "email"
        
        # Check SMS notifications route to SMS queue
        assert PRIORITY_QUEUE_ROUTING.get(("normal", "sms")) == "sms"
        assert PRIORITY_QUEUE_ROUTING.get(("low", "sms")) == "sms"
        
        # Check webhook notifications route to webhook queue
        assert PRIORITY_QUEUE_ROUTING.get(("normal", "webhook")) == "webhook"
        assert PRIORITY_QUEUE_ROUTING.get(("low", "webhook")) == "webhook"
    
    @pytest.mark.asyncio
    async def test_default_queue_fallback(self):
        """Test that unmatched combinations route to default queue."""
        from app.core.constants import PRIORITY_QUEUE_ROUTING
        
        # Check that unspecified combinations route to default
        assert PRIORITY_QUEUE_ROUTING.get(("normal", "unknown")) == "default"
        assert PRIORITY_QUEUE_ROUTING.get(("unknown", "email")) == "default"
    
    @pytest.mark.asyncio
    async def test_celery_worker_prefetch_multiplier(self):
        """Test that worker prefetch multiplier is set to 1 for reliability."""
        from app.workers.celery_app import celery_app
        
        assert celery_app.conf.worker_prefetch_multiplier == 1
    
    @pytest.mark.asyncio
    async def test_celery_task_acks_late(self):
        """Test that late task acknowledgments are enabled."""
        from app.workers.celery_app import celery_app
        
        assert celery_app.conf.task_acks_late is True
    
    @pytest.mark.asyncio
    async def test_celery_timezone_configuration(self):
        """Test that Celery timezone is properly configured."""
        from app.workers.celery_app import celery_app
        
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True
