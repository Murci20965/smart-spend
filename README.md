# 💰 Smart Spend - Intelligent Personal Finance Manager

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.122.0-brightgreen?logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-blue?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-5.3.1-red?logo=redis)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Smart Spend** is an intelligent, AI-powered personal finance management system that automatically categorizes bank transactions, learns from user corrections, and provides personalized financial advice. Built with **FastAPI**, **PostgreSQL**, **Redis**, and **HuggingFace AI models**, it is designed for scalability, security, and privacy.

---

## 📌 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Key Technologies & Design Decisions](#key-technologies--design-decisions)
- [Architecture](#architecture)
- [AI/ML Components](#aiml-components)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Setup](#setup)
- [Usage](#usage)
- [Testing](#testing)
- [Deployment](#deployment)
- [Security Features](#security-features)
- [License](#license)
- [Contributing](#contributing)
- [Contact](#contact)

---

## 📖 Overview

Smart Spend is a production-grade financial management application that processes bank statement CSVs, automatically categorizes transactions using AI, and provides actionable financial insights. The system uses a **two-tier categorization system** (rule-based + AI fallback), **learns from user corrections**, and offers **personalized financial coaching** powered by large language models.

### Key Capabilities
- 📄 **CSV Upload & Processing** – Flexible column mapping for various bank statement formats  
- 🤖 **AI-Powered Categorization** – Zero-shot classification for immediate, accurate grouping  
- 💡 **Learning from User Input** – User corrections automatically create new, high-priority categorization rules  
- 💬 **Personalized Coaching** – LLM-powered insights based on spending habits  
- 🔒 **Privacy-First Design** – PII is sanitized before being sent to external AI services  

---

## ✨ Features

### Core Functionality
- **User Authentication**: Secure registration and login with JWTs and Argon2 password hashing  
- **Transaction Management**: Full CRUD operations for all user transactions  
- **Rule Management**: Create and manage custom categorization rules  
- **Dashboard**: Visualization of spending trends and category distribution  
- **Asynchronous Processing**: CSV processing runs in the background for a smooth user experience  

---

## 🛠️ Key Technologies & Design Decisions

| Technology          | Purpose                  | Design Decision |
|-------------------|-------------------------|----------------|
| FastAPI            | API Framework           | High performance, async support, automatic OpenAPI/Swagger documentation |
| PostgreSQL         | Primary Database        | Robust, transactional, and scalable data persistence |
| SQLAlchemy (Async) | ORM                     | Type-safe, asynchronous database interaction |
| Redis / ARQ        | Cache & Queue           | Used for JWT blocklist cache and background job processing (CSV uploads) |
| Pandas             | Data Processing         | Efficient CSV standardization and mapping |
| HuggingFace        | AI Categorization       | Zero-shot model used for fast, general-purpose text categorization |
| Docker Compose     | Development Setup       | Easy setup for API, database, cache, and worker services |

---

## 🏗️ Architecture

Smart Spend separates **synchronous I/O-bound API handling** and **asynchronous background processing** using ARQ + Redis for CPU/network-bound tasks. This ensures a responsive API while processing large CSVs efficiently.

### Request Flow (CSV Upload)
1. Client uploads CSV via `/upload/`  
2. FastAPI authenticates the user (JWT) and performs initial CSV parsing with Pandas  
3. Transaction data is enqueued as a `process_csv_job` in Redis  
4. Job ID is immediately returned to the client  
5. ARQ worker picks up the job asynchronously  
6. PII is sanitized before categorization  
7. Categorization occurs:  
   - **Tier 1 (Rule-Based)** – checks existing user rules  
   - **Tier 2 (AI Fallback)** – calls HuggingFace zero-shot classifier if no rule matches  
8. Categorized transactions are persisted in PostgreSQL  
9. Client can poll job status via `/jobs/{job_id}`  

---

## 🤖 AI/ML Components

| Component                | Technology                     | Logic |
|--------------------------|--------------------------------|-------|
| Transaction Categorization | HuggingFace Inference API (Zero-Shot) | Classifies sanitized transaction descriptions; fallback to "Uncategorized" if unavailable |
| Financial Coaching       | OpenAI-compatible API          | Generates personalized insights from monthly spending data |
| PII Redaction Strategy   | Custom Python Logic/RegEx      | Sanitizes sensitive information via `sanitize_description()` |

---

smart-spend/
├── .github/
│   └── woorkflows
│       └── ci.yml
│
├── smart-spend-backend/
│   │
│   ├── docs/                                 # Backend documentation
│   │
│   ├── app/
│   │   ├── main.py                           # FastAPI app initialization & route registration
│   │   │
│   │   ├── core/                             # Core infrastructure
│   │   │   ├── config.py                     # Settings management (Pydantic Settings)
│   │   │   ├── database.py                   # Async SQLAlchemy engine & session factory
│   │   │   ├── dependencies.py               # FastAPI dependencies (auth, DB sessions)
│   │   │   ├── logging_config.py
│   │   │   └── security.py                   # Password hashing, JWT creation/validation
│   │   │
│   │   ├── models/                           # SQLAlchemy ORM models
│   │   │   └── models.py                     # User, Transaction, CategoryRule models
│   │   │
│   │   ├── schemas/                          # Pydantic request/response models
│   │   │   └── schemas.py                    # Validation schemas for all endpoints
│   │   │
│   │   ├── routers/                          # API route handlers
│   │   │   ├── auth.py                       # Registration, login, session validation
│   │   │   ├── upload.py                     # CSV upload & job enqueueing
│   │   │   ├── jobs.py                       # Job status polling
│   │   │   └── transactions.py               # Transaction CRUD, dashboard, AI coach
│   │   │
│   │   └── services/                         # Business logic & external integrations
│   │       ├── ai_service.py                 # HuggingFace API calls, PII sanitization
│   │       └── worker.py                     # Background CSV processing job
│   │
│   ├── tests/
│   │   ├── integration
│   │   │   └── test_e2e.py
│   │   ├── unit
│   │   │   ├── test_ai_service.py
│   │   │   ├── test_auth.py
│   │   │   ├── test_category_overwrite.py
│   │   │   ├── test_jobs.py
│   │   │   ├── test_transactions.py
│   │   │   ├── test_upload.py
│   │   │   └── test_worker.py
│   │   ├── conftest.py
│   │   ├── utils.py
│   │   └── README.md
│   │
│   ├── .venv/
│   │
│   ├── alembic/                              # Database migrations
│   │   ├── versions/                         # Migration scripts
│   │   └── env.py                            # Alembic configuration
│   │
│   ├── .flake8
│   ├── .dockerignore
│   ├── .gitignore
│   ├── Dockerfile
│   ├── package.json
│   ├── pytest.ini
│   ├── README.md
│   ├── entrypoint_migrate_and_run.sh
│   ├── arq_worker.py                         # ARQ worker configuration
│   ├── alembic.ini                           # Alembic settings
│   ├── requirements.txt                      # Python dependencies
│   ├── .env.template
│   └── .env                                  # Environment variables (not in Git)
│
├── smart-spend-frontend/                     # currently empty
├── .env
├── .env.template
├── docker-compose.yml
├── README.md
├── git_branching_strategy.md
└── test_trandactions.csv                      # Example csv file for testing (Optional)

---

## 🚀 Setup (Docker Compose)

1. **Clone Repository**
```bash
git clone -b main https://github.com/Murci20965/smart-spend.git
cd smart-spend
```

2. **Create Development Branch**
```bash
git checkout -b dev
```

3. **Configure Environment**
```bash
cp smart-spend-backend/.env.template smart-spend-backend/.env
# Add HF_TOKEN if AI features are needed
```

4. **Start Services & Run Migrations**
```bash
docker compose up --build -d
# Alembic migrations run automatically via entrypoint_migrate_and_run.sh
```

5. **Access**
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)  
- Adminer: [http://localhost:8080](http://localhost:8080)  

6. **Stop Services**
```bash
docker compose down
```

---

## 💻 Usage

### Development (Without Docker)
```bash
# Run PostgreSQL & Redis locally
uvicorn app.main:app --reload
# Start ARQ worker
arq arq_worker.WorkerSettings
```

### Production
- Use Docker Compose or orchestrator (e.g., Kubernetes, systemd) for persistent services  

---

## 🧪 Testing
```bash
# Run all tests
docker compose run --rm api pytest -q

# With coverage report
docker compose run --rm api pytest --cov=app --cov-report=html
```

---

## 📦 Deployment
- Separate `.env` files per environment  
- Enable SSL/TLS via reverse proxy  
- Configure CORS securely  
- Ensure database pooling  
- Always run migrations: `alembic upgrade head`  
- Scale API and worker services independently  

---

## 🔒 Security Features
- **Passwords**: Argon2 hashing  
- **Authentication**: JWT with Redis blocklist  
- **PII Redaction**: Masked before external API calls  
- **Input Validation**: Pydantic schemas  
- **Data Isolation**: User data scoped by Foreign Keys  

---

## 📝 License
MIT License  

---

## 🤝 Contributing
- Submit issues or pull requests  
- Follow coding standards: black/isort/flake8  
- Include tests and documentation updates  

---

## 📞 Contact
- Murci: +27 67 660 8432

