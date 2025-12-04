# scm/kafka_consumer.py
import os
import time
import socket
import json
from kafka import KafkaConsumer
from pymongo import MongoClient, errors
from dotenv import load_dotenv

load_dotenv()

DEFAULT_BOOTSTRAP = "kafka:9092"
bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", DEFAULT_BOOTSTRAP)
wait_timeout = int(os.getenv("WAIT_TIMEOUT", "120"))  # seconds
topic = os.getenv("KAFKA_TOPIC", "device_data")
mongo_uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")  # adjust if needed
mongo_db_name = os.getenv("MONGO_DB", "db")
mongo_collection = os.getenv("MONGO_COLLECTION", "device_streams")

def parse_host_port(bootstrap_str):
    first = bootstrap_str.split(",")[0]
    host, port = first.split(":")
    return host, int(port)

def wait_for_tcp(host, port, timeout_s):
    start = time.time()
    while True:
        try:
            with socket.create_connection((host, port), timeout=3):
                print(f"[wait] {host}:{port} reachable")
                return True
        except OSError:
            elapsed = time.time() - start
            if elapsed >= timeout_s:
                raise TimeoutError(f"Timed out waiting for {host}:{port} after {timeout_s}s")
            print(f"[wait] {host}:{port} not reachable yet — sleeping 1s")
            time.sleep(1)

# Wait for Kafka
host, port = parse_host_port(bootstrap)
wait_for_tcp(host, port, wait_timeout)

# Connect to MongoDB with retries (if Mongo is remote or in a service)
mongo = None
start = time.time()
while True:
    try:
        mongo = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        # attempt an operation that forces a server selection
        mongo.admin.command('ping')
        print(f"[mongo] Connected to MongoDB ({mongo_uri})")
        break
    except Exception as e:
        elapsed = time.time() - start
        if elapsed >= wait_timeout:
            print(f"[mongo] Could not connect to MongoDB within {wait_timeout}s: {e}")
            raise
        print(f"[mongo] Waiting for MongoDB ({mongo_uri}) — sleeping 1s")
        time.sleep(1)

db = mongo[mongo_db_name]
device_collection = db[mongo_collection]

# Create Kafka consumer
consumer = KafkaConsumer(
    topic,
    bootstrap_servers=bootstrap,
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    consumer_timeout_ms=1000  # adjust if needed
)

print("[consumer] Kafka consumer started. Waiting for messages...")

try:
    for message in consumer:
        data = message.value
        device_collection.insert_one(data)
        print(f"[consumer] Inserted into MongoDB: {data}")
except KeyboardInterrupt:
    print("Consumer interrupted, exiting.")
except Exception as e:
    print(f"Consumer fatal error: {e}")
    raise
finally:
    try:
        consumer.close()
    except Exception:
        pass
