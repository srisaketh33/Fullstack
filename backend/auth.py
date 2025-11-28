# backend/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional
import jwt as pyjwt
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
from .database import users_collection, blacklist_collection
from bson import ObjectId

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey") # Change in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = pyjwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Dependency: Get Current User from Cookie ---
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    # Check if token is blacklisted (Revocation Check)
    if blacklist_collection.find_one({"token": token}):
        raise HTTPException(status_code=401, detail="Session expired/logged out")

    try:
        payload = pyjwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except pyjwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Convert ObjectId to string for easier handling
    user["id"] = str(user["_id"])
    return user

# --- Dependency: Check if Admin ---
async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# --- Logout Endpoint (Token Revocation) ---
@router.post("/logout")
async def logout(response: Response, request: Request):
    token = request.cookies.get("access_token")
    if token:
        # Strip Bearer
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
        # Add to blacklist
        blacklist_collection.insert_one({"token": token, "blacklisted_at": datetime.utcnow()})
    
    # Clear cookie
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

# --- Check Session Endpoint (for Frontend UI logic) ---
@router.get("/me")
async def check_session(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"], 
        "email": current_user["email"],
        "role": current_user.get("role", "user")
    }