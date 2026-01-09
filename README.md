# AI Agent: Virtual Assistant & Task Scheduler

## Overview

A **deployable, modular AI agent** that combines conversational assistance with reliable task scheduling for:

1. **Intelligent Inbox Management** – Fetch emails, classify, flag, and auto-reply (with approval gates)
2. **Quick Data Analysis** – Upload datasets, run analysis, get LLM-generated summaries + downloadable reports
3. **Extensible Automation** – Easy-to-add connectors and task definitions for future automations

**Goal**: Production-ready MVP on your infrastructure (DigitalOcean, AWS, or on-prem) in ~8 weeks.

---

## Key Features

✅ **Email Linking** – Secure OAuth2 to Gmail/Outlook; tokens encrypted at rest  
✅ **Smart Classification** – LangChain + OpenAI embeddings for email categorization  
✅ **Rule Engine** – YAML/JSON rules (trigger → condition → action) with no-code management  
✅ **Pre-Approved Replies** – Templates with safety gates (confidence threshold, daily limits, sensitive topics)  
✅ **Task Scheduler** – Celery + Redis for reliable job execution with retries  
✅ **Data Analysis** – CSV upload → stats → LLM summary → downloadable report  
✅ **Audit Logging** – Every action tracked and encrypted (GDPR-ready)  
✅ **Dashboard + CLI** – Next.js dashboard + Python Typer CLI for power users  
✅ **Docker Ready** – `docker-compose up` runs everything locally

---

## Stack

| Layer                | Technology            | Why                                           |
| -------------------- | --------------------- | --------------------------------------------- |
| **Backend**          | Python + FastAPI      | Fast, async, strong ecosystem                 |
| **Orchestration**    | LangChain             | Best-in-class LLM chains & connectors         |
| **LLM Provider**     | OpenAI (start)        | Best dev DX; migrate to Anthropic/local later |
| **Embeddings**       | FAISS (MVP)           | Free, in-process; scale to Pinecone           |
| **Scheduler**        | Celery + Redis        | Mature, cheap, battle-tested                  |
| **Database**         | PostgreSQL            | ACID, JSON support, scalable                  |
| **Storage**          | S3-compatible         | Cheap, durable (DigitalOcean Spaces)          |
| **Frontend**         | Next.js + TailwindCSS | Fast dev, great DX                            |
| **Containerization** | Docker Compose        | Single-host MVP; scale to k8s                 |
| **Hosting (MVP)**    | DigitalOcean Droplet  | $12/month + managed DB/Redis                  |

**Annual Cost (MVP)**: ~$600 ($50/month compute + DB + storage + LLM calls)

---

## Quick Start (Windows & Mac/Linux)

### Prerequisites

- Python 3.11+
- Git
- Docker (for containerized deployment)
- OpenAI API key
- Gmail/Outlook OAuth credentials (optional, for testing)

### 1. Clone & Setup

**Windows** (PowerShell):

```powershell
git clone <repo-url>
cd virtual-assistant-scheduler
powershell -ExecutionPolicy Bypass -File setup.ps1
```

**Mac/Linux** (Bash):

```bash
git clone <repo-url>
cd virtual-assistant-scheduler
bash setup.sh
```

### 2. Configure Environment

```bash
# Edit .env with your secrets
cp .env.example .env
# Then edit .env:
#   OPENAI_API_KEY=sk-...
#   GMAIL_CLIENT_ID=xxx
#   ENCRYPTION_KEY=... (generate with Fernet)
```

### 3. Start Services

```bash
# Terminal 1: Start Docker services
docker-compose up --build

# Terminal 2: Activate venv and test
source venv/bin/activate  # or: venv\Scripts\Activate.ps1
pytest tests/ -v

# Terminal 3: Verify health
curl http://localhost:8000/health
```

### 4. Access Dashboard

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Postgres**: localhost:5432
- **Redis**: localhost:6379

---

## Project Structure

