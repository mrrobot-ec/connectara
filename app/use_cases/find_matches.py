from typing import List, Dict, Any
from app.domain.ports import SocialGraph
import asyncio

class FindMatchesUseCase:
    def __init__(self, social_graph: SocialGraph):
        self.social_graph = social_graph

    async def execute(self, username: str, k: int = 10) -> Dict[str, Any]:
        # 1. Get Person
        person = await self.social_graph.get_person(username)
        if not person:
            raise ValueError(f"User '{username}' not found. Please analyze them first.")

        if not person.ocean_vector:
            raise ValueError(f"User '{username}' has no personality vector. Please re-analyze.")

        if not person.content_embedding:
             # Fallback if old profile without embedding? Or just fail?
             # For now, let's assume we need to re-analyze if missing.
             raise ValueError(f"User '{username}' has no content embedding. Please re-analyze.")

        # 2. Find Matches
        matches = await self.social_graph.find_matches_hybrid(person.content_embedding, person.ocean_vector, k=k, exclude_username=username)

        return {
            "username": username,
            "matches": matches
        }
