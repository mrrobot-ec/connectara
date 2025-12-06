from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase
from app.domain.ports import SocialGraph, JobRepository
from app.domain.models import Person, AnalysisJob, JobStatus
import os
import json
from datetime import datetime

class Neo4jAdapter(SocialGraph, JobRepository):
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "password")
        self.driver = AsyncGraphDatabase.driver(self.uri, auth=(self.user, self.password))

    async def ensure_index(self):
        # Index for Personality (OCEAN) - Optional now if we rely on Content
        query_ocean = """
        CREATE VECTOR INDEX person_personality_index IF NOT EXISTS
        FOR (p:Person)
        ON (p.ocean_vector)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 5,
            `vector.similarity_function`: 'cosine'
        }}
        """

        # Index for Content (Interests)
        # all-MiniLM-L6-v2 has 384 dimensions
        query_content = """
        CREATE VECTOR INDEX person_content_index IF NOT EXISTS
        FOR (p:Person)
        ON (p.content_embedding)
        OPTIONS {indexConfig: {
            `vector.dimensions`: 384,
            `vector.similarity_function`: 'cosine'
        }}
        """

        max_retries = 10
        for attempt in range(max_retries):
            try:
                async with self.driver.session() as session:
                    await session.run(query_ocean)
                    await session.run(query_content)
                    print("DEBUG: Neo4j Vector Indices ensured.")
                    return
            except Exception as e:
                print(f"DEBUG: Attempt {attempt+1}/{max_retries} - Waiting for Neo4j... ({e})")
                await asyncio.sleep(2)

        print("ERROR: Could not connect to Neo4j after multiple attempts.")

    async def close(self):
        await self.driver.close()

    async def save_profile(self, person: Person) -> None:
        query = """
        MERGE (p:Person {username: $username})
        SET p.full_name = COALESCE($full_name, p.full_name),
            p.headline = COALESCE($headline, p.headline),
            p.summary = COALESCE($summary, p.summary),
            p.location = COALESCE($location, p.location),
            p.ocean_vector = COALESCE($ocean_vector, p.ocean_vector),
            p.content_embedding = COALESCE($content_embedding, p.content_embedding),
            p.personality_analysis = COALESCE($personality_analysis, p.personality_analysis),
            p.posts = $posts,
            p.updated_at = datetime()
        """
        params = {
            "username": person.username,
            "full_name": person.profile.full_name,
            "headline": person.profile.headline,
            "summary": person.profile.summary,
            "location": person.profile.location,
            "ocean_vector": person.ocean_vector,
            "content_embedding": person.content_embedding,
            "personality_analysis": person.personality_analysis,
            "posts": person.posts
        }
        async with self.driver.session() as session:
            await session.run(query, params)

    async def get_person(self, username: str) -> Optional[Person]:
        query = """
        MATCH (p:Person {username: $username})
        RETURN p
        """
        async with self.driver.session() as session:
            result = await session.run(query, username=username)
            record = await result.single()
            if not record:
                return None

            node = record["p"]
            # Reconstruct Person object (simplified, assuming Profile data is flattened or we just need vector)
            # Note: We might need to adjust Person model to be more flexible if fields are missing
            from app.domain.models import Profile
            return Person(
                username=node["username"],
                profile=Profile(
                    username=node["username"],
                    full_name=node.get("full_name"),
                    headline=node.get("headline"),
                    summary=node.get("summary"),
                    location=node.get("location")
                ),
                ocean_vector=node.get("ocean_vector"),
                content_embedding=node.get("content_embedding"),
                posts=node.get("posts", []),
                personality_analysis=node.get("personality_analysis")
            )

    async def find_similar_peers(self, content_embedding: List[float], k: int = 10, exclude_username: str = None) -> List[Dict[str, Any]]:
        # Hybrid Matching Strategy:
        # 1. Retrieve candidates based on Content Similarity (Interests)
        # 2. Return them (Client-side or UseCase can re-rank, but for now let's just return content matches)
        # Note: The user asked to use embeddings for summary+posts (Content) and OCEAN for compatibility.
        # Ideally, we should pass content_embedding here, not ocean_vector.
        # But the interface currently takes ocean_vector. We need to update the interface or overload it.
        # For now, let's assume the UseCase passes the content_embedding in the first argument if we change the flow.
        # BUT, to be clean, we should update the signature or method.

        # Let's assume the caller (UseCase) will now pass the CONTENT embedding to a new method or we update this one.
        # Since we are refactoring, let's update this method to take `embedding` and `embedding_type`.

        # WAIT: I need to update the interface first if I change the signature significantly.
        # The user said: "get embeddings for summary and posts... not for OCEAN".
        # So the primary retrieval should be on content_embedding.

        # I will implement a new method `find_matches` that takes both vectors?
        # Or just update this one to use content index.

        # Let's stick to the plan: Update Neo4jAdapter (New Index + Hybrid Matching).
        # I'll implement the logic assuming I have access to the content embedding.
        # I will modify the signature in the next step or assume the `ocean_vector` argument is actually the `content_embedding` for now?
        # No, that's hacky. I'll add `content_embedding` to the arguments.

        # Use the new content_embedding for similarity search
        query = """
        CALL db.index.vector.queryNodes('person_content_index', $k + 1, $content_embedding)
        YIELD node, score
        WHERE ($exclude_username IS NULL OR node.username <> $exclude_username)
        RETURN node.username AS username,
               node.full_name AS full_name,
               node.headline AS headline,
               score
        LIMIT $k
        """
        async with self.driver.session() as session:
            result = await session.run(query, k=k, content_embedding=content_embedding, exclude_username=exclude_username)
            records = await result.data()
            return records

    async def find_matches_hybrid(self, content_embedding: List[float], ocean_vector: List[float], k: int = 10, exclude_username: str = None) -> List[Dict[str, Any]]:
        # 1. Candidate Retrieval (Content Similarity)
        # Fetch top 50 candidates based on interests (content embedding)
        query = """
        CALL db.index.vector.queryNodes('person_content_index', 50, $content_embedding)
        YIELD node, score AS content_score
        WHERE ($exclude_username IS NULL OR node.username <> $exclude_username)
        RETURN node.username AS username,
               node.full_name AS full_name,
               node.headline AS headline,
               node.ocean_vector AS ocean_vector,
               content_score
        """

        candidates = []
        async with self.driver.session() as session:
            result = await session.run(query, content_embedding=content_embedding, exclude_username=exclude_username)
            candidates = await result.data()

        # 2. Re-ranking (Personality Compatibility)
        # Heuristic:
        # - High O + High O (Shared Interest)
        # - High C + High A (Harmony)
        # - High E + Low N (Stability)
        # - Complementary: High E + Low E (Balance)

        def calculate_compatibility(user_ocean, peer_ocean):
            if not user_ocean or not peer_ocean:
                return 0.5 # Neutral if missing data

            # O, C, E, A, N indices: 0, 1, 2, 3, 4
            score = 0.0

            # Openness (0): Similarity is good (Shared Interests)
            score += 1.0 - abs(user_ocean[0] - peer_ocean[0])

            # Conscientiousness (1) & Agreeableness (3): High + High is good
            if user_ocean[1] > 0.6 and peer_ocean[3] > 0.6: score += 0.5
            if peer_ocean[1] > 0.6 and user_ocean[3] > 0.6: score += 0.5

            # Extraversion (2): Balance (Complementary)
            # score += abs(user_ocean[2] - peer_ocean[2]) # Difference is good? Or similarity?
            # User said: "Introverts and Extroverts can balance each other" -> Difference is good.
            score += abs(user_ocean[2] - peer_ocean[2]) * 0.5

            # Neuroticism (4): Low is generally better for stability
            # High N clashes with Low A or Low C.
            if user_ocean[4] > 0.7:
                if peer_ocean[3] < 0.4: score -= 0.5 # Clash with Low A
                if peer_ocean[1] < 0.4: score -= 0.5 # Clash with Low C

            return score

        ranked_results = []
        for cand in candidates:
            peer_ocean = cand.get("ocean_vector")
            compatibility_score = calculate_compatibility(ocean_vector, peer_ocean)

            # Final Score = Weighted Average of Content (Interests) and Personality (Compatibility)
            # Adjust weights as needed. 0.6 Content / 0.4 Personality
            final_score = (cand["content_score"] * 0.6) + (compatibility_score * 0.1) # Scale compatibility down as it's additive

            cand["compatibility_score"] = compatibility_score
            cand["final_score"] = final_score
            ranked_results.append(cand)

        # Sort by final score
        ranked_results.sort(key=lambda x: x["final_score"], reverse=True)

        return ranked_results[:k]

    async def record_interaction(self, from_username: str, to_username: str, sentiment: float, text: str) -> None:
        query = """
        MERGE (a:Person {username: $from_username})
        MERGE (b:Person {username: $to_username})
        MERGE (a)-[r:INTERACTED_WITH]->(b)
        ON CREATE SET
            r.weight = 1,
            r.avg_sentiment = $sentiment,
            r.last_interaction = datetime(),
            r.total_messages = 1
        ON MATCH SET
            r.avg_sentiment = (r.avg_sentiment * r.total_messages + $sentiment) / (r.total_messages + 1),
            r.weight = r.weight + 1,
            r.total_messages = r.total_messages + 1,
            r.last_interaction = datetime()
        """
        async with self.driver.session() as session:
            await session.run(query, from_username=from_username, to_username=to_username, sentiment=sentiment)

    # JobRepository Implementation
    async def create_job(self, job: AnalysisJob) -> None:
        query = """
        CREATE (j:AnalysisJob {
            job_id: $job_id,
            username: $username,
            status: $status,
            created_at: $created_at,
            updated_at: $updated_at
        })
        """
        params = {
            "job_id": job.job_id,
            "username": job.username,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
        async with self.driver.session() as session:
            await session.run(query, params)

    async def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        query = """
        MATCH (j:AnalysisJob {job_id: $job_id})
        RETURN j
        """
        async with self.driver.session() as session:
            result = await session.run(query, job_id=job_id)
            record = await result.single()
            if not record:
                return None

            node = record["j"]
            return AnalysisJob(
                job_id=node["job_id"],
                username=node["username"],
                status=JobStatus(node["status"]),
                result=json.loads(node["result"]) if node.get("result") else None,
                error=node.get("error"),
                created_at=datetime.fromisoformat(node["created_at"]),
                updated_at=datetime.fromisoformat(node["updated_at"])
            )

    async def update_job_status(self, job_id: str, status: JobStatus, result: Optional[Dict] = None, error: Optional[str] = None) -> None:
        query = """
        MATCH (j:AnalysisJob {job_id: $job_id})
        SET j.status = $status,
            j.updated_at = $updated_at,
            j.result = $result,
            j.error = $error
        """
        params = {
            "job_id": job_id,
            "status": status.value,
            "updated_at": datetime.utcnow().isoformat(),
            "result": json.dumps(result) if result else None,
            "error": error
        }
        async with self.driver.session() as session:
            await session.run(query, params)