```
virtual-assistant-scheduler/
├── backend/                    # Python FastAPI backend
│   ├── main.py                 # FastAPI app entry point
│   ├── models.py               # SQLAlchemy ORM (User, EmailJob, Task, etc.)
│   ├── config.py               # Environment configuration
│   ├── api/
│   │   ├── auth.py             # Login/register/logout
│   │   ├── email.py            # Email linking & processing
│   │   ├── jobs.py             # Job status & launcher
│   │   └── templates.py        # Template CRUD
│   ├── connectors/
│   │   ├── base.py             # BaseEmailConnector ABC
│   │   ├── email_adapters.py   # Gmail, Outlook, IMAP implementations
│   │   └── data_adapters.py    # CSV, Sheets, S3, SQL adapters
│   ├── llm/
│   │   ├── embeddings.py       # OpenAI embeddings
│   │   └── classifier_chain.py # LangChain email classifier
│   ├── storage/
│   │   ├── vector_store.py     # FAISS index
│   │   └── s3_client.py        # S3 object storage
│   ├── worker/
│   │   ├── celery_app.py       # Celery configuration
│   │   └── tasks/
│   │       ├── email_processor.py   # Fetch, classify, route emails
│   │       ├── auto_reply.py        # Send pre-approved replies
│   │       └── data_analysis.py     # Run analysis jobs
│   ├── security/
│   │   ├── encryption.py       # Token encryption/decryption
│   │   └── jwt.py              # JWT auth
│   └── engine/
│       └── rules_engine.py     # YAML/JSON rule evaluation
│
├── frontend/                   # Next.js React dashboard
│   ├── pages/
│   │   ├── index.tsx           # Dashboard home
│   │   ├── login.tsx           # Auth page
│   │   ├── inbox.tsx           # Email list & classify
│   │   ├── analysis.tsx        # Data upload & results
│   │   ├── templates.tsx       # Template manager
│   │   └── rules.tsx           # Rule builder
│   ├── components/             # React components
│   ├── lib/                    # API client & utilities
│   └── styles/                 # TailwindCSS styles
│
├── tests/                      # Unit & integration tests
│   ├── test_auth.py
│   ├── test_email_processor.py
│   ├── test_rules_engine.py
│   ├── test_data_analysis.py
│   ├── test_auto_reply.py
│   └── test_acceptance.py      # 6 end-to-end tests
│
├── docs/                       # Documentation
│   ├── SETUP.md                # Local development setup
│   ├── DEPLOYMENT.md           # Production deployment
│   ├── ADMIN_RUNBOOK.md        # Operations guide
│   ├── API_DOCUMENTATION.md    # API reference
│   ├── ARCHITECTURE.md         # System design
│   ├── COST_ANALYSIS.md        # Pricing & infrastructure
│   └── SECURITY.md             # Compliance & security
│
├── docker-compose.yml          # Local dev stack (postgres, redis, backend, worker)
├── Dockerfile                  # Backend image
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── README.md                   # This file
└── setup.sh / setup.ps1        # Quick-start scripts
```

---

## Documentation

| Document                                          | Purpose                                                       |
| ------------------------------------------------- | ------------------------------------------------------------- |
| [SETUP.md](docs/SETUP.md)                         | Local development setup, virtual env, database migrations     |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md)               | Production deployment to DigitalOcean/AWS/on-prem             |
| [ADMIN_RUNBOOK.md](docs/ADMIN_RUNBOOK.md)         | How to operate: link email, approve templates, manage workers |
| [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | All endpoints: auth, email, jobs, templates, rules            |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md)           | System design, data flows, extension points                   |
| [COST_ANALYSIS.md](docs/COST_ANALYSIS.md)         | Cost breakdown, pricing models, scaling strategy              |
| [SECURITY.md](docs/SECURITY.md)                   | OAuth2, encryption, audit logging, GDPR compliance            |

---

## Development Phases

### Phase A: MVP (Weeks 1-2)

- ✅ Project scaffold, auth, email linking via OAuth
- ✅ Basic inbox processor (fetch, classify, label)
- ✅ CSV upload & analysis with LLM summary
- **Expected**: Can login, link Gmail, process emails, analyze data

### Phase B: Core Features (✅ COMPLETE - Weeks 3-6)

- ✅ Gmail OAuth2 integration with secure token storage
- ✅ Email fetching pipeline with encryption
- ✅ Classification system (LangChain + OpenAI)
- ✅ Celery task integration
- ✅ 24+ passing tests
- **Status**: Email ingestion and classification fully functional

### Phase C Step 1: Email Classification (✅ COMPLETE)

- ✅ EmailClassifier with OpenAI integration
- ✅ 5 email categories: important, actionable, followup, promotional, spam
- ✅ Confidence scoring (0-100%)
- ✅ Explanation generation
- ✅ API endpoints for manual + automatic classification
- ✅ 16 passing unit tests
- **Status**: See [PHASE_C_STEP1_COMPLETE.md](PHASE_C_STEP1_COMPLETE.md)

