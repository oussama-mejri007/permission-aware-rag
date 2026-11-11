from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import (create_access_token,get_current_user,hash_password,verify_password,save_refresh_token,create_refresh_token,get_refresh_token_expiry,)
from app.database import SessionLocal, engine, create_tables
from app.models.models import User, RefreshToken
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends, FastAPI, HTTPException, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
import re
from app.auth import hash_refresh_token
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy import update

ALLOWED_USER_ROLES = {"finance", "employee"}


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Permission-Aware Multi-Tenant RAG"
)
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,
)

create_tables()
def get_db():
    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class RefreshRequest(BaseModel):
    refresh_token: str
class AskRequest(BaseModel):
    question: str
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=12)
    role: str = Field(..., pattern="^(finance|employee)$")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain a lowercase letter")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain an uppercase letter")
        if not re.search(r"\d", value):
            raise ValueError("Password must contain a digit")
        if not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must contain a special character")

        return value
class UserUpdate(BaseModel):
    is_active: bool


def get_authenticated_user(
    token_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, token_user["user_id"])

    if (
        user is None
        or not user.is_active
        or user.tenant_id != token_user["tenant_id"]
        or user.role != token_user["role"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication is no longer valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

def get_admin_user(
    current_user: User = Depends(get_authenticated_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/health/database")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "database": "ok"
    }

@app.post("/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    ):
    user = db.scalar(
        select(User).where(User.email == form_data.username)
    )

    if (
        user is None
        or not user.is_active
        or not user.password_hash
        or not verify_password(form_data.password, user.password_hash)
        ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        

    token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )
    refresh_token = save_refresh_token(db, user.id)

    return TokenResponse(access_token=access_token,refresh_token=refresh_token,)

@app.post("/auth/refresh", response_model=TokenResponse)
def refresh_access_token(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(payload.refresh_token)

    db_token = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )

    now = datetime.now(timezone.utc)

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if db_token.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == db_token.user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected. All sessions revoked.",
        )

    if db_token.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = db.get(User, db_token.user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication is no longer valid",
        )

    db_token.revoked_at = now

    new_refresh_token = create_refresh_token()

    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=get_refresh_token_expiry(),
        )
    )

    new_access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )

@app.post("/auth/logout")
def logout(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
):
    token_hash = hash_refresh_token(payload.refresh_token)

    db_token = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )

    if db_token is not None and db_token.revoked_at is None:
        db_token.revoked_at = datetime.now(timezone.utc)
        db.commit()

    return {"message": "Logged out successfully"}

@app.post("/rag/ask")
def ask_rag(
    data: AskRequest,
    current_user: User = Depends(get_authenticated_user),
    db: Session = Depends(get_db),
):
    from app.rag import ask_question
    answer = ask_question(
        question = data.question,
        tenant_id = current_user.tenant_id,
        role = current_user.role,
        user_id = current_user.id,
    )
    return {"answer": answer}

@app.get("/users", response_model=list[UserResponse])
def list_users(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    users = db.scalars(
        select(User).where(
            User.tenant_id == current_user.tenant_id
        )
    ).all()

    return users

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(
    data: UserCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    existing_user = db.scalar(
        select(User).where(User.email == data.email)
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_user = User(
        tenant_id=current_user.tenant_id,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        is_active=True,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another admin",
        )

    if user.is_active and not data.is_active:
     db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(timezone.utc))
    )

    user.is_active = data.is_active

    db.commit()
    db.refresh(user)

    return user

@app.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.id == user_id,
            User.tenant_id == current_user.tenant_id,
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another admin",
        )

    db.delete(user)
    db.commit()

    return None