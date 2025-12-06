from app.domain.ports import MessagingAdminService
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka import AIOKafkaConsumer, TopicPartition
from typing import Dict, Any, List
import logging
import asyncio

logger = logging.getLogger(__name__)

class KafkaAdminAdapter(MessagingAdminService):
    def __init__(self, bootstrap_servers: str, sasl_username: str, sasl_password: str, topic: str):
        self.bootstrap_servers = bootstrap_servers
        self.sasl_username = sasl_username
        self.sasl_password = sasl_password
        self.topic = topic

        self.ssl_context = self._create_ssl_context()

    def _create_ssl_context(self):
        import ssl
        context = ssl.create_default_context()
        return context

    async def get_group_status(self, group_id: str) -> Dict[str, Any]:
        # 1. Fetch Committed Offsets (using AdminClient to avoid joining group)
        admin_client = AIOKafkaAdminClient(
            bootstrap_servers=self.bootstrap_servers,
            sasl_mechanism="PLAIN",
            security_protocol="SASL_SSL",
            ssl_context=self.ssl_context,
            sasl_plain_username=self.sasl_username,
            sasl_plain_password=self.sasl_password,
        )
        await admin_client.start()
        try:
            # This returns {TopicPartition: OffsetAndMetadata}
            committed_offsets = await admin_client.list_consumer_group_offsets(group_id)
        finally:
            await admin_client.close()

        # 2. Fetch End Offsets (using a standalone Consumer, no group_id)
        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=None, # Important: Do not join a group!
            sasl_mechanism="PLAIN",
            security_protocol="SASL_SSL",
            ssl_context=self.ssl_context,
            sasl_plain_username=self.sasl_username,
            sasl_plain_password=self.sasl_password,
            enable_auto_commit=False
        )
        await consumer.start()
        try:
            # Get partitions for topic
            partitions = [TopicPartition(self.topic, p) for p in consumer.partitions_for_topic(self.topic)]

            # Get end offsets
            end_offsets = await consumer.end_offsets(partitions)

            status = {}
            total_lag = 0

            for tp in partitions:
                # Find committed offset for this partition
                committed_meta = committed_offsets.get(tp)
                committed_offset = committed_meta.offset if committed_meta else 0

                end_offset = end_offsets.get(tp, 0)
                lag = end_offset - committed_offset

                status[f"partition_{tp.partition}"] = {
                    "committed": committed_offset,
                    "end": end_offset,
                    "lag": lag
                }
                total_lag += lag

            return {"group_id": group_id, "total_lag": total_lag, "partitions": status}

        finally:
            await consumer.stop()

    async def reset_offsets_to_latest(self, group_id: str) -> None:
        await self._reset_offsets(group_id, to_earliest=False)

    async def reset_offsets_to_earliest(self, group_id: str) -> None:
        await self._reset_offsets(group_id, to_earliest=True)

    async def _reset_offsets(self, group_id: str, to_earliest: bool) -> None:
        # Note: We use manual assignment to avoid rebalance delays and ensure we can seek/commit.
        consumer = AIOKafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            sasl_mechanism="PLAIN",
            security_protocol="SASL_SSL",
            ssl_context=self.ssl_context,
            sasl_plain_username=self.sasl_username,
            sasl_plain_password=self.sasl_password,
            enable_auto_commit=False # We commit manually
        )
        await consumer.start()
        try:
            # Get all partitions for the topic
            partitions = [TopicPartition(self.topic, p) for p in consumer.partitions_for_topic(self.topic)]

            # Manually assign them (steals from other consumers, but that's what we want for a reset)
            consumer.assign(partitions)

            if to_earliest:
                await consumer.seek_to_beginning(*partitions)
            else:
                await consumer.seek_to_end(*partitions)

            # Commit the new offsets
            await consumer.commit()
            logger.info(f"Offsets reset for group {group_id} (Earliest: {to_earliest})")
        finally:
            await consumer.stop()
