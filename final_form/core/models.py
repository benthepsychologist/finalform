"""Core output models for measurement events.

Re-exports FHIR-aligned models from the builders module.
These models represent the unified output contract for all
measurement domains.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict

# Re-export from builders - these are the canonical definitions
from final_form.builders.measurement import (
    MeasurementEvent,
    Observation,
    Source,
    Telemetry,
)


class ProcessingResult(BaseModel):
    """Result of processing a single form response.

    Contains the generated MeasurementEvents and processing diagnostics.
    This is the unified return type from all domain processors.
    """

    form_submission_id: str
    events: list[MeasurementEvent]
    diagnostics: Any  # ProcessingDiagnostics - forward reference to avoid circular import
    success: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


__all__ = [
    "MeasurementEvent",
    "Observation",
    "ProcessingResult",
    "Source",
    "Telemetry",
]
