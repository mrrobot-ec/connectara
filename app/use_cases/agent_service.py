from app.domain.ports import LLMService, SocialGraph, MessagingService
from app.use_cases.find_matches import FindMatchesUseCase
from typing import Dict, Any, List
import logging
import json

logger = logging.getLogger(__name__)

class AgentService:
    def __init__(self, llm_service: LLMService, social_graph: SocialGraph, find_matches_use_case: FindMatchesUseCase, messaging_service: MessagingService):
        self.llm_service = llm_service
        self.social_graph = social_graph
        self.find_matches_use_case = find_matches_use_case
        self.messaging_service = messaging_service

    async def process_message(self, sender_phone: str, text: str, chat_id: str):
        """
        Process an incoming message from a user (sender_phone).
        1. Gather context (recent interactions, user profile if available).
        2. Ask LLM to determine intent and generate response.
        3. Execute actions (e.g., find matches) if needed.
        """
        logger.info(f"Agent processing message from {sender_phone}: {text}")

        # 1. Gather Context
        # Check if we know this user
        person = await self.social_graph.get_person(sender_phone) # Assuming get_person works with phone or we need a lookup
        # Actually get_person takes username. We might need a lookup by phone.
        # For now, let's assume the sender_phone IS the username or we can find them.
        # If not found, we treat them as a new user or guest.

        # Let's try to find recent interactions to give context to the LLM
        recent_interactions = await self.social_graph.find_recent_interactions(sender_phone, limit=3)

        context = {
            "user_phone": sender_phone,
            "recent_interactions": recent_interactions,
            "user_message": text
        }

        # 2. Intent Recognition & Response Generation
        # We ask the LLM to output a JSON if it wants to trigger an action, or just text.
        # Prompt Engineering:
        prompt = f"""
        You are Connectara, a helpful and friendly AI assistant for a professional community.
        You are talking to a user with phone number {sender_phone}.

        Context:
        Recent Interactions: {recent_interactions}

        User Message: "{text}"

        Your Goal:
        - Be a friendly conversational partner. You can chat about the weather, time, technology, or any general topic.
        - Do NOT push the user to find matches unless they ask for it.
        - If the user explicitly asks to "find matches", "meet people", or "who should I talk to", then trigger the 'find_matches' action.
        - If the user asks for the current time, you can provide it (assume UTC or ask for their timezone).
        - If the user asks for weather, you can say you don't have access to real-time weather data yet.

        Output Format:
        If you want to reply with text only: just write the text.
        If you want to trigger an action: write a JSON object like {{"action": "find_matches", "params": {{...}}, "reply_text": "Sure, let me look for matches..."}}

        Do not output markdown code blocks for the JSON, just the raw JSON string if it's an action.
        """

        response_text = await self.llm_service.generate_response(prompt)
        # response_text = "DEBUG: LLM Disabled"

        # Parse Response
        try:
            # simple heuristic to check if it's JSON
            if response_text.strip().startswith("{"):
                action_data = json.loads(response_text)
                action = action_data.get("action")
                reply_text = action_data.get("reply_text", "")

                if action == "find_matches":
                    await self._handle_find_matches(sender_phone, chat_id, reply_text)
                else:
                    # Unknown action, just send the text
                    await self.messaging_service.send_message(chat_id, reply_text)
            else:
                # Normal text response
                await self.messaging_service.send_message(chat_id, response_text)

        except json.JSONDecodeError:
            # Fallback if LLM messed up JSON
            await self.messaging_service.send_message(chat_id, response_text)
        except Exception as e:
            logger.error(f"Error in agent processing: {e}")
            await self.messaging_service.send_message(chat_id, "I encountered an error while processing your request.")

    async def _handle_find_matches(self, username: str, chat_id: str, initial_reply: str):
        # Send the initial "I'm looking..." message
        if initial_reply:
            await self.messaging_service.send_message(chat_id, initial_reply)

        try:
            # Execute Find Matches
            # Note: FindMatchesUseCase expects a username. If 'username' is a phone number,
            # we hope it matches the 'username' field in Neo4j or we need to resolve it.
            # For this implementation, we assume phone number IS the username or they are linked.
            matches_result = await self.find_matches_use_case.execute(username, k=10)
            matches = matches_result.get("matches", [])

            if not matches:
                await self.messaging_service.send_message(chat_id, "I couldn't find any good matches for you right now. Try updating your profile!")
                return

            # Format matches for the user
            response_lines = ["Here are some people you might like:"]
            if matches_result.get("note"):
                response_lines.append(f"(Note: {matches_result.get('note')})")

            for m in matches:
                score_text = ""
                if m.get('final_score'):
                    score = int(m.get('final_score', 0) * 100)
                    score_text = f"- {score}% Match"

                line = f"- {m.get('full_name', 'Unknown')} (@{m.get('username')}) {score_text}"
                if m.get('phone_number'):
                    line += f"\n  Phone: {m.get('phone_number')}"
                if m.get('linkedin_url'):
                    line += f"\n  LinkedIn: {m.get('linkedin_url')}"

                response_lines.append(line)

            await self.messaging_service.send_message(chat_id, "\n".join(response_lines))

        except ValueError as ve:
            await self.messaging_service.send_message(chat_id, f"I couldn't find matches: {str(ve)}")
        except Exception as e:
            logger.error(f"Find matches failed: {e}")
            await self.messaging_service.send_message(chat_id, "Something went wrong while finding matches.")
