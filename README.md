# wodGod

A stateful CrossFit programming engine for up to 10 athletes. Postgres stores structured historical data, deterministic backend logic computes trends, and an LLM generates structured workout prescriptions within enforced guardrails. Dark-mode mobile-first GUI included.

## Architecture

```
┌───────────┐     ┌──────────────┐     ┌─────────────┐
│ Postgres 15│◄───│  FastAPI      │────►│  LLM        │
│ (source of │    │  Backend      │     │  (Ollama /   │
│  truth)    │    │  (validates)  │     │   OpenAI)    │
└───────────┘     └──────┬───────┘     └─────────────┘
                         │
                    ┌────┴────┐
                    │   GUI   │
                    │ (SPA)   │
                    └─────────┘
```

**The LLM proposes. The backend enforces. The database is the source of truth.**

## Quick Start

```bash
cp .env.example .env
docker compose up -d
```

Open `http://localhost:8000` for the GUI. API docs at `http://localhost:8000/docs`.

Demo account: `demo` / `demo`

## Features

- **Multi-user auth** — JWT-based login, up to 10 athlete profiles
- **First-time setup** — name, weight, age, sex, training age, equipment
- **View WOD** — today's pre-generated workout with pre/post logging
- **Calendar** — 7-day upcoming fixed schedule
- **History** — completed workouts, RPE tracking, progression
- **Weekly batch generation** — 7 days generated in advance
- **Missed workouts skipped** — no shifting, no compression, health-first
- **Dark-mode mobile-first GUI**

## API Endpoints

### Auth (public)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Login, get JWT |
| POST | `/auth/setup-profile` | First-time profile setup |
| GET | `/auth/me` | Current user profile |

### Workouts (authenticated)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workouts/state` | Current SYSTEM_STATE JSON |
| GET | `/workouts/today` | Today's scheduled workout |
| GET | `/workouts/calendar` | 7-day upcoming calendar |
| POST | `/workouts/generate?day_index=1` | Generate single workout |
| POST | `/workouts/generate-week` | Generate full week |
| GET | `/workouts` | List workouts |
| GET | `/workouts/{id}` | Get a workout |

### Logging (authenticated)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workouts/{id}/log` | Log completed workout |
| GET | `/logs` | Recent workout logs |
| POST | `/readiness` | Submit daily readiness |
| GET | `/readiness` | Recent readiness scores |

### Programs (authenticated)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/programs/active` | Active program info |
| POST | `/programs/advance-week` | Advance to next week |
| POST | `/programs/set-phase?phase=X` | Set program phase |
| GET | `/programs/movements` | Movement taxonomy (public) |
| GET | `/programs/strength` | Strength metrics |

## Weekly Generation Policy

- Workouts generated in 7-day blocks via `/workouts/generate-week`
- Calendar is **fixed** — no regeneration mid-week
- Missed workouts are **skipped** (no shifting, no compression)
- Preserves periodization integrity and prevents CNS overload

## Workout Generation Flow

1. Backend calls `fn_build_system_state()` — assembles all trends from SQL
2. SYSTEM_STATE JSON sent to LLM with strict output schema
3. LLM returns structured workout JSON
4. Backend validates: schema, movement taxonomy, load bounds, CNS limits, phase intensity cap, aerobic floor
5. If invalid, retry up to 3 times
6. Validated workout stored in DB with scheduled date

## Database

Postgres 15 with `pgcrypto`. Schema auto-initializes via Docker init scripts.

**Tables:** `users`, `movements`, `strength_metrics`, `programs`, `workouts`, `workout_logs`, `daily_readiness`

## LLM Configuration

Supports Ollama (default) or any OpenAI-compatible API:

```
LLM_PROVIDER=ollama          # or openai_compatible
LLM_BASE_URL=http://...
LLM_MODEL=llama3
```
