# backend/device.py

from fastapi import APIRouter, HTTPException, status
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from typing import List 
from .models import DeviceData 

# --- Configuration and Database Setup ---
load_dotenv()
uri = os.getenv("MONGO_URI")

# We can reuse the same MongoDB client connection logic
try:
    mongo = MongoClient(uri)
    db = mongo["db"]
    device_collection = db["device_streams"] 
    print("Database connection for device stream established.")
except Exception as e:
    print(f"Error connecting to database for devices: {e}")
    exit()

# --- API Router Definition ---
router = APIRouter()

# --- API Endpoints ---

@router.get("/devices", summary="Get a list of all unique device IDs")
async def get_all_device_ids():
    """
    Retrieves a list of all distinct device IDs from the database.
    This is useful for populating the dropdown on the frontend.
    """
    try:
        # The distinct method is efficient for getting unique values
        device_ids = device_collection.distinct("Device Id")
        if not device_ids:
            raise HTTPException(status_code=404, detail="No devices found")
        return device_ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/devices/{device_id}", summary="Get data stream for a specific device")
async def get_device_data_stream(device_id: str):
    """
    Retrieves all data stream records for a given device ID.
    The data is returned sorted by timestamp in descending order (newest first).
    """
    try:
        # Query the collection for all documents matching the device_id
        # The second argument ({'_id': 0}) excludes the default MongoDB ObjectId
        # Sort by Timestamp descending (-1)
        data = list(device_collection.find({"Device Id": device_id}, {'_id': 0}).sort("Timestamp", -1))
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for Device ID: {device_id}"
            )
        return data
    except Exception as e:
        # Handle potential server errors
        raise HTTPException(status_code=500, detail=str(e))
