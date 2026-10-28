from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Category = Literal["bug", "security", "missing_test"]
Severity = Literal["low", "medium", "high"]


class Finding(BaseModel):
    """One review finding. Anything the model returns that does not fit this exactly is dropped."""

    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1, max_length=500)
    line: int = Field(ge=1)
    category: Category
    severity: Severity
    confidence: float = Field(ge=0, le=1)
    explanation: str = Field(min_length=1, max_length=2000)
    # Replacement for the reported line, offered as a GitHub suggestion the author can commit.
    fix: str | None = Field(default=None, min_length=1, max_length=1000)
    # Last line the fix replaces (lines `line`..`fix_end_line`); None = only `line`.
    fix_end_line: int | None = Field(default=None, ge=1)

    @field_validator("fix")
    @classmethod
    def _fix_stays_a_small_code_block(cls, v: str | None) -> str | None:
        # A fence would end the suggestion block and let model text render as markdown.
        if v is not None and ("```" in v or "~~~" in v or v.count("\n") >= 10):
            raise ValueError("fix must be at most 10 lines and contain no code fences")
        return v

    @model_validator(mode="after")
    def _fix_range_is_small(self) -> "Finding":
        end = self.fix_end_line
        if end is not None and not self.line <= end < self.line + 10:
            raise ValueError("fix_end_line must be within 10 lines from line")
        return self
