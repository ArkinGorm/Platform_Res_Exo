"""
Multi-provider LangChain setup.
Supports Gemini (Google) and Ollama (local) with easy extensibility.
"""
from enum import Enum
from typing import Optional
from django.conf import settings

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_core.language_models.chat_models import BaseChatModel


class AIProvider(str, Enum):
    GEMINI = "gemini"
    OLLAMA = "ollama"


PROVIDER_LABELS = {
    AIProvider.GEMINI: "Google Gemini",
    AIProvider.OLLAMA: "Ollama — qwen2.5-coder:7b",
}

# Modèle Ollama par défaut — peut être surchargé par la variable d'env OLLAMA_MODEL
DEFAULT_OLLAMA_MODEL = getattr(settings, "OLLAMA_MODEL", "qwen2.5-coder:7b")


def get_llm(provider: str, **kwargs) -> BaseChatModel:
    """
    Factory function — returns a LangChain chat model for the given provider.

    Usage:
        llm = get_llm("ollama")                          # qwen2.5-coder:7b par défaut
        llm = get_llm("ollama", model="llama3:8b")       # autre modèle
        llm = get_llm("gemini", temperature=0.2)
    """
    provider = AIProvider(provider)

    if provider == AIProvider.GEMINI:
        return _build_gemini(**kwargs)
    elif provider == AIProvider.OLLAMA:
        return _build_ollama(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def _build_gemini(
    model: str = "gemini-3.5-flash",
    temperature: float = 0.7,
    **kwargs,
) -> ChatGoogleGenerativeAI:
    api_key = getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set in Django settings / environment."
        )
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        convert_system_message_to_human=True,
        **kwargs,
    )


def _build_ollama(
    model: Optional[str] = None,
    temperature: float = 0.7,
    base_url: Optional[str] = None,
    **kwargs,
) -> ChatOllama:
    """
    Construit un client Ollama.

    L'URL est résolue dans cet ordre de priorité :
      1. Paramètre base_url passé à la fonction
      2. Variable d'env / setting OLLAMA_BASE_URL
      3. Fallback : http://host.docker.internal:11434  (hôte depuis un conteneur)

    Le modèle est résolu dans cet ordre :
      1. Paramètre model passé à la fonction
      2. Variable d'env / setting OLLAMA_MODEL
      3. Fallback : qwen2.5-coder:7b
    """
    url = (
        base_url
        or getattr(settings, "OLLAMA_BASE_URL", None)
        or "http://host.docker.internal:11434"
    )
    resolved_model = model or DEFAULT_OLLAMA_MODEL

    return ChatOllama(
        model=resolved_model,
        base_url=url,
        temperature=temperature,
        # Augmente le timeout pour les gros modèles locaux (défaut = 120s)
        timeout=300,
        **kwargs,
    )


def list_providers() -> list[dict]:
    """Returns available providers for the frontend selector."""
    return [
        {"id": p.value, "label": PROVIDER_LABELS[p]}
        for p in AIProvider
    ]


def check_ollama_connection() -> dict:
    """
    Vérifie qu'Ollama est accessible et que qwen2.5-coder:7b est bien présent.
    Utile pour déboguer depuis le shell Django :
        from exercises.Auto_Gen.providers import check_ollama_connection
        check_ollama_connection()
    """
    import requests
    from django.conf import settings as dj_settings

    url = getattr(dj_settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    model = getattr(dj_settings, "OLLAMA_MODEL", "qwen2.5-coder:7b")

    result = {"url": url, "model": model, "reachable": False, "model_available": False}

    try:
        r = requests.get(f"{url}/api/tags", timeout=5)
        result["reachable"] = r.status_code == 200
        if result["reachable"]:
            models = [m["name"] for m in r.json().get("models", [])]
            result["available_models"] = models
            result["model_available"] = any(model in m for m in models)
    except Exception as exc:
        result["error"] = str(exc)

    return result
