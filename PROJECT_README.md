# Virtual Assistant & Scheduler Automation

**AI-powered email management and task scheduling engine combining conversational assistance with reliable task automation.**

## Project Overview

This is a full-stack application that:

- **Manages inbox intelligently**: AI-driven email classification, flagging, and pre-approved auto-replies
- **Schedules and automates tasks**: Reliable background job execution with Celery + Redis
- **Analyzes data on-demand**: CSV uploads with LLM-powered insights and analysis
- **Provides conversational assistance**: Natural language interface powered by LangChain + OpenAI

### Status: Phase A - MVP Scoping & Repository Initialization ✅

**Core Files Created:**

- ✅ Backend scaffold (FastAPI, SQLAlchemy ORM, Celery workers)
- ✅ Docker Compose setup (PostgreSQL, Redis, containers)
- ✅ Database models (User, EmailAccount, EmailJob, AutoReplyRule, etc.)
- ✅ Configuration system (Pydantic Settings for env vars)
- ✅ Security utilities (JWT, password hashing, token encryption)
- ✅ Test structure (pytest, FastAPI TestClient)

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API key (for LLM features)
- Gmail OAuth2 credentials (optional, for email integration)

### Local Development (Docker)

1. **Clone and setup:**

   ```bash
   cd "Virtual Assistant & Scheduler Automation"
   python init.py  # Initialize directories
   cp .env.example .env  # Create local env file
   ```

2. **Update .env with your credentials:**

   ```bash
   # Add your OpenAI API key
   OPENAI_API_KEY=sk-...

   # Add Gmail OAuth credentials (optional)
   GMAIL_CLIENT_ID=...
   GMAIL_CLIENT_SECRET=...
   ```

3. **Start the stack:**

   ```bash
   docker-compose up -d
   ```

4. **Access the application:**

   - API: http://localhost:8000
   - FastAPI Docs (Swagger UI): http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health

5. **View logs:**
   ```bash
   docker-compose logs -f backend
   docker-compose logs -f worker
   ```

### Local Development (Native Python)

1. **Create virtual environment:**

   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # or: source venv/bin/activate  # macOS/Linux
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up local PostgreSQL and Redis** (or use containers separately)

4. **Run the application:**

   ```bash
   # Terminal 1: FastAPI backend
   cd backend
   python -m uvicorn main:app --reload

   # Terminal 2: Celery worker
   cd backend
   celery -A worker.celery_config worker --loglevel=info
   ```

## Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Pydantic Settings for configuration
├── models.py              # SQLAlchemy ORM models
├── database.py            # Database session factory
├── api/                   # API endpoints
│   ├── auth.py           # Authentication (to be created)
│   ├── email.py          # Email management (to be created)
│   └── jobs.py           # Job management (to be created)
├── connectors/            # Email provider adapters
│   ├── gmail.py          # Gmail integration (to be created)
│   └── outlook.py        # Outlook integration (to be created)
├── llm/                   # LLM utilities
│   ├── classifier.py     # Email classification (to be created)
│   └── analyzer.py       # Data analysis (to be created)
├── security/
│   ├── encryption.py     # Token encryption & JWT handling
│   └── __init__.py
├── storage/               # S3/vector store utilities
│   └── __init__.py
├── engine/                # Rules engine for auto-reply DSL
│   └── __init__.py
└── worker/                # Celery task workers
    ├── celery_config.py  # Celery configuration
    ├── tasks/            # Task definitions
    └── __init__.py

frontend/                  # Next.js + TailwindCSS (scaffolding)
├── pages/
├── components/
├── lib/
└── styles/

tests/                     # Pytest test suite
├── test_api.py
├── test_models.py
└── __init__.py

docs/                      # Documentation
├── ARCHITECTURE.md       # System design & data flow
└── API_REFERENCE.md      # Endpoint documentation

