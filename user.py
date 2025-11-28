# backend/user.py
from fastapi import APIRouter, HTTPException, status, Depends, Response
from .database import users_collection
from .models import User, UserLogin, UserResponse, UserUpdate, PasswordChange
from .auth import create_access_token, get_current_user, get_admin_user
import bcrypt
from datetime import timedelta
from bson import ObjectId

router = APIRouter()

# --- Utility Functions ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- AUTH & REGISTRATION ---

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered.")

    hashed_pass = hash_password(user.password)
    user_data = user.model_dump()
    user_data["hashed_password"] = hashed_pass
    del user_data["password"] # Don't store plain password
    
    users_collection.insert_one(user_data)
    return {"message": "User created successfully!", "username": user.username}

@router.post("/login")
async def login(credentials: UserLogin, response: Response):
    db_user = users_collection.find_one({"email": credentials.email})
    
    if not db_user or not verify_password(credentials.password, db_user.get("hashed_password")):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
        
    # Create JWT
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": db_user["email"], "role": db_user.get("role", "user")}, 
        expires_delta=access_token_expires
    )
    
    # SET HTTPONLY COOKIE (Secure Session Management)
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,   # JavaScript cannot access this (XSS protection)
        secure=False,    # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return {
        "message": "Login successful", 
        "username": db_user.get("username"),
        "role": db_user.get("role", "user")
    }

# --- PROFILE MANAGEMENT (Protected) ---

@router.put("/profile/update")
async def update_profile(data: UserUpdate, current_user: dict = Depends(get_current_user)):
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided")

    users_collection.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": update_data}
    )
    return {"message": "Profile updated successfully"}

@router.put("/profile/change-password")
async def change_password(data: PasswordChange, current_user: dict = Depends(get_current_user)):
    # Verify old password
    if not verify_password(data.old_password, current_user["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    
    # Hash new password
    new_hashed = hash_password(data.new_password)
    users_collection.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {"hashed_password": new_hashed}}
    )
    return {"message": "Password changed successfully"}

# --- ADMIN: USER MANAGEMENT ---

@router.get("/all", dependencies=[Depends(get_admin_user)])
async def get_all_users():
    users = []
    cursor = users_collection.find({})
    for doc in cursor:
        users.append({
            "id": str(doc["_id"]),
            "username": doc["username"],
            "email": doc["email"],
            "role": doc.get("role", "user")
        })
    return users