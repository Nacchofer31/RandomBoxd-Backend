"""LLM client configuration (stub for Phase 3)."""

from app.config import settings


def get_llm_client():
    """
    Get LLM client based on configuration.

    TODO: Implement in Phase 3 with LangChain integration.
    Supports OpenAI and Ollama providers.
    """
    if settings.llm_provider == "openai":
        # from langchain_openai import ChatOpenAI
        # return ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key)
        raise NotImplementedError("LLM client not yet implemented. Coming in Phase 3.")
    elif settings.llm_provider == "ollama":
        # from langchain_ollama import ChatOllama
        # return ChatOllama(model=settings.ollama_model, base_url=settings.ollama_base_url)
        raise NotImplementedError("Ollama client not yet implemented. Coming in Phase 3.")
    else:
        raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
