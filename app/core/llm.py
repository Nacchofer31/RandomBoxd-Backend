"""LLM client factory with multi-provider support."""

from typing import Any

from langchain_core.language_models import BaseChatModel

from app.config import settings


def get_llm_client() -> BaseChatModel:
    """
    Get LLM client based on configuration.

    Supports: openai, gemini, claude, openrouter, ollama
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.7,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Gemini provider")
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=0.7,
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Claude provider")
        return ChatAnthropic(
            model=settings.claude_model,
            api_key=settings.anthropic_api_key,
            temperature=0.7,
        )

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouter provider")
        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.7,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_with_structured_output(schema: Any) -> BaseChatModel:
    """
    Get LLM client configured for structured output.

    Args:
        schema: Pydantic model schema for structured output

    Returns:
        LLM client with structured output enabled
    """
    llm = get_llm_client()

    # All LangChain chat models support with_structured_output
    return llm.with_structured_output(schema)
