# 💰 Smart Spend - Intelligent Personal Finance Manager

An intelligent, AI-powered personal finance management system was implemented to automatically categorize bank transactions, learn from user corrections, and provide personalized financial advice. The backend was built with FastAPI, PostgreSQL, Redis, and HuggingFace AI models; scalability, security, and user privacy were prioritized.

## 📖 Overview

Smart Spend is a production-grade financial management application. Bank statement CSVs are processed, transactions are automatically categorized using AI, and actionable financial insights are provided. The system employs a two-tier categorization system (rule-based + AI fallback), learns from user feedback to improve accuracy over time, and personalized financial coaching is offered, powered by large language models.

Key Capabilities:

📄 CSV Upload & Processing – Flexible column mapping for various bank statement formats is offered.

🤖 AI-Powered Categorization – Zero-shot classification via HuggingFace models is used.

🎓 Learning System – Categorization rules are automatically created from user corrections.

💡 Financial Coaching – Personalized advice is generated based on spending patterns.

🔒 Privacy-First – PII redaction, secure authentication, and user data isolation are prioritized.

⚡ Async Architecture – Background job processing is utilized for maximum scalability.

## 📚 Documentation

Documentation was organized to aid system navigation:

- 🏗 Architecture & Design — System design, tech stack decisions, and data flow were documented.
- 🔌 API Documentation — Endpoints, request/response examples, and the auth flow were described.
- 🤖 AI & ML Models — Details on the HuggingFace models and the coaching engine were recorded.
- 🗄 Database Schema — The SQL schema, relationships, and design choices were outlined.
- 🔒 Security — PII protection, encryption, and authentication handling were documented.

## ✨ Features

### Core Functionality

✅ Smart CSV Processing – Intelligent column mapping is implemented (handles "Payee", "Transaction Details", "Memo").

✅ AI Transaction Categorization – Expenses are automatically classified into 9 categories using zero-shot learning.

✅ Adaptive Learning – Manual corrections are turned into persistent categorization rules.

✅ Financial Dashboard – Spending summaries, category breakdowns, and monthly trends are provided.

✅ AI Financial Coach – Personalized advice comparing budget vs. actual spending is offered.

✅ PII Protection – Account numbers and sensitive data are automatically redacted.

### Technical Features

✅ Async/Await Architecture – Non-blocking I/O is used for high performance.

✅ Background Job Processing – ARQ workers with Redis queues are utilized for CSV processing.

✅ JWT Authentication – The app is secured with token-based auth and Argon2 password hashing.

✅ Database Migrations – Alembic is used for version-controlled schema management.

✅ Type Safety – Requests/responses are strictly validated with Pydantic models.

✅ Comprehensive Error Handling – Graceful fallbacks and detailed logging are ensured.

## ⚡ Quick start (Docker Compose)

A `Dockerfile` for the backend and a `docker-compose.yml` under `infrastructure/` were provided. Postgres, Redis, the API, and the background worker can be brought up by using Docker Compose. The Docker setup is the recommended method for running the application and reproducing CI locally.

1) A `.env` file should be created from `.env.template` in `smart-spend-backend/` and populated with values (do not commit `.env`).

docker compose -f infrastructure/docker-compose.yml up --build -d
2) From the repository root the services may be started (images will be built on first run):

```powershell
# from repo root
docker compose up --build -d
```

3) Alembic migrations should be run inside the API container so the database schema is prepared:

```powershell
docker compose run --rm api \
	bash -c "alembic upgrade head"
```

Database volume / password note
--------------------------------

If you change container-side Postgres initialization values (for example
`POSTGRES_PASSWORD`) after the Postgres container has already initialized,
the existing `pgdata` volume will keep the old credentials. To reinitialize
the database with new `POSTGRES_*` values during development, remove the
compose-managed volume and restart the stack:

```powershell
docker compose -f infrastructure/docker-compose.yml down -v
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Warning: this deletes the Postgres data in the volume — do not run on
production databases.

4) The API can be opened at http://localhost:8000 and the interactive API docs at http://localhost:8000/docs

5) To tail logs for the worker or api services, the following commands may be used:

```powershell
docker compose logs -f worker
docker compose logs -f api
```

Running tests (inside container)

The full test suite may be executed inside the built API container so that the environment matches CI:

```powershell
docker compose run --rm api \
	bash -c "alembic upgrade head && pytest -q"
```

To stop and remove containers, the following command may be used:

```powershell
docker compose down
```

## 📝 License

This project is licensed under the MIT License.

## Notes on recent changes

- The repository was Dockerized and a `Dockerfile` was added for the backend; the backend image was built from `smart-spend-backend/Dockerfile`.
- The `Dockerfile` was updated so that dependencies are installed from `requirements.txt` only; the previous `requirements-dev.txt` file was removed and was no longer referenced.
- A `.dockerignore` file was added to prevent `.env` and other local files from being sent to the Docker build context.
- The `infrastructure/docker-compose.yml` file was cleaned and validated so that top-level services (postgres, redis, adminer, api, worker) are defined and a `pgdata` volume is used for Postgres data.

If further adjustments are required (healthchecks, secrets via Docker secrets, or CI image builds), these changes can be proposed and applied.