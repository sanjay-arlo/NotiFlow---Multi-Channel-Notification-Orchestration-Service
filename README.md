# 🚀 NotiFlow - Multi-Channel Notification Orchestration Service

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

A production-grade **FastAPI** backend service that provides a unified API for sending notifications across multiple channels (email, SMS, webhook), with intelligent channel selection, user preference management, priority queuing, retry logic, and delivery tracking.

</div>

## ✨ Features

- 🔄 **Multi-Channel Support** - Email, SMS, and Webhook notifications
- 🧠 **Intelligent Channel Selection** - Automatic best channel based on content and preferences
- 👤 **User Preferences** - Per-user channel preferences and quiet hours
- 🚀 **Priority Queuing** - Critical, high, and normal priority queues
- 🔁 **Smart Retry Logic** - Exponential backoff with jitter
- 📊 **Delivery Tracking** - Real-time delivery status and analytics
- 🛡️ **Secure** - API key authentication and HMAC signatures
- 🐳 **Docker Ready** - Complete containerized deployment
- 📈 **Monitoring** - Built-in health checks and metrics

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+
- Docker & Docker Compose (optional but recommended)

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/sanjay-arlo/NotiFlow---Multi-Channel-Notification-Orchestration-Service.git
   cd multi-channel-notification-orchestration
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   # Set your database password and API keys
   ```

4. **Start Services with Docker (Recommended)**
   ```bash
   docker-compose up -d
   ```

5. **Manual Setup (Alternative)**
   ```bash
   # Start PostgreSQL and Redis
   docker-compose up -d postgres redis
   
   # Run database migrations
   alembic upgrade head
   
   # Start API server
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Start Celery workers (in separate terminals)
   celery -A app.workers.celery_app worker --queue=critical --loglevel=warning
   celery -A app.workers.celery_app worker --queue=email --concurrency=4
   celery -A app.workers.celery_app worker --queue=sms --concurrency=2
   celery -A app.workers.celery_app worker --queue=webhook --concurrency=4
   celery -A app.workers.celery_app worker --queue=default --concurrency=2
   
   # Start Celery beat scheduler
   celery -A app.workers.celery_app beat --loglevel=info
   ```

### 🌐 Access Points

Once running, you can access:

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Flower Monitoring**: http://localhost:5555 (if started)

## 📁 Project Structure

```
multi-channel-notification-orchestration/
├── app/                          # Main application package
│   ├── core/                    # Core configuration and utilities
│   │   ├── config.py           # Pydantic Settings
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── security.py         # Security utilities
│   │   └── constants.py        # Constants and enums
│   ├── api/                      # FastAPI routes and dependencies
│   │   ├── deps.py            # Dependency injection
│   │   ├── router.py          # Main router aggregation
│   │   └── routes/           # API endpoints
│   ├── db/                       # Database models and sessions
│   │   ├── models/            # SQLAlchemy models
│   │   ├── base.py            # Base classes
│   │   └── session.py         # Async session factory
│   ├── schemas/                   # Pydantic request/response models
│   ├── services/                 # Business logic services
│   │   ├── notification_service.py
│   │   ├── preference_service.py
│   │   ├── template_service.py
│   │   ├── delivery_service.py
│   │   └── webhook_config_service.py
│   ├── channels/                 # Notification channel implementations
│   │   ├── base.py            # Abstract channel interface
│   │   ├── email_channel.py   # SMTP email channel
│   │   ├── sms_channel.py     # Twilio SMS channel
│   │   ├── webhook_channel.py # HTTP webhook channel
│   │   └── registry.py       # Channel registry
│   ├── workers/                  # Celery workers and tasks
│   │   ├── celery_app.py      # Celery configuration
│   │   ├── tasks.py           # Task definitions
│   │   ├── routers.py         # Task routing
│   │   └── schedulers.py      # Beat schedules
│   ├── repositories/              # Data access layer
│   │   ├── base.py            # Generic repository
│   │   ├── notification_repo.py
│   │   ├── user_repo.py
│   │   ├── delivery_repo.py
│   │   ├── preference_repo.py
│   │   ├── template_repo.py
│   │   └── webhook_config_repo.py
│   └── utils/                    # Utility functions
│       ├── redis_client.py     # Redis client wrapper
│       ├── id_utils.py         # ID generation
│       ├── time_utils.py       # Time utilities
│       ├── retry.py            # Retry logic
│       └── signature.py        # HMAC signatures
├── alembic/                      # Database migrations
├── docker/                        # Docker configuration
├── templates/                     # Jinja2 email templates
├── tests/                         # Test suite
├── scripts/                       # Utility scripts
├── docs/                         # Documentation
├── pyproject.toml                # Project configuration
├── requirements.txt              # Python dependencies
├── docker-compose.yml           # Docker services
└── .env.example                  # Environment template
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=notiflow
DB_USER=notiflow
DB_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM_EMAIL=noreply@yourdomain.com

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890

# API Security
SECRET_KEY=your-secret-key-here
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
```

## 📡 API Usage

### Authentication

All API endpoints require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: nf_live_abc123..." http://localhost:8000/api/v1/notifications/
```

### Quick Examples

#### Send a Simple Notification

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/send" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nf_live_abc123..." \
  -d '{
    "user_id": "user_123",
    "content": {
      "subject": "Welcome to NotiFlow!",
      "body": "Your notification service is ready to use."
    },
    "channels": ["email"],
    "priority": "normal"
  }'
```

#### Create User with Preferences

```bash
curl -X PUT "http://localhost:8000/api/v1/users/user_123" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nf_live_abc123..." \
  -d '{
    "email": "user@example.com",
    "phone": "+1234567890",
    "preferences": {
      "email": {"enabled": true, "quiet_hours": false},
      "sms": {"enabled": false, "quiet_hours": false},
      "webhook": {"enabled": true, "quiet_hours": false}
    }
  }'
```

#### Batch Send Notifications

```bash
curl -X POST "http://localhost:8000/api/v1/notifications/batch" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: nf_live_abc123..." \
  -d '{
    "notifications": [
      {
        "user_id": "user_123",
        "content": {"subject": "Hello", "body": "First message"},
        "channels": ["email"]
      },
      {
        "user_id": "user_456", 
        "content": {"subject": "Hello", "body": "Second message"},
        "channels": ["sms"]
      }
    ]
  }'
```

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/notifications/send` | Send single notification |
| `POST` | `/api/v1/notifications/batch` | Send batch notifications |
| `GET` | `/api/v1/notifications/{id}` | Get notification details |
| `PUT` | `/api/v1/users/{user_id}` | Create/update user |
| `GET` | `/api/v1/users/{user_id}/preferences` | Get user preferences |
| `POST` | `/api/v1/templates/` | Create template |
| `GET` | `/api/v1/webhooks/` | List webhook configs |
| `GET` | `/health` | Basic health check |

### 📚 Full API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## � Docker Deployment

### Quick Start with Docker

```bash
# Clone and start everything
git clone https://github.com/sanjay-arlo/NotiFlow---Multi-Channel-Notification-Orchestration-Service.git
cd multi-channel-notification-orchestration
cp .env.example .env
# Edit .env with your configuration
docker-compose up -d
```

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker-email

# Stop services
docker-compose down
```

### Production

```bash
# Use production configuration
docker-compose -f docker/docker-compose.yml up -d --build

# Scale workers for high load
docker-compose up -d --scale worker-email=3 --scale worker-sms=2
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html

# Run specific test suites
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/           # End-to-end tests

# Run with specific markers
pytest -m "not slow"        # Skip slow tests
pytest -m integration       # Only integration tests
```

## 📊 Key Features

### 🧠 Intelligent Channel Resolution
- **Auto-resolve**: Automatically selects best channel based on content and user preferences
- **Priority-based**: Critical notifications use ALL enabled channels
- **Content-aware**: Long content defaults to email
- **Fallback**: Graceful fallback when preferred channels unavailable

### 🌙 Quiet Hours Support
- **Timezone-aware**: Respects user's local timezone
- **Per-day rules**: Different quiet hours for each day of week
- **Critical bypass**: Critical notifications always bypass quiet hours
- **Smart rescheduling**: Automatically reschedules when quiet hours end

### 🔁 Smart Retry Logic
- **Channel-specific**: Different retry strategies per channel type
- **Exponential backoff**: Smart retry with jitter
- **Rate limiting**: Per-user, per-channel rate limiting
- **Error classification**: Intelligent permanent vs transient error detection

### 📝 Template System
- **Multi-channel**: Separate templates for email, SMS, webhook
- **Jinja2**: Powerful templating with validation
- **Variable schema**: Type-safe variable definitions
- **Preview mode**: Test templates before sending

## � Monitoring & Observability

### Health Checks
- `GET /health` - Basic service health
- `GET /health/ready` - Readiness check with dependencies
- `GET /health/queues` - Queue depth monitoring

### Monitoring Tools
- **Flower**: http://localhost:5555 - Celery monitoring UI
- **Structured Logging**: Request IDs for tracing
- **Metrics**: Delivery rates, queue depths, error rates

## 🔒 Security Features

- **API Key Authentication**: SHA-256 hashed API keys
- **Rate Limiting**: Per-tenant rate limiting with Redis
- **Input Validation**: Pydantic models for all inputs
- **HMAC Signatures**: Webhook payload signing
- **SQL Injection Prevention**: SQLAlchemy ORM usage

## 🚀 Performance Optimizations

- **Async Operations**: Full async/await support
- **Connection Pooling**: Database connection pooling
- **Redis Caching**: Frequently accessed data cached
- **Batch Operations**: Bulk database operations
- **Queue Separation**: Priority-based queue routing

## �️ Development

### Code Quality Tools

```bash
# Code formatting
black app/ tests/

# Linting and formatting
ruff check app/ tests/
ruff format app/ tests/

# Type checking
mypy app/

# Run pre-commit hooks
pre-commit run --all-files
```

### Project Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks
pre-commit install

# Run database migrations
alembic upgrade head
```

## 🔧 Troubleshooting

### Common Issues

1. **Database Connection**
   ```bash
   # Check PostgreSQL status
   docker-compose ps postgres
   
   # Test connection
   docker-compose exec postgres psql -U notiflow -d notiflow
   ```

2. **Redis Connection**
   ```bash
   # Test Redis connection
   docker-compose exec redis redis-cli ping
   ```

3. **Celery Workers**
   ```bash
   # Check worker status
   celery -A app.workers.celery_app status
   
   # View active tasks
   celery -A app.workers.celery_app inspect active
   ```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Guidelines

- Follow the existing code style (Black + Ruff)
- Add tests for new functionality
- Update documentation as needed
- Ensure all tests pass before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📖 **Documentation**: Check this README and `/docs` folder
- 🐛 **Issues**: [Open an issue](https://github.com/sanjay-arlo/NotiFlow---Multi-Channel-Notification-Orchestration-Service/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/sanjay-arlo/NotiFlow---Multi-Channel-Notification-Orchestration-Service/discussions)

## 🙏 Acknowledgments

Built with these amazing technologies:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit and ORM
- [Celery](https://docs.celeryproject.org/) - Distributed task queue
- [Redis](https://redis.io/) - In-memory data structure store
- [PostgreSQL](https://www.postgresql.org/) - Powerful open source database
- [Docker](https://www.docker.com/) - Container platform

---

<div align="center">

**⭐ Star this repo if it helped you!**

Made with ❤️ by the NotiFlow Team

</div>
