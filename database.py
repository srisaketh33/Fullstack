import motor.motor_asyncio
from config import MONGO_URI, MONGO_DB

print("Loading database.py...") # <--- Add this

# Initialize MongoDB client
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client[MONGO_DB]
print("db object created in database.py.") # <--- Add this