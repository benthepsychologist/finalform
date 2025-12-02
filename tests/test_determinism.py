"""Tests for pipeline determinism.

Verifies that the same input always produces the same output.
"""

import json
from pathlib import Path

import pytest

from final_form.pipeline import Pipeline, PipelineConfig


@pytest.fixture
def deterministic_pipeline(
    measure_registry_path: Path,
    binding_registry_path: Path,
    measure_schema_path: Path,
    binding_schema_path: Path,
) -> Pipeline:
    """Create a pipeline with deterministic IDs."""
    config = PipelineConfig(
        measure_registry_path=measure_registry_path,
        binding_registry_path=binding_registry_path,
        binding_id="example_intake",
        binding_version="1.0.0",
        measure_schema_path=measure_schema_path,
        binding_schema_path=binding_schema_path,
        deterministic_ids=True,
    )
    return Pipeline(config)


@pytest.fixture
def golden_form_response() -> dict:
    """Load the golden test form response."""
    fixture_path = Path(__file__).parent / "fixtures" / "canonical" / "phq9_complete.json"
    with open(fixture_path) as f:
        return json.load(f)


class TestDeterminism:
    """Tests for processing determinism."""

    def test_same_input_same_output(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        measure_schema_path: Path,
        binding_schema_path: Path,
        golden_form_response: dict,
    ) -> None:
        """Test that processing the same input produces identical output."""
        # Create two independent pipelines
        config = PipelineConfig(
            measure_registry_path=measure_registry_path,
            binding_registry_path=binding_registry_path,
            binding_id="example_intake",
            binding_version="1.0.0",
            measure_schema_path=measure_schema_path,
            binding_schema_path=binding_schema_path,
            deterministic_ids=True,
        )

        pipeline1 = Pipeline(config)
        pipeline2 = Pipeline(config)

        result1 = pipeline1.process(golden_form_response)
        result2 = pipeline2.process(golden_form_response)

        # Event IDs should match
        assert len(result1.events) == len(result2.events)
        for e1, e2 in zip(result1.events, result2.events):
            assert e1.measurement_event_id == e2.measurement_event_id

        # Observation IDs should match
        for e1, e2 in zip(result1.events, result2.events):
            assert len(e1.observations) == len(e2.observations)
            for o1, o2 in zip(e1.observations, e2.observations):
                assert o1.observation_id == o2.observation_id

    def test_repeated_processing_same_output(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        measure_schema_path: Path,
        binding_schema_path: Path,
        golden_form_response: dict,
    ) -> None:
        """Test that repeated processing produces identical results when starting fresh."""
        # Process the same input 5 times with fresh pipelines each time
        results = []
        for _ in range(5):
            # Create a fresh pipeline to reset the counter
            config = PipelineConfig(
                measure_registry_path=measure_registry_path,
                binding_registry_path=binding_registry_path,
                binding_id="example_intake",
                binding_version="1.0.0",
                measure_schema_path=measure_schema_path,
                binding_schema_path=binding_schema_path,
                deterministic_ids=True,
            )
            pipeline = Pipeline(config)
            results.append(pipeline.process(golden_form_response))

        # All results should have the same event IDs (fresh pipelines = same counters)
        first_event_ids = [e.measurement_event_id for e in results[0].events]
        for result in results[1:]:
            event_ids = [e.measurement_event_id for e in result.events]
            assert event_ids == first_event_ids

    def test_json_serialization_deterministic(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test that JSON serialization is deterministic."""
        result1 = deterministic_pipeline.process(golden_form_response)
        # Reset the pipeline to get fresh counters
        new_pipeline = Pipeline(deterministic_pipeline.config)
        result2 = new_pipeline.process(golden_form_response)

        # JSON output should be identical (excluding telemetry.processed_at)
        for e1, e2 in zip(result1.events, result2.events):
            json1 = e1.model_dump(by_alias=True)
            json2 = e2.model_dump(by_alias=True)

            # Remove processed_at since it will differ
            del json1["telemetry"]["processed_at"]
            del json2["telemetry"]["processed_at"]

            assert json1 == json2

    def test_score_values_deterministic(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test that score values are deterministic."""
        results = [deterministic_pipeline.process(golden_form_response) for _ in range(3)]

        # Get PHQ-9 scores from each run
        phq9_scores = []
        for result in results:
            phq9_event = next(e for e in result.events if e.measure_id == "phq9")
            total_obs = next(o for o in phq9_event.observations if o.code == "phq9_total")
            phq9_scores.append(total_obs.value)

        # All scores should be identical
        assert all(s == phq9_scores[0] for s in phq9_scores)


class TestGoldenOutput:
    """Tests for golden output verification."""

    def test_phq9_expected_scores(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test PHQ-9 produces expected scores for golden input."""
        result = deterministic_pipeline.process(golden_form_response)

        phq9_event = next(e for e in result.events if e.measure_id == "phq9")

        # Check PHQ-9 total score
        # Input: 0, 1, 2, 3, 0, 1, 2, 3, 0 = 12
        total_obs = next(o for o in phq9_event.observations if o.code == "phq9_total")
        assert total_obs.value == 12.0
        assert total_obs.label == "Moderate"  # 10-14 range

        # Check PHQ-9 severity
        severity_obs = next(o for o in phq9_event.observations if o.code == "phq9_severity")
        assert severity_obs.value == 1.0  # "somewhat difficult" = 1
        assert severity_obs.label == "Somewhat difficult"

    def test_gad7_expected_scores(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test GAD-7 produces expected scores for golden input."""
        result = deterministic_pipeline.process(golden_form_response)

        gad7_event = next(e for e in result.events if e.measure_id == "gad7")

        # Check GAD-7 total score
        # Input: 0, 1, 2, 3, 0, 1, 2 = 9
        total_obs = next(o for o in gad7_event.observations if o.code == "gad7_total")
        assert total_obs.value == 9.0
        assert total_obs.label == "Mild"  # 5-9 range

    def test_item_observations_count(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test that correct number of item observations are generated."""
        result = deterministic_pipeline.process(golden_form_response)

        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        phq9_items = [o for o in phq9_event.observations if o.kind == "item"]
        assert len(phq9_items) == 10  # PHQ-9 has 10 items

        gad7_event = next(e for e in result.events if e.measure_id == "gad7")
        gad7_items = [o for o in gad7_event.observations if o.kind == "item"]
        assert len(gad7_items) == 8  # GAD-7 has 8 items

    def test_telemetry_metadata(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test that telemetry contains expected metadata."""
        result = deterministic_pipeline.process(golden_form_response)

        for event in result.events:
            assert event.telemetry.final_form_version == "0.1.0"
            assert event.telemetry.form_binding_spec == "example_intake@1.0.0"

        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        assert phq9_event.telemetry.measure_spec == "phq9@1.0.0"

        gad7_event = next(e for e in result.events if e.measure_id == "gad7")
        assert gad7_event.telemetry.measure_spec == "gad7@1.0.0"

    def test_source_metadata(
        self,
        deterministic_pipeline: Pipeline,
        golden_form_response: dict,
    ) -> None:
        """Test that source contains expected metadata."""
        result = deterministic_pipeline.process(golden_form_response)

        for event in result.events:
            assert event.source.form_id == "googleforms::1FAIpQLSe_example"
            assert event.source.form_submission_id == "golden_phq9_complete"
            assert event.source.binding_id == "example_intake"
            assert event.source.binding_version == "1.0.0"
