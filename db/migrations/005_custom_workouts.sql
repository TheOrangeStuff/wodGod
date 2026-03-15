-- ============================================================
-- Custom Workouts: allow user-entered freeform workouts
-- Adds custom_description column and makes program fields nullable
-- ============================================================

-- Add custom_description column for freeform workout text
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS custom_description TEXT;

-- Add is_custom flag to distinguish custom vs generated workouts
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS is_custom BOOLEAN NOT NULL DEFAULT false;

-- Make program_id nullable so custom workouts don't need a program
ALTER TABLE workouts ALTER COLUMN program_id DROP NOT NULL;

-- Make program_week nullable for custom workouts
ALTER TABLE workouts ALTER COLUMN program_week DROP NOT NULL;
ALTER TABLE workouts DROP CONSTRAINT IF EXISTS workouts_program_week_check;

-- Make day_index nullable for custom workouts
ALTER TABLE workouts ALTER COLUMN day_index DROP NOT NULL;
ALTER TABLE workouts DROP CONSTRAINT IF EXISTS workouts_day_index_check;

-- Make workout_json nullable (custom workouts may not have structured data)
ALTER TABLE workouts ALTER COLUMN workout_json DROP NOT NULL;

-- Add user_id directly to workouts for custom workouts (not tied to a program)
ALTER TABLE workouts ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Backfill user_id from program for existing workouts
UPDATE workouts w SET user_id = p.user_id
FROM programs p WHERE w.program_id = p.id AND w.user_id IS NULL;

-- Index for querying custom workouts by user
CREATE INDEX IF NOT EXISTS idx_workouts_user_custom ON workouts(user_id, is_custom) WHERE is_custom = true;
CREATE INDEX IF NOT EXISTS idx_workouts_user ON workouts(user_id);
