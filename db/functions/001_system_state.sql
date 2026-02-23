-- ============================================================
-- SYSTEM STATE JSON GENERATION
-- All trend computation and state assembly in SQL
-- ============================================================

-- ============================================================
-- Rolling 7-day average RPE
-- ============================================================
CREATE OR REPLACE FUNCTION fn_rolling_rpe(p_user_id UUID, p_days INTEGER DEFAULT 7)
RETURNS NUMERIC AS $$
    SELECT COALESCE(ROUND(AVG(wl.actual_rpe), 1), 0)
    FROM workout_logs wl
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - (p_days || ' days')::interval;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Missed reps in last 7 days
-- ============================================================
CREATE OR REPLACE FUNCTION fn_missed_reps_7d(p_user_id UUID)
RETURNS INTEGER AS $$
    SELECT COALESCE(SUM(wl.missed_reps), 0)::integer
    FROM workout_logs wl
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- CNS load exposure (last 7 days)
-- Returns counts of low/moderate/high CNS sessions
-- ============================================================
CREATE OR REPLACE FUNCTION fn_cns_exposure_7d(p_user_id UUID)
RETURNS JSONB AS $$
    SELECT jsonb_build_object(
        'low',      COALESCE(SUM(CASE WHEN w.cns_load = 'low' THEN 1 ELSE 0 END), 0),
        'moderate',  COALESCE(SUM(CASE WHEN w.cns_load = 'moderate' THEN 1 ELSE 0 END), 0),
        'high',     COALESCE(SUM(CASE WHEN w.cns_load = 'high' THEN 1 ELSE 0 END), 0)
    )
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Sessions completed in last 7 days
-- ============================================================
CREATE OR REPLACE FUNCTION fn_sessions_completed_7d(p_user_id UUID)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::integer
    FROM workout_logs wl
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Zone 2 aerobic minutes in last 7 days
-- Reads from performance_json -> aerobic -> duration_minutes
-- ============================================================
CREATE OR REPLACE FUNCTION fn_zone2_minutes_7d(p_user_id UUID)
RETURNS INTEGER AS $$
    SELECT COALESCE(
        SUM(
            CASE
                WHEN (wl.performance_json -> 'aerobic' ->> 'completed')::boolean = true
                THEN (wl.performance_json -> 'aerobic' ->> 'duration_minutes')::integer
                ELSE 0
            END
        ), 0
    )::integer
    FROM workout_logs wl
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Movement category balance (last 7 days)
-- Returns how many sets hit each movement category
-- ============================================================
CREATE OR REPLACE FUNCTION fn_movement_balance_7d(p_user_id UUID)
RETURNS JSONB AS $$
WITH workout_movements AS (
    -- Extract primary strength movement
    SELECT
        wl.user_id,
        w.workout_json -> 'primary_strength' ->> 'movement' AS movement_name
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days'

    UNION ALL

    -- Extract secondary strength movement
    SELECT
        wl.user_id,
        w.workout_json -> 'secondary_strength' ->> 'movement' AS movement_name
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days'

    UNION ALL

    -- Extract conditioning movements
    SELECT
        wl.user_id,
        cond_mov ->> 'movement' AS movement_name
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id,
    jsonb_array_elements(w.workout_json -> 'conditioning' -> 'movements') AS cond_mov
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '7 days'
),
category_counts AS (
    SELECT m.category::text AS cat, COUNT(*) AS cnt
    FROM workout_movements wm
    JOIN movements m ON m.name = wm.movement_name
    GROUP BY m.category
)
SELECT COALESCE(
    jsonb_object_agg(cat, cnt),
    '{}'::jsonb
)
FROM category_counts;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Average readiness (last 3 days)
-- ============================================================
CREATE OR REPLACE FUNCTION fn_avg_readiness_3d(p_user_id UUID)
RETURNS NUMERIC AS $$
    SELECT COALESCE(ROUND(AVG(readiness_score), 1), 3.0)
    FROM daily_readiness
    WHERE user_id = p_user_id
      AND date >= CURRENT_DATE - 2;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Latest readiness entry