### Phase C Step 2: Rule Evaluation Engine (✅ COMPLETE)

- ✅ RuleEngine class with rule evaluation logic
- ✅ 5 default rules (flag important, archive promotional, etc.)
- ✅ Pattern matching (wildcard, regex, case-insensitive)
- ✅ ActionRecommendation database model
- ✅ Celery tasks for async recommendation generation
- ✅ 6 REST API endpoints
- ✅ **27 passing unit tests** (100% pass rate)
- ✅ End-to-end verification passing
- **Key Achievement**: Generates action recommendations WITHOUT executing actions
- **Status**: See [PHASE_C_STEP2_COMPLETE.md](PHASE_C_STEP2_COMPLETE.md) and [PHASE_C_STEP2_RULE_ENGINE.md](PHASE_C_STEP2_RULE_ENGINE.md)

### Phase C Step 3: Action Execution (PLANNED)

- [ ] Action executor engine
- [ ] Safe execution with audit logging
- [ ] User confirmation workflow
- [ ] Rollback capability

### Phase C: Hardening (Weeks 7-8)

- [ ] Token encryption, audit logging
- [ ] Unit & integration tests (80%+ coverage)
- [ ] Security audit, vulnerability scan
- [ ] Docker Compose deployment
- [ ] CI/CD pipeline (GitHub Actions)
- **Expected**: Production-ready MVP ready to deploy

### Phase D: Scaling (Optional, Weeks 9+)

- [ ] Migrate FAISS → Pinecone
- [ ] Migrate Celery → Temporal
- [ ] Kubernetes deployment
- [ ] RBAC, multi-tenancy, advanced connectors
- **Expected**: Enterprise-ready system

---

## Acceptance Criteria

Run the 6 acceptance tests to verify MVP readiness:

```bash
pytest tests/test_acceptance.py -v
```

1. ✅ **Login & OAuth** – User can register, login, and link Gmail account securely
2. ✅ **Email Processing** – Fetch test emails, classify with confidence scores, apply labels
3. ✅ **Auto-Reply** – Approve template, trigger auto-reply on rule match, verify delivery
4. ✅ **Task Scheduling** – Create follow-up task, confirm scheduled in Celery
5. ✅ **Data Analysis** – Upload CSV, analyze, get LLM summary + downloadable report
6. ✅ **Audit Logs** – Verify all actions logged with encryption

**If all 6 pass → MVP ready for deployment.**

---

## API Quick Reference

### Auth

```
POST   /api/auth/register           – Register new user
POST   /api/auth/login              – Login, get JWT token
POST   /api/auth/logout             – Logout
GET    /api/auth/me                 – Get current user
```

### Email

```
GET    /api/email/oauth-authorize   – Initiate OAuth flow
GET    /api/email/oauth-callback    – OAuth callback handler
POST   /api/emails/process          – Trigger email processing
GET    /api/emails                  – List emails with labels
POST   /api/emails/{id}/flag        – Flag email
```

### Jobs

```
GET    /api/jobs                    – List all jobs
GET    /api/jobs/{id}               – Get job status
POST   /api/jobs                    – Create new job
POST   /api/jobs/{id}/cancel        – Cancel job
```

### Templates

```
GET    /api/templates               – List templates
POST   /api/templates               – Create template
PUT    /api/templates/{id}          – Update template
POST   /api/templates/{id}/approve  – Approve for auto-send
DELETE /api/templates/{id}          – Delete template
```

### Data Analysis

```
POST   /api/data/upload             – Upload CSV
GET    /api/data/{id}/results       – Get analysis results
GET    /api/data/{id}/report        – Download report (PDF/HTML)
```

