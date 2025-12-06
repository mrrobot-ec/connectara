from typing import List, Dict, Any
from app.domain.ports import (
    ProfileFetcher, DiscoveryService, RetrievalService,
    PersonalityAnalyzer, TextEmbedder, SocialGraph, JobRepository
)
from app.domain.models import Person, AnalysisJob, JobStatus
import asyncio

class AnalyzeProfileUseCase:
    def __init__(
        self,
        profile_fetcher: ProfileFetcher,
        discovery_service: DiscoveryService,
        retrieval_service: RetrievalService,
        personality_analyzer: PersonalityAnalyzer,
        text_embedder: TextEmbedder,
        social_graph: SocialGraph,
        job_repository: JobRepository
    ):
        self.profile_fetcher = profile_fetcher
        self.discovery_service = discovery_service
        self.retrieval_service = retrieval_service
        self.personality_analyzer = personality_analyzer
        self.text_embedder = text_embedder
        self.social_graph = social_graph
        self.job_repository = job_repository

    async def execute(self, job_id: str, username: str):
        try:
            # 1. Update Status
            await self.job_repository.update_job_status(job_id, JobStatus.IN_PROGRESS)

            # 2. Fetch Profile
            print(f"Fetching profile for {username}...")
            profile = await self.profile_fetcher.get_profile(username)

            # 3. Discover Posts
            print(f"Discovering posts for {username}...")
            # Use education/experience for better dorking if available
            education_names = [edu.get('schoolName') for edu in profile.raw_data.get('education', []) if edu.get('schoolName')]
            post_urls = await self.discovery_service.find_posts(profile.full_name, username, education=education_names)

            # 4. Retrieve and Validate Content
            print(f"Retrieving and validating content from {len(post_urls)} posts...")
            posts_content = await self.retrieval_service.fetch_validated_content(
                post_urls,
                expected_name=profile.full_name,
                expected_profile_url=profile.profile_url
            )
            # Take up to 5 validated posts
            posts_content = posts_content[:5]

            full_text = f"{profile.summary or ''} {' '.join(posts_content)}"

            # 5. Analyze Personality (OCEAN)
            print("Analyzing personality...")
            ocean_vector = await self.personality_analyzer.analyze(full_text)

            # 6. Generate Content Embedding (Interests)
            print("Generating content embedding...")
            content_embedding = await self.text_embedder.embed(full_text)

            # 7. Save to Graph
            traits = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
            # Create a readable string: "Openness: 0.85, Conscientiousness: 0.20..."
            readable_traits = ", ".join([f"{t}: {v:.2f}" for t, v in zip(traits, ocean_vector)])

            person = Person(
                username=username,
                profile=profile,
                ocean_vector=ocean_vector,
                content_embedding=content_embedding,
                posts=post_urls,
                personality_analysis=readable_traits
            )
            await self.social_graph.save_profile(person)

            # 8. Find Matches (Hybrid)
            print("Finding matches...")
            matches = await self.social_graph.find_matches_hybrid(content_embedding, ocean_vector, exclude_username=username)

            # 9. Update Job Status to COMPLETED
            result = {
                "profile": profile.dict(),
                "ocean_vector": ocean_vector,
                "matches": matches
            }
            await self.job_repository.update_job_status(job_id, JobStatus.COMPLETED, result=result)
            print(f"Job {job_id} completed successfully.")

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            await self.job_repository.update_job_status(job_id, JobStatus.FAILED, error=str(e))