-- ============================================================
CREATE OR REPLACE FUNCTION fn_latest_readiness(p_user_id UUID)
RETURNS JSONB AS $$
    SELECT jsonb_build_object(
        'date', date,
        'readiness_score', readiness_score,
        'sleep_quality', sleep_quality,
        'soreness', soreness,
        'stress', stress
    )
    FROM daily_readiness
    WHERE user_id = p_user_id
    ORDER BY date DESC
    LIMIT 1;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- MAIN: Assemble full SYSTEM_STATE JSON
-- ============================================================
CREATE OR REPLACE FUNCTION fn_build_system_state(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_program RECORD;
    v_user RECORD;
    v_result JSONB;
BEGIN
    -- Fetch user
    SELECT * INTO v_user FROM users WHERE id = p_user_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

    -- Fetch active program
    SELECT * INTO v_program FROM programs
    WHERE user_id = p_user_id AND is_active = true
    ORDER BY created_at DESC LIMIT 1;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active program for user: %', p_user_id;
    END IF;

    v_result := jsonb_build_object(
        'meta', jsonb_build_object(
            'generated_at', now(),
            'program_id', v_program.id,
            'phase', v_program.phase,
            'week_number', v_program.week_number,
            'program_start_date', v_program.start_date
        ),
        'user_profile', jsonb_build_object(
            'user_id', v_user.id,
            'age', v_user.age,
            'sex', v_user.sex,
            'weight_kg', v_user.weight_kg,
            'height_cm', v_user.height_cm,
            'training_age_yr', v_user.training_age_yr,
            'equipment', v_user.equipment
        ),
        'strength_metrics', (
            SELECT COALESCE(jsonb_agg(
                jsonb_build_object(
                    'movement', m.name,
                    'category', m.category,
                    'training_max', sm.training_max,
                    'estimated_1rm', sm.estimated_1rm,
                    'tested_at', sm.tested_at
                )
            ), '[]'::jsonb)
            FROM strength_metrics sm
            JOIN movements m ON m.id = sm.movement_id
            WHERE sm.user_id = p_user_id
        ),
        'fatigue_state', jsonb_build_object(
            'rolling_rpe_7d', fn_rolling_rpe(p_user_id),
            'missed_reps_7d', fn_missed_reps_7d(p_user_id),
            'sessions_completed_7d', fn_sessions_completed_7d(p_user_id),
            'cns_exposure_7d', fn_cns_exposure_7d(p_user_id),
            'avg_readiness_3d', fn_avg_readiness_3d(p_user_id),
            'latest_readiness', fn_latest_readiness(p_user_id)
        ),
        'movement_balance_last_7_days', fn_movement_balance_7d(p_user_id),
        'aerobic_status', jsonb_build_object(
            'zone2_minutes_7d', fn_zone2_minutes_7d(p_user_id),
            'minimum_weekly_minutes', 60
        ),
        'progress_trends', jsonb_build_object(
            'total_sessions_logged', (
                SELECT COUNT(*) FROM workout_logs WHERE user_id = p_user_id
            ),
            'program_days_elapsed', (CURRENT_DATE - v_program.start_date)
        ),
        'rules', jsonb_build_object(
            'phase', v_program.phase,
            'intensity_cap_rpe', CASE v_program.phase
                WHEN 'accumulation' THEN 7.5
                WHEN 'intensification' THEN 8.5
                WHEN 'realization' THEN 9.5
                WHEN 'deload' THEN 6.0
            END,
            'max_high_cns_sessions_per_week', CASE v_program.phase
                WHEN 'accumulation' THEN 2
                WHEN 'intensification' THEN 3
                WHEN 'realization' THEN 2
                WHEN 'deload' THEN 0
            END,
            'volume_guideline', CASE v_program.phase
                WHEN 'accumulation' THEN 'high volume, moderate intensity'
                WHEN 'intensification' THEN 'moderate volume, high intensity'
                WHEN 'realization' THEN 'low volume, peak intensity'
                WHEN 'deload' THEN 'minimal volume, low intensity'
            END,
            'aerobic_minimum_weekly_minutes', 60,
            'allowed_movements', (
                SELECT jsonb_agg(name ORDER BY category, name)
                FROM movements
            )
        )
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql STABLE;
