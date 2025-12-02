"""Tests for the diagnostics collector."""

import pytest

from final_form.diagnostics import (
    DiagnosticError,
    DiagnosticsCollector,
    DiagnosticWarning,
    ProcessingStatus,
    QualityMetrics,
)
from final_form.mapping import MappedItem, MappedSection, MappingResult
from final_form.recoding import RecodedItem, RecodedSection, RecodingResult
from final_form.scoring import ScaleScore, ScoringResult
from final_form.validation import ValidationResult


@pytest.fixture
def collector() -> DiagnosticsCollector:
    """Create a diagnostics collector for testing."""
    return DiagnosticsCollector(
        form_submission_id="sub_123",
        form_id="googleforms::test",
        binding_id="example_intake",
        binding_version="1.0.0",
    )


class TestDiagnosticsCollector:
    """Tests for DiagnosticsCollector."""

    def test_collector_initialization(self, collector: DiagnosticsCollector) -> None:
        """Test collector initializes with correct metadata."""
        assert collector.form_submission_id == "sub_123"
        assert collector.form_id == "googleforms::test"
        assert collector.binding_id == "example_intake"

    def test_add_form_level_error(self, collector: DiagnosticsCollector) -> None:
        """Test adding a form-level error."""
        collector.add_error(
            stage="mapping",
            code="BINDING_NOT_FOUND",
            message="Binding spec not found",
        )

        result = collector.finalize()
        assert len(result.errors) == 1
        assert result.errors[0].code == "BINDING_NOT_FOUND"
        assert result.status == ProcessingStatus.FAILED

    def test_add_instrument_error(self, collector: DiagnosticsCollector) -> None:
        """Test adding an instrument-level error."""
        collector.add_error(
            stage="recoding",
            code="UNKNOWN_RESPONSE",
            message="Unknown response text",
            measure_id="phq9",
            item_id="phq9_item1",
        )

        result = collector.finalize()
        assert len(result.measures) == 1
        assert result.measures[0].measure_id == "phq9"
        assert len(result.measures[0].errors) == 1
        assert result.measures[0].status == ProcessingStatus.FAILED

    def test_add_warning(self, collector: DiagnosticsCollector) -> None:
        """Test adding a warning."""
        collector.add_warning(
            stage="validation",
            code="MISSING_ITEM",
            message="Item phq9_item3 is missing",
            measure_id="phq9",
            item_id="phq9_item3",
        )

        result = collector.finalize()
        assert len(result.measures) == 1
        assert len(result.measures[0].warnings) == 1
        assert result.measures[0].status == ProcessingStatus.PARTIAL

    def test_success_status_when_no_issues(self, collector: DiagnosticsCollector) -> None:
        """Test that status is SUCCESS when no errors or warnings."""
        # Set up instrument with quality but no errors
        collector.set_measure_quality(
            measure_id="phq9",
            items_total=9,
            items_present=9,
            missing_items=[],
            out_of_range_items=[],
            prorated_scales=[],
        )

        result = collector.finalize()
        assert result.status == ProcessingStatus.SUCCESS
        assert result.measures[0].status == ProcessingStatus.SUCCESS

    def test_partial_status_with_warnings_only(self, collector: DiagnosticsCollector) -> None:
        """Test that status is PARTIAL when only warnings exist."""
        collector.add_warning(
            stage="scoring",
            code="PRORATED_SCORE",
            message="Score was prorated",
            measure_id="phq9",
        )

        result = collector.finalize()
        assert result.status == ProcessingStatus.PARTIAL

    def test_failed_status_with_errors(self, collector: DiagnosticsCollector) -> None:
        """Test that status is FAILED when errors exist."""
        collector.add_error(
            stage="recoding",
            code="RECODING_ERROR",
            message="Failed to recode value",
            measure_id="phq9",
        )

        result = collector.finalize()
        assert result.status == ProcessingStatus.FAILED

    def test_collect_from_mapping_result(self, collector: DiagnosticsCollector) -> None:
        """Test collecting diagnostics from mapping result."""
        # Mapping result with unmapped fields - the mapper doesn't store errors in items,
        # but collects unmapped fields at the result level
        mapping_result = MappingResult(
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
            sections=[
                MappedSection(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    items=[
                        MappedItem(
                            measure_id="phq9",
                            measure_version="1.0.0",
                            item_id="phq9_item1",
                            field_key="entry.123",
                            raw_answer="not at all",
                        ),
                    ],
                )
            ],
            unmapped_fields=["entry.unknown"],
        )

        collector.collect_from_mapping(mapping_result)
        result = collector.finalize()

        # Instruments are registered from mapping
        assert len(result.measures) == 1
        assert result.measures[0].measure_id == "phq9"

    def test_collect_from_recoding_result(self, collector: DiagnosticsCollector) -> None:
        """Test collecting diagnostics from recoding result."""
        recoding_result = RecodingResult(
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
            sections=[
                RecodedSection(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    items=[
                        RecodedItem(
                            measure_id="phq9",
                            measure_version="1.0.0",
                            item_id="phq9_item1",
                            value=1,
                            raw_answer="several days",
                            position=1,
                        ),
                        RecodedItem(
                            measure_id="phq9",
                            measure_version="1.0.0",
                            item_id="phq9_item2",
                            value=None,
                            raw_answer=None,
                            position=2,
                            missing=True,
                        ),
                    ],
                )
            ]
        )

        collector.collect_from_recoding(recoding_result)
        result = collector.finalize()

        assert len(result.measures) == 1
        assert len(result.measures[0].warnings) == 1  # From the missing value

    def test_collect_from_validation_result(self, collector: DiagnosticsCollector) -> None:
        """Test collecting diagnostics from validation result."""
        validation_result = ValidationResult(
            measure_id="phq9",
            valid=False,
            completeness=0.89,
            missing_items=["phq9_item2"],
            out_of_range_items=["phq9_item1"],
            errors=["Item phq9_item1: value 5 out of range [0, 3]"],
        )

        collector.collect_from_validation(validation_result, "phq9")
        result = collector.finalize()

        assert len(result.measures) == 1
        # Errors from out_of_range + errors list
        assert len(result.measures[0].errors) >= 1
        # Warnings from missing_items
        assert len(result.measures[0].warnings) >= 1

    def test_collect_from_scoring_result(self, collector: DiagnosticsCollector) -> None:
        """Test collecting diagnostics from scoring result."""
        scoring_result = ScoringResult(
            measure_id="phq9",
            measure_version="1.0.0",
            scales=[
                ScaleScore(
                    scale_id="phq9_total",
                    name="PHQ-9 Total",
                    value=9.0,
                    method="sum",
                    items_used=8,
                    items_total=9,
                    missing_items=["phq9_item3"],
                    reversed_items=[],
                    prorated=True,
                ),
            ],
        )

        collector.collect_from_scoring(scoring_result)
        result = collector.finalize()

        assert len(result.measures) == 1
        assert len(result.measures[0].warnings) == 1
        assert result.measures[0].warnings[0].code == "PRORATED_SCORE"

    def test_set_measure_quality(self, collector: DiagnosticsCollector) -> None:
        """Test setting quality metrics for an instrument."""
        collector.set_measure_quality(
            measure_id="phq9",
            items_total=9,
            items_present=8,
            missing_items=["phq9_item3"],
            out_of_range_items=[],
            prorated_scales=["phq9_total"],
        )

        result = collector.finalize()

        assert result.measures[0].quality is not None
        assert result.measures[0].quality.completeness == pytest.approx(8 / 9)
        assert result.measures[0].quality.missing_items == ["phq9_item3"]
        assert result.measures[0].quality.prorated_scales == ["phq9_total"]

    def test_aggregate_quality_metrics(self, collector: DiagnosticsCollector) -> None:
        """Test that aggregate quality metrics are computed correctly."""
        collector.set_measure_quality(
            measure_id="phq9",
            items_total=9,
            items_present=8,
            missing_items=["phq9_item3"],
            out_of_range_items=[],
            prorated_scales=["phq9_total"],
        )
        collector.set_measure_quality(
            measure_id="gad7",
            items_total=7,
            items_present=7,
            missing_items=[],
            out_of_range_items=[],
            prorated_scales=[],
        )

        result = collector.finalize()

        assert result.quality is not None
        assert result.quality.items_total == 16
        assert result.quality.items_present == 15
        assert result.quality.completeness == pytest.approx(15 / 16)
        assert result.quality.missing_items == ["phq9_item3"]

    def test_multiple_instruments(self, collector: DiagnosticsCollector) -> None:
        """Test handling multiple instruments."""
        collector.add_error(
            stage="recoding",
            code="ERROR1",
            message="Error in PHQ-9",
            measure_id="phq9",
        )
        collector.add_warning(
            stage="scoring",
            code="WARNING1",
            message="Warning in GAD-7",
            measure_id="gad7",
        )

        result = collector.finalize()

        assert len(result.measures) == 2

        phq9 = next(i for i in result.measures if i.measure_id == "phq9")
        gad7 = next(i for i in result.measures if i.measure_id == "gad7")

        assert phq9.status == ProcessingStatus.FAILED
        assert gad7.status == ProcessingStatus.PARTIAL
        assert result.status == ProcessingStatus.FAILED  # Overall is worst case


