from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
