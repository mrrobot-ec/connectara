import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer
from dotenv import load_dotenv
import ssl

load_dotenv()

async def consume_all_messages():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("KAFKA_TOPIC")
    sasl_username = os.getenv("KAFKA_SASL_USERNAME")
    sasl_password = os.getenv("KAFKA_SASL_PASSWORD")

    if not all([bootstrap_servers, topic, sasl_username, sasl_password]):
        print("Error: Missing Kafka environment variables.")
        return

    print(f"Connecting to {bootstrap_servers} on topic {topic}...")

    # SSL Context
    ssl_context = ssl.create_default_context()

    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="debug-consumer-group-" + os.urandom(4).hex(), # Random group to fetch ALL messages
        sasl_mechanism="PLAIN",
        security_protocol="SASL_SSL",
        ssl_context=ssl_context,
        sasl_plain_username=sasl_username,
        sasl_plain_password=sasl_password,
        value_deserializer=lambda x: x.decode('utf-8'), # Raw string
        auto_offset_reset="earliest" # Start from beginning
    )

    await consumer.start()
    try:
        print("Consumer started. Listening for messages (Ctrl+C to stop)...")
        async for msg in consumer:
            print(f"[{msg.timestamp}] Offset: {msg.offset} | Value: {msg.value[:100]}...")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    try:
        asyncio.run(consume_all_messages())
    except KeyboardInterrupt:
        print("Stopped.")
