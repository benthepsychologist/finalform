"""Tests for core module."""

from typing import Any

import pytest

from final_form.core import (
    DiagnosticError,
    DiagnosticWarning,
    DomainProcessor,
    DomainRouter,
    MeasurementEvent,
    Observation,
    ProcessingDiagnostics,
    ProcessingResult,
    ProcessingStatus,
    QualityMetrics,
    Source,
    Telemetry,
)
from final_form.core.router import DomainNotFoundError
from final_form.registry.models import FormBindingSpec, MeasureSpec


class TestCoreModels:
    """Tests for core output models."""

    def test_source_model(self) -> None:
        """Test Source model creation."""
        source = Source(
            form_id="form_123",
            form_submission_id="sub_456",
            binding_id="example_intake",
            binding_version="1.0.0",
        )
        assert source.form_id == "form_123"
        assert source.form_correlation_id is None

    def test_telemetry_model(self) -> None:
        """Test Telemetry model creation."""
        telemetry = Telemetry(
            processed_at="2025-01-15T10:30:00Z",
            final_form_version="0.1.0",
            measure_spec="phq9@1.0.0",
            form_binding_spec="example_intake@1.0.0",
        )
        assert telemetry.warnings == []

    def test_observation_model(self) -> None:
        """Test Observation model creation."""
        obs = Observation(
            observation_id="obs_123",
            measure_id="phq9",
            code="phq9_item1",
            kind="item",
            value=2,
            value_type="integer",
        )
        assert obs.schema_ == "com.lifeos.observation.v1"
        assert obs.missing is False

    def test_observation_with_alias(self) -> None:
        """Test Observation serialization uses alias."""
        obs = Observation(
            observation_id="obs_123",
            measure_id="phq9",
            code="phq9_item1",
            kind="item",
            value=2,
            value_type="integer",
        )
        data = obs.model_dump(by_alias=True)
        assert "schema" in data
        assert "schema_" not in data

    def test_measurement_event_model(self) -> None:
        """Test MeasurementEvent model creation."""
        event = MeasurementEvent(
            measurement_event_id="event_123",
            measure_id="phq9",
            measure_version="1.0.0",
            subject_id="patient_789",
            timestamp="2025-01-15T10:30:00Z",
            source=Source(
                form_id="form_123",
                form_submission_id="sub_456",
                binding_id="example_intake",
                binding_version="1.0.0",
            ),
            observations=[],
            telemetry=Telemetry(
                processed_at="2025-01-15T10:30:00Z",
                final_form_version="0.1.0",
                measure_spec="phq9@1.0.0",
                form_binding_spec="example_intake@1.0.0",
            ),
        )
        assert event.schema_ == "com.lifeos.measurement_event.v1"


class TestCoreDiagnostics:
    """Tests for core diagnostics models."""

    def test_processing_status_enum(self) -> None:
        """Test ProcessingStatus enum values."""
        assert ProcessingStatus.SUCCESS.value == "success"
        assert ProcessingStatus.PARTIAL.value == "partial"
        assert ProcessingStatus.FAILED.value == "failed"

    def test_diagnostic_error(self) -> None:
        """Test DiagnosticError model."""
        error = DiagnosticError(
            stage="mapping",
            code="FIELD_NOT_FOUND",
            message="Field entry.123 not found",
            field_key="entry.123",
        )
        assert error.stage == "mapping"
        assert error.item_id is None

    def test_diagnostic_warning(self) -> None:
        """Test DiagnosticWarning model."""
        warning = DiagnosticWarning(
            stage="validation",
            code="MISSING_ITEM",
            message="Item phq9_item3 is missing",
            item_id="phq9_item3",
        )
        assert warning.stage == "validation"

    def test_quality_metrics(self) -> None:
        """Test QualityMetrics model."""
        quality = QualityMetrics(
            completeness=0.9,
            missing_items=["phq9_item3"],
            items_total=10,
            items_present=9,
        )
        assert quality.completeness == 0.9
        assert len(quality.missing_items) == 1

    def test_processing_diagnostics(self) -> None:
        """Test ProcessingDiagnostics model."""
        diag = ProcessingDiagnostics(
            form_submission_id="sub_123",
            form_id="form_456",
            binding_id="example_intake",
            binding_version="1.0.0",
            status=ProcessingStatus.SUCCESS,
        )
        assert diag.status == ProcessingStatus.SUCCESS
        assert diag.measures == []


