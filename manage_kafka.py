import asyncio
import argparse
import os
import logging
from dotenv import load_dotenv
from app.infrastructure.kafka_admin_adapter import KafkaAdminAdapter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="Manage Kafka Consumer Group")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Status Command
    subparsers.add_parser("status", help="Show consumer group status and lag")

    # Purge Command
    subparsers.add_parser("purge", help="Reset offsets to LATEST (skip backlog)")

    # Replay Command
    subparsers.add_parser("replay", help="Reset offsets to EARLIEST (re-process all)")

    args = parser.parse_args()

    # Config
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    sasl_username = os.getenv("KAFKA_SASL_USERNAME")
    sasl_password = os.getenv("KAFKA_SASL_PASSWORD")
    topic = os.getenv("KAFKA_TOPIC")
    group_id = os.getenv("KAFKA_CONSUMER_GROUP")

    if not all([bootstrap_servers, sasl_username, sasl_password, topic, group_id]):
        print("Error: Missing Kafka configuration in .env")
        return

    adapter = KafkaAdminAdapter(bootstrap_servers, sasl_username, sasl_password, topic)

    try:
        if args.command == "status":
            print(f"Checking status for group: {group_id}...")
            status = await adapter.get_group_status(group_id)
            print("\n--- Consumer Group Status ---")
            print(f"Group ID: {status['group_id']}")
            print(f"Total Lag: {status['total_lag']}")
            print("Partitions:")
            for p, data in status["partitions"].items():
                print(f"  {p}: Lag={data['lag']} (Committed={data['committed']}, End={data['end']})")
            print("-----------------------------")

        elif args.command == "purge":
            confirm = input(f"WARNING: This will skip ALL pending messages for group '{group_id}'. Continue? (y/n): ")
            if confirm.lower() == 'y':
                print(f"Purging queue for group: {group_id}...")
                await adapter.reset_offsets_to_latest(group_id)
                print("Success! Queue purged.")
            else:
                print("Operation cancelled.")

        elif args.command == "replay":
            confirm = input(f"WARNING: This will re-process ALL messages in topic '{topic}' for group '{group_id}'. Continue? (y/n): ")
            if confirm.lower() == 'y':
                print(f"Resetting to earliest for group: {group_id}...")
                await adapter.reset_offsets_to_earliest(group_id)
                print("Success! Ready to replay.")
            else:
                print("Operation cancelled.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
