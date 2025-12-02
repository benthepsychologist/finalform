"""Wearable domain processor (stub).

Will handle processing of wearable device data streams.
"""

from typing import Any

from final_form.core.models import ProcessingResult
from final_form.registry.models import FormBindingSpec, MeasureSpec


class WearableProcessor:
    """Processor for wearable device measures (stub).

    Will handle heart rate variability, sleep data, activity metrics, etc.
    """

    SUPPORTED_KINDS = ("wearable",)

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
        raise NotImplementedError("Wearable domain processor not yet implemented")

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        raise NotImplementedError("Wearable domain processor not yet implemented")
