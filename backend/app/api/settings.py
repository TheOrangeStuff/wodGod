"""Settings endpoints — LLM provider listing and switching."""

import httpx
from fastapi import APIRouter, Depends

from app.core.auth import get_current_user_id
from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _available_providers():
    """Return list of LLM providers that have been configured via env vars."""
    providers = []

    # Ollama — configured if LLM_PROVIDER is ollama or LLM_BASE_URL looks like Ollama
    if settings.LLM_PROVIDER == "ollama" or settings.LLM_BASE_URL:
        providers.append({
            "id": "ollama",
            "name": f"Ollama ({settings.LLM_MODEL})",
            "model": settings.LLM_MODEL,
        })

    # OpenAI-compatible — configured if LLM_PROVIDER is openai_compatible
    if settings.LLM_PROVIDER == "openai_compatible":
        providers.append({
            "id": "openai_compatible",
            "name": f"OpenAI ({settings.LLM_MODEL})",
            "model": settings.LLM_MODEL,
        })

    # Claude — configured if CLAUDE_API_KEY is set
    if settings.CLAUDE_API_KEY:
        providers.append({
            "id": "claude",
            "name": f"Claude ({settings.CLAUDE_MODEL})",
            "model": settings.CLAUDE_MODEL,
        })

    return providers


@router.get("/llm")
def get_llm_settings(_user_id=Depends(get_current_user_id)):
    """Return available LLM providers and the currently active one."""
    return {
        "providers": _available_providers(),
        "active": settings.active_llm,
    }


@router.post("/llm/{provider_id}")
async def set_llm_provider(provider_id: str, _user_id=Depends(get_current_user_id)):
    """Switch the active LLM provider and test connectivity."""
    available_ids = [p["id"] for p in _available_providers()]
    if provider_id not in available_ids:
        return {"ok": False, "error": f"Provider '{provider_id}' is not configured."}

    # Test connectivity before switching
    ok, error = await _test_provider(provider_id)
    if not ok:
        return {"ok": False, "error": error}

    settings.active_llm = provider_id
    provider = next(p for p in _available_providers() if p["id"] == provider_id)
    return {"ok": True, "active": provider_id, "name": provider["name"]}


async def _test_provider(provider_id: str) -> tuple[bool, str]:
    """Test that the given provider is reachable."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider_id == "ollama":
                resp = await client.get(f"{settings.LLM_BASE_URL}/api/tags")
                resp.raise_for_status()
                return True, ""

            elif provider_id == "claude":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.CLAUDE_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.CLAUDE_MODEL,
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                resp.raise_for_status()
                return True, ""

            elif provider_id == "openai_compatible":
                headers = {"Content-Type": "application/json"}
                if settings.LLM_API_KEY:
                    headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
                resp = await client.get(
                    f"{settings.LLM_BASE_URL}/v1/models",
                    headers=headers,
                )
                resp.raise_for_status()
                return True, ""

    except httpx.ConnectError:
        return False, "Could not connect to the AI server."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return False, "Invalid API key."
        return False, f"Server returned {e.response.status_code}."
    except Exception as e:
        return False, str(e)

    return False, "Unknown provider."
