"""LLM integration layer for workout generation."""

import json
import httpx

from app.core.config import settings

SYSTEM_PROMPT = """You are a CrossFit programming engine. You generate structured workout prescriptions as JSON.

RULES:
1. You MUST return valid JSON matching the exact schema below — no markdown, no commentary.
2. You MUST only use movements from the allowed_movements list in the system state.
3. You MUST respect the intensity_cap_rpe for the current phase.
4. You MUST respect CNS load limits.
5. You MUST include an aerobic prescription of at least 10 minutes.
6. Load percentages are relative to the athlete's training max for that movement.
7. Select movements to balance categories that are underrepresented in movement_balance_last_7_days. Use movement_balance_last_21_days for mesocycle-level balance.
8. Consider fatigue_state when choosing intensity and volume. Use 21-day trends to detect accumulated fatigue or staleness.
9. If readiness is low (<=2), reduce intensity and volume.
10. Review recent_prescriptions to see the full workout details from the last 14 days. Do NOT repeat the same movement/scheme/load combination from the last 2-3 sessions. Vary stimulus by changing movements, rep schemes, or load percentages. Some entries may have is_custom=true with a custom_description — these are user-reported workouts done outside the program. Factor them into your programming decisions (e.g., if the user ran a 10K yesterday, avoid high-volume monostructural cardio today).
11. Use movement_load_history to intelligently progress loading. If the athlete completed a movement at a given load with RPE < 8, progress load by 2-5%. If RPE was high (>=9) or reps were missed, maintain or reduce load.
12. Avoid programming the same primary strength movement more than twice per week unless the phase specifically calls for it.

REQUIRED OUTPUT SCHEMA:
{
  "focus": "<string: e.g. 'lower_strength + conditioning'>",
  "intensity_target_rpe": <float: 1.0-10.0>,
  "time_domain": "<string: e.g. '60-75 min'>",
  "cns_load": "<string: 'low' | 'moderate' | 'high'>",
  "primary_strength": {
    "movement": "<string: from allowed_movements>",
    "scheme": "<string: e.g. '5x5'>",
    "load_percentage": <float: 0.0-1.0>,
    "rest_seconds": <int>
  },
  "secondary_strength": {
    "movement": "<string: from allowed_movements>",
    "scheme": "<string: e.g. '3x10'>",
    "load_percentage": <float: 0.0-1.0>,
    "rest_seconds": <int>
  },
  "conditioning": {
    "type": "<string: 'amrap' | 'for_time' | 'emom' | 'interval'>",
    "time_cap_minutes": <int>,
    "movements": [
      {"movement": "<string>", "reps": <int>}
    ]
  },
  "aerobic_prescription": {
    "type": "<string: e.g. 'zone2'>",
    "modality": "<string: from allowed_movements>",
    "duration_minutes": <int: >= 10>
  },
  "mobility_prompt": "<string: specific mobility work>"
}

Return ONLY the JSON object. No explanation. No markdown fences."""

USER_PROMPT_TEMPLATE = """Generate a workout prescription for the following system state.

SYSTEM STATE:
{system_state}

Generate the workout JSON now."""

CUSTOM_WORKOUT_PROMPT = """You are a CrossFit programming assistant. A user has described a workout they performed (or plan to perform) in plain text. Your job is to extract structured data from their description.

Return ONLY a JSON object with these fields:
{
  "focus": "<string: what the workout focused on, e.g. 'Cardio', 'Lower Strength', 'Mixed Modal', 'Running', 'Recovery'>",
  "intensity_target_rpe": <float: estimated RPE 1.0-10.0 based on the description>,
  "time_domain": "<string: estimated duration, e.g. '30 min'>",
  "cns_load": "<string: 'low' | 'moderate' | 'high'>",
  "summary": "<string: a clean 1-2 sentence summary of what was performed>"
}

Be reasonable with your estimates. A casual 5K run might be RPE 5-6 with low CNS load. A heavy lifting session would be higher RPE and moderate-to-high CNS.

Return ONLY the JSON object. No explanation. No markdown fences."""

MAX_RETRIES = 3


async def generate_workout(system_state: dict) -> str:
    """Call the LLM and return raw JSON string."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        system_state=json.dumps(system_state, indent=2, default=str)
    )

    provider = settings.active_llm
    if provider == "ollama":
        return await _call_ollama(user_prompt)
    elif provider == "claude":
        return await _call_claude(user_prompt)
    else:
        return await _call_openai_compatible(user_prompt)


async def parse_custom_workout(description: str) -> dict | None:
    """Use the LLM to extract structured data from a freeform workout description.

    Returns a dict with focus, intensity_target_rpe, time_domain, cns_load, summary.
    Returns None if the LLM is unavailable or parsing fails.
    """
    user_prompt = f"User's workout description:\n{description}\n\nExtract the structured data now."

    try:
        provider = settings.active_llm
        if provider == "ollama":
            raw = await _call_ollama_custom(user_prompt)
        elif provider == "claude":
            raw = await _call_claude_custom(user_prompt)
        else:
            raw = await _call_openai_compatible_custom(user_prompt)

        parsed = json.loads(raw)
        # Validate expected fields
        result = {
            "focus": str(parsed.get("focus", "Custom")),
            "intensity_target_rpe": max(1.0, min(10.0, float(parsed.get("intensity_target_rpe", 5.0)))),
            "time_domain": str(parsed.get("time_domain", "Unknown")),
            "cns_load": parsed.get("cns_load", "low") if parsed.get("cns_load") in ("low", "moderate", "high") else "low",
            "summary": str(parsed.get("summary", description[:200])),
        }
        return result
    except Exception:
        return None


async def _call_ollama_custom(user_prompt: str) -> str:
    url = f"{settings.LLM_BASE_URL}/api/chat"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": CUSTOM_WORKOUT_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _call_claude_custom(user_prompt: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": 512,
        "system": CUSTOM_WORKOUT_PROMPT,
        "messages": [{"role": "user", "content": user_prompt}],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def _call_openai_compatible_custom(user_prompt: str) -> str:
    url = f"{settings.LLM_BASE_URL}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": CUSTOM_WORKOUT_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 512,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_ollama(user_prompt: str) -> str:
    """Call Ollama API."""
    url = f"{settings.LLM_BASE_URL}/api/chat"
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.4,
            "num_predict": 2048,
        },
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def _call_claude(user_prompt: str) -> str:
    """Call Claude (Anthropic) API."""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": settings.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
    }
    payload = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": 2048,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_openai_compatible(user_prompt: str) -> str:
    """Call OpenAI-compatible API (vLLM, TGI, etc.)."""
    url = f"{settings.LLM_BASE_URL}/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 2048,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
