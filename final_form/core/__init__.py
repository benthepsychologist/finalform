"""Core shared infrastructure for final-form.

Contains domain-agnostic models, protocols, and utilities shared
across all measurement domains (questionnaire, lab, vital, wearable).

Most types are re-exported from their canonical locations in the
builders and diagnostics modules.
"""

from final_form.core.domain import DomainProcessor
from final_form.core.models import (
    MeasurementEvent,
    Observation,
    ProcessingResult,
    Source,
    Telemetry,
)
from final_form.core.diagnostics import (
    DiagnosticError,
    DiagnosticWarning,
    FormDiagnostic,
    MeasureDiagnostic,
    ProcessingDiagnostics,
    ProcessingStatus,
    QualityMetrics,
)
from final_form.core.router import DomainRouter
from final_form.core.factory import create_router, get_default_router

__all__ = [
    # Models
    "MeasurementEvent",
    "Observation",
    "ProcessingResult",
    "Source",
    "Telemetry",
    # Diagnostics
    "DiagnosticError",
    "DiagnosticWarning",
    "FormDiagnostic",
    "MeasureDiagnostic",
    "ProcessingDiagnostics",
    "ProcessingStatus",
    "QualityMetrics",
    # Domain
    "DomainProcessor",
    "DomainRouter",
    # Factory
    "create_router",
    "get_default_router",
]
