-- wodGod seed data v1
-- Populates: user, movements, strength metrics, program, workout, workout log

-- ============================================================
-- SEED USER
-- ============================================================
-- password is 'demo' hashed with bcrypt (passlib-compatible $2b$ format)
INSERT INTO users (id, username, password_hash, name, age, weight_kg, height_cm, sex, training_age_yr, equipment, profile_complete)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'demo',
    '$2b$12$alQhzdRYeEru5Xmxhyx03uRv8J0eXaZ5Z2uwRV/Hbba.qC/.a18ry',
    'Demo Athlete',
    32,
    88.5,
    178.0,
    'male',
    4.0,
    '["barbell", "dumbbells", "pull_up_bar", "rower", "assault_bike", "jump_rope", "kettlebell", "rings", "box", "wall_ball", "ab_mat"]'::jsonb,
    true
);

-- ============================================================
-- SEED MOVEMENTS (controlled vocabulary)
-- ============================================================

-- Squats
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('back_squat',       'squat', true,  false),
    ('front_squat',      'squat', true,  false),
    ('overhead_squat',   'squat', true,  false),
    ('goblet_squat',     'squat', false, false),
    ('pistol_squat',     'squat', false, true),
    ('air_squat',        'squat', false, false),
    ('wall_ball',        'squat', false, false),
    ('thruster',         'squat', true,  false);

-- Hinges
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('deadlift',           'hinge', true,  false),
    ('sumo_deadlift',      'hinge', true,  false),
    ('romanian_deadlift',  'hinge', true,  false),
    ('kettlebell_swing',   'hinge', false, false),
    ('good_morning',       'hinge', true,  false),
    ('hip_thrust',         'hinge', true,  false),
    ('single_leg_rdl',     'hinge', false, true);

-- Horizontal Press
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('bench_press',       'press_horizontal', true,  false),
    ('dumbbell_bench',    'press_horizontal', false, false),
    ('push_up',           'press_horizontal', false, false),
    ('dumbbell_floor_press', 'press_horizontal', false, false);

-- Vertical Press
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('strict_press',       'press_vertical', true,  false),
    ('push_press',         'press_vertical', true,  false),
    ('push_jerk',          'press_vertical', true,  false),
    ('dumbbell_push_press','press_vertical', false, false),
    ('handstand_push_up',  'press_vertical', false, false);

-- Horizontal Pull
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('barbell_row',        'pull_horizontal', true,  false),
    ('dumbbell_row',       'pull_horizontal', false, true),
    ('ring_row',           'pull_horizontal', false, false);

-- Vertical Pull
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('pull_up',            'pull_vertical', false, false),
    ('chest_to_bar',       'pull_vertical', false, false),
    ('kipping_pull_up',    'pull_vertical', false, false),
    ('strict_pull_up',     'pull_vertical', false, false);

-- Olympic
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('clean',              'olympic', true,  false),
    ('power_clean',        'olympic', true,  false),
    ('hang_clean',         'olympic', true,  false),
    ('snatch',             'olympic', true,  false),
    ('power_snatch',       'olympic', true,  false),
    ('hang_snatch',        'olympic', true,  false),
    ('clean_and_jerk',     'olympic', true,  false);

-- Monostructural
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('rowing',             'monostructural', false, false),
    ('assault_bike',       'monostructural', false, false),
    ('run',                'monostructural', false, false),
    ('jump_rope_singles',  'monostructural', false, false),
    ('double_unders',      'monostructural', false, false);

-- Gymnastics
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('muscle_up',          'gymnastics', false, false),
    ('ring_muscle_up',     'gymnastics', false, false),
    ('bar_muscle_up',      'gymnastics', false, false),
    ('toes_to_bar',        'gymnastics', false, false),
    ('knees_to_elbow',     'gymnastics', false, false),
    ('rope_climb',         'gymnastics', false, false),
    ('box_jump',           'gymnastics', false, false),
    ('burpee',             'gymnastics', false, false);

-- Core
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('ghd_sit_up',         'core', false, false),
    ('ab_mat_sit_up',      'core', false, false),
    ('plank',              'core', false, false),
    ('l_sit',              'core', false, false),
    ('russian_twist',      'core', false, false);

