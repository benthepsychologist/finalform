"""Tests for the measurement event builder."""

from pathlib import Path

import pytest

from final_form.builders import (
    MeasurementEvent,
    MeasurementEventBuilder,
    Observation,
    Source,
    Telemetry,
)
from final_form.interpretation import InterpretationResult, InterpretedScore
from final_form.recoding import RecodedItem, RecodedSection
from final_form.registry import BindingRegistry
from final_form.scoring import ScaleScore, ScoringResult


@pytest.fixture
def builder() -> MeasurementEventBuilder:
    """Create a builder with deterministic IDs for testing."""
    return MeasurementEventBuilder(deterministic_ids=True)


@pytest.fixture
def example_binding(binding_registry_path: Path, binding_schema_path: Path):
    """Load the example_intake binding spec."""
    registry = BindingRegistry(binding_registry_path, schema_path=binding_schema_path)
    return registry.get("example_intake", "1.0.0")


@pytest.fixture
def phq9_recoded_section() -> RecodedSection:
    """A complete PHQ-9 recoded section."""
    return RecodedSection(
        measure_id="phq9",
        measure_version="1.0.0",
        items=[
            RecodedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id=f"phq9_item{i}",
                value=1,
                raw_answer="several days",
                position=i,
            )
            for i in range(1, 10)
        ] + [
            RecodedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item10",
                value=1,
                raw_answer="somewhat difficult",
                position=10,
            )
        ],
    )


@pytest.fixture
def phq9_scoring_result() -> ScoringResult:
    """A PHQ-9 scoring result."""
    return ScoringResult(
        measure_id="phq9",
        measure_version="1.0.0",
        scales=[
            ScaleScore(
                scale_id="phq9_total",
                name="PHQ-9 Total Score",
                value=9.0,
                method="sum",
                items_used=9,
                items_total=9,
                missing_items=[],
                reversed_items=[],
            ),
            ScaleScore(
                scale_id="phq9_severity",
                name="PHQ-9 Functional Severity",
                value=1.0,
                method="sum",
                items_used=1,
                items_total=1,
                missing_items=[],
                reversed_items=[],
            ),
        ],
    )


@pytest.fixture
def phq9_interpretation_result() -> InterpretationResult:
    """A PHQ-9 interpretation result."""
    return InterpretationResult(
        measure_id="phq9",
        measure_version="1.0.0",
        scores=[
            InterpretedScore(
                scale_id="phq9_total",
                name="PHQ-9 Total Score",
                value=9.0,
                label="Mild",
                interpretation_min=5,
                interpretation_max=9,
            ),
            InterpretedScore(
                scale_id="phq9_severity",
                name="PHQ-9 Functional Severity",
                value=1.0,
                label="Somewhat difficult",
                interpretation_min=1,
                interpretation_max=1,
            ),
        ],
    )


