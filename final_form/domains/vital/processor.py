"""Vital domain processor (stub).

Will handle processing of vital signs measurements.
"""

from typing import Any

from final_form.core.models import ProcessingResult
from final_form.registry.models import FormBindingSpec, MeasureSpec


class VitalProcessor:
    """Processor for vital sign measures (stub).

    Will handle blood pressure, heart rate, temperature, etc.
    """

    SUPPORTED_KINDS = ("vital",)

    @property
    def supported_kinds(self) -> tuple[str, ...]:
        return self.SUPPORTED_KINDS

    def process(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measures: dict[str, MeasureSpec],
        deterministic_ids: bool = False,
    ) -> ProcessingResult:
        raise NotImplementedError("Vital domain processor not yet implemented")

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        raise NotImplementedError("Vital domain processor not yet implemented")
