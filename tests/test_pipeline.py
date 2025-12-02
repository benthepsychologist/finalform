"""Tests for the pipeline orchestrator."""

from pathlib import Path

import pytest

from final_form.pipeline import Pipeline, PipelineConfig, ProcessingResult


@pytest.fixture
def pipeline_config(
    measure_registry_path: Path,
    binding_registry_path: Path,
    measure_schema_path: Path,
    binding_schema_path: Path,
) -> PipelineConfig:
    """Create a pipeline config for testing."""
    return PipelineConfig(
        measure_registry_path=measure_registry_path,
        binding_registry_path=binding_registry_path,
        binding_id="example_intake",
        binding_version="1.0.0",
        measure_schema_path=measure_schema_path,
        binding_schema_path=binding_schema_path,
        deterministic_ids=True,
    )


@pytest.fixture
def pipeline(pipeline_config: PipelineConfig) -> Pipeline:
    """Create a pipeline for testing."""
    return Pipeline(pipeline_config)


@pytest.fixture
def complete_phq9_response() -> dict:
    """A complete PHQ-9 form response (PHQ-9 only, no GAD-7)."""
    items = []
    phq9_answers = [
        "not at all",
        "several days",
        "more than half the days",
        "nearly every day",
        "not at all",
        "several days",
        "more than half the days",
        "nearly every day",
        "not at all",
        "somewhat difficult",
    ]
    # Match the actual binding field keys: entry.123456001 through entry.123456010
    for i, answer in enumerate(phq9_answers, 1):
        items.append({
            "field_key": f"entry.123456{i:03d}",
            "position": i,
            "answer": answer,
        })

    return {
        "form_id": "googleforms::test_form",
        "form_submission_id": "sub_phq9_complete",
        "subject_id": "contact::abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "items": items,
    }


@pytest.fixture
def complete_multi_instrument_response() -> dict:
    """A form response with both PHQ-9 and GAD-7."""
    items = []

    # PHQ-9 answers (10 items) - binding uses entry.123456001 through entry.123456010
    phq9_answers = ["several days"] * 9 + ["somewhat difficult"]
    for i, answer in enumerate(phq9_answers, 1):
        items.append({
            "field_key": f"entry.123456{i:03d}",
            "position": i,
            "answer": answer,
        })

    # GAD-7 answers (8 items) - binding uses entry.789012001 through entry.789012008
    gad7_answers = ["several days"] * 7 + ["somewhat difficult"]
    for i, answer in enumerate(gad7_answers, 1):
        items.append({
            "field_key": f"entry.789012{i:03d}",
            "position": 10 + i,  # Continue from PHQ-9 positions
            "answer": answer,
        })

    return {
        "form_id": "googleforms::test_form",
        "form_submission_id": "sub_multi",
        "subject_id": "contact::abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "items": items,
    }


class TestPipeline:
    """Tests for Pipeline class."""

    def test_pipeline_initialization(self, pipeline: Pipeline) -> None:
        """Test that pipeline initializes correctly."""
        assert pipeline.binding_spec.binding_id == "example_intake"
        assert "phq9" in pipeline.measures
        assert "gad7" in pipeline.measures

    def test_process_complete_response(
        self,
        pipeline: Pipeline,
        complete_phq9_response: dict,
    ) -> None:
        """Test processing a complete form response."""
        # Need to add GAD-7 items since our binding expects both
        # GAD-7 binding uses entry.789012001 through entry.789012008
        items = complete_phq9_response["items"].copy()
        gad7_answers = ["several days"] * 7 + ["somewhat difficult"]
        for i, answer in enumerate(gad7_answers, 1):
            items.append({
                "field_key": f"entry.789012{i:03d}",
                "position": 10 + i,
                "answer": answer,
            })
        complete_phq9_response["items"] = items

        result = pipeline.process(complete_phq9_response)

        assert isinstance(result, ProcessingResult)
        assert result.form_submission_id == "sub_phq9_complete"
        # Should have events for both PHQ-9 and GAD-7
        assert len(result.events) == 2

    def test_process_returns_measurement_events(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that processing returns MeasurementEvents."""
        result = pipeline.process(complete_multi_instrument_response)

        assert len(result.events) == 2  # PHQ-9 and GAD-7

        # Check PHQ-9 event
        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        assert phq9_event.measure_version == "1.0.0"
        assert phq9_event.subject_id == "contact::abc123"
        assert len(phq9_event.observations) > 0

        # Check GAD-7 event
        gad7_event = next(e for e in result.events if e.measure_id == "gad7")
        assert gad7_event.measure_version == "1.0.0"

    def test_process_includes_scores(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that events include scale scores."""
        result = pipeline.process(complete_multi_instrument_response)

        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        scale_obs = [o for o in phq9_event.observations if o.kind == "scale"]

        # PHQ-9 has 2 scales: total and severity
        assert len(scale_obs) == 2

        total_score = next(o for o in scale_obs if o.code == "phq9_total")
        assert total_score.value is not None
        assert total_score.label is not None  # Interpretation label

    def test_process_includes_item_observations(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that events include item observations."""
        result = pipeline.process(complete_multi_instrument_response)

        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        item_obs = [o for o in phq9_event.observations if o.kind == "item"]

        # PHQ-9 has 10 items
        assert len(item_obs) == 10

        first_item = next(o for o in item_obs if o.code == "phq9_item1")
        assert first_item.value == 1  # "several days" = 1

    def test_process_returns_diagnostics(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that processing returns diagnostics."""
        result = pipeline.process(complete_multi_instrument_response)

        assert result.diagnostics is not None
        assert result.diagnostics.form_submission_id == "sub_multi"
        assert result.diagnostics.binding_id == "example_intake"

    def test_process_success_status(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that complete responses get success status."""
        result = pipeline.process(complete_multi_instrument_response)

        assert result.success is True
        assert result.diagnostics.status.value in ("success", "partial")

    def test_process_batch(
        self,
        pipeline: Pipeline,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test batch processing."""
        responses = [
            complete_multi_instrument_response,
            {**complete_multi_instrument_response, "form_submission_id": "sub_2"},
        ]

        results = pipeline.process_batch(responses)

        assert len(results) == 2
        assert all(isinstance(r, ProcessingResult) for r in results)

    def test_deterministic_ids(
        self,
        pipeline_config: PipelineConfig,
        complete_multi_instrument_response: dict,
    ) -> None:
        """Test that deterministic IDs produce same results."""
        pipeline1 = Pipeline(pipeline_config)
        pipeline2 = Pipeline(pipeline_config)

        result1 = pipeline1.process(complete_multi_instrument_response)
        result2 = pipeline2.process(complete_multi_instrument_response)

        # Event IDs should match
        assert result1.events[0].measurement_event_id == result2.events[0].measurement_event_id


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_config_attributes(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
    ) -> None:
        """Test PipelineConfig has expected attributes."""
        config = PipelineConfig(
            measure_registry_path=measure_registry_path,
            binding_registry_path=binding_registry_path,
            binding_id="test_binding",
        )

        assert config.binding_id == "test_binding"
        assert config.binding_version is None
        assert config.deterministic_ids is False

    def test_config_with_version(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
    ) -> None:
        """Test PipelineConfig with version specified."""
        config = PipelineConfig(
            measure_registry_path=measure_registry_path,
            binding_registry_path=binding_registry_path,
            binding_id="test_binding",
            binding_version="2.0.0",
        )

        assert config.binding_version == "2.0.0"
