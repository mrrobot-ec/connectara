from aiokafka import AIOKafkaConsumer
from app.domain.ports import EventConsumer
import os
import json
import asyncio
from typing import Callable, Awaitable, Dict, Any

class KafkaEventConsumer(EventConsumer):
    def __init__(self, handler: Callable[[Dict[str, Any]], Awaitable[None]]):
        self.bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        self.topic = os.getenv("KAFKA_TOPIC")
        self.group_id = os.getenv("KAFKA_CONSUMER_GROUP")
        self.sasl_username = os.getenv("KAFKA_SASL_USERNAME")
        self.sasl_password = os.getenv("KAFKA_SASL_PASSWORD")
        self.handler = handler
        self.consumer = None
        self.running = False

        if not all([self.bootstrap_servers, self.topic, self.group_id, self.sasl_username, self.sasl_password]):
             # Log warning but don't crash, maybe just disable consumer
             print("WARNING: Kafka credentials missing. Consumer will not start.")
        else:
             print(f"Kafka Config: Server={self.bootstrap_servers}, Topic={self.topic}, UserLen={len(self.sasl_username)}, PassLen={len(self.sasl_password)}")

    async def start(self):
        if not self.bootstrap_servers:
            return

        print(f"Starting Kafka Consumer for topic: {self.topic}")
        import ssl
        ssl_context = ssl.create_default_context()
        self.consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            sasl_mechanism="PLAIN",
            security_protocol="SASL_SSL",
            ssl_context=ssl_context,
            sasl_plain_username=self.sasl_username,
            sasl_plain_password=self.sasl_password,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset="latest" # Only read new messages from when consumer starts
        )
        await self.consumer.start()
        self.running = True
        asyncio.create_task(self._consume_loop())

    async def stop(self):
        self.running = False
        if self.consumer:
            await self.consumer.stop()
            print("Kafka Consumer stopped.")

    async def _consume_loop(self):
        while self.running:
            try:
                async for msg in self.consumer:
                    if not self.running:
                        break

                    try:
                        print(f"DEBUG: Raw Kafka Message Received: {msg.value}", flush=True)
                        await self.handler(msg.value)
                    except Exception as e:
                        print(f"Error processing Kafka message: {e}")
            except Exception as e:
                print(f"Kafka Consumer Loop Error: {e}")
                print("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
                # aiokafka consumer might need a restart or just a retry depending on the error.
                # Ideally, we should check if consumer is closed.
                # But for now, just retrying iteration might work if it's a fetch error.
                # If connection is lost, aiokafka usually handles it, but if it raises out of the loop, we catch it here.