See [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for full details.

---

## Key Configuration Variables

See `.env.example` for complete list:

```env
# Backend
FASTAPI_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/ai_agent_db

# Redis & Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Gmail OAuth
GMAIL_CLIENT_ID=xxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=xxx
GMAIL_REDIRECT_URI=http://localhost:8000/api/email/oauth-callback/gmail

# Encryption
ENCRYPTION_KEY=<base64-encoded-fernet-key>

# Optional: AWS/S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_S3_BUCKET=ai-agent-reports
```

---

## Deployment

### Local (Docker Compose)

```bash
docker-compose up --build
# Then: http://localhost:3000 (frontend) + http://localhost:8000/docs (API)
```

### Production (DigitalOcean)

```bash
# See DEPLOYMENT.md for step-by-step instructions
# 1. Create droplet (6GB recommended)
# 2. Install Docker
# 3. Set environment variables in .env
# 4. Run: docker-compose -f docker-compose.prod.yml up -d
# 5. Setup SSL/TLS with certbot
```

### Scaling (Kubernetes)

```bash
# See DEPLOYMENT.md for Helm charts and k8s setup
# Cost: ~$100+/month on GKE/EKS
```

---

## Monitoring & Observability

- **Error Tracking**: Sentry (free tier)
- **Logs**: Postgres + S3 archive
- **Metrics**: Prometheus (optional)
- **Dashboard**: Grafana (optional)
- **Status**: Health check endpoint: `GET /health`

---

## Security Highlights

🔐 **OAuth2** – Secure email linking (no password storage)  
🔐 **Token Encryption** – AES-256 at rest  
🔐 **Audit Logging** – Every action tracked (who, what, when)  
🔐 **Approval Gates** – Auto-replies require confidence score + approval  
🔐 **GDPR Ready** – Data export & deletion support  
🔐 **HTTPS/TLS** – Let's Encrypt certificates

See [SECURITY.md](docs/SECURITY.md) for details.

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=backend --cov-report=html

# Acceptance tests (MVP validation)
pytest tests/test_acceptance.py -v

# Load testing (simulate 100 emails/min)
locust -f tests/load_test.py --headless -u 100 -r 10
```

---

## Contributing

1. Create feature branch: `git checkout -b feature/my-automation`
2. Implement changes + tests
3. Pass PR checklist (see docs)
4. Submit PR with description
5. At least 1 code review approval
6. Merge to main

See [PR_CHECKLIST.md](docs/PR_CHECKLIST.md) for details.

---

## Cost Breakdown

### MVP (100 emails/day, 5 analysis jobs/day)

| Component               | Cost/Month | Notes                            |
| ----------------------- | ---------- | -------------------------------- |
| Compute (DO Droplet)    | $12        | 6GB RAM, shared vCPU             |
| Database (Postgres)     | $15        | Managed, automated backups       |
| Cache (Redis)           | $15        | Managed, high availability       |
| Storage (S3-compatible) | $5         | 250 GB/month                     |
| LLM (OpenAI)            | $3         | Email classification + summaries |
| Monitoring              | $0         | Sentry free tier                 |
| **Total**               | **$50**    | Annual: $600                     |

### Scale (1,000 emails/day, 50 analysis jobs/day)

| Component              | Cost/Month |
| ---------------------- | ---------- |
| Compute (auto-scaling) | $50        |
| Database (RDS)         | $40        |
| Cache (ElastiCache)    | $50        |
| Storage (S3)           | $20        |
| LLM (OpenAI)           | $28        |
| Monitoring             | $50        |
| **Total**              | **$238**   |

See [COST_ANALYSIS.md](docs/COST_ANALYSIS.md) for detailed pricing & migration strategy.

---

## Roadmap

| Phase | Timeline  | Focus                                             |
| ----- | --------- | ------------------------------------------------- |
| **A** | Weeks 1-2 | MVP scaffold, auth, email, data analysis          |
| **B** | Weeks 3-6 | Scheduler, templates, rules engine, dashboard     |
| **C** | Weeks 7-8 | Hardening, testing, deployment, docs              |
| **D** | Weeks 9+  | Scaling, enterprise features, advanced connectors |

---

## Support & Hand-Off

### What You Get

✅ Source code (GitHub repo)  
✅ Docker images (in registry)  
✅ Full documentation (5 guides)  
✅ Acceptance test results  
✅ Admin runbook (operations)  
✅ Demo script (working end-to-end)

### Hand-Off Call (45 min)

1. System overview (15 min)
2. Live demo (20 min)
3. Operations & support (10 min)

### Post-Hand-Off Support

- Email support for 2 weeks
- 1 follow-up call (1 week post-launch)
- Bug fixes for critical issues

---

## License

MIT License – Free to use, modify, and distribute.

---

## Questions?

Refer to:

- **Setup issues** → [SETUP.md](docs/SETUP.md)
- **Deployment** → [DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Operations** → [ADMIN_RUNBOOK.md](docs/ADMIN_RUNBOOK.md)
- **Architecture** → [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **API reference** → [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

---

**Ready to build?** Start with: `bash setup.sh` (Mac/Linux) or `powershell setup.ps1` (Windows)

Good luck! 🚀
