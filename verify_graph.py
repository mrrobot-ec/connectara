import asyncio
import os
from neo4j import AsyncGraphDatabase
from dotenv import load_dotenv

load_dotenv()

async def verify_graph():
    uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    try:
        async with driver.session() as session:
            # Check for interaction
            query = """
            MATCH ()-[r:INTERACTED_WITH]->()
            RETURN count(r) as interactions
            """
            result = await session.run(query)
            record = await result.single()
            count = record["interactions"]

            print(f"Interactions found: {count}")

            if count > 0:
                print("SUCCESS: Graph relationship created.")
            else:
                print("FAILURE: No relationship found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await driver.close()

if __name__ == "__main__":
    asyncio.run(verify_graph())
