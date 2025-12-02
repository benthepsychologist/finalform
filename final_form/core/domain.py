"""Domain processor protocol.

Defines the interface that all domain processors must implement.
Each domain (questionnaire, lab, vital, wearable) provides a processor
that conforms to this protocol.
"""

from typing import Any, Protocol, runtime_checkable

from final_form.core.models import ProcessingResult
from final_form.registry.models import FormBindingSpec, MeasureSpec


@runtime_checkable
class DomainProcessor(Protocol):
    """Protocol for domain-specific processors.

    Each measurement domain (questionnaire, lab, vital, wearable)
    implements this protocol to provide domain-specific processing logic.
    """

    @property
    def supported_kinds(self) -> tuple[str, ...]:
        """Return the measure kinds this processor handles.

        Examples:
            - Questionnaire domain: ("questionnaire", "scale", "inventory", "checklist")
            - Lab domain: ("lab_panel",)
            - Vital domain: ("vital",)
            - Wearable domain: ("wearable",)
        """
        ...

    def process(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measures: dict[str, MeasureSpec],
        deterministic_ids: bool = False,
    ) -> ProcessingResult:
        """Process a form response and return measurement events.

        Args:
            form_response: Canonical form response dict with fields:
                - form_id: str
                - form_submission_id: str
                - subject_id: str
                - timestamp: str
                - items: list[dict] with field_key/position and answer
            binding_spec: The form binding specification.
            measures: Dict mapping measure_id to MeasureSpec.
            deterministic_ids: If True, generate deterministic UUIDs (for testing).

        Returns:
            ProcessingResult containing MeasurementEvents and diagnostics.
        """
        ...

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        """Validate that a measure spec is compatible with this domain.

        Args:
            measure: The measure specification to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        ...
