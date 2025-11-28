# backend/shipment.py

from fastapi import APIRouter, HTTPException, status
from pymongo import MongoClient
import os
from dotenv import load_dotenv

# Use a relative import to get the model from the models.py file in the same directory
from .models import ShipmentCreate

# --- Setup and Database Connection ---
load_dotenv()
uri = os.getenv("MONGO_URI")

try:
    mongo = MongoClient(uri)
    db = mongo["db"]
    shipments_collection = db["shipments"]
    print("Database connection for shipments established.")
except Exception as e:
    print(f"FATAL: Error connecting to MongoDB for shipments. {e}")
    exit()


# --- API Router ---
# The router is created without a prefix. This will be added in main.py.
router = APIRouter()

# --- API Route (Endpoint) ---
@router.post("/create-shipment", status_code=status.HTTP_201_CREATED)
async def create_shipment(shipment: ShipmentCreate):
    """
    Creates a new shipment record in the database.
    Checks for duplicate shipment numbers before insertion.
    """
    if shipments_collection.find_one({"shipment_number": shipment.shipment_number}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A shipment with number '{shipment.shipment_number}' already exists."
        )

    # Convert the Pydantic model to a dictionary for MongoDB
    shipment_data = shipment.model_dump() 
    
    try:
        result = shipments_collection.insert_one(shipment_data)
        if result.inserted_id:
            return {"message": "Shipment created successfully!", "shipment_id": str(result.inserted_id)}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database insertion failed.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")

@router.get("/shipments", status_code=status.HTTP_200_OK)
async def get_shipments():
    """
    Retrieves all shipment records from the database.
    """
    try:
        shipments = list(shipments_collection.find({}, {"_id": 0}))  
        # Excluding MongoDB's internal _id field for cleaner output
        return {"shipments": shipments}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}"
        )
