from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

# Import the dependency to validate tokens
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import Token, UserCreate, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


# -------------------------------
# REGISTER
# -------------------------------
@router.post("/register", response_model=UserOut)
async def register_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new user.

    Note: payload validation (password regex) is handled by Pydantic
    via the UserCreate schema.
    """

    # Check if user already exists
    existing = await db.execute(select(User).where(User.email == payload.email))
    existing_user = existing.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# -------------------------------
# Helper function for login logic (using form data)
# -------------------------------
async def authenticate_user(db: AsyncSession, email: str, password: str):
    # Fetch user by email (which acts as the username in the form)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return None  # Authentication failed

    return user


# -------------------------------
# LOGIN (OAuth2 Form Data)
# -------------------------------
@router.post("/login", response_model=Token)
async def login_for_access_token(
    # Expects form data (username/password)
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # Use the helper function for validation
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT
    token = create_access_token({"sub": str(user.id)})

    return Token(access_token=token)


# -------------------------------
# ME (Session Validation)
# -------------------------------
@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Returns the current authenticated user.
    Used by frontend to validate session persistence.
    """
    return current_user
