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

To initialize the database schema on a fresh Postgres instance, run the SQL files in order:
```bash
psql $DATABASE_URL -f db/migrations/001_schema.sql
psql $DATABASE_URL -f db/migrations/002_auth_multiuser.sql
psql $DATABASE_URL -f db/functions/001_system_state.sql
psql $DATABASE_URL -f db/functions/002_enhanced_state.sql
psql $DATABASE_URL -f db/seeds/001_seed_data.sql
```

## Project Structure

```
backend/
  app/
    main.py              # FastAPI entry point + NoCacheStaticMiddleware
    api/
      auth.py            # Auth & profile endpoints
      workouts.py        # Workout CRUD & generation
      logs.py            # Workout logging & readiness
      programs.py        # Program management
    core/
      config.py          # Settings from env vars
      auth.py            # JWT, password hashing, middleware
      bootstrap.py       # Database auto-creation on startup
      database.py        # Postgres connection & context manager
      migrate.py         # Auto-migration runner (schema_migrations table)
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
    index.html           # SPA shell (cache-busted v= query params)
    app.js               # Vanilla JS app (auth, wod, calendar, history, profile)
    style.css            # Dark mode, mobile-first CSS
db/
  init.sh                # DB init orchestrator (runs on container start)
  migrations/            # Schema DDL (001–003)
  functions/             # SQL functions (fn_build_system_state, enhanced context helpers)
  seeds/                 # Demo user & movement taxonomy
unraid/
  wodgod.xml             # Unraid Docker template for App Store installation
  Gemini_Generated_*.png # Container logo image
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
- **Frontend:** Single-page app with view routing via `currentView` (wod, calendar, history, profile). kebab-case CSS classes, camelCase JS functions. Dark mode only, mobile-first (max-width 480px). Static assets served with no-cache headers via `NoCacheStaticMiddleware`; cache-busted `?v=N` query params in `index.html`.
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
- `fn_build_system_state(user_id)` returns comprehensive JSONB (profile, fatigue, movement balance, aerobic status, progress, rules, recent prescriptions, per-movement load history)
- Enhanced LLM context (via `002_enhanced_state.sql`): `recent_prescriptions` (14-day workout history), `movement_load_history` (per-movement load/RPE for last 4 sessions), `movement_balance_last_21_days` (mesocycle balance), extended 21-day fatigue metrics
- Max 10 users enforced by database trigger
- Key tables: `users`, `movements`, `strength_metrics`, `programs`, `workouts`, `workout_logs`, `daily_readiness`

## Environment Variables

See `.env.example` for all configuration. Key variables:
- `JWT_SECRET` — Must change for production
- `LLM_PROVIDER` — `ollama` or `openai_compatible`
- `LLM_BASE_URL` — LLM server endpoint
- `LLM_MODEL` — Model name (e.g., `llama3`)
- `DATABASE_URL` — Full connection string pointing to the externally-provided Postgres instance

## Development Status (as of 2026-03-14)

### Infrastructure Setup
- [x] `.env` configured with individual Postgres credentials (POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
- [x] PostgreSQL connection verified
- [x] Backend started via `docker compose up -d backend`
- [x] Auto-migration added — backend applies all SQL migrations on startup via `schema_migrations` tracking table
- [x] Database auto-creation on startup via `bootstrap.py`
- [x] CI/CD: GitHub Actions workflow builds and pushes Docker image to GHCR with `:latest` tag on master merges
- [x] Unraid template (`unraid/wodgod.xml`) with container logo
- [x] bcrypt/passlib compatibility fixed (bcrypt pinned to 4.0.1)
- [x] Static asset caching fixed — no-cache middleware + cache-busted query params in index.html
- [x] Enhanced LLM context — recent prescriptions, per-movement load history, 21-day fatigue/balance windows fed to LLM for smarter programming
- [ ] LLM provider configured and reachable

### Frontend
- [x] Auth flow (login/register)
- [x] First-time profile setup
- [x] WOD view (today's workout display + log modal)
- [x] Calendar view (weekly overview + generate week)
- [x] History view (completed workout logs)
- [x] Profile page (Edit Profile, Settings — placeholders; Log Out with confirmation modal)
- [x] Centered header with wodGod branding
- [x] 4-tab bottom navigation (WOD, Calendar, History, Profile)

### User Testing
- [ ] Login to the app (demo/demo or new account)
- [ ] Set up athlete profile
- [ ] Generate a workout
- [ ] Log a completed workout
- [ ] Test calendar/history views
- [ ] Test readiness check-in flow
- [ ] End-to-end: generate a full week of programming