class TestDiagnosticModels:
    """Tests for diagnostic data models."""

    def test_diagnostic_error_attributes(self) -> None:
        """Test DiagnosticError model attributes."""
        error = DiagnosticError(
            stage="mapping",
            code="TEST_ERROR",
            message="Test error message",
            item_id="item1",
            field_key="entry.123",
            details={"extra": "info"},
        )

        assert error.stage == "mapping"
        assert error.code == "TEST_ERROR"
        assert error.item_id == "item1"
        assert error.details == {"extra": "info"}

    def test_diagnostic_warning_attributes(self) -> None:
        """Test DiagnosticWarning model attributes."""
        warning = DiagnosticWarning(
            stage="validation",
            code="TEST_WARNING",
            message="Test warning message",
        )

        assert warning.stage == "validation"
        assert warning.code == "TEST_WARNING"

    def test_quality_metrics_bounds(self) -> None:
        """Test QualityMetrics completeness bounds."""
        # Completeness at bounds
        metrics = QualityMetrics(completeness=0.0)
        assert metrics.completeness == 0.0

        metrics = QualityMetrics(completeness=1.0)
        assert metrics.completeness == 1.0

    def test_processing_status_enum(self) -> None:
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.SUCCESS.value == "success"
        assert ProcessingStatus.PARTIAL.value == "partial"
        assert ProcessingStatus.FAILED.value == "failed"

    def test_form_diagnostic_serialization(self, collector: DiagnosticsCollector) -> None:
        """Test FormDiagnostic serializes to JSON."""
        collector.add_warning(
            stage="scoring",
            code="TEST",
            message="Test",
            measure_id="phq9",
        )
        collector.set_measure_quality(
            measure_id="phq9",
            items_total=9,
            items_present=9,
            missing_items=[],
            out_of_range_items=[],
            prorated_scales=[],
        )

        result = collector.finalize()
        json_dict = result.model_dump()

        assert json_dict["form_submission_id"] == "sub_123"
        assert json_dict["status"] == "partial"
        assert "measures" in json_dict
        assert "quality" in json_dict
