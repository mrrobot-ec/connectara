import asyncio
import json
import os
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

load_dotenv()

async def produce_test_message():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    topic = os.getenv("KAFKA_TOPIC")
    sasl_username = os.getenv("KAFKA_SASL_USERNAME")
    sasl_password = os.getenv("KAFKA_SASL_PASSWORD")

    if not all([bootstrap_servers, topic, sasl_username, sasl_password]):
        print("Error: Missing Kafka environment variables.")
        return

    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        sasl_mechanism="PLAIN",
        security_protocol="SASL_SSL",
        sasl_plain_username=sasl_username,
        sasl_plain_password=sasl_password,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    await producer.start()
    try:
        message = {
            "event_type": "message.received",
            "data": {
                "chat_id": "test_chat_123",
                "text": "Hello Connectara! This is a test message.",
                "from_phone": "+1234567890",
                "chat_handles": [{"identifier": "+1234567890", "is_me": False}]
            }
        }
        print(f"Sending message to {topic}...")
        await producer.send_and_wait(topic, message)
        print("Message sent successfully!")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(produce_test_message())
