import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

password_hash = PasswordHash.recommended()

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError("JWT_SECRET_KEY is not configured")
    return secret
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password,hashed_password)
def create_access_token( user_id: int, tenant_id: int, role: str )-> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": tenant_id,
        "role":role,
        "iat":now,
        "exp":now + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload,get_jwt_secret(), algorithm=JWT_ALGORITHM)
def decode_access_token(token:str) -> dict:
    return jwt.decode(
        token,get_jwt_secret(),
        algorithms = [JWT_ALGORITHM]
    )
def get_current_user(token:str = Depends(oauth2_scheme)) -> dict:
    unauthorized = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Invalid or expired token",
        headers = {"www-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role")

        if (
            not isinstance(user_id,str)
            or not user_id.isdigit()
            or not isinstance(tenant_id, int)
            or isinstance(tenant_id,bool)
            or not isinstance(role,str)
            or not role
        ):
            raise unauthorized
        return{
            "user_id": int(user_id),
            "tenant_id": tenant_id,
            "role": role,
        }
    except(jwt.InvalidTokenError, TypeError, ValueError):
        raise unauthorized
