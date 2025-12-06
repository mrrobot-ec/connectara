import unittest
from unittest.mock import AsyncMock, MagicMock
import asyncio
from app.use_cases.analyze_profile import AnalyzeProfileUseCase
from app.domain.models import Profile, JobStatus

class TestAnalyzeProfileFlow(unittest.TestCase):
    def setUp(self):
        self.profile_fetcher = AsyncMock()
        self.discovery_service = AsyncMock()
        self.retrieval_service = AsyncMock()
        self.personality_analyzer = AsyncMock()
        self.social_graph = AsyncMock()
        self.job_repository = AsyncMock()

        self.use_case = AnalyzeProfileUseCase(
            self.profile_fetcher,
            self.discovery_service,
            self.retrieval_service,
            self.personality_analyzer,
            self.social_graph,
            self.job_repository
        )

    def test_flow(self):
        async def run_test():
            # Setup Mocks
            self.profile_fetcher.get_profile.return_value = Profile(
                username="testuser",
                full_name="Test User",
                summary="I am a test user."
            )
            self.discovery_service.find_posts.return_value = ["http://linkedin.com/post/1"]
            self.retrieval_service.fetch_content.return_value = ["Post content 1"]
            self.personality_analyzer.analyze.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
            self.social_graph.find_similar_peers.return_value = [{"username": "peer1", "score": 0.9}]

            # Execute
            await self.use_case.execute("job-123", "testuser")

            # Verify
            self.job_repository.update_job_status.assert_any_call("job-123", JobStatus.IN_PROGRESS)
            self.profile_fetcher.get_profile.assert_called_with("testuser")
            self.discovery_service.find_posts.assert_called_with("Test User", "testuser")
            self.retrieval_service.fetch_content.assert_called_with(["http://linkedin.com/post/1"])
            self.personality_analyzer.analyze.assert_called()
            self.social_graph.save_profile.assert_called()
            self.social_graph.find_similar_peers.assert_called_with([0.1, 0.2, 0.3, 0.4, 0.5])
            self.job_repository.update_job_status.assert_called_with(
                "job-123",
                JobStatus.COMPLETED,
                result={
                    "profile": self.profile_fetcher.get_profile.return_value.dict(),
                    "ocean_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "matches": [{"username": "peer1", "score": 0.9}]
                }
            )

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
