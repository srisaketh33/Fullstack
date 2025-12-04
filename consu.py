from kafka import KafkaConsumer
from pymongo import MongoClient, errors
import json
import time
import datetime
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env and kafka.env files
load_dotenv()
load_dotenv('kafka.env')

# Kafka settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC")
KAFKA_CONSUMER_GROUP_ID = os.getenv("KAFKA_CONSUMER_GROUP_ID")

# MongoDB settings
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "iot_data")  # default database name
SENSOR_READINGS_COLLECTION = os.getenv("SENSOR_READINGS_COLLECTION", "sensor_readings")  # default collection name

# Check if required environment variables are set
if not all([KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC, KAFKA_CONSUMER_GROUP_ID, MONGODB_URI]):
    print("[✗] Required environment variables are not set. Exiting.")
    sys.exit(1)

# Retry Kafka connection
for attempt in range(10):
    try:
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id=KAFKA_CONSUMER_GROUP_ID
        )
        print("[✓] Connected to Kafka.")
        break
    except Exception as e:
        print(f"[!] Kafka connection failed: {e}. Retrying ({attempt + 1}/10)...")
        time.sleep(5)
else:
    print("[✗] Kafka is not available after multiple attempts. Exiting.")
    sys.exit(1)

try:
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db[SENSOR_READINGS_COLLECTION]
    print("[✓] Connected to MongoDB.")
except errors.ConnectionFailure as e:
    print(f"[✗] MongoDB connection error: {e}")
    sys.exit(1)

print("[*] Kafka consumer started. Waiting for messages...")

for message in consumer:
    try:
        data = message.value
        data['timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        collection.insert_one(data)
        print(f"[→] Inserted into MongoDB: {data}")
    except Exception as e:
        print(f"[!] Error inserting data: {e}")