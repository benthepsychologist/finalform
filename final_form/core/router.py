"""Domain router for kind-based processor selection.

Routes measure processing to the appropriate domain processor
based on the measure's `kind` field.
"""

from typing import Any

from final_form.core.domain import DomainProcessor
from final_form.core.models import ProcessingResult
from final_form.registry.models import FormBindingSpec, MeasureSpec


class DomainNotFoundError(Exception):
    """Raised when no processor is registered for a measure kind."""

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__(f"No domain processor registered for kind: {kind}")


class DomainRouter:
    """Routes processing to domain-specific processors.

    The router maintains a mapping from measure kinds to processors
    and delegates processing based on the measure's kind field.
    """

    def __init__(self) -> None:
        """Initialize an empty router."""
        self._processors: dict[str, DomainProcessor] = {}

    def register(self, processor: DomainProcessor) -> None:
        """Register a domain processor.

        Args:
            processor: A DomainProcessor implementation.
        """
        for kind in processor.supported_kinds:
            self._processors[kind] = processor

    def get_processor(self, kind: str) -> DomainProcessor:
        """Get the processor for a measure kind.

        Args:
            kind: The measure kind (e.g., "questionnaire", "lab_panel").

        Returns:
            The registered DomainProcessor for this kind.

        Raises:
            DomainNotFoundError: If no processor is registered for this kind.
        """
        if kind not in self._processors:
            raise DomainNotFoundError(kind)
        return self._processors[kind]

    def has_processor(self, kind: str) -> bool:
        """Check if a processor is registered for a kind.

        Args:
            kind: The measure kind.

        Returns:
            True if a processor is registered, False otherwise.
        """
        return kind in self._processors

    @property
    def supported_kinds(self) -> list[str]:
        """List all supported measure kinds."""
        return list(self._processors.keys())

    def process(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measures: dict[str, MeasureSpec],
        deterministic_ids: bool = False,
    ) -> ProcessingResult:
        """Process a form response, routing to appropriate domain processors.

        This method determines the kind from the first measure and delegates
        to the appropriate processor. For multi-measure forms where measures
        have different kinds, processing is done per-measure.

        Args:
            form_response: Canonical form response.
            binding_spec: Form binding specification.
            measures: Dict mapping measure_id to MeasureSpec.
            deterministic_ids: If True, generate deterministic UUIDs.

        Returns:
            Aggregated ProcessingResult from all domain processors.

        Raises:
            DomainNotFoundError: If a measure's kind has no registered processor.
        """
        if not measures:
            from final_form.core.diagnostics import ProcessingDiagnostics, ProcessingStatus

            return ProcessingResult(
                form_submission_id=form_response.get("form_submission_id", "unknown"),
                events=[],
                diagnostics=ProcessingDiagnostics(
                    form_submission_id=form_response.get("form_submission_id", "unknown"),
                    form_id=form_response.get("form_id", "unknown"),
                    binding_id=binding_spec.binding_id,
                    binding_version=binding_spec.version,
                    status=ProcessingStatus.SUCCESS,
                ),
                success=True,
            )

        # Group measures by kind
        measures_by_kind: dict[str, dict[str, MeasureSpec]] = {}
        for measure_id, measure in measures.items():
            kind = measure.kind
            if kind not in measures_by_kind:
                measures_by_kind[kind] = {}
            measures_by_kind[kind][measure_id] = measure

        # For now, we process all measures with a single processor
        # This works because current forms have homogeneous measure kinds
        # Future: aggregate results from multiple processors
        first_kind = next(iter(measures_by_kind.keys()))
        processor = self.get_processor(first_kind)

        return processor.process(
            form_response=form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=deterministic_ids,
        )
