-- wodGod schema v1
-- Requires: Postgres 15, pgcrypto

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    age             INTEGER NOT NULL CHECK (age > 0 AND age < 120),
    weight_kg       NUMERIC(5,1) NOT NULL CHECK (weight_kg > 0),
    height_cm       NUMERIC(5,1) NOT NULL CHECK (height_cm > 0),
    training_age_yr NUMERIC(4,1) NOT NULL DEFAULT 0,
    equipment       JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- MOVEMENTS (controlled vocabulary)
-- ============================================================
CREATE TYPE movement_category AS ENUM (
    'squat',
    'hinge',
    'press_horizontal',
    'press_vertical',
    'pull_horizontal',
    'pull_vertical',
    'olympic',
    'monostructural',
    'gymnastics',
    'core',
    'carry',
    'accessory'
);

CREATE TABLE movements (
    id          SERIAL PRIMARY KEY,
    name        TEXT UNIQUE NOT NULL,
    category    movement_category NOT NULL,
    is_barbell  BOOLEAN NOT NULL DEFAULT false,
    is_unilateral BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_movements_category ON movements(category);

-- ============================================================
-- STRENGTH METRICS
-- ============================================================
CREATE TABLE strength_metrics (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movement_id     INTEGER NOT NULL REFERENCES movements(id) ON DELETE CASCADE,
    training_max    NUMERIC(6,1) NOT NULL CHECK (training_max > 0),
    estimated_1rm   NUMERIC(6,1) NOT NULL CHECK (estimated_1rm > 0),
    tested_at       DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, movement_id)
);

CREATE INDEX idx_strength_user ON strength_metrics(user_id);

-- ============================================================
-- PROGRAMS
-- ============================================================
CREATE TYPE program_phase AS ENUM (
    'accumulation',
    'intensification',
    'realization',
    'deload'
);

CREATE TABLE programs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    start_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    phase       program_phase NOT NULL DEFAULT 'accumulation',
    week_number INTEGER NOT NULL DEFAULT 1 CHECK (week_number > 0),
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_programs_user_active ON programs(user_id, is_active);

-- ============================================================
-- WORKOUTS
-- ============================================================
CREATE TABLE workouts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id          UUID NOT NULL REFERENCES programs(id) ON DELETE CASCADE,
    program_week        INTEGER NOT NULL CHECK (program_week > 0),
    day_index           INTEGER NOT NULL CHECK (day_index >= 1 AND day_index <= 7),
    focus               TEXT NOT NULL,
    intensity_target_rpe NUMERIC(3,1) NOT NULL CHECK (intensity_target_rpe >= 1 AND intensity_target_rpe <= 10),
    cns_load            TEXT NOT NULL CHECK (cns_load IN ('low', 'moderate', 'high')),
    workout_json        JSONB NOT NULL,
    scheduled_date      DATE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(program_id, program_week, day_index)
);

CREATE INDEX idx_workouts_program ON workouts(program_id);
CREATE INDEX idx_workouts_date ON workouts(scheduled_date);

-- ============================================================
-- WORKOUT LOGS
-- ============================================================
CREATE TABLE workout_logs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workout_id       UUID NOT NULL REFERENCES workouts(id) ON DELETE CASCADE,
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    completed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    actual_rpe       NUMERIC(3,1) CHECK (actual_rpe >= 1 AND actual_rpe <= 10),
    missed_reps      INTEGER NOT NULL DEFAULT 0 CHECK (missed_reps >= 0),
    performance_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_logs_user ON workout_logs(user_id);
CREATE INDEX idx_logs_workout ON workout_logs(workout_id);
CREATE INDEX idx_logs_completed ON workout_logs(completed_at);

-- ============================================================
-- DAILY READINESS
-- ============================================================
CREATE TABLE daily_readiness (
    id              SERIAL PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date            DATE NOT NULL DEFAULT CURRENT_DATE,
    readiness_score INTEGER NOT NULL CHECK (readiness_score >= 1 AND readiness_score <= 5),
    sleep_quality   INTEGER CHECK (sleep_quality >= 1 AND sleep_quality <= 5),
    soreness        INTEGER CHECK (soreness >= 1 AND soreness <= 5),
    stress          INTEGER CHECK (stress >= 1 AND stress <= 5),
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, date)
);

CREATE INDEX idx_readiness_user_date ON daily_readiness(user_id, date);

-- ============================================================
-- Updated-at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_programs_updated_at
    BEFORE UPDATE ON programs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
