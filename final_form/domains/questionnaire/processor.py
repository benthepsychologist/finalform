"""Questionnaire domain processor.

Handles processing of clinical questionnaires, scales, inventories,
and checklists through the mapping, recoding, validation, scoring,
interpretation, and event building pipeline.
"""

from typing import Any

from final_form.builders import MeasurementEvent, MeasurementEventBuilder
from final_form.core.diagnostics import ProcessingDiagnostics, ProcessingStatus
from final_form.core.models import ProcessingResult
from final_form.diagnostics import DiagnosticsCollector
from final_form.interpretation import Interpreter
from final_form.mapping import Mapper
from final_form.recoding import Recoder
from final_form.registry.models import FormBindingSpec, MeasureSpec
from final_form.scoring import ScoringEngine
from final_form.validation import Validator


class QuestionnaireProcessor:
    """Processor for questionnaire-type measures.

    Handles clinical questionnaires, scales, inventories, and checklists.
    Implements the DomainProcessor protocol.
    """

    SUPPORTED_KINDS = ("questionnaire", "scale", "inventory", "checklist")

    def __init__(self) -> None:
        """Initialize the questionnaire processor."""
        self.mapper = Mapper()
        self.recoder = Recoder()
        self.validator = Validator()
        self.scoring_engine = ScoringEngine()
        self.interpreter = Interpreter()

    @property
    def supported_kinds(self) -> tuple[str, ...]:
        """Return the measure kinds this processor handles."""
        return self.SUPPORTED_KINDS

    def process(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measures: dict[str, MeasureSpec],
        deterministic_ids: bool = False,
    ) -> ProcessingResult:
        """Process a questionnaire form response.

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
        form_id = form_response["form_id"]
        form_submission_id = form_response["form_submission_id"]
        subject_id = form_response["subject_id"]
        timestamp = form_response["timestamp"]

        # Initialize builder with deterministic ID setting
        builder = MeasurementEventBuilder(deterministic_ids=deterministic_ids)

        # Initialize diagnostics collector
        collector = DiagnosticsCollector(
            form_submission_id=form_submission_id,
            form_id=form_id,
            binding_id=binding_spec.binding_id,
            binding_version=binding_spec.version,
        )

        events: list[MeasurementEvent] = []
        warnings: list[str] = []

        try:
            # 1. Map form items to measure items
            mapping_result = self.mapper.map(
                form_response=form_response,
                binding_spec=binding_spec,
            )
            collector.collect_from_mapping(mapping_result)

            # 2. Recode values for each measure section
            recoding_result = self.recoder.recode(
                mapping_result=mapping_result,
                measures=measures,
            )
            collector.collect_from_recoding(recoding_result)

            # 3. Process each measure section
            for section in recoding_result.sections:
                measure = measures[section.measure_id]

                # 3a. Validate
                validation_result = self.validator.validate(
                    section=section,
                    measure=measure,
                )
                collector.collect_from_validation(validation_result, section.measure_id)

                # Set quality metrics
                collector.set_measure_quality(
                    measure_id=section.measure_id,
                    items_total=len(measure.items),
                    items_present=len([i for i in section.items if not i.missing]),
                    missing_items=validation_result.missing_items,
                    out_of_range_items=validation_result.out_of_range_items,
                    prorated_scales=[],  # Will be filled from scoring
                )

                # 3b. Score
                scoring_result = self.scoring_engine.score(
                    section=section,
                    measure=measure,
                )
                collector.collect_from_scoring(scoring_result)

                # Update prorated scales
                prorated = [s.scale_id for s in scoring_result.scales if s.prorated]
                if prorated:
                    collector.set_measure_quality(
                        measure_id=section.measure_id,
                        items_total=len(measure.items),
                        items_present=len([i for i in section.items if not i.missing]),
                        missing_items=validation_result.missing_items,
                        out_of_range_items=validation_result.out_of_range_items,
                        prorated_scales=prorated,
                    )

                # Collect warnings for prorated scores
                section_warnings: list[str] = []
                for scale in scoring_result.scales:
                    if scale.prorated:
                        section_warnings.append(
                            f"Scale {scale.scale_id} was prorated "
                            f"(missing: {scale.missing_items})"
                        )

                # 3c. Interpret
                interpretation_result = self.interpreter.interpret(
                    scoring_result=scoring_result,
                    measure=measure,
                )

                # 3d. Build MeasurementEvent
                event = builder.build(
                    recoded_section=section,
                    scoring_result=scoring_result,
                    interpretation_result=interpretation_result,
                    binding_spec=binding_spec,
                    form_id=form_id,
                    form_submission_id=form_submission_id,
                    subject_id=subject_id,
                    timestamp=timestamp,
                    warnings=section_warnings if section_warnings else None,
                )
                events.append(event)
                warnings.extend(section_warnings)

        except Exception as e:
            collector.add_error(
                stage="building",
                code="PIPELINE_ERROR",
                message=str(e),
            )

        # Finalize diagnostics
        form_diagnostic = collector.finalize()

        # FormDiagnostic is now ProcessingDiagnostics (they're the same type)
        diagnostics = form_diagnostic

        return ProcessingResult(
            form_submission_id=form_submission_id,
            events=events,
            diagnostics=diagnostics,
            success=diagnostics.status in (ProcessingStatus.SUCCESS, ProcessingStatus.PARTIAL),
        )

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        """Validate that a measure spec is compatible with questionnaire domain.

        Args:
            measure: The measure specification to validate.

        Returns:
            List of validation error messages (empty if valid).
        """
        errors: list[str] = []

        # Check kind
        if measure.kind not in self.SUPPORTED_KINDS:
            errors.append(
                f"Measure kind '{measure.kind}' is not supported by questionnaire domain. "
                f"Supported kinds: {', '.join(self.SUPPORTED_KINDS)}"
            )
            return errors  # No point checking further if kind is wrong

        # Questionnaires must have items
        if not measure.items:
            errors.append("Questionnaire measures must have at least one item")

        # Each item must have a response_map
        for item in measure.items:
            if not item.response_map:
                errors.append(f"Item {item.item_id} must have a response_map")

        # Each scale must reference valid items
        item_ids = {item.item_id for item in measure.items}
        for scale in measure.scales:
            for item_id in scale.items:
                if item_id not in item_ids:
                    errors.append(
                        f"Scale {scale.scale_id} references unknown item: {item_id}"
                    )

        return errors
