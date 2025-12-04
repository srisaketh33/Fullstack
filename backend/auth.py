# backend/auth.py
import os
from datetime import datetime, timedelta
from typing import Optional
import jwt as pyjwt
from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from .database import users_collection, blacklist_collection, password_reset_collection
from bson import ObjectId
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
import random
import string

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey") # Change in production
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30))

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

# Make OAuth2 optional so cookie-only sessions work
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)
async def get_current_user(request: Request, bearer_token: Optional[str] = Depends(oauth2_scheme)):
    token = request.cookies.get("access_token")
    if not token and bearer_token:
        token = bearer_token
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
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

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

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

@router.get("/me")
async def check_session(current_user: dict = Depends(get_current_user)):
    return {
        "username": current_user["username"], 
        "email": current_user["email"],
        "role": current_user.get("role", "user")
    }

@router.post("/token")
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_collection.find_one({"email": form_data.username})
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    from .hash import verify_password as verify_pwd
    if not verify_pwd(form_data.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token({"sub": user["email"], "role": user.get("role", "user")}, access_token_expires)
    return {"access_token": token, "token_type": "bearer"}

mail_conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),
    MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
    MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
    MAIL_FROM=os.getenv("MAIL_FROM", "noreply@example.com"),
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)
fm = FastMail(mail_conf)

def generate_otp(length: int = 6) -> str:
    return ''.join(random.choices(string.digits, k=length))

@router.post("/forgot-password")
async def forgot_password(payload: dict):
    email = payload.get("email")
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    password_reset_collection.delete_many({"email": email})
    password_reset_collection.insert_one({"email": email, "otp": otp, "expires_at": expires_at})

    message = MessageSchema(
        subject="Your Password Reset OTP",
        recipients=[email],
        body=f"Your OTP is {otp}. It expires in 10 minutes.",
        subtype="plain"
    )
    try:
        await fm.send_message(message)
    except Exception:
        pass
    print(f"OTP for {email}: {otp}")
    return {"message": "OTP sent to email"}

@router.post("/verify-otp")
async def verify_otp(payload: dict):
    email = payload.get("email")
    otp = payload.get("otp")
    rec = password_reset_collection.find_one({"email": email, "otp": otp})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    return {"message": "OTP verified"}

@router.post("/reset-password")
async def reset_password(payload: dict):
    email = payload.get("email")
    otp = payload.get("otp")
    new_password = payload.get("new_password")
    rec = password_reset_collection.find_one({"email": email, "otp": otp})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if rec["expires_at"] < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    from .hash import hash_password as hash_pwd
    users_collection.update_one({"email": email}, {"$set": {"hashed_password": hash_pwd(new_password)}})
    password_reset_collection.delete_many({"email": email})
    return {"message": "Password updated"}
