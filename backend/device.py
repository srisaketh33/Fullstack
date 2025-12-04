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
    shipments_collection = db["shipments"]
    print("Database connection for device stream established.")
except Exception as e:
    print(f"Error connecting to database for devices: {e}")
    exit()

# --- API Router Definition ---
router = APIRouter()

# --- API Endpoints ---

def _distinct_device_ids() -> List[str]:
    ids = set()
    try:
        ids.update(str(x) for x in filter(None, device_collection.distinct("Device Id")))
    except Exception:
        pass
    try:
        ids.update(str(x) for x in filter(None, device_collection.distinct("Device_ID")))
    except Exception:
        pass
    try:
        ids.update(str(x) for x in filter(None, device_collection.distinct("DeviceId")))
    except Exception:
        pass
    return sorted(ids)

def _device_query(device_id: str):
    values = [device_id]
    try:
        num = int(device_id)
        values.append(num)
    except Exception:
        pass
    return {
        "$or": [
            {"Device Id": {"$in": values}},
            {"Device_ID": {"$in": values}},
            {"DeviceId": {"$in": values}},
        ]
    }

def _normalize_record(doc: dict) -> dict:
    return {
        "Device Id": doc.get("Device Id") or doc.get("Device_ID") or doc.get("DeviceId"),
        "Battery Level": doc.get("Battery Level") or doc.get("Battery_Level"),
        "First Sensor temperature": doc.get("First Sensor temperature") or doc.get("First_Sensor_temperature") or doc.get("Temp"),
        "Route From": doc.get("Route From") or doc.get("Route_From"),
        "Route To": doc.get("Route To") or doc.get("Route_To"),
        "Timestamp": doc.get("Timestamp")
    }

@router.get("/devices", summary="Get a list of all unique device IDs")
async def get_all_device_ids():
    try:
        stream_ids = set(_distinct_device_ids())
        shipment_ids = set(str(x) for x in filter(None, shipments_collection.distinct("device")))
        all_ids = sorted(stream_ids.union(shipment_ids))
        return all_ids
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/device-ids-only", summary="Get device IDs that have telemetry")
async def get_stream_device_ids():
    try:
        return _distinct_device_ids()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/device-status/{device_id}")
async def device_status(device_id: str):
    try:
        count = device_collection.count_documents(_device_query(device_id))
        last_cursor = device_collection.find(_device_query(device_id), {'_id': 0}).sort("Timestamp", -1).limit(1)
        last_raw = next(last_cursor, None)
        last_record = _normalize_record(last_raw) if last_raw else None
        return {"device_id": device_id, "has_telemetry": count > 0, "total_records": count, "last_record": last_record}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shipment-status/{shipment_number}")
async def shipment_status(shipment_number: str):
    try:
        s = shipments_collection.find_one({"shipment_number": shipment_number}, {"_id": 0, "device": 1})
        if not s:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
        dev = s.get("device")
        count = device_collection.count_documents(_device_query(dev))
        last_cursor = device_collection.find(_device_query(dev), {'_id': 0}).sort("Timestamp", -1).limit(1)
        last_raw = next(last_cursor, None)
        last_record = _normalize_record(last_raw) if last_raw else None
        return {"shipment_number": shipment_number, "device_id": dev, "has_telemetry": count > 0, "total_records": count, "last_record": last_record}
    except HTTPException:
        raise
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
        cursor = device_collection.find(_device_query(device_id), {'_id': 0}).sort("Timestamp", -1)
        data = [_normalize_record(d) for d in cursor]
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for Device ID: {device_id}"
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        # Handle potential server errors
        raise HTTPException(status_code=500, detail=str(e))

# --- Shipment-based lookups ---

@router.get("/shipment-ids", summary="List all shipment numbers that have devices")
async def get_shipment_ids():
    try:
        valid_device_ids = set(_distinct_device_ids())
        cursor = shipments_collection.find({}, {"_id": 0, "shipment_number": 1, "device": 1})
        ids = []
        for s in cursor:
            dev = s.get("device")
            if dev and dev in valid_device_ids:
                ids.append(s.get("shipment_number"))
        return sorted(ids)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shipments/{shipment_number}", summary="Get device data by shipment number")
async def get_device_data_by_shipment(shipment_number: str):
    try:
        shipment = shipments_collection.find_one({"shipment_number": shipment_number})
        if not shipment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
        device_id = shipment.get("device")
        if not device_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment has no device assigned")

        cursor = device_collection.find(_device_query(device_id), {'_id': 0}).sort("Timestamp", -1)
        data = [_normalize_record(d) for d in cursor]
        if not data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No data found for device {device_id}")
        return {"device_id": device_id, "records": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
<th>Device Id</th>
                            <th>Battery Level</th>
                            <th>Temp</th>
                            <th>Route From</th>
                            <th>Route To</th>
                            <th>Timestamp</th>
"""
@router.post("/device-input")
def evic(Battery_Level: float, Temp: float, Route_From: str, Route_To: str, Timestamp: str):
    device_data = {
        "Battery_Level": Battery_Level,
        "Temp": Temp,
        "Route_From": Route_From,
        "Route_To": Route_To,
        "Timestamp": Timestamp
    }
    status = device_collection.insert_one(device_data)
    return {"status": "success" if status.acknowledged else "failure"}