docker-compose.yml         # Multi-container orchestration
Dockerfile                 # Multi-stage backend container
Makefile                   # Development commands
requirements.txt           # Python dependencies
.env.example              # Environment variable template
.env                      # Local development config (gitignored)
```

## Technology Stack

| Component             | Technology            | Rationale                            |
| --------------------- | --------------------- | ------------------------------------ |
| **Backend Framework** | FastAPI               | Modern async, fast development       |
| **ORM**               | SQLAlchemy            | Flexible, powerful schema management |
| **Database**          | PostgreSQL            | Reliable, feature-rich               |
| **Task Queue**        | Celery                | Battle-tested async tasks            |
| **Message Broker**    | Redis                 | Fast, in-memory caching              |
| **LLM**               | OpenAI GPT-3.5 Turbo  | Cost-effective, reliable             |
| **LLM Framework**     | LangChain             | Prompt chains, memory, RAG           |
| **Vector Store**      | FAISS (MVP)           | In-process, no external deps         |
| **Frontend**          | Next.js + TailwindCSS | Fast dev, mobile-ready               |
| **Auth**              | OAuth2 + JWT          | Secure, provider-agnostic            |
| **Encryption**        | Fernet (AES-256)      | Token encryption at rest             |
| **Containerization**  | Docker                | Consistent environments              |
| **Testing**           | Pytest                | Comprehensive test coverage          |

## Core Features (MVP - Phase A)

### 1. Intelligent Email Management

- **Classification**: AI categorizes emails (important, followup, spam, etc.)
- **Flagging**: Automatic flagging of priority emails
- **Auto-replies**: Pre-approved replies for classified emails
- **Multi-provider**: Gmail, Outlook (extensible adapter pattern)

### 2. On-Demand Data Analysis

- **File upload**: CSV/Excel to S3
- **LLM analysis**: Ask questions about your data
- **Results**: Summaries, insights, forecasts
- **Async processing**: Long-running jobs via Celery

### 3. Background Task Scheduling

- **Email sync**: Periodic inbox fetching and processing
- **Auto-replies**: Trigger based on rules
- **Data analysis**: On-demand and scheduled
- **Extensible**: Add custom tasks easily

### 4. Security & Compliance

- **OAuth2**: Secure provider authorization
- **Encryption**: Tokens encrypted at rest (Fernet AES-256)
- **Audit logging**: Track all operations
- **GDPR ready**: Data deletion, privacy controls

## Development Commands

```bash
# Setup
make install              # Create venv and install dependencies
make dev                  # Start full development stack

# Docker
make build               # Build Docker images
make up                  # Start containers
make down                # Stop containers
make logs                # View container logs

# Testing
make test                # Run pytest with coverage
make lint                # Run code linting
make format              # Format code with black

# Database
make db-migrate          # Run migrations (placeholder)
make db-seed             # Seed sample data (placeholder)

# Cleanup
make docker-clean        # Remove containers and volumes
```

## API Endpoints (Phase A)

### System

- `GET /health` - Health check
- `GET /` - API root

### To Be Implemented (Phase B)

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/gmail/authorize` - Gmail OAuth flow
- `GET /api/v1/email/jobs` - List email jobs
- `POST /api/v1/email/rules` - Create auto-reply rule
- `POST /api/v1/analysis/jobs` - Start data analysis
- `GET /api/v1/analysis/jobs/{id}` - Get analysis results

See [API_REFERENCE.md](docs/API_REFERENCE.md) for full documentation.

## Database Schema

### Users

- `id`: UUID primary key
- `email`: Unique email address
- `username`: Unique username
- `hashed_password`: Bcrypt hash
- `is_active`, `is_superuser`: Account status flags
- Relationships: `email_accounts`, `email_jobs`, `rules`, `tasks`, `data_analysis_jobs`

### Email Accounts

- `id`: UUID primary key
- `user_id`: Foreign key to User
- `provider`: 'gmail', 'outlook', etc.
- `email`: Connected email address
- `access_token_encrypted`: Encrypted OAuth token
- `refresh_token_encrypted`: Encrypted refresh token
- `token_expires_at`: Token expiration timestamp
- `is_active`, `last_sync`: Status fields

### Email Jobs

- `id`: UUID primary key
- `user_id`, `email_account_id`: Foreign keys
- `email_id`, `subject`, `sender`, `body`: Email metadata
- `classification`: AI-determined category
- `is_flagged`, `auto_reply_sent`, `is_processed`: Status flags
- Timestamps: `created_at`, `processed_at`

### Auto Reply Rules

- `id`: UUID primary key
- `user_id`: Foreign key
- `name`, `description`: Rule identification
- `rule_config`: JSON DSL for conditions & actions
- `is_active`: Enable/disable rule

### Scheduled Tasks

- `id`: UUID primary key
- `user_id`: Foreign key
- `task_type`: 'email_sync', 'data_analysis', etc.
- `schedule`: Cron expression or interval
- `is_active`, `metadata`: Configuration

### Data Analysis Jobs

- `id`: UUID primary key
- `user_id`: Foreign key
- `name`, `description`: Job metadata
- `file_path`: S3 path to uploaded file
- `analysis_type`: 'summary', 'insights', 'forecast'
- `prompt`: User's analysis request
- `status`: 'pending', 'processing', 'completed', 'failed'
- `result`, `error_message`: Outcomes
- Timestamps: `created_at`, `started_at`, `completed_at`

