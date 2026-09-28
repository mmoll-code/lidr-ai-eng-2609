"""Request and response schemas for estimation endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PreprocessingMode = Literal["none", "inline_cleaning", "two_phase"]
ExampleFormat = Literal["markdown", "json", "narrative"]


class EstimationRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "transcription": (
                        "The client wants a small CRM with authentication, contacts, and roles."
                    )
                }
            ]
        }
    )

    transcription: str = Field(min_length=1)
    preprocessing: PreprocessingMode = Field(
        default="none",
        description="Input preprocessing strategy: none | inline_cleaning | two_phase",
    )
    example_format: ExampleFormat = Field(
        default="markdown",
        description="Format used to render the CAG examples in the system prompt",
    )
    num_examples: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Number of canonical examples to inject",
    )
    use_examples: bool = Field(
        default=True,
        description="Toggle the CAG examples block on or off",
    )
    model: str | None = Field(
        default=None,
        description="Override the default model for this request",
    )
    max_tokens: int = Field(default=4000, gt=0, le=16000)
    thinking_budget: int | None = Field(
        default=None,
        ge=0,
        le=16000,
        description="Extended thinking budget (Anthropic only). Ignored for OpenAI.",
    )
    evaluate: bool = Field(
        default=True,
        description="Run the structural evaluation on the generated estimation",
    )

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
    preprocessing_input_tokens: int = 0
    preprocessing_output_tokens: int = 0


class StructureCheck(BaseModel):
    """Level-1 structural evaluation of the generated estimation."""

    has_title: bool
    has_breakdown_table: bool
    has_totals_section: bool
    has_team_section: bool
    has_duration_section: bool
    declared_total_hours: int | None
    sum_row_hours: int | None
    hours_match: bool | None
    declared_total_cost: float | None
    sum_row_cost: float | None
    cost_match: bool | None
    finish_reason_ok: bool
    score: float
    issues: list[str]


class EstimationResponse(BaseModel):
    estimation: str
    model: str
    provider: str
    usage: TokenUsage | None = None
    estimated_cost_usd: float | None = None
    generated_at: datetime
    finish_reason: str = "stop"
    preprocessing: PreprocessingMode = "none"
    extracted_requirements: str | None = None
    latency_ms: int = 0
    validation: StructureCheck | None = None
    cache_hit: bool = False


class StreamEstimationRequest(BaseModel):
    """Streaming endpoint request. Generation knobs stay on the blocking endpoint."""

    transcription: str = Field(min_length=1)
    model: str | None = Field(default=None, description="Override the default model")
    max_tokens: int = Field(default=4000, gt=0, le=16000)

    @field_validator("transcription")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Transcription must not be empty")
        return stripped
