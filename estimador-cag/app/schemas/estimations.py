"""Request and response schemas for estimation endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EstimationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "transcription": (
                        "En la reunión con el cliente se discutió la necesidad de..."
                    )
                }
            ]
        }
    )

    transcription: str = Field(min_length=1)

    @field_validator("transcription")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Transcription must not be empty")
        return stripped


class TokenUsage(BaseModel):
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    usage: TokenUsage | None = None
    estimated_cost_usd: float | None = None
    generated_at: datetime
