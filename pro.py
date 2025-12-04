import os
from kafka import KafkaProducer
import json
import time
import random
from dotenv import load_dotenv
from datetime import datetime
load_dotenv('kafka.env')

# Kafka configuration
bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
topic = os.getenv("KAFKA_TOPIC", "sensor_data")

while True:
    try:
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Connected to Kafka")
        break
    except Exception as e:
        print(f"Kafka not ready, retrying in 5 seconds: {e}")
        time.sleep(5)

route = ['Newyork,USA', 'Chennai, India', 'Bengaluru, India', 'London,UK']

while True:
    routefrom = random.choice(route)
    routeto = random.choice(route)
    if routefrom != routeto:
        data = {
            "Battery_Level": round(random.uniform(2.0, 5.0), 2),
            "Device_ID": random.randint(1150, 1158),
            "First_Sensor_temperature": round(random.uniform(10, 40.0), 1),
            "Route_From": routefrom,
            "Route_To": routeto,
            "timestamp": datetime.utcnow().isoformat()
        }
        producer.send(topic, data)
        print(f"Sent to Kafka: {data}")
        time.sleep(10)