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
7. Select movements to balance categories that are underrepresented in movement_balance_last_7_days.
8. Consider fatigue_state when choosing intensity and volume.
9. If readiness is low (<=2), reduce intensity and volume.

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

MAX_RETRIES = 3


async def generate_workout(system_state: dict) -> str:
    """Call the LLM and return raw JSON string."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        system_state=json.dumps(system_state, indent=2, default=str)
    )

    if settings.LLM_PROVIDER == "ollama":
        return await _call_ollama(user_prompt)
    else:
        return await _call_openai_compatible(user_prompt)


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
