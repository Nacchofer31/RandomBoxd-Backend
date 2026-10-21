"""Tests for Phase 3: LLM factory and LangGraph workflow."""

import pytest

from app.core.llm import get_llm_client, get_llm_with_structured_output
from app.config import settings


class TestLLMFactory:
    """Test LLM client factory with multi-provider support."""

    def test_get_llm_client_openai(self, monkeypatch):
        """Test that OpenAI provider returns correct client type."""
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "openai_api_key", "test-key")
        
        client = get_llm_client()
        assert client is not None
        # Verify it's the correct type
        from langchain_openai import ChatOpenAI
        assert isinstance(client, ChatOpenAI)

    def test_get_llm_client_missing_api_key(self, monkeypatch):
        """Test that missing API key raises ValueError."""
        monkeypatch.setattr(settings, "llm_provider", "openai")
        monkeypatch.setattr(settings, "openai_api_key", "")
        
        with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
            get_llm_client()

    def test_get_llm_client_ollama(self, monkeypatch):
        """Test that Ollama provider returns correct client type."""
        monkeypatch.setattr(settings, "llm_provider", "ollama")
        
        client = get_llm_client()
        assert client is not None
        from langchain_ollama import ChatOllama
        assert isinstance(client, ChatOllama)

    def test_get_llm_client_unknown_provider(self, monkeypatch):
        """Test that unknown provider raises ValueError."""
        monkeypatch.setattr(settings, "llm_provider", "unknown")
        
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client()

    def test_get_llm_with_structured_output(self, monkeypatch):
        """Test that structured output wrapper works."""
        from pydantic import BaseModel
        
        class TestSchema(BaseModel):
            name: str
        
        monkeypatch.setattr(settings, "llm_provider", "ollama")
        
        client = get_llm_with_structured_output(TestSchema)
        assert client is not None


class TestWorkflow:
    """Test LangGraph workflow execution."""

    @pytest.mark.asyncio
    async def test_workflow_validates_pool(self):
        """Test that workflow validates empty pool."""
        from app.workflow.graph import recommendation_workflow
        from app.models.schemas import MoodAnswers, MoodEra, MoodEnergy, MoodCompany, PoolContext
        
        state = {
            "mood_answers": MoodAnswers(
                era=MoodEra.RECENT,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.SOLO,
            ),
            "movie_pool": [],
            "pool_context": PoolContext(),
        }
        
        result = await recommendation_workflow.ainvoke(state)
        assert result["error"] == "Movie pool is empty"

    @pytest.mark.asyncio
    async def test_workflow_completes_successfully(self):
        """Test that workflow completes with valid input."""
        from app.workflow.graph import recommendation_workflow
        from app.models.schemas import (
            Film,
            MoodAnswers,
            MoodEra,
            MoodEnergy,
            MoodCompany,
            PoolContext,
        )
        
        # Create test data
        mood_answers = MoodAnswers(
            era=MoodEra.RECENT,
            genre="SPECIFIC_ACTION",
            energy=MoodEnergy.HIGH,
            company=MoodCompany.FRIENDS,
        )
        movie_pool = [
            Film(
                slug="mad-max-fury-road-2015",
                name="Mad Max: Fury Road",
                release_year=2015,
                image_url="https://example.com/madmax.jpg",
            ),
            Film(
                slug="inception-2010",
                name="Inception",
                release_year=2010,
                image_url="https://example.com/inception.jpg",
            ),
        ]
        pool_context = PoolContext(
            user_names=["user1"],
            search_mode="UNION",
            genres=["action", "thriller"],
        )
        
        state = {
            "mood_answers": mood_answers,
            "movie_pool": movie_pool,
            "pool_context": pool_context,
        }
        
        result = await recommendation_workflow.ainvoke(state)
        
        # Should have a recommendation
        assert result["recommendation"] is not None
        assert result.get("error") is None
        
        # Should have scored films
        assert result.get("scored_films") is not None
        assert len(result["scored_films"]) > 0
        
        # Should have user profile
        assert result.get("user_profile") is not None

    @pytest.mark.asyncio
    async def test_workflow_no_era_match(self):
        """Test workflow handles no era matches."""
        from app.workflow.graph import recommendation_workflow
        from app.models.schemas import (
            Film,
            MoodAnswers,
            MoodEra,
            MoodEnergy,
            MoodCompany,
            PoolContext,
        )
        
        # Pool with only recent films, but request classic era
        state = {
            "mood_answers": MoodAnswers(
                era=MoodEra.CLASSIC,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.SOLO,
            ),
            "movie_pool": [
                Film(
                    slug="inception-2010",
                    name="Inception",
                    release_year=2010,
                    image_url="https://example.com/inception.jpg",
                ),
            ],
            "pool_context": PoolContext(),
        }
        
        result = await recommendation_workflow.ainvoke(state)
        
        # Should have error about no matches
        assert "No films match" in result["error"]

    def test_workflow_conditional_routing(self):
        """Test that conditional routing stops on errors."""
        from app.workflow.graph import should_continue, WorkflowState
        from app.models.schemas import MoodAnswers, MoodEra, MoodEnergy, MoodCompany, PoolContext
        
        # State with error
        state_with_error = WorkflowState(
            mood_answers=MoodAnswers(
                era=MoodEra.RECENT,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.SOLO,
            ),
            movie_pool=[],
            pool_context=PoolContext(),
            error="Movie pool is empty",
        )
        
        assert should_continue(state_with_error) == "error"
        
        # State without error
        state_without_error = WorkflowState(
            mood_answers=MoodAnswers(
                era=MoodEra.RECENT,
                genre="ANY",
                energy=MoodEnergy.HIGH,
                company=MoodCompany.SOLO,
            ),
            movie_pool=[],
            pool_context=PoolContext(),
        )
        
        assert should_continue(state_without_error) == "continue"
