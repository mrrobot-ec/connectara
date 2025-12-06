from dependency_injector import containers, providers
from app.infrastructure.linkedin_piloterr import LinkedInPiloterrAdapter
from app.infrastructure.google_search_adapter import GoogleSearchAdapter
from app.infrastructure.serp_api_adapter import SerpApiDiscoveryAdapter
from app.infrastructure.playwright_crawler import PlaywrightCrawler
from app.infrastructure.bert_adapter import BertAdapter
from app.infrastructure.neo4j_adapter import Neo4jAdapter
from app.infrastructure.sentence_transformer_adapter import SentenceTransformerAdapter
from app.use_cases.analyze_profile import AnalyzeProfileUseCase
from app.use_cases.find_matches import FindMatchesUseCase
import os

from app.infrastructure.series_adapter import SeriesMessagingAdapter
from app.infrastructure.kafka_consumer import KafkaEventConsumer
from app.infrastructure.sentiment_adapter import SentimentAdapter
from app.use_cases.messaging import SendMessageUseCase, ReceiveMessageUseCase

from app.infrastructure.llm_adapter import GeminiLLMAdapter
from app.use_cases.agent_service import AgentService

class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=["app.interfaces.api"])

    config = providers.Configuration()

    # Infrastructure Adapters
    profile_fetcher = providers.Singleton(LinkedInPiloterrAdapter)

    # Switched to SerpApi
    discovery_service = providers.Singleton(
        SerpApiDiscoveryAdapter,
        api_key=os.getenv("SERP_TOKEN")
    )

    retrieval_service = providers.Singleton(PlaywrightCrawler)

    personality_analyzer = providers.Singleton(
        BertAdapter
    )

    text_embedder = providers.Singleton(
        SentenceTransformerAdapter
    )

    neo4j_adapter = providers.Singleton(
        Neo4jAdapter,
        uri=os.getenv("NEO4J_URI"),
        user=os.getenv("NEO4J_USER"),
        password=os.getenv("NEO4J_PASSWORD")
    )

    messaging_service = providers.Singleton(SeriesMessagingAdapter)

    sentiment_analyzer = providers.Singleton(SentimentAdapter)

    llm_service = providers.Singleton(
        GeminiLLMAdapter,
        api_key=os.getenv("GOOGLE_API_KEY")
    )

    # Use Cases
    analyze_profile_use_case = providers.Factory(
        AnalyzeProfileUseCase,
        profile_fetcher=profile_fetcher,
        discovery_service=discovery_service,
        retrieval_service=retrieval_service,
        personality_analyzer=personality_analyzer,
        text_embedder=text_embedder,
        social_graph=neo4j_adapter,
        job_repository=neo4j_adapter
    )

    find_matches_use_case = providers.Factory(
        FindMatchesUseCase,
        social_graph=neo4j_adapter
    )

    send_message_use_case = providers.Factory(
        SendMessageUseCase,
        messaging_service=messaging_service
    )

    agent_service = providers.Factory(
        AgentService,
        llm_service=llm_service,
        social_graph=neo4j_adapter,
        find_matches_use_case=find_matches_use_case,
        messaging_service=messaging_service
    )

    receive_message_use_case = providers.Factory(
        ReceiveMessageUseCase,
        messaging_service=messaging_service,
        sentiment_analyzer=sentiment_analyzer,
        social_graph=neo4j_adapter,
        agent_service=agent_service
    )

    # Event Consumer
    # We inject the handler from the use case
    event_consumer = providers.Singleton(
        KafkaEventConsumer,
        handler=receive_message_use_case.provided.execute
    )
