from pydantic import BaseModel, Field
from typing import Optional


class RegisterInput(BaseModel):
    username: str = Field(min_length=3, max_length=30)
    password: str = Field(min_length=4, max_length=128)


class LoginInput(BaseModel):
    username: str
    password: str


class ProfileSetupInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=10, le=100)
    weight_kg: float = Field(gt=0)
    height_cm: float = Field(gt=0)
    sex: str = Field(pattern="^(male|female)$")
    training_age_yr: float = Field(ge=0, default=0)
    unit_system: str = Field(default="metric", pattern="^(metric|imperial)$")
    equipment: list[str] = Field(
        default_factory=lambda: [
            "barbell", "dumbbells", "pull_up_bar", "rower",
            "assault_bike", "jump_rope", "kettlebell", "rings",
            "box", "wall_ball", "ab_mat",
        ]
    )


class ProfileUpdateInput(BaseModel):
    username: Optional[str] = Field(default=None, min_length=3, max_length=30)
    password: Optional[str] = Field(default=None, min_length=4, max_length=128)
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, ge=10, le=100)
    weight_kg: Optional[float] = Field(default=None, gt=0)
    height_cm: Optional[float] = Field(default=None, gt=0)
    sex: Optional[str] = Field(default=None, pattern="^(male|female)$")
    training_age_yr: Optional[float] = Field(default=None, ge=0)
    unit_system: Optional[str] = Field(default=None, pattern="^(metric|imperial)$")
