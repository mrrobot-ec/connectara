from app.domain.ports import MessagingService, SentimentAnalyzer, SocialGraph
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SendMessageUseCase:
    def __init__(self, messaging_service: MessagingService):
        self.messaging_service = messaging_service

    async def execute(self, chat_id: str, text: str) -> Dict[str, Any]:
        return await self.messaging_service.send_message(chat_id, text)

class ReceiveMessageUseCase:
    def __init__(self, messaging_service: MessagingService, sentiment_analyzer: SentimentAnalyzer, social_graph: SocialGraph):
        self.messaging_service = messaging_service
        self.sentiment_analyzer = sentiment_analyzer
        self.social_graph = social_graph

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
        from_phone = data.get("from_phone")

        # Check if message is from me (to avoid infinite loops)
        is_from_me = False
        chat_handles = data.get("chat_handles", [])
        for handle in chat_handles:
            if handle.get("identifier") == from_phone and handle.get("is_me"):
                is_from_me = True
                break

        if is_from_me:
            logger.info("Ignoring message from self.")
            return

        logger.info(f"Received message from {from_phone}: {text}")

        # 1. Analyze Sentiment
        sentiment_score = 0.0
        if text:
            try:
                sentiment_score = await self.sentiment_analyzer.analyze_sentiment(text)
                logger.info(f"Sentiment Score: {sentiment_score}")
            except Exception as e:
                logger.error(f"Sentiment analysis failed: {e}")

        # 2. Update Social Graph
        # Assumption: For Hackathon, we treat phone numbers as usernames or identifiers if we don't have a mapping.
        # Ideally, we should look up the Person by phone number.
        # Let's assume 'Connectara' (the bot) is the 'to_username'.
        # And 'from_phone' is the 'from_username'.
        # We need to ensure these nodes exist. record_interaction does MERGE, so it will create them if missing.
        try:
            # We record interaction from User -> Bot
            # But maybe we want to record User -> User if it's a group chat?
            # For 1:1 with bot, it's User -> Bot.
            # Let's use a placeholder for the bot's username.
            bot_username = "connectara_bot"

            # We use the phone number as the username for the sender for now
            sender_username = from_phone

            await self.social_graph.record_interaction(sender_username, bot_username, sentiment_score, text)
            logger.info(f"Recorded interaction: {sender_username} -> {bot_username} (Sentiment: {sentiment_score})")
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")

        # 3. Reply (Echo + Sentiment)
        if chat_id:
            reply_text = f"Connectara received: {text}\nSentiment: {sentiment_score:.2f}"
            await self.messaging_service.send_message(str(chat_id), reply_text)
            logger.info(f"Sent reply to chat {chat_id}")
