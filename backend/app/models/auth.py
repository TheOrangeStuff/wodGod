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
    equipment: list[str] = Field(
        default_factory=lambda: [
            "barbell", "dumbbells", "pull_up_bar", "rower",
            "assault_bike", "jump_rope", "kettlebell", "rings",
            "box", "wall_ball", "ab_mat",
        ]
    )