class MockProcessor:
    """Mock domain processor for testing."""

    def __init__(self, kinds: tuple[str, ...] = ("questionnaire",)) -> None:
        self._kinds = kinds

    @property
    def supported_kinds(self) -> tuple[str, ...]:
        return self._kinds

    def process(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measures: dict[str, MeasureSpec],
        deterministic_ids: bool = False,
    ) -> ProcessingResult:
        return ProcessingResult(
            form_submission_id=form_response.get("form_submission_id", "test"),
            events=[],
            diagnostics=ProcessingDiagnostics(
                form_submission_id=form_response.get("form_submission_id", "test"),
                form_id=form_response.get("form_id", "test"),
                binding_id=binding_spec.binding_id,
                binding_version=binding_spec.version,
                status=ProcessingStatus.SUCCESS,
            ),
            success=True,
        )

    def validate_measure(self, measure: MeasureSpec) -> list[str]:
        return []


class TestDomainRouter:
    """Tests for domain router."""

    def test_register_processor(self) -> None:
        """Test registering a domain processor."""
        router = DomainRouter()
        processor = MockProcessor(("questionnaire", "scale"))
        router.register(processor)

        assert router.has_processor("questionnaire")
        assert router.has_processor("scale")
        assert not router.has_processor("lab_panel")

    def test_get_processor(self) -> None:
        """Test getting a registered processor."""
        router = DomainRouter()
        processor = MockProcessor()
        router.register(processor)

        retrieved = router.get_processor("questionnaire")
        assert retrieved is processor

    def test_get_processor_not_found(self) -> None:
        """Test error when processor not found."""
        router = DomainRouter()

        with pytest.raises(DomainNotFoundError) as exc_info:
            router.get_processor("unknown")

        assert "unknown" in str(exc_info.value)

    def test_supported_kinds(self) -> None:
        """Test listing supported kinds."""
        router = DomainRouter()
        router.register(MockProcessor(("questionnaire", "scale")))
        router.register(MockProcessor(("lab_panel",)))

        kinds = router.supported_kinds
        assert "questionnaire" in kinds
        assert "scale" in kinds
        assert "lab_panel" in kinds

    def test_domain_processor_protocol(self) -> None:
        """Test that MockProcessor satisfies DomainProcessor protocol."""
        processor = MockProcessor()
        assert isinstance(processor, DomainProcessor)


class TestProcessingResult:
    """Tests for ProcessingResult model."""

    def test_processing_result(self) -> None:
        """Test ProcessingResult creation."""
        result = ProcessingResult(
            form_submission_id="sub_123",
            events=[],
            diagnostics=ProcessingDiagnostics(
                form_submission_id="sub_123",
                form_id="form_456",
                binding_id="example_intake",
                binding_version="1.0.0",
                status=ProcessingStatus.SUCCESS,
            ),
            success=True,
        )
        assert result.success is True
        assert result.events == []


class TestRouterFactory:
    """Tests for router factory functions."""

    def test_create_router(self) -> None:
        """Test creating a router with default processors."""
        from final_form.core import create_router

        router = create_router()

        # Should have questionnaire processor registered
        assert router.has_processor("questionnaire")
        assert router.has_processor("scale")
        assert router.has_processor("inventory")
        assert router.has_processor("checklist")

        # Should not have future domains yet
        assert not router.has_processor("lab_panel")
        assert not router.has_processor("vital")
        assert not router.has_processor("wearable")
