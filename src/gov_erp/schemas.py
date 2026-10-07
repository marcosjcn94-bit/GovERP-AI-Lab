from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    municipality_id: str = Field(min_length=7, max_length=12, pattern=r"^[0-9]+$")


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=512)
    start_date: date | None = None
    end_date: date | None = None


class ReviewRequest(BaseModel):
    decision: Literal["confirmed", "rejected", "needs_information"]
    note: str = Field(min_length=12, max_length=800)


class SessionView(BaseModel):
    user_id: str
    display_name: str
    role: str
    municipality_id: str
    municipality_name: str
    csrf_token: str


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
