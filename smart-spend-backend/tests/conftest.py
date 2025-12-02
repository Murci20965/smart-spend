import asyncio
import os
import tempfile

import pytest
from typing import AsyncGenerator
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token, hash_password

# Import app, Base, get_db etc.
# We import main.app directly (ensure tests run from smart-spend-backend folder)
from app.main import app as fastapi_app
from app.models.models import Base  # SQLAlchemy metadata

# Use a temporary file-based sqlite DB for tests to avoid aiosqlite
# in-memory DB threading issues (no such table: users). The file
# will be removed when the engine fixture is torn down.
TEST_DATABASE_FILE = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
TEST_DATABASE_FILE.close()
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DATABASE_FILE.name}"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """
    Session-scoped database engine for in-memory SQLite.
    Creates all tables once for the entire test session.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    # create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    # Clean up the temporary sqlite file
    try:
        os.unlink(TEST_DATABASE_FILE.name)
    except Exception:
        pass


@pytest.fixture
async def async_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a function-scoped database session and wraps the test in a transaction.
    The transaction is rolled back after the test completes.
    """
    AsyncSessionLocal = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    # 1. Start a connection/transaction for the test
    async with engine.connect() as connection:
        # Begin a transaction
        async with connection.begin() as transaction:
            # Create a session bound to the transaction
            session = AsyncSessionLocal(bind=connection)

            # 2. Yield the session to the test
            yield session

            # 3. Clean up: Rollback the transaction and close the session
            # All changes made during the test are discarded.
            await session.close()
            await transaction.rollback()


# Override FastAPI dependency get_db to use the test session
@pytest.fixture
def override_get_db(async_session: AsyncSession):
    """
    Overrides the application's get_db dependency to yield the rollback-managed session.
    Note: We no longer need to close the session here, as the `async_session` fixture
    handles closing and rolling back after the dependency generator exits.
    """

    async def _get_db():
        yield async_session

    return _get_db


@pytest.fixture
async def client(override_get_db, monkeypatch):
    """
    Provide an AsyncClient with the FastAPI app and a DB dependency override.
    """
    # Use FastAPI's dependency_overrides so the app uses our test session
    # for all calls to the original get_db dependency. This is more
    # reliable than trying to monkeypatch imported references.
    from app.core import database as database_module
    from app.core import dependencies as dependencies_module

    # Save any existing overrides so we can restore them after the test
    original_overrides = dict(fastapi_app.dependency_overrides)
    fastapi_app.dependency_overrides[database_module.get_db] = override_get_db
    fastapi_app.dependency_overrides[dependencies_module.get_db] = override_get_db

    # FIX: Use ASGITransport to correctly link httpx.AsyncClient to the FastAPI app
    transport = ASGITransport(app=fastapi_app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # ensure Lifespan (startup events) run
        async with LifespanManager(fastapi_app):
            try:
                yield ac
            finally:
                # restore any original overrides to avoid leaking state
                fastapi_app.dependency_overrides = original_overrides


# Helper fixture for creating a user directly in DB
@pytest.fixture
async def test_user(async_session: AsyncSession):
    """
    Creates a test user and commits it. Since the entire test is rolled back,
    this user will only exist for the duration of the test that uses this fixture.
    """
    from app.models.models import User

    password = "ValidPass1!"
    user = User(email="test@example.com", password_hash=hash_password(password))
    async_session.add(user)
    # Commit is necessary to make the user available to other code running in the test
    await async_session.commit()
    await async_session.refresh(user)
    return {"id": user.id, "email": user.email, "password": password}


@pytest.fixture
def auth_token(test_user):
    """
    Generates an authentication token for the test user.
    """
    # create token using user id
    token = create_access_token({"sub": str(test_user["id"])})
    return token
