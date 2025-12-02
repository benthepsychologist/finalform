"""Collector for processing diagnostics.

Collects errors, warnings, and quality metrics throughout the pipeline
and produces a complete diagnostic report for each form submission.
"""

from typing import Literal

from final_form.diagnostics.models import (
    DiagnosticError,
    DiagnosticWarning,
    FormDiagnostic,
    MeasureDiagnostic,
    ProcessingStatus,
    QualityMetrics,
)
from final_form.mapping.mapper import MappingResult
from final_form.recoding.recoder import RecodingResult
from final_form.scoring.engine import ScoringResult
from final_form.validation.checks import ValidationResult


class DiagnosticsCollector:
    """Collects diagnostics throughout the processing pipeline.

    Tracks errors, warnings, and quality metrics for form submissions
    and produces structured diagnostic reports.
    """

    def __init__(
        self,
        form_submission_id: str,
        form_id: str,
        binding_id: str,
        binding_version: str,
    ) -> None:
        """Initialize the collector for a form submission.

        Args:
            form_submission_id: Unique identifier for the form submission.
            form_id: Identifier for the form (e.g., "googleforms::abc").
            binding_id: The binding spec ID used.
            binding_version: The binding spec version used.
        """
        self.form_submission_id = form_submission_id
        self.form_id = form_id
        self.binding_id = binding_id
        self.binding_version = binding_version

        self._form_errors: list[DiagnosticError] = []
        self._form_warnings: list[DiagnosticWarning] = []
        self._measures: dict[str, MeasureDiagnostic] = {}

    def add_error(
        self,
        stage: Literal["mapping", "recoding", "validation", "scoring", "interpretation", "building"],
        code: str,
        message: str,
        measure_id: str | None = None,
        item_id: str | None = None,
        field_key: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Add an error to the diagnostics.

        Args:
            stage: Processing stage where the error occurred.
            code: Error code (e.g., "MAPPING_FIELD_NOT_FOUND").
            message: Human-readable error message.
            measure_id: Optional measure the error relates to.
            item_id: Optional item ID the error relates to.
            field_key: Optional field key the error relates to.
            details: Optional additional details.
        """
        error = DiagnosticError(
            stage=stage,
            code=code,
            message=message,
            item_id=item_id,
            field_key=field_key,
            details=details,
        )

        if measure_id:
            self._ensure_measure(measure_id)
            self._measures[measure_id].errors.append(error)
        else:
            self._form_errors.append(error)

    def add_warning(
        self,
        stage: Literal["mapping", "recoding", "validation", "scoring", "interpretation", "building"],
        code: str,
        message: str,
        measure_id: str | None = None,
        item_id: str | None = None,
        field_key: str | None = None,
        details: dict | None = None,
    ) -> None:
        """Add a warning to the diagnostics.

        Args:
            stage: Processing stage where the warning occurred.
            code: Warning code (e.g., "MISSING_ITEM").
            message: Human-readable warning message.
            measure_id: Optional measure the warning relates to.
            item_id: Optional item ID the warning relates to.
            field_key: Optional field key the warning relates to.
            details: Optional additional details.
        """
        warning = DiagnosticWarning(
            stage=stage,
            code=code,
            message=message,
            item_id=item_id,
            field_key=field_key,
            details=details,
        )

        if measure_id:
            self._ensure_measure(measure_id)
            self._measures[measure_id].warnings.append(warning)
        else:
            self._form_warnings.append(warning)

    def _ensure_measure(
        self,
        measure_id: str,
        measure_version: str = "unknown",
    ) -> None:
        """Ensure a measure diagnostic exists."""
        if measure_id not in self._measures:
            self._measures[measure_id] = MeasureDiagnostic(
                measure_id=measure_id,
                measure_version=measure_version,
                status=ProcessingStatus.SUCCESS,
            )

    def collect_from_mapping(
        self,
        mapping_result: MappingResult,
    ) -> None:
        """Collect diagnostics from a mapping result.

        Args:
            mapping_result: The result from the mapping stage.
        """
        for section in mapping_result.sections:
            self._ensure_measure(section.measure_id, section.measure_version)
            inst = self._measures[section.measure_id]
            inst.measure_version = section.measure_version

        # Collect warnings for unmapped fields
        for field_key in mapping_result.unmapped_fields:
            self.add_warning(
                stage="mapping",
                code="UNMAPPED_FIELD",
                message=f"Field {field_key} was not mapped to any measure item",
                field_key=field_key,
            )

    def collect_from_recoding(
        self,
        recoding_result: RecodingResult,
    ) -> None:
        """Collect diagnostics from a recoding result.

        Args:
            recoding_result: The result from the recoding stage.
        """
        for section in recoding_result.sections:
            self._ensure_measure(section.measure_id, section.measure_version)

            for item in section.items:
                if item.missing:
                    self.add_warning(
                        stage="recoding",
                        code="MISSING_VALUE",
                        message=f"Item {item.item_id} has missing value",
                        measure_id=section.measure_id,
                        item_id=item.item_id,
                    )

    def collect_from_validation(
        self,
        validation_result: ValidationResult,
        measure_id: str,
    ) -> None:
        """Collect diagnostics from a validation result.

        Args:
            validation_result: The result from the validation stage.
            measure_id: The measure ID being validated.
        """
        self._ensure_measure(measure_id)

        # Collect errors from the errors list
        for error_msg in validation_result.errors:
            self.add_error(
                stage="validation",
                code="VALIDATION_ERROR",
                message=error_msg,
                measure_id=measure_id,
            )

        # Collect warnings for missing items
        for item_id in validation_result.missing_items:
            self.add_warning(
                stage="validation",
                code="VALIDATION_MISSING",
                message=f"Item {item_id} is missing",
                measure_id=measure_id,
                item_id=item_id,
            )

        # Collect errors for out-of-range items (if not already in errors)
        for item_id in validation_result.out_of_range_items:
            # Check if there's already an error message for this item
            has_error = any(item_id in e for e in validation_result.errors)
            if not has_error:
                self.add_error(
                    stage="validation",
                    code="VALIDATION_RANGE",
                    message=f"Item {item_id} has out-of-range value",
                    measure_id=measure_id,
                    item_id=item_id,
                )

    def collect_from_scoring(
        self,
        scoring_result: ScoringResult,
    ) -> None:
        """Collect diagnostics from a scoring result.

        Args:
            scoring_result: The result from the scoring stage.
        """
        self._ensure_measure(scoring_result.measure_id, scoring_result.measure_version)

        for scale in scoring_result.scales:
            if scale.error:
                self.add_error(
                    stage="scoring",
                    code="SCORING_ERROR",
                    message=scale.error,
                    measure_id=scoring_result.measure_id,
                    details={"scale_id": scale.scale_id},
                )
            if scale.prorated:
                self.add_warning(
                    stage="scoring",
                    code="PRORATED_SCORE",
                    message=f"Scale {scale.scale_id} was prorated due to missing items",
                    measure_id=scoring_result.measure_id,
                    details={
                        "scale_id": scale.scale_id,
                        "missing_items": scale.missing_items,
                    },
                )

    def set_measure_quality(
        self,
        measure_id: str,
        items_total: int,
        items_present: int,
        missing_items: list[str],
        out_of_range_items: list[str],
        prorated_scales: list[str],
    ) -> None:
        """Set quality metrics for a measure.

        Args:
            measure_id: The measure ID.
            items_total: Total number of items expected.
            items_present: Number of items that were present.
            missing_items: List of missing item IDs.
            out_of_range_items: List of out-of-range item IDs.
            prorated_scales: List of scales that were prorated.
        """
        self._ensure_measure(measure_id)

        completeness = items_present / items_total if items_total > 0 else 0.0

        self._measures[measure_id].quality = QualityMetrics(
            completeness=completeness,
            missing_items=missing_items,
            out_of_range_items=out_of_range_items,
            prorated_scales=prorated_scales,
            items_total=items_total,
            items_present=items_present,
        )

    def finalize(self) -> FormDiagnostic:
        """Finalize and return the complete diagnostic report.

        Computes final status based on collected errors and warnings.

        Returns:
            Complete FormDiagnostic for the form submission.
        """
        # Determine measure statuses
        for inst in self._measures.values():
            if inst.errors:
                inst.status = ProcessingStatus.FAILED
            elif inst.warnings:
                inst.status = ProcessingStatus.PARTIAL
            else:
                inst.status = ProcessingStatus.SUCCESS

        # Determine overall form status
        measures_list = list(self._measures.values())

        if self._form_errors or any(i.status == ProcessingStatus.FAILED for i in measures_list):
            form_status = ProcessingStatus.FAILED
        elif self._form_warnings or any(i.status == ProcessingStatus.PARTIAL for i in measures_list):
            form_status = ProcessingStatus.PARTIAL
        else:
            form_status = ProcessingStatus.SUCCESS

        # Compute aggregate quality metrics
        total_items = sum(i.quality.items_total for i in measures_list if i.quality)
        present_items = sum(i.quality.items_present for i in measures_list if i.quality)
        all_missing = []
        all_out_of_range = []
        all_prorated = []

        for inst in measures_list:
            if inst.quality:
                all_missing.extend(inst.quality.missing_items)
                all_out_of_range.extend(inst.quality.out_of_range_items)
                all_prorated.extend(inst.quality.prorated_scales)

        form_quality = QualityMetrics(
            completeness=present_items / total_items if total_items > 0 else 1.0,
            missing_items=all_missing,
            out_of_range_items=all_out_of_range,
            prorated_scales=all_prorated,
            items_total=total_items,
            items_present=present_items,
        )

        return FormDiagnostic(
            form_submission_id=self.form_submission_id,
            form_id=self.form_id,
            binding_id=self.binding_id,
            binding_version=self.binding_version,
            status=form_status,
            measures=measures_list,
            errors=self._form_errors,
            warnings=self._form_warnings,
            quality=form_quality,
        )
