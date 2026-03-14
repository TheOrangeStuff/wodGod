-- Add unit_system preference to users (metric or imperial)
ALTER TABLE users ADD COLUMN IF NOT EXISTS unit_system TEXT NOT NULL DEFAULT 'metric'
    CHECK (unit_system IN ('metric', 'imperial'));
