from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.database import SessionLocal, engine, create_tables
from app.models.models import User
from app.auth import create_access_token, verify_password, get_current_user
from fastapi.security import OAuth2PasswordRequestForm



app = FastAPI(
    title="Permission-Aware Multi-Tenant RAG"
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
class AskRequest(BaseModel):
    question: str
class TokenResponse(BaseModel):
    access_token: str
    token_type: str= "bearer"

def get_authenticated_user(
        token_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db),
) -> User:
    user = db.get(User, token_user["user_id"])
    if (
        user is None
        or user.tenant_id != token_user["tenant_id"]
        or user.role != token_user["role"]
    ):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            setail = "User authentication is no longer valid",
            headers = {"WWW-Authenticate" : "Bearer"},
        )
    return user


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
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(User.email == form_data.username)
    )

    if (
        user is None
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

    return TokenResponse(access_token=token)
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