# Tests — How to Run and What They Rely On

This directory contains pytest fixtures, unit tests, and integration tests for the **Smart Spend backend**. The instructions below match the CI workflow and the current test setup so you can run the same checks locally.

---

## Quick Start (Docker)

The recommended way to run tests locally is via Docker Compose so the dependencies match CI. The compose setup brings up **Postgres** and **Redis** and builds the API image.

1. Ensure `smart-spend-backend/.env` exists and is populated from `.env.template`.
2. Bring up services (Postgres + Redis) in the background:

```bash
docker compose up -d postgres redis
```

3. Run migrations and tests inside the API container:

```bash
docker compose run --rm api bash -c "alembic upgrade head && pytest -q"
```

Run a single test:

```bash
docker compose run --rm api pytest tests/integration/test_e2e.py::test_end_to_end_upload_and_rule_learning -q
```

---

## Linters and Formatters

CI runs `isort`, `black`, and `flake8` (88-character max). You can run these checks inside the API container (the image includes dev dependencies) or install them locally.

```bash
docker compose run --rm api bash -c "isort . && black . && flake8 --max-line-length=88"
```

Or install `requirements-dev.txt` locally and run them directly.

---

## Environment & Test-Time Configuration

- Tests override the app’s DB dependency to use a temporary SQLite file-based DB (see `tests/conftest.py`). This avoids in-memory threading issues while keeping the test suite isolated.
- Redis pool is mocked in tests (`app.state.redis_pool = None`) via monkeypatching.
- Required environment variables (for CI and some integration tests):

```text
SECRET_KEY
ALGORITHM (e.g., HS256)
DATABASE_URL (for CI; local tests use temporary SQLite file)
REDIS_HOST / REDIS_PORT / REDIS_DB / REDIS_PASSWORD (CI)
ENV (set to `testing` in CI)
```

- You can create a `.env` file in `smart-spend-backend/` or set env vars in your shell before running tests. The project also contains a `.env.template` listing expected variables.

---

## Important Test Behaviors & Notes for Contributors

- **Worker (`app.services.worker`)**: Monkeypatch `async_session` for testing worker logic.
- **Upload Endpoint (`app.routers.upload`)**: Monkeypatch `get_redis_pool()` for fake async Redis pool.
- Tests intentionally use `ASGITransport` + `LifespanManager` to ensure FastAPI app lifespan is exercised.

---

## CI Specifics (GitHub Actions)

The CI job (`.github/workflows/ci.yml`) performs these steps:

1. Checkout + setup Python 3.11
2. Cache pip
3. Install dependencies (`requirements-dev.txt`)
4. Run linters (`isort`, `black`, `flake8`)
5. Start Postgres + Redis worker services
6. Run Alembic migrations against the test Postgres DB
7. Run pytest (unit + integration)

> CI uses ephemeral services with placeholder secrets. For production, GitHub Secrets should be used.  
> CI triggers on `main` and `dev` branches, and PRs to these branches.

---

## Git Branch Workflow for Testing and Feature Development

**Allowed / Suggested Branches:**

- `main` — stable production-ready code
- `dev` — integration and staging of features
- `feature/<name>` — new features, merged to dev
- `hotfix/<name>` — urgent fixes, merged to both dev and main
- `fix/<name>` — minor fixes, merged to dev
- `docs/<name>` — documentation updates

**Merging Strategy:**

- **Dev → Main:** Only merge when dev is stable, CI passed, and QA approved.

```bash
git checkout main
git merge dev
git push origin main
```

- **Feature → Dev:** Open a PR after completing a feature.

```bash
git checkout dev
git merge feature/<name>
git push origin dev
```

- **Hotfix → Main + Dev:**

```bash
git checkout main
git merge hotfix/<name>
git push origin main

git checkout dev
git merge hotfix/<name>
git push origin dev
```

---

## Example Feature Workflow

1. Create a feature branch from dev:

```bash
git checkout dev
git checkout -b feature/user-auth
```

2. Implement feature and commit in small steps:

```bash
git add smart-spend-backend/app/routers/auth.py
git commit -m "feature: add JWT authentication for login and registration"
```

3. Push to GitHub:

```bash
git push origin feature/user-auth
```

4. Open PR: `feature/user-auth → dev`. CI runs tests and linter. Code review is performed.
5. After approval, merge PR to dev. Repeat until dev is stable, then merge `dev → main`.

---

## Troubleshooting

- "No module named 'app'" → ensure Python path includes `smart-spend-backend`.
- Test failures due to lingering DB files → delete any `*.db` test files in project root.
- Adminer / DB connection issues → use `postgres` as host, not port, when connecting to Docker Compose Postgres.

---

This integration ensures **consistency between local testing, feature development, and CI**, providing a robust and repeatable workflow for contributors.

