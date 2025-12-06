from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.containers import Container
from app.interfaces import api
from app.domain.ports import EventConsumer
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Access container from app state or global
    # Since we create container here, we can use it directly if we keep reference
    # But better to use the one attached to app
    container = app.container
    # Ensure Neo4j Indices
    await container.neo4j_adapter().ensure_index()

    consumer: EventConsumer = container.event_consumer()
    await consumer.start()
    yield
    await consumer.stop()

def create_app() -> FastAPI:
    container = Container()

    # Wire the container to the api module
    # This is CRITICAL: We wire to the module object itself
    container.wire(modules=[api])

    app = FastAPI(lifespan=lifespan)
    app.container = container
    app.include_router(api.router)

    return app

app = create_app()
