import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from fastapi.responses import RedirectResponse

# Import Routers
# These imports assume you are running the command from the PROJECT ROOT folder
from backend.user import router as user_router
from backend.auth import router as auth_router
from backend.device import router as device_router
from backend.shipment import router as shipment_router

# --- DEFINING APP INSTANCE ---
app = FastAPI(title="SCMXpertLite")

# CORS Middleware (Allows frontend to talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MOUNT FRONTEND STATIC FILES ---
# This logic ensures we find the 'frontend' folder regardless of where the script runs
BASE_DIR = Path(__file__).resolve().parent.parent
frontend_dir = BASE_DIR / "frontend"

if not os.path.isdir(frontend_dir):
    # Fallback if specific path logic fails
    frontend_dir = os.path.join(os.getcwd(), "frontend")

if os.path.isdir(frontend_dir):
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {frontend_dir}")

# --- INCLUDE ROUTERS ---
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(device_router, prefix="/stream", tags=["Device"]) # Note: Prefix is /stream based on your frontend JS
app.include_router(shipment_router, prefix="/shipment", tags=["Shipment"])

# --- ROOT REDIRECT ---
@app.get("/")
def root():
    return RedirectResponse(url="/frontend/trail.html")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)