"""
Integration tests for delivery tracking and status updates.
"""

import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.api.routes.deliveries import router
from app.core.constants import DeliveryStatus
from app.db.models.delivery import Delivery
from app.db.models.notification import Notification


class TestDeliveryTrackingAPI:
    """Integration tests for delivery tracking endpoints."""
    
    @pytest.fixture
    def api_client(self, test_client):
        """Create API client for testing."""
        return TestClient(app=router, base_url="http://test")
    
    @pytest.fixture
    def mock_tenant(self):
        """Mock tenant for API key authentication."""
        return {
            "id": "test-tenant-id",
            "name": "Test Tenant",
            "api_key_hash": "test-hash",
            "api_key_prefix": "nf_live_",
            "is_active": True
        }
    
    @pytest.fixture
    def mock_delivery(self):
        """Mock delivery for testing."""
        return Delivery(
            id="test-delivery-id",
            notification_id="test-notification-id",
            channel="email",
            destination="test@example.com",
            status=DeliveryStatus.SENT,
            provider_id="test-provider-id",
            sent_at="2024-01-15T10:00:00Z",
            attempts=1
        )
    
    @pytest.mark.asyncio
    async def test_get_delivery_success(
        self,
        api_client,
        mock_tenant,
        mock_delivery
    ):
        """Test getting delivery details successfully."""
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.get_delivery.return_value = mock_delivery
                
                response = await api_client.get("/test-delivery-id")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test-delivery-id"
        assert data["notification_id"] == "test-notification-id"
        assert data["channel"] == "email"
        assert data["status"] == "sent"
        assert data["destination"] == "test@example.com"
        assert data["provider_id"] == "test-provider-id"
        assert data["attempts"] == 1
    
    @pytest.mark.asyncio
    async def test_get_delivery_not_found(
        self,
        api_client,
        mock_tenant
    ):
        """Test getting non-existent delivery."""
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.get_delivery.return_value = None
                
                response = await api_client.get("/non-existent-id")
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_list_deliveries_success(
        self,
        api_client,
        mock_tenant
    ):
        """Test listing deliveries successfully."""
        mock_deliveries = [
            Delivery(
                id="delivery-1",
                notification_id="notif-1",
                channel="email",
                status="delivered",
                destination="user1@example.com"
            ),
            Delivery(
                id="delivery-2",
                notification_id="notif-2",
                channel="sms",
                status="failed",
                destination="+1234567890"
            )
        ]
        
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.delivery_repo.get_deliveries_by_date_range.return_value = mock_deliveries
                
                response = await api_client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        
        # Check first delivery
        delivery_1 = data["items"][0]
        assert delivery_1["id"] == "delivery-1"
        assert delivery_1["channel"] == "email"
        assert delivery_1["status"] == "delivered"
        
        # Check second delivery
        delivery_2 = data["items"][1]
        assert delivery_2["id"] == "delivery-2"
        assert delivery_2["channel"] == "sms"
        assert delivery_2["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_list_deliveries_with_filters(
        self,
        api_client,
        mock_tenant
    ):
        """Test listing deliveries with filters."""
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.delivery_repo.get_deliveries_by_date_range.return_value = []
                
                response = await api_client.get("/?status=delivered&channel=email")
        
        assert response.status_code == 200
        
        # Verify service was called with filters
        mock_service.delivery_repo.get_deliveries_by_date_range.assert_called_once()
        call_args = mock_service.delivery_repo.get_deliveries_by_date_range.call_args
        assert call_args[1]["channel"] == "email"
        assert call_args[1]["status"] == "delivered"
    
    @pytest.mark.asyncio
    async def test_get_delivery_stats_success(
        self,
        api_client,
        mock_tenant
    ):
        """Test getting delivery statistics successfully."""
        mock_stats = {
            "by_channel": {
                "email": {"total": 100, "delivered": 95, "failed": 5},
                "sms": {"total": 50, "delivered": 45, "failed": 5}
            },
            "by_status": {
                "delivered": 140,
                "failed": 10,
                "sent": 150
            },
            "total": 150
        }
        
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.get_delivery_stats.return_value = mock_stats
                
                response = await api_client.get("/stats")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 150
        assert data["by_channel"]["email"]["delivered"] == 95
        assert data["by_status"]["delivered"] == 140
    
    @pytest.mark.asyncio
    async def test_retry_failed_deliveries_success(
        self,
        api_client,
        mock_tenant
    ):
        """Test retrying failed deliveries."""
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.get_deliveries_for_retry.return_value = [
                    Delivery(
                        id="retry-delivery-1",
                        status="failed",
                        attempt_count=1,
                        max_attempts=3
                    )
                ]
                
                response = await api_client.post("/retry")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["retryable_deliveries"] == 1
        assert data["message"] == "Retry process initiated"
        
        # Verify service was called
        mock_service.get_deliveries_for_retry.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_delivery_with_events(
        self,
        api_client,
        mock_tenant
    ):
        """Test getting delivery with events included."""
        mock_events = [
            {
                "id": 1,
                "from_status": "pending",
                "to_status": "sent",
                "event_type": "status_change",
                "details": {"provider_id": "test-id"},
                "created_at": "2024-01-15T10:05:00Z"
            }
        ]
        
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_delivery = Delivery(
                    id="test-delivery-id",
                    status="sent",
                    events=mock_events
                )
                mock_service.get_delivery.return_value = mock_delivery
                
                response = await api_client.get("/test-delivery-id")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test-delivery-id"
        assert data["status"] == "sent"
    
    @pytest.mark.asyncio
    async def test_list_deliveries_pagination(
        self,
        api_client,
        mock_tenant
    ):
        """Test delivery listing with pagination."""
        mock_deliveries = [Delivery() for _ in range(25)]  # 25 deliveries
        
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.delivery_repo.get_deliveries_by_date_range.return_value = mock_deliveries
                
                response = await api_client.get("/?page=1&per_page=10")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert data["total"] == 25
        assert len(data["items"]) == 10  # First page
    
    @pytest.mark.asyncio
    async def test_list_deliveries_date_range_filter(
        self,
        api_client,
        mock_tenant
    ):
        """Test delivery listing with date range filter."""
        from datetime import datetime, timedelta
        
        from_date = (datetime.utcnow() - timedelta(days=7)).isoformat()
        to_date = datetime.utcnow().isoformat()
        
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                mock_service.delivery_repo.get_deliveries_by_date_range.return_value = []
                
                response = await api_client.get(f"/?from_date={from_date}&to_date={to_date}")
        
        assert response.status_code == 200
        
        # Verify service was called with date range
        mock_service.delivery_repo.get_deliveries_by_date_range.assert_called_once()
        call_args = mock_service.delivery_repo.get_deliveries_by_date_range.call_args
        assert "from_date" in call_args[1]
        assert "to_date" in call_args[1]
    
    @pytest.mark.asyncio
    async def test_delivery_error_handling(
        self,
        api_client,
        mock_tenant
    ):
        """Test error handling in delivery endpoints."""
        with patch('app.api.routes.deliveries.get_current_tenant', return_value=mock_tenant):
            with patch('app.api.routes.deliveries.get_delivery_service') as mock_service:
                # Simulate service error
                mock_service.get_delivery.side_effect = Exception("Database error")
                
                response = await api_client.get("/test-id")
        
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(
        self,
        api_client
    ):
        """Test unauthorized access to delivery endpoints."""
        response = await api_client.get("/test-id")
        
        assert response.status_code == 401
