"""Data models for processing diagnostics.

Tracks processing status, errors, warnings, and quality metrics
for each form submission through the pipeline.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """Status of form processing."""

    SUCCESS = "success"  # All items processed, no errors
    PARTIAL = "partial"  # Some items processed, but warnings/missing data
    FAILED = "failed"  # Processing failed with errors


class DiagnosticError(BaseModel):
    """An error that occurred during processing."""

    stage: Literal["mapping", "recoding", "validation", "scoring", "interpretation", "building"]
    code: str  # Error code like "MAPPING_FIELD_NOT_FOUND"
    message: str
    item_id: str | None = None
    field_key: str | None = None
    details: dict | None = None


class DiagnosticWarning(BaseModel):
    """A warning that occurred during processing."""

    stage: Literal["mapping", "recoding", "validation", "scoring", "interpretation", "building"]
    code: str  # Warning code like "MISSING_ITEM"
    message: str
    item_id: str | None = None
    field_key: str | None = None
    details: dict | None = None


class QualityMetrics(BaseModel):
    """Quality metrics for a processed form."""

    completeness: float = Field(ge=0.0, le=1.0)  # Fraction of items present
    missing_items: list[str] = Field(default_factory=list)
    out_of_range_items: list[str] = Field(default_factory=list)
    prorated_scales: list[str] = Field(default_factory=list)
    items_total: int = 0
    items_present: int = 0


class MeasureDiagnostic(BaseModel):
    """Diagnostics for a single measure within a form submission."""

    measure_id: str
    measure_version: str
    status: ProcessingStatus
    errors: list[DiagnosticError] = Field(default_factory=list)
    warnings: list[DiagnosticWarning] = Field(default_factory=list)
    quality: QualityMetrics | None = None


class FormDiagnostic(BaseModel):
    """Diagnostics for a complete form submission."""

    form_submission_id: str
    form_id: str
    binding_id: str
    binding_version: str
    status: ProcessingStatus
    measures: list[MeasureDiagnostic] = Field(default_factory=list)
    errors: list[DiagnosticError] = Field(default_factory=list)
    warnings: list[DiagnosticWarning] = Field(default_factory=list)
    quality: QualityMetrics | None = None