class TestMeasurementEventBuilder:
    """Tests for MeasurementEventBuilder."""

    def test_build_measurement_event(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test building a complete measurement event."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        assert isinstance(event, MeasurementEvent)
        assert event.schema_ == "com.lifeos.measurement_event.v1"
        assert event.measure_id == "phq9"
        assert event.measure_version == "1.0.0"
        assert event.subject_id == "contact::abc"
        assert event.timestamp == "2025-01-15T10:30:00Z"

    def test_event_has_source(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that event has correct source information."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
            form_correlation_id="corr_456",
        )

        assert event.source.form_id == "googleforms::test"
        assert event.source.form_submission_id == "sub_123"
        assert event.source.form_correlation_id == "corr_456"
        assert event.source.binding_id == "example_intake"
        assert event.source.binding_version == "1.0.0"

    def test_event_has_telemetry(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that event has telemetry information."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
            warnings=["Test warning"],
        )

        assert event.telemetry.final_form_version == "0.1.0"
        assert event.telemetry.measure_spec == "phq9@1.0.0"
        assert event.telemetry.form_binding_spec == "example_intake@1.0.0"
        assert "Test warning" in event.telemetry.warnings

    def test_event_has_item_observations(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that event has item observations."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        item_obs = [o for o in event.observations if o.kind == "item"]
        assert len(item_obs) == 10  # 10 PHQ-9 items

        first_item = next(o for o in item_obs if o.code == "phq9_item1")
        assert first_item.value == 1
        assert first_item.value_type == "integer"
        assert first_item.raw_answer == "several days"
        assert first_item.position == 1

    def test_event_has_scale_observations(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that event has scale observations."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="googleforms::test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        scale_obs = [o for o in event.observations if o.kind == "scale"]
        assert len(scale_obs) == 2  # total + severity

        total = next(o for o in scale_obs if o.code == "phq9_total")
        assert total.value == 9.0
        assert total.label == "Mild"

    def test_deterministic_ids(
        self,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that deterministic IDs are reproducible."""
        builder1 = MeasurementEventBuilder(deterministic_ids=True)
        builder2 = MeasurementEventBuilder(deterministic_ids=True)

        event1 = builder1.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        event2 = builder2.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        assert event1.measurement_event_id == event2.measurement_event_id

    def test_random_ids_are_different(
        self,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that random IDs are different each time."""
        builder = MeasurementEventBuilder(deterministic_ids=False)

        event1 = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        event2 = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        assert event1.measurement_event_id != event2.measurement_event_id

    def test_json_serialization(
        self,
        builder: MeasurementEventBuilder,
        example_binding,
        phq9_recoded_section,
        phq9_scoring_result,
        phq9_interpretation_result,
    ) -> None:
        """Test that event serializes to valid JSON."""
        event = builder.build(
            recoded_section=phq9_recoded_section,
            scoring_result=phq9_scoring_result,
            interpretation_result=phq9_interpretation_result,
            binding_spec=example_binding,
            form_id="test",
            form_submission_id="sub_123",
            subject_id="contact::abc",
            timestamp="2025-01-15T10:30:00Z",
        )

        # Should serialize without error
        json_dict = event.model_dump(by_alias=True)

        assert "schema" in json_dict  # alias for schema_
        assert json_dict["schema"] == "com.lifeos.measurement_event.v1"
        assert "measurement_event_id" in json_dict
        assert "observations" in json_dict


class TestObservation:
    """Tests for Observation model."""

    def test_observation_item(self) -> None:
        """Test item observation attributes."""
        obs = Observation(
            schema="com.lifeos.observation.v1",
            observation_id="test-id",
            measure_id="phq9",
            code="phq9_item1",
            kind="item",
            value=2,
            value_type="integer",
            raw_answer="more than half the days",
            position=1,
        )

        assert obs.schema_ == "com.lifeos.observation.v1"
        assert obs.kind == "item"
        assert obs.value == 2

    def test_observation_scale(self) -> None:
        """Test scale observation attributes."""
        obs = Observation(
            schema="com.lifeos.observation.v1",
            observation_id="test-id",
            measure_id="phq9",
            code="phq9_total",
            kind="scale",
            value=15.0,
            value_type="float",
            label="Moderately severe",
        )

        assert obs.kind == "scale"
        assert obs.label == "Moderately severe"


class TestSource:
    """Tests for Source model."""

    def test_source_attributes(self) -> None:
        """Test Source model attributes."""
        source = Source(
            form_id="googleforms::abc",
            form_submission_id="sub_123",
            form_correlation_id="corr_456",
            binding_id="example_intake",
            binding_version="1.0.0",
        )

        assert source.form_id == "googleforms::abc"
        assert source.binding_id == "example_intake"


class TestTelemetry:
    """Tests for Telemetry model."""

    def test_telemetry_attributes(self) -> None:
        """Test Telemetry model attributes."""
        telemetry = Telemetry(
            processed_at="2025-01-15T10:30:00Z",
            final_form_version="0.1.0",
            measure_spec="phq9@1.0.0",
            form_binding_spec="example_intake@1.0.0",
            warnings=["Warning 1"],
        )

        assert telemetry.final_form_version == "0.1.0"
        assert len(telemetry.warnings) == 1
