# CLAUDE.md

## Project Overview

wodGod is a stateful CrossFit programming engine for up to 10 athletes. It generates personalized workouts via an LLM, stores training history in PostgreSQL, and enforces programming rules and safety constraints. The frontend is a dark-mode, mobile-first SPA served by FastAPI.

**Architecture:** PostgreSQL <-> FastAPI (Python) <-> LLM (Ollama or OpenAI-compatible)

## Tech Stack

- **Backend:** Python 3.12, FastAPI 0.115.6, Uvicorn, psycopg2 (raw SQL, no ORM), Pydantic 2
- **Auth:** JWT (PyJWT) + bcrypt (passlib)
- **Frontend:** Vanilla JS SPA (no build step), served via FastAPI StaticFiles
- **Database:** PostgreSQL 15 with pgcrypto, ENUM types, JSONB columns, UUID PKs
- **LLM:** Ollama (default) or OpenAI-compatible APIs via httpx
- **Infrastructure:** Docker Compose for the backend; PostgreSQL is provided externally by the user

## Quick Start

The Postgres database is provided externally (not managed by docker compose). Ensure it is running and reachable before starting the backend. Database migrations are applied automatically on backend startup — no manual `psql` steps needed.

```bash
cp .env.example .env
# Edit .env to point DATABASE_URL at your Postgres instance
docker compose up -d backend
# GUI: http://localhost:8000
# API Docs: http://localhost:8000/docs
# Demo account: demo / demo
```

To manually re-run migrations (if needed):
```bash
psql $DATABASE_URL -f db/migrations/001_schema.sql
psql $DATABASE_URL -f db/migrations/002_auth_multiuser.sql
psql $DATABASE_URL -f db/functions/001_system_state.sql
psql $DATABASE_URL -f db/seeds/001_seed_data.sql
```

## Project Structure

```
backend/
  app/
    main.py              # FastAPI entry point
    api/
      auth.py            # Auth & profile endpoints
      workouts.py        # Workout CRUD & generation
      logs.py            # Workout logging & readiness
      programs.py        # Program management
    core/
      config.py          # Settings from env vars
      auth.py            # JWT, password hashing, middleware
      database.py        # Postgres connection & context manager
    models/
      auth.py            # Pydantic auth models
      workout.py         # Pydantic workout schemas
    services/
      llm_service.py     # LLM integration
      state_service.py   # System state assembly from DB
      generation_service.py  # Weekly batch generation
      validation_service.py  # Workout validation rules
  static/
    index.html           # SPA shell
    app.js               # Vanilla JS app (auth, wod, calendar, history)
    style.css            # Dark mode, mobile-first CSS
db/
  init.sh                # DB init orchestrator (runs on container start)
  migrations/            # Schema DDL (001_schema.sql, 002_auth_multiuser.sql)
  functions/             # SQL functions (fn_build_system_state)
  seeds/                 # Demo user & movement taxonomy
```

## Key Commands

```bash
# Start backend (Postgres must already be running)
docker compose up -d backend

# Rebuild after code changes
docker compose up -d --build backend

# View backend logs
docker compose logs -f backend

# Stop backend
docker compose down

# Re-run migrations (on externally-provided Postgres)
psql $DATABASE_URL -f db/migrations/001_schema.sql
```

## Code Conventions

- **Python:** PEP 8 style. FastAPI `Depends()` for auth and DB injection. Async endpoints for LLM calls, sync for DB-only.
- **SQL:** Raw parameterized queries via psycopg2 RealDictCursor. No ORM.
- **Database:** snake_case tables, ENUM types, UUIDs via `gen_random_uuid()`, `created_at`/`updated_at` timestamps (TIMESTAMPTZ).
- **API:** RESTful paths, Bearer token auth, JSON request/response bodies. Status codes: 200, 201, 401, 404, 409, 422.
- **Frontend:** Single-page app with view routing via `currentView`. kebab-case CSS classes, camelCase JS functions. Dark mode only, mobile-first (max-width 480px).
- **No formal test suite or linter configured yet.**

## API Endpoints

| Group | Endpoints |
|-------|-----------|
| Auth (public) | `POST /auth/register`, `POST /auth/login`, `POST /auth/setup-profile`, `GET /auth/me` |
| Workouts | `GET /workouts/state`, `GET /workouts/today`, `GET /workouts/calendar`, `POST /workouts/generate`, `POST /workouts/generate-week`, `GET /workouts`, `GET /workouts/{id}` |
| Logs | `POST /workouts/{id}/log`, `GET /logs`, `POST /readiness`, `GET /readiness` |
| Programs | `GET /programs/active`, `POST /programs/advance-week`, `POST /programs/set-phase`, `GET /programs/movements`, `GET /programs/strength` |
| Health | `GET /health` |

## Database

- Postgres is provided externally by the user — not managed by docker compose
- Migrations can be run manually via `psql` (see Quick Start) or automatically via `db/init.sh` if using the docker-compose `db` service
- `fn_build_system_state(user_id)` returns comprehensive JSONB (profile, fatigue, movement balance, aerobic status, progress, rules)
- Max 10 users enforced by database trigger
- Key tables: `users`, `movements`, `strength_metrics`, `programs`, `workouts`, `workout_logs`, `daily_readiness`

## Environment Variables

See `.env.example` for all configuration. Key variables:
- `JWT_SECRET` — Must change for production
- `LLM_PROVIDER` — `ollama` or `openai_compatible`
- `LLM_BASE_URL` — LLM server endpoint
- `LLM_MODEL` — Model name (e.g., `llama3`)
- `DATABASE_URL` — Full connection string (or use individual `POSTGRES_*` vars below)
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` — Individual credentials; used to auto-build `DATABASE_URL` and to bootstrap the database if it doesn't exist

## Development Status (as of 2026-03-14)

### Infrastructure Setup
- [x] `.env` configured — supports both `DATABASE_URL` and individual `POSTGRES_*` env vars
- [x] PostgreSQL connection verified
- [x] Backend runs via `docker compose up -d backend`
- [x] Auto-migration on startup via `schema_migrations` tracking table (`backend/app/core/migrate.py`)
- [x] Auto-creates `wodgod_db` database if it doesn't exist (bootstraps from individual Postgres credentials)
- [x] Migration runner handles pre-existing databases gracefully (no crash on re-run)
- [x] User registration fixed (CHECK constraint conflict on profile fields resolved)
- [ ] LLM provider configured and reachable

### User Testing
- [x] Login to the app (demo/demo or new account)
- [x] Register a new account
- [ ] Set up athlete profile
- [ ] Generate a workout (requires LLM provider)
- [ ] Log a completed workout
- [ ] Test calendar/history views
- [ ] Test readiness check-in flow
- [ ] End-to-end: generate a full week of programming
