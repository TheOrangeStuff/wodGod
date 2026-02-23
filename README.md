# wodGod

A stateful, single-user CrossFit programming engine. Postgres stores structured historical data, deterministic backend logic computes trends, and an LLM generates structured workout prescriptions within enforced guardrails.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Postgres 15 │◄───│  FastAPI      │────►│  LLM        │
│  (source of  │    │  Backend      │     │  (Ollama /   │
│   truth)     │    │  (validates)  │     │   OpenAI)    │
└─────────────┘     └──────────────┘     └─────────────┘
```

**The LLM proposes. The backend enforces. The database is the source of truth.**

The LLM does NOT control: phase transitions, progression math, intensity caps, or aerobic minimum enforcement.

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/workouts/state` | Current SYSTEM_STATE JSON |
| POST | `/workouts/generate?day_index=1` | Generate a new workout via LLM |
| GET | `/workouts` | List workouts |
| GET | `/workouts/{id}` | Get a workout |
| POST | `/workouts/{id}/log` | Log a completed workout |
| GET | `/logs` | Recent workout logs |
| POST | `/readiness` | Submit daily readiness |
| GET | `/readiness` | Recent readiness scores |
| GET | `/programs/active` | Active program info |
| POST | `/programs/advance-week` | Advance to next week |
| POST | `/programs/set-phase?phase=X` | Set program phase |
| GET | `/programs/movements` | Movement taxonomy |
| GET | `/programs/strength` | Strength metrics |

## Workout Generation Flow

1. Backend calls `fn_build_system_state()` — assembles all trends from SQL
2. SYSTEM_STATE JSON sent to LLM with strict output schema
3. LLM returns structured workout JSON
4. Backend validates: schema, movement taxonomy, load bounds, CNS limits, phase intensity cap, aerobic floor
5. If invalid, retry up to 3 times
6. Validated workout stored in DB

## Database

Postgres 15 with `pgcrypto` for UUIDs. Schema auto-initializes via Docker init scripts.

**Tables:** `users`, `movements`, `strength_metrics`, `programs`, `workouts`, `workout_logs`, `daily_readiness`

## LLM Configuration

Supports Ollama (default) or any OpenAI-compatible API. Configure via environment variables:

```
LLM_PROVIDER=ollama          # or openai_compatible
LLM_BASE_URL=http://...
LLM_MODEL=llama3
```
