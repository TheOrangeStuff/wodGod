from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class CnsLoad(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class ConditioningType(str, Enum):
    AMRAP = "amrap"
    FOR_TIME = "for_time"
    EMOM = "emom"
    INTERVAL = "interval"


class StrengthBlock(BaseModel):
    movement: str
    scheme: str = Field(description="e.g. '5x5', '3x10'")
    load_percentage: float = Field(ge=0.0, le=1.0)
    rest_seconds: int = Field(ge=0)


class ConditioningMovement(BaseModel):
    movement: str
    reps: Optional[int] = None
    distance_m: Optional[int] = None
    calories: Optional[int] = None


class ConditioningBlock(BaseModel):
    type: ConditioningType
    time_cap_minutes: int = Field(ge=1)
    movements: list[ConditioningMovement] = Field(min_length=1)
    rounds: Optional[int] = None


class AerobicPrescription(BaseModel):
    type: str = Field(description="e.g. 'zone2', 'steady_state'")
    modality: str
    duration_minutes: int = Field(ge=5)


class WorkoutPrescription(BaseModel):
    """The structured workout JSON the LLM must produce."""
    focus: str
    intensity_target_rpe: float = Field(ge=1.0, le=10.0)
    time_domain: str = Field(description="e.g. '60-75 min'")
    cns_load: CnsLoad
    primary_strength: StrengthBlock
    secondary_strength: StrengthBlock
    conditioning: ConditioningBlock
    aerobic_prescription: AerobicPrescription
    mobility_prompt: str


class WorkoutLogInput(BaseModel):
    actual_rpe: float = Field(ge=1.0, le=10.0)
    missed_reps: int = Field(ge=0, default=0)
    performance_json: dict = Field(default_factory=dict)
    notes: Optional[str] = None


class ReadinessInput(BaseModel):
    readiness_score: int = Field(ge=1, le=5)
    sleep_quality: Optional[int] = Field(ge=1, le=5, default=None)
    soreness: Optional[int] = Field(ge=1, le=5, default=None)
    stress: Optional[int] = Field(ge=1, le=5, default=None)
    notes: Optional[str] = None
