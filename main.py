# main.py
from fastapi import FastAPI
from database import db
from auth import get_password_hash
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
# --- ADD THIS CODE BLOCK ---
origins = [
    "http://localhost:3000", # If using React default
    "http://localhost:5173", # If using Vite
    "http://localhost:8080", 
    "*"                      # Allow all (use only for development)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------

@app.post("/register") # Example endpoint
def register_user(user_data: dict):
    return {"msg": "Success"}

# Import Routers
from Routes.user_routes import router as user_router
from Routes.shipments_routes import router as shipments_router
from Routes.admin_routes import router as admin_router
from Routes.device_routes import router as device_router 

app = FastAPI(title="SCM_Architecture")

@app.on_event("startup")
async def startup_db_and_admin():
    # 1. Create Indexes for speed and uniqueness
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.sessions.create_index("refresh_token_hash")
    await db.shipments.create_index("created_by")
    await db.devices_data.create_index("device_id")
    
    # 2. Create Default Admin if not exists
    admin_email = "admin@example.com"
    if not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "email": admin_email,
            "username": "superadmin",
            "full_name": "Super Admin",
            "password_hash": get_password_hash("AdminPass123!"), # Meets validation requirements
            "is_admin": True,
            "created_at": datetime.utcnow()
        })
        print(f"Admin created: {admin_email}")

# Include Routers
app.include_router(user_router)
app.include_router(shipments_router)
app.include_router(device_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "System Online. Visit /docs for Swagger UI"}