## Environment Variables

See `.env.example` for all required variables:

```bash
# Backend API
FASTAPI_ENV=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=va_scheduler

# Redis / Celery
REDIS_HOST=redis
CELERY_BROKER_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Gmail OAuth2
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...

# Encryption
ENCRYPTION_KEY=...  # Fernet key
SECRET_KEY=...      # JWT secret
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_api.py::test_health_check -v
```

Current test status:

- ✅ Health check endpoint
- ✅ Model creation and relationships
- ✅ Token encryption/decryption
- 🟡 Auth endpoints (Phase B)
- 🟡 Email processing (Phase B)
- 🟡 Data analysis (Phase B)

## Deployment

### Production Considerations

1. **Environment**: Deploy with `FASTAPI_ENV=production`
2. **Secrets**: Use secure secret management (AWS Secrets Manager, HashiCorp Vault)
3. **Database**: Managed PostgreSQL (AWS RDS, DigitalOcean, etc.)
4. **Redis**: Managed Redis cluster
5. **Storage**: S3 or DigitalOcean Spaces for file uploads
6. **Monitoring**: Sentry for error tracking
7. **Scaling**: Use Kubernetes or container orchestration

See [IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md) for deployment details.

## Development Phases

### Phase A: MVP Scoping & Repo Init ✅ (Current)

- ✅ Project scaffold
- ✅ Core models & database
- ✅ Configuration system
- ✅ Docker setup
- 🔄 Basic API endpoints
- 🔄 Test structure

### Phase B: Core Feature Implementation (Next)

- Authentication & OAuth2
- Email connector adapters
- Email classification & auto-reply logic
- Celery task implementation
- Data analysis workflow
- API endpoints for all features

### Phase C: Hardening & Polish

- Comprehensive test coverage
- Error handling & validation
- Rate limiting & security
- Logging & monitoring
- UI/UX refinement

### Phase D: Scale & Optimize

- Performance optimization
- Horizontal scaling
- Advanced caching
- Load testing
- Production deployment

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes and add tests
3. Run `make lint` and `make format`
4. Commit: `git commit -am 'Add feature'`
5. Push: `git push origin feature/your-feature`
6. Open a pull request

## Troubleshooting

### Container Issues

```bash
# Check logs
docker-compose logs backend
docker-compose logs worker

# Rebuild containers
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d

# Access container shell
docker exec -it va-scheduler-backend /bin/bash
```

### Database Issues

```bash
# Connect to PostgreSQL
docker exec -it va-scheduler-postgres psql -U postgres -d va_scheduler

# Reset database
docker-compose down -v
docker-compose up -d
```

### Celery Worker Issues

```bash
# Check if worker is running
docker-compose logs worker

# Inspect Celery tasks
docker exec va-scheduler-worker celery -A worker.celery_config inspect active
```

## Documentation

- [System Architecture](docs/ARCHITECTURE.md) - Design patterns, data flow
- [API Reference](docs/API_REFERENCE.md) - Endpoint documentation
- [Implementation Guide](docs/IMPLEMENTATION_GUIDE.md) - Setup & deployment
- [Master Plan Notebook](AI_Agent_Master_Plan.ipynb) - Comprehensive planning document

## Cost Analysis

### MVP (Current)

- **OpenAI API**: ~$5-10/month (development)
- **PostgreSQL**: ~$15/month (managed DB)
- **Redis**: ~$0/month (included in hosting)
- **Storage**: ~$5/month (S3 compatible)
- **Compute**: ~$25-30/month (VPS or container service)
- **Total**: ~$50-60/month

### Scaling (Phase D)

- **OpenAI API**: $50-200/month (increased usage)
- **Database**: $50-200/month (managed cluster)
- **Redis**: $20-50/month (managed cluster)
- **Storage**: $20-50/month (increased files)
- **Compute**: $100-500/month (multiple instances)
- **Monitoring**: $20-50/month (Sentry, monitoring tools)
- **Total**: ~$350-1000/month

## Support

For questions or issues:

1. Check the [troubleshooting section](#troubleshooting)
2. Review the [master plan notebook](AI_Agent_Master_Plan.ipynb)
3. Check existing GitHub issues
4. Create a new issue with details

## License

MIT License - See LICENSE file for details

---

**Created**: 2024  
**Status**: MVP Phase (Phase A - Complete, Phase B - In Progress)  
**Next Milestone**: Phase B - Core Feature Implementation
