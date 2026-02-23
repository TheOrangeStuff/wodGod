"""Validates LLM-generated workout prescriptions against system rules."""

import json
from dataclasses import dataclass, field

from app.models.workout import WorkoutPrescription, CnsLoad
from app.services.state_service import get_allowed_movements


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str):
        self.valid = False
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)


def validate_workout(
    prescription: WorkoutPrescription,
    system_state: dict,
) -> ValidationResult:
    """Run all validation checks against the prescription."""
    result = ValidationResult()
    rules = system_state.get("rules", {})
    fatigue = system_state.get("fatigue_state", {})
    aerobic = system_state.get("aerobic_status", {})

    _validate_schema(prescription, result)
    _validate_movements(prescription, rules, result)
    _validate_intensity(prescription, rules, result)
    _validate_cns(prescription, rules, fatigue, result)
    _validate_aerobic(prescription, aerobic, result)
    _validate_load_bounds(prescription, system_state, result)

    return result


def _validate_schema(rx: WorkoutPrescription, result: ValidationResult):
    """Verify required fields are present and well-formed."""
    if not rx.focus:
        result.add_error("Missing 'focus' field")
    if not rx.mobility_prompt:
        result.add_error("Missing 'mobility_prompt'")
    if not rx.conditioning.movements:
        result.add_error("Conditioning must include at least one movement")


def _validate_movements(
    rx: WorkoutPrescription, rules: dict, result: ValidationResult
):
    """Ensure all movements are from the allowed taxonomy."""
    allowed = set(rules.get("allowed_movements", []))
    if not allowed:
        allowed = set(get_allowed_movements())

    all_movements = [
        rx.primary_strength.movement,
        rx.secondary_strength.movement,
        rx.aerobic_prescription.modality,
    ] + [m.movement for m in rx.conditioning.movements]

    for mov in all_movements:
        if mov not in allowed:
            result.add_error(f"Movement '{mov}' is not in allowed taxonomy")


def _validate_intensity(
    rx: WorkoutPrescription, rules: dict, result: ValidationResult
):
    """Check intensity against phase cap."""
    cap = rules.get("intensity_cap_rpe")
    if cap is not None and rx.intensity_target_rpe > cap:
        result.add_error(
            f"RPE {rx.intensity_target_rpe} exceeds phase cap of {cap}"
        )


def _validate_cns(
    rx: WorkoutPrescription,
    rules: dict,
    fatigue: dict,
    result: ValidationResult,
):
    """Check CNS load against weekly limits."""
    if rx.cns_load == CnsLoad.HIGH:
        max_high = rules.get("max_high_cns_sessions_per_week", 2)
        cns_exposure = fatigue.get("cns_exposure_7d", {})
        current_high = cns_exposure.get("high", 0)
        if current_high >= max_high:
            result.add_error(
                f"Already {current_high} high-CNS sessions this week "
                f"(max {max_high}). Cannot add another."
            )

    # Deload phase: no high CNS
    phase = rules.get("phase")
    if phase == "deload" and rx.cns_load == CnsLoad.HIGH:
        result.add_error("High CNS load not allowed during deload phase")


def _validate_aerobic(
    rx: WorkoutPrescription, aerobic: dict, result: ValidationResult
):
    """Check aerobic prescription meets minimums."""
    min_weekly = aerobic.get("minimum_weekly_minutes", 60)
    current = aerobic.get("zone2_minutes_7d", 0)
    prescribed = rx.aerobic_prescription.duration_minutes

    if prescribed < 10:
        result.add_warning(
            f"Aerobic prescription of {prescribed} min is very short"
        )

    remaining_needed = max(0, min_weekly - current)
    if remaining_needed > 0 and prescribed < 10:
        result.add_warning(
            f"Only {current} of {min_weekly} aerobic minutes completed "
            f"this week. Consider prescribing at least {remaining_needed} min."
        )


def _validate_load_bounds(
    rx: WorkoutPrescription, state: dict, result: ValidationResult
):
    """Check load percentages are reasonable for the phase."""
    phase = state.get("rules", {}).get("phase", "accumulation")

    max_load_pct = {
        "accumulation": 0.80,
        "intensification": 0.90,
        "realization": 0.95,
        "deload": 0.60,
    }.get(phase, 0.85)

    for label, block in [
        ("primary_strength", rx.primary_strength),
        ("secondary_strength", rx.secondary_strength),
    ]:
        if block.load_percentage > max_load_pct:
            result.add_error(
                f"{label} load {block.load_percentage:.0%} exceeds "
                f"phase max of {max_load_pct:.0%}"
            )
        if block.load_percentage < 0.30:
            result.add_warning(
                f"{label} load {block.load_percentage:.0%} is unusually low"
            )


def parse_and_validate(
    raw_json: str, system_state: dict
) -> tuple[WorkoutPrescription | None, ValidationResult]:
    """Parse raw LLM JSON output and validate it."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        result = ValidationResult()
        result.add_error(f"Invalid JSON from LLM: {e}")
        return None, result

    try:
        prescription = WorkoutPrescription(**data)
    except Exception as e:
        result = ValidationResult()
        result.add_error(f"Schema validation failed: {e}")
        return None, result

    result = validate_workout(prescription, system_state)
    return prescription, result
