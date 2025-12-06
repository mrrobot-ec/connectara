from app.domain.ports import MessagingService, SentimentAnalyzer, SocialGraph
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SendMessageUseCase:
    def __init__(self, messaging_service: MessagingService):
        self.messaging_service = messaging_service

    async def execute(self, chat_id: str, text: str) -> Dict[str, Any]:
        try:
            await self.messaging_service.stop_typing(chat_id=chat_id)
        except Exception as e: #loose logic to passthrough if error when double-stop
            pass
        
        return await self.messaging_service.send_message(chat_id, text)

class ReceiveMessageUseCase:
    def __init__(self, messaging_service: MessagingService, sentiment_analyzer: SentimentAnalyzer, social_graph: SocialGraph, agent_service: 'AgentService'):
        self.messaging_service = messaging_service
        self.sentiment_analyzer = sentiment_analyzer
        self.social_graph = social_graph
        self.agent_service = agent_service

    async def execute(self, event: Dict[str, Any]):
        """
        Handle incoming Kafka events.
        Expected format:
        {
          "event_type": "message.received",
          "data": {
            "chat_id": "...",
            "text": "...",
            "from_phone": "...",
            "chat_handles": [ ... ]
          }
        }
        """
        event_type = event.get("event_type")
        data = event.get("data", {})

        if event_type == "message.received":
            await self._handle_message_received(data)
        elif event_type == "typing_indicator.received":
            pass # Ignore for now
        else:
            logger.info(f"Ignored event type: {event_type}")

    async def _handle_message_received(self, data: Dict[str, Any]):
        chat_id = data.get("chat_id")
        text = data.get("text")

        await self.messaging_service.mark_as_read(chat_id=chat_id)

        try:
            await self.messaging_service.start_typing(chat_id=chat_id)
        except Exception as e: #loose logic to passthrough if error when double-start
            pass

        # Better sender identification logic
        chat_handles = data.get("chat_handles", [])
        sender_handle = None

        # Find the handle that is NOT me
        for handle in chat_handles:
            if not handle.get("is_me"):
                sender_handle = handle
                break

        if not sender_handle:
            logger.warning(f"Could not identify sender for chat {chat_id}. Handles: {chat_handles}")
            return

        from_phone = sender_handle.get("identifier")

        # Double check if message is from me (redundant but safe)
        if data.get("from_phone") and data.get("from_phone") != from_phone:
             pass

        # Let's log all handles to debug.
        logger.info(f"Processing message. Chat ID: {chat_id}. Handles: {chat_handles}. Raw from_phone: {data.get('from_phone')}")

        # If the message is from the bot itself (e.g. sync), we ignore.
        is_from_me = False
        for handle in chat_handles:
            if handle.get("identifier") == data.get("from_phone") and handle.get("is_me"):
                is_from_me = True
                break

        if is_from_me:
            logger.info("Ignoring message from self.")
            return

        actual_sender = data.get("from_phone")

        logger.info(f"Received message from {actual_sender}: {text} and chat_id: {chat_id}")

        # Delegate to Agent Service
        await self.agent_service.process_message(actual_sender, text, chat_id)

        # 2. Background Processing (Sentiment + Graph) - Optional: Can be moved to AgentService or kept here
        # For now, let's keep it here or let AgentService handle it?
        # The user said "every time someone send a message the llm is the one that has to respond... and then... we have average sentiment"
        # So we should still record the interaction.

        import asyncio
        asyncio.create_task(self._process_message_background(actual_sender, text, chat_id))

    async def _process_message_background(self, sender: str, text: str, chat_id: str):
        logger.info(f"Starting background processing for message from {sender}")

        # Analyze Sentiment
        sentiment_score = 0.0
        if text:
            try:
                sentiment_score = await self.sentiment_analyzer.analyze_sentiment(text)
                logger.info(f"Sentiment Score: {sentiment_score}")
            except Exception as e:
                logger.error(f"Sentiment analysis failed: {e}")

        # Update Social Graph
        try:
            bot_username = "connectara_bot"
            await self.social_graph.record_interaction(sender, bot_username, sentiment_score, text)
            logger.info(f"Recorded interaction: {sender} -> {bot_username} (Sentiment: {sentiment_score})")
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")

