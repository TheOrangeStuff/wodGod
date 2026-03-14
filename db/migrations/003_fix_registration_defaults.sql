-- wodGod schema v3: fix registration defaults
-- Migration 002 set defaults of 0 for age, weight_kg, height_cm, but
-- migration 001 has CHECK constraints requiring > 0. This causes INSERT
-- to fail when registering with just username + password.
-- Fix: use NULL defaults (NULL passes CHECK constraints per SQL spec).

ALTER TABLE users ALTER COLUMN age SET DEFAULT NULL;
ALTER TABLE users ALTER COLUMN weight_kg SET DEFAULT NULL;
ALTER TABLE users ALTER COLUMN height_cm SET DEFAULT NULL;