-- Carry
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('farmers_carry',      'carry', false, false),
    ('front_rack_carry',   'carry', false, false),
    ('overhead_carry',     'carry', false, false);

-- Accessory
INSERT INTO movements (name, category, is_barbell, is_unilateral) VALUES
    ('banded_pull_apart',  'accessory', false, false),
    ('face_pull',          'accessory', false, false),
    ('bicep_curl',         'accessory', false, false),
    ('tricep_extension',   'accessory', false, false);

-- ============================================================
-- SEED STRENGTH METRICS
-- ============================================================
INSERT INTO strength_metrics (user_id, movement_id, training_max, estimated_1rm)
SELECT
    '11111111-1111-1111-1111-111111111111',
    m.id,
    v.training_max,
    v.estimated_1rm
FROM (VALUES
    ('back_squat',    135.0, 150.0),
    ('front_squat',   110.0, 122.0),
    ('deadlift',      170.0, 190.0),
    ('bench_press',   100.0, 112.0),
    ('strict_press',   62.0,  70.0),
    ('clean',         100.0, 112.0),
    ('snatch',         72.0,  80.0),
    ('push_press',     80.0,  90.0)
) AS v(movement_name, training_max, estimated_1rm)
JOIN movements m ON m.name = v.movement_name;

-- ============================================================
-- SEED PROGRAM
-- ============================================================
INSERT INTO programs (id, user_id, start_date, phase, week_number, is_active)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    CURRENT_DATE - INTERVAL '7 days',
    'accumulation',
    2,
    true
);

-- ============================================================
-- SEED WORKOUT (week 1, day 1)
-- ============================================================
INSERT INTO workouts (id, program_id, program_week, day_index, focus, intensity_target_rpe, cns_load, scheduled_date, workout_json)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '22222222-2222-2222-2222-222222222222',
    1,
    1,
    'lower_strength + conditioning',
    7.0,
    'moderate',
    CURRENT_DATE - INTERVAL '7 days',
    '{
        "primary_strength": {
            "movement": "back_squat",
            "scheme": "5x5",
            "load_percentage": 0.75,
            "rest_seconds": 180
        },
        "secondary_strength": {
            "movement": "romanian_deadlift",
            "scheme": "3x10",
            "load_percentage": 0.60,
            "rest_seconds": 120
        },
        "conditioning": {
            "type": "amrap",
            "time_cap_minutes": 12,
            "movements": [
                {"movement": "wall_ball", "reps": 15},
                {"movement": "kettlebell_swing", "reps": 12},
                {"movement": "box_jump", "reps": 10}
            ]
        },
        "aerobic_prescription": {
            "type": "zone2",
            "modality": "rowing",
            "duration_minutes": 15
        },
        "mobility_prompt": "Hip flexor stretch, couch stretch, pigeon pose — 2 min each side"
    }'::jsonb
);

-- ============================================================
-- SEED WORKOUT LOG
-- ============================================================
INSERT INTO workout_logs (workout_id, user_id, actual_rpe, missed_reps, performance_json, notes)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    '11111111-1111-1111-1111-111111111111',
    7.5,
    0,
    '{
        "primary_strength": {
            "completed_sets": 5,
            "completed_reps_per_set": [5, 5, 5, 5, 5],
            "load_kg": 101.25
        },
        "secondary_strength": {
            "completed_sets": 3,
            "completed_reps_per_set": [10, 10, 10],
            "load_kg": 102.0
        },
        "conditioning": {
            "rounds_completed": 3,
            "partial_reps": 8,
            "movement_logged": "wall_ball"
        },
        "aerobic": {
            "completed": true,
            "duration_minutes": 15,
            "avg_hr": 142
        }
    }'::jsonb,
    'Felt strong on squats. Conditioning was tough but manageable.'
);

-- ============================================================
-- SEED READINESS (last 3 days)
-- ============================================================
INSERT INTO daily_readiness (user_id, date, readiness_score, sleep_quality, soreness, stress) VALUES
    ('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 2, 4, 4, 2, 2),
    ('11111111-1111-1111-1111-111111111111', CURRENT_DATE - 1, 3, 3, 3, 3),
    ('11111111-1111-1111-1111-111111111111', CURRENT_DATE,     4, 4, 2, 2);
