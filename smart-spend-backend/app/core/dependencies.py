import asyncio
from importlib import import_module
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # JWT stores the subject as a string; convert to UUID for DB queries
    try:
        user_uuid = UUID(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if not user:
        # User does not exist -> return 401 Unauthorized
        raise HTTPException(status_code=401, detail="User not found")

    return user


async def get_redis_pool(request: Request):
    """Dependency to return the app-level redis pool created at startup.

    Tests run in a 'testing' environment and may not create a pool; callers
    should handle None gracefully.
    """
    pool = getattr(request.app.state, "redis_pool", None)
    # If there is no pool (tests often skip pool creation), allow tests to
    # monkeypatch a module-level `get_redis_pool` on `app.routers.upload`.
    # By checking here we ensure FastAPI's dependency system executes the
    # test-provided fake when present.
    if pool is None:
        try:
            mod = import_module("app.routers.upload")
            candidate = getattr(mod, "get_redis_pool", None)
            if callable(candidate):
                maybe = candidate()
                if asyncio.iscoroutine(maybe):
                    pool = await maybe
                else:
                    pool = maybe
        except Exception:
            # Ignore any issues and return whatever pool we have (None)
            pass
    return pool
