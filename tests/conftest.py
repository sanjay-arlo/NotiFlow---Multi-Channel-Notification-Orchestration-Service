"""
Pytest configuration and fixtures for NotiFlow testing.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.models import *  # Import all models
from app.utils.redis_client import redis_client


# Configure pytest-asyncio
pytest_asyncio.configure(
    asyncio_default_loop_factory=asyncio.DefaultEventLoopPolicy.new_event_loop_policy,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database for each test."""
    # Use in-memory SQLite for testing
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    TestSessionLocal = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with TestSessionLocal() as session:
        yield session
    
    await test_engine.dispose()


@pytest.fixture
async def test_redis():
    """Redis fixture for testing."""
    await redis_client.connect()
    yield redis_client
    await redis_client.disconnect()


@pytest.fixture
def test_client() -> TestClient:
    """Create a test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_tenant():
    """Sample tenant data for testing."""
    return {
        "name": "Test Tenant",
        "api_key_hash": "test_hash",
        "api_key_prefix": "nf_live_",
        "is_active": True,
        "rate_limit": 1000
    }


@pytest.fixture
def sample_user():
    """Sample user data for testing."""
    return {
        "external_id": "test_user_123",
        "email": "test@example.com",
        "phone": "+1234567890",
        "timezone": "UTC",
        "display_name": "Test User",
        "metadata": {"department": "Engineering"}
    }


@pytest.fixture
def sample_notification():
    """Sample notification data for testing."""
    return {
        "title": "Test Notification",
        "body": "This is a test notification.",
        "priority": "normal",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_template():
    """Sample template data for testing."""
    return {
        "name": "Test Template",
        "slug": "test-template",
        "email_subject": "Test: {{ subject }}",
        "email_body": "<h1>{{ title }}</h1><p>{{ content }}</p>",
        "sms_body": "{{ title }}: {{ content }}",
        "variables_schema": [
            {"name": "subject", "type": "string", "required": True},
            {"name": "content", "type": "string", "required": True}
        ],
        "category": "transactional",
        "description": "Test template"
    }


@pytest.fixture
def sample_webhook_config():
    """Sample webhook config data for testing."""
    return {
        "name": "Test Webhook",
        "url": "https://example.com/webhook",
        "secret": "test_secret",
        "headers": {"Content-Type": "application/json"},
        "max_retries": 3,
        "timeout_seconds": 10
    }


@pytest.fixture
def mock_api_key():
    """Mock API key for testing."""
    return "nf_live_test123456789012345678901234567890"


@pytest.fixture
def mock_tenant_id():
    """Mock tenant ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_user_id():
    """Mock user ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440001"


@pytest.fixture
def mock_notification_id():
    """Mock notification ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440002"


@pytest.fixture
def mock_delivery_id():
    """Mock delivery ID for testing."""
    return "550e8400-e29b-41d4-a716-446655440003"


# Override settings for testing
@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for testing."""
    settings.debug = True
    settings.testing = True
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.redis_url = "redis://localhost:6379/1"
    settings.secret_key = "test-secret-key"
    settings.cors_origins = ["*"]
