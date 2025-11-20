# auth.py (corrected)
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import HTTPException, Depends, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import JWTError, jwt
from bson import ObjectId

from database import db
from models import UserOut, SessionOut, TokenResponse, PyObjectId
import config

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed: str) -> bool:
    return pwd_context.verify(plain_password, hashed)


# Token utilities
def hash_refresh_token(token: str) -> str:
    h = hashlib.sha256()
    h.update((token + config.JWT_SECRET).encode("utf-8"))
    return h.hexdigest()


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    jti: Optional[str] = None,
) -> str:
    to_encode = data.copy()
    # Use seconds value from config; allow optional timedelta override
    default_seconds = getattr(config, "ACCESS_TOKEN_EXPIRES_SECONDS", 3600)
    expire = datetime.utcnow() + (expires_delta or timedelta(seconds=default_seconds))
    _jti = jti or secrets.token_urlsafe(16)
    to_encode.update({"exp": expire, "jti": _jti})
    encoded = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return encoded


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


# DB helpers
async def get_user_by_email(email: str):
    return await db.users.find_one({"email": email.lower()})


async def get_user_by_id(user_id: str):
    if not ObjectId.is_valid(user_id):
        return None
    return await db.users.find_one({"_id": ObjectId(user_id)})


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


# Auth dependencies
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")
    token = parts[1]
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = payload.get("sub")
        jti = payload.get("jti")
        if user_id is None or jti is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    session = await db.sessions.find_one({"user_id": ObjectId(user_id), "jti": jti, "revoked": {"$ne": True}})
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked or not found")

    await db.sessions.update_one({"_id": session["_id"]}, {"$set": {"last_active_at": datetime.utcnow()}})

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    user["session_id"] = str(session["_id"])
    return user


async def require_admin(current_user=Depends(get_current_user)):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
