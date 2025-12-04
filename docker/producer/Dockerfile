FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY kafka_producer.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "kafka_producer.py"]

