# NotiFlow — Multi-Channel Notification Orchestration Service

A production-oriented **FastAPI prototype** for orchestrating notifications across email, SMS and webhooks with user preferences, quiet hours, priority queues, retries and delivery tracking.

> **Scope:** portfolio / prototype project. It is not presented as a production service or audited security implementation.

## What it demonstrates

- Multi-channel notification delivery
- User channel preferences and quiet hours
- Priority-based Celery queues
- Retry handling with backoff/jitter
- Delivery-status persistence and tracking
- API-key authentication and webhook signing
- PostgreSQL + Redis integration
- Docker-based local deployment
- Unit and integration testing

## Architecture

```text
Client
  │
  ▼
FastAPI
  │
  ├── PostgreSQL  ← application state
  ├── Redis       ← queue/cache coordination
  └── Celery      ← asynchronous delivery
          │
          ├── Email
          ├── SMS
          └── Webhook
```

## Repository structure

```text
.
├── app/
│   ├── api/          # HTTP routes and dependencies
│   ├── channels/     # Email, SMS and webhook adapters
│   ├── core/         # Configuration, security and constants
│   ├── db/           # SQLAlchemy models and sessions
│   ├── repositories/ # Database access layer
│   ├── schemas/      # Pydantic request/response models
│   ├── services/     # Application/business logic
│   └── workers/      # Celery tasks and routing
├── alembic/          # Database migrations
├── docker/            # Dockerfiles and compose configuration
├── scripts/           # Seed/simulation/test helpers
├── templates/         # Email templates
├── tests/             # Unit and integration tests
├── .env.example       # Configuration template
├── .gitignore
├── pyproject.toml
└── requirements.txt
```

## Quick start

The repository is designed to run with Docker Compose so PostgreSQL and Redis do not need to be installed separately.

```bash
git clone https://github.com/sanjay-arlo/NotiFlow---Multi-Channel-Notification-Orchestration-Service.git
cd NotiFlow---Multi-Channel-Notification-Orchestration-Service
cp .env.example .env
# Edit .env with local credentials and service configuration
docker compose -f docker/docker-compose.yml up -d
```

Run migrations when the containers are ready:

```bash
alembic upgrade head
```

For a local Python run, install dependencies and start the API with:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI is available at `http://localhost:8000/docs` when the API is running.

## Configuration

Secrets and environment-specific settings belong in `.env` or an external secret manager. Do **not** commit real credentials, API keys, SMTP passwords or provider tokens.

Example configuration is provided in `.env.example`.

## Testing

```bash
pytest
pytest tests/unit/
pytest tests/integration/
```

The repository contains both unit and integration test suites covering notification flows, preferences, retries, priority queues, quiet hours, delivery tracking and channel adapters.

## Important implementation notes

- Provider credentials are configuration inputs, not source-code constants.
- External delivery providers may require real credentials and network access for end-to-end testing.
- Celery/Redis behaviour depends on the local worker and broker configuration.
- “Delivery” in local simulation does not prove successful delivery through a real provider.

## Security posture

The project includes API-key authentication, HMAC webhook signing, Pydantic validation and ORM-based database access. These are implementation features of the prototype; they should not be interpreted as a complete production security review.

For portfolio use, treat the project as a **production-oriented architecture exercise** and evaluate deployment, threat modelling, secret management, dependency scanning and operational controls separately.

## License

MIT License.

## Author

**Sanjay Arlo**  
Business Analyst / Data Analyst | Software & Analytics Projects
