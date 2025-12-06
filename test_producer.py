import asyncio
import os
import json
import logging
from dotenv import load_dotenv
from aiokafka import AIOKafkaProducer

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def produce_test_message():
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    sasl_username = os.getenv("KAFKA_SASL_USERNAME")
    sasl_password = os.getenv("KAFKA_SASL_PASSWORD")
    topic = os.getenv("KAFKA_TOPIC")

    if not all([bootstrap_servers, sasl_username, sasl_password, topic]):
        logger.error("Missing Kafka configuration in .env")
        return

    import ssl
    context = ssl.create_default_context()

    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        sasl_mechanism="PLAIN",
        security_protocol="SASL_SSL",
        ssl_context=context,
        sasl_plain_username=sasl_username,
        sasl_plain_password=sasl_password,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    await producer.start()
    try:
        message = {
            "text": "Test message from Connectara Debugger",
            "chat_id": "debug-123",
            "from_phone": "+10000000000",
            "chat_handles": [
                {"identifier": "+10000000000", "is_me": False},
                {"identifier": "+19999999999", "is_me": True}
            ]
        }
        logger.info(f"Sending message to topic {topic}...")
        await producer.send_and_wait(topic, message)
        logger.info("Message sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(produce_test_message())
