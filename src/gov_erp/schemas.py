from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    municipality_id: str = Field(min_length=7, max_length=12, pattern=r"^[0-9]+$")


class AssistantRequest(BaseModel):
    question: str = Field(min_length=3, max_length=512)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ReviewRequest(BaseModel):
    decision: Literal["confirmed", "rejected", "needs_information"]
    note: str = Field(min_length=12, max_length=800)

    @field_validator("note", mode="before")
    @classmethod
    def trim_note(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SessionView(BaseModel):
    user_id: str
    display_name: str
    role: str
    municipality_id: str
    municipality_name: str
    csrf_token: str


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
