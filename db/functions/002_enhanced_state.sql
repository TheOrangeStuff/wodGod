-- ============================================================
-- Enhanced system state: richer LLM context
-- Adds recent prescriptions, load history, extended windows
-- ============================================================

-- ============================================================
-- Movement category balance (last 21 days) — mesocycle window
-- ============================================================
CREATE OR REPLACE FUNCTION fn_movement_balance_21d(p_user_id UUID)
RETURNS JSONB AS $$
WITH workout_movements AS (
    SELECT w.workout_json -> 'primary_strength' ->> 'movement' AS movement_name
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days'
    UNION ALL
    SELECT w.workout_json -> 'secondary_strength' ->> 'movement'
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days'
    UNION ALL
    SELECT cond_mov ->> 'movement'
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id,
    jsonb_array_elements(w.workout_json -> 'conditioning' -> 'movements') AS cond_mov
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days'
),
category_counts AS (
    SELECT m.category::text AS cat, COUNT(*) AS cnt
    FROM workout_movements wm
    JOIN movements m ON m.name = wm.movement_name
    GROUP BY m.category
)
SELECT COALESCE(jsonb_object_agg(cat, cnt), '{}'::jsonb)
FROM category_counts;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Recent workout prescriptions (last 14 days)
-- Returns full workout_json + log data for recent sessions
-- ============================================================
CREATE OR REPLACE FUNCTION fn_recent_prescriptions(p_user_id UUID)
RETURNS JSONB AS $$
    SELECT COALESCE(jsonb_agg(
        jsonb_build_object(
            'scheduled_date', w.scheduled_date,
            'day_index', w.day_index,
            'focus', w.focus,
            'cns_load', w.cns_load,
            'intensity_target_rpe', w.intensity_target_rpe,
            'workout_json', w.workout_json,
            'is_custom', COALESCE(w.is_custom, false),
            'custom_description', w.custom_description,
            'actual_rpe', wl.actual_rpe,
            'missed_reps', wl.missed_reps,
            'completed_at', wl.completed_at
        ) ORDER BY wl.completed_at DESC
    ), '[]'::jsonb)
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '14 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Per-movement load history (last 21 days)
-- Returns last 4 sessions' load percentages per strength movement
-- ============================================================
CREATE OR REPLACE FUNCTION fn_movement_load_history(p_user_id UUID)
RETURNS JSONB AS $$
WITH strength_sessions AS (
    SELECT
        w.workout_json -> 'primary_strength' ->> 'movement' AS movement,
        (w.workout_json -> 'primary_strength' ->> 'load_percentage')::numeric AS load_pct,
        w.workout_json -> 'primary_strength' ->> 'scheme' AS scheme,
        wl.actual_rpe,
        wl.completed_at::date AS session_date
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days'
      AND w.workout_json -> 'primary_strength' ->> 'movement' IS NOT NULL
    UNION ALL
    SELECT
        w.workout_json -> 'secondary_strength' ->> 'movement',
        (w.workout_json -> 'secondary_strength' ->> 'load_percentage')::numeric,
        w.workout_json -> 'secondary_strength' ->> 'scheme',
        wl.actual_rpe,
        wl.completed_at::date
    FROM workout_logs wl
    JOIN workouts w ON w.id = wl.workout_id
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days'
      AND w.workout_json -> 'secondary_strength' ->> 'movement' IS NOT NULL
),
ranked AS (
    SELECT *,
        ROW_NUMBER() OVER (PARTITION BY movement ORDER BY session_date DESC) AS rn
    FROM strength_sessions
),
per_movement AS (
    SELECT movement,
        jsonb_agg(
            jsonb_build_object(
                'date', session_date,
                'load_percentage', load_pct,
                'scheme', scheme,
                'actual_rpe', actual_rpe
            ) ORDER BY session_date DESC
        ) AS sessions
    FROM ranked
    WHERE rn <= 4
    GROUP BY movement
)
SELECT COALESCE(jsonb_object_agg(movement, sessions), '{}'::jsonb)
FROM per_movement;
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Extended fatigue: rolling 21-day RPE and session count
-- ============================================================
CREATE OR REPLACE FUNCTION fn_fatigue_extended(p_user_id UUID)
RETURNS JSONB AS $$
    SELECT jsonb_build_object(
        'rolling_rpe_21d', COALESCE(ROUND(AVG(wl.actual_rpe), 1), 0),
        'sessions_completed_21d', COUNT(*)::integer,
        'missed_reps_21d', COALESCE(SUM(wl.missed_reps), 0)::integer
    )
    FROM workout_logs wl
    WHERE wl.user_id = p_user_id
      AND wl.completed_at >= now() - interval '21 days';
$$ LANGUAGE sql STABLE;

-- ============================================================
-- Update fn_build_system_state with new context fields
-- ============================================================
CREATE OR REPLACE FUNCTION fn_build_system_state(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_program RECORD;
    v_user RECORD;
    v_result JSONB;
BEGIN
    SELECT * INTO v_user FROM users WHERE id = p_user_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'User not found: %', p_user_id;
    END IF;

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
            'rolling_rpe_21d', (fn_fatigue_extended(p_user_id) ->> 'rolling_rpe_21d')::numeric,
            'missed_reps_7d', fn_missed_reps_7d(p_user_id),
            'missed_reps_21d', (fn_fatigue_extended(p_user_id) ->> 'missed_reps_21d')::integer,
            'sessions_completed_7d', fn_sessions_completed_7d(p_user_id),
            'sessions_completed_21d', (fn_fatigue_extended(p_user_id) ->> 'sessions_completed_21d')::integer,
            'cns_exposure_7d', fn_cns_exposure_7d(p_user_id),
            'avg_readiness_3d', fn_avg_readiness_3d(p_user_id),
            'latest_readiness', fn_latest_readiness(p_user_id)
        ),
        'movement_balance_last_7_days', fn_movement_balance_7d(p_user_id),
        'movement_balance_last_21_days', fn_movement_balance_21d(p_user_id),
        'recent_prescriptions', fn_recent_prescriptions(p_user_id),
        'movement_load_history', fn_movement_load_history(p_user_id),
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
