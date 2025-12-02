"""Lab domain processor (stub).

Will handle processing of laboratory panels and test results.
"""

from typing import Any

from final_form.core.models import ProcessingResult
from final_form.registry.models import FormBindingSpec, MeasureSpec


class LabProcessor:
    """Processor for lab panel measures (stub).

    Will handle CBC, BMP, lipid panels, etc.
    """

    SUPPORTED_KINDS = ("lab_panel",)

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
        raise NotImplementedError("Lab domain processor not yet implemented")

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        raise NotImplementedError("Lab domain processor not yet implemented")
