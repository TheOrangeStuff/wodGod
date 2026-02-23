-- wodGod schema v2: multi-user auth, sex field, user cap
-- Applied after 001_schema.sql

-- ============================================================
-- ADD AUTH AND SEX FIELDS TO USERS
-- ============================================================
ALTER TABLE users ADD COLUMN username TEXT UNIQUE;
ALTER TABLE users ADD COLUMN password_hash TEXT;
ALTER TABLE users ADD COLUMN sex TEXT CHECK (sex IN ('male', 'female'));
ALTER TABLE users ADD COLUMN profile_complete BOOLEAN NOT NULL DEFAULT false;

-- Make name nullable for registration (set during first-time setup)
ALTER TABLE users ALTER COLUMN name DROP NOT NULL;
ALTER TABLE users ALTER COLUMN age DROP NOT NULL;
ALTER TABLE users ALTER COLUMN weight_kg DROP NOT NULL;
ALTER TABLE users ALTER COLUMN height_cm DROP NOT NULL;

-- Add defaults so registration only needs username + password
ALTER TABLE users ALTER COLUMN age SET DEFAULT 0;
ALTER TABLE users ALTER COLUMN weight_kg SET DEFAULT 0;
ALTER TABLE users ALTER COLUMN height_cm SET DEFAULT 0;

-- ============================================================
-- ENFORCE MAX 10 USERS
-- ============================================================
CREATE OR REPLACE FUNCTION fn_enforce_user_limit()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM users) >= 10 THEN
        RAISE EXCEPTION 'Maximum of 10 athlete profiles reached';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_user_limit
    BEFORE INSERT ON users
    FOR EACH ROW EXECUTE FUNCTION fn_enforce_user_limit();
