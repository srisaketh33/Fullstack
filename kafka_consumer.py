# scm/kafka_consumer.py
import os
import time
import socket
import json
import traceback
from kafka import KafkaConsumer, KafkaError
from pymongo import MongoClient, errors
from dotenv import load_dotenv

load_dotenv()

# Config with sensible defaults for Compose
BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "device_data")
WAIT_TIMEOUT = int(os.getenv("WAIT_TIMEOUT", "180"))  # seconds
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017")
MONGO_DB = os.getenv("MONGO_DB", "db")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "device_streams")
RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))

def parse_host_port(bootstrap_str):
    # support "host:port" or "host1:port,host2:port"
    first = bootstrap_str.split(",")[0]
    host_port = first.rsplit(":", 1)
    if len(host_port) != 2:
        raise ValueError(f"Invalid bootstrap '{bootstrap_str}'")
    return host_port[0], int(host_port[1])

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

def wait_for_mongo(uri, timeout_s):
    start = time.time()
    while True:
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            print(f"[wait] MongoDB reachable at {uri}")
            return client
        except Exception as e:
            elapsed = time.time() - start
            if elapsed >= timeout_s:
                raise TimeoutError(f"Timed out waiting for MongoDB {uri}: {e}")
            print(f"[wait] MongoDB not reachable yet ({e}) — sleeping 1s")
            time.sleep(1)

def make_consumer(bootstrap, topic):
    # Create a consumer that will keep running
    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')) if isinstance(m, (bytes, bytearray)) else m,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        # no consumer_timeout_ms -> iterator blocks and stays running
    )

def main():
    print("[startup] Consumer starting...")
    while True:
        try:
            # 1) Wait for Kafka TCP
            host, port = parse_host_port(BOOTSTRAP)
            print(f"[startup] Waiting for Kafka at {host}:{port} (timeout {WAIT_TIMEOUT}s)")
            wait_for_tcp(host, port, WAIT_TIMEOUT)

            # 2) Wait for Mongo and get client
            print(f"[startup] Waiting for MongoDB at {MONGO_URI} (timeout {WAIT_TIMEOUT}s)")
            mongo_client = wait_for_mongo(MONGO_URI, WAIT_TIMEOUT)
            db = mongo_client[MONGO_DB]
            device_collection = db[MONGO_COLLECTION]

            # 3) Create consumer
            consumer = make_consumer(BOOTSTRAP, TOPIC)
            print(f"[startup] Connected to Kafka ({BOOTSTRAP}), consuming topic '{TOPIC}'")

            # 4) consume loop
            for msg in consumer:
                try:
                    raw_value = msg.value
                    # If value comes as JSON string for some reason, make it a dict
                    if isinstance(raw_value, str):
                        try:
                            value = json.loads(raw_value)
                        except Exception:
                            value = {"raw": raw_value}
                    else:
                        value = raw_value

                    if not isinstance(value, dict):
                        # wrap non-dict payloads
                        value = {"payload": value}

                    # optionally add metadata
                    value["_received_at"] = int(time.time())

                    # attempt insert
                    res = device_collection.insert_one(value)
                    print(f"[insert] inserted _id={res.inserted_id} value={value}")
                except Exception as e:
                    print(f"[error] failed inserting message: {e}")
                    traceback.print_exc()

        except KeyboardInterrupt:
            print("Consumer interrupted by user, exiting.")
            break
        except TimeoutError as te:
            print(f"[fatal] Timeout waiting for services: {te}")
            print(f"[info] Sleeping {RECONNECT_DELAY}s before retrying...")
            time.sleep(RECONNECT_DELAY)
            continue
        except Exception as e:
            print(f"[fatal] Unexpected consumer error: {e}")
            traceback.print_exc()
            print(f"[info] Sleeping {RECONNECT_DELAY}s before retrying...")
            time.sleep(RECONNECT_DELAY)
            continue
        finally:
            try:
                consumer.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
