# backend/database.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client[os.getenv("DB_NAME", "db")] # Default to 'db' if not set

users_collection = db["users"]
# New collection for token revocation
blacklist_collection = db["token_blacklist"] 
shipments_collection = db["shipments"]
device_collection = db["device_streams"]