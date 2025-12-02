"""Tests for the questionnaire domain processor."""

from pathlib import Path

import pytest

from final_form.core import DomainProcessor, ProcessingStatus
from final_form.domains.questionnaire import QuestionnaireProcessor
from final_form.registry import BindingRegistry, MeasureRegistry


@pytest.fixture
def processor() -> QuestionnaireProcessor:
    """Create a questionnaire processor instance."""
    return QuestionnaireProcessor()


@pytest.fixture
def measures(measure_registry_path: Path, measure_schema_path: Path) -> dict:
    """Load measure specs."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return {
        "phq9": registry.get("phq9", "1.0.0"),
        "gad7": registry.get("gad7", "1.0.0"),
    }


@pytest.fixture
def binding_spec(binding_registry_path: Path, binding_schema_path: Path):
    """Load binding spec."""
    registry = BindingRegistry(binding_registry_path, schema_path=binding_schema_path)
    return registry.get("example_intake", "1.0.0")


@pytest.fixture
def complete_form_response() -> dict:
    """A complete form response with all items."""
    return {
        "form_id": "googleforms::1FAIpQLSe_example",
        "form_submission_id": "sub_12345",
        "subject_id": "contact::abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "items": [
            # PHQ-9 items (10 items)
            {"field_key": "entry.123456001", "position": 1, "answer": "several days"},
            {"field_key": "entry.123456002", "position": 2, "answer": "not at all"},
            {"field_key": "entry.123456003", "position": 3, "answer": "more than half the days"},
            {"field_key": "entry.123456004", "position": 4, "answer": "nearly every day"},
            {"field_key": "entry.123456005", "position": 5, "answer": "several days"},
            {"field_key": "entry.123456006", "position": 6, "answer": "not at all"},
            {"field_key": "entry.123456007", "position": 7, "answer": "several days"},
            {"field_key": "entry.123456008", "position": 8, "answer": "not at all"},
            {"field_key": "entry.123456009", "position": 9, "answer": "not at all"},
            {"field_key": "entry.123456010", "position": 10, "answer": "somewhat difficult"},
            # GAD-7 items (8 items)
            {"field_key": "entry.789012001", "position": 11, "answer": "several days"},
            {"field_key": "entry.789012002", "position": 12, "answer": "not at all"},
            {"field_key": "entry.789012003", "position": 13, "answer": "several days"},
            {"field_key": "entry.789012004", "position": 14, "answer": "not at all"},
            {"field_key": "entry.789012005", "position": 15, "answer": "several days"},
            {"field_key": "entry.789012006", "position": 16, "answer": "not at all"},
            {"field_key": "entry.789012007", "position": 17, "answer": "several days"},
            {"field_key": "entry.789012008", "position": 18, "answer": "not difficult at all"},
        ],
    }


class TestQuestionnaireProcessor:
    """Tests for QuestionnaireProcessor."""

    def test_implements_domain_processor_protocol(self, processor: QuestionnaireProcessor) -> None:
        """Test that processor implements DomainProcessor protocol."""
        assert isinstance(processor, DomainProcessor)

    def test_supported_kinds(self, processor: QuestionnaireProcessor) -> None:
        """Test supported kinds property."""
        assert processor.supported_kinds == ("questionnaire", "scale", "inventory", "checklist")

    def test_process_complete_form(
        self,
        processor: QuestionnaireProcessor,
        complete_form_response: dict,
        binding_spec,
        measures: dict,
    ) -> None:
        """Test processing a complete form response."""
        result = processor.process(
            form_response=complete_form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=True,
        )

        assert result.success is True
        assert result.form_submission_id == "sub_12345"
        assert len(result.events) == 2  # PHQ-9 and GAD-7
        assert result.diagnostics.status == ProcessingStatus.SUCCESS

    def test_process_returns_measurement_events(
        self,
        processor: QuestionnaireProcessor,
        complete_form_response: dict,
        binding_spec,
        measures: dict,
    ) -> None:
        """Test that processing returns proper MeasurementEvent objects."""
        result = processor.process(
            form_response=complete_form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=True,
        )

        # Check PHQ-9 event
        phq9_event = next(e for e in result.events if e.measure_id == "phq9")
        assert phq9_event.measure_version == "1.0.0"
        assert phq9_event.subject_id == "contact::abc123"
        assert phq9_event.timestamp == "2025-01-15T10:30:00Z"
        assert len(phq9_event.observations) > 0

        # Check has both items and scales
        item_obs = [o for o in phq9_event.observations if o.kind == "item"]
        scale_obs = [o for o in phq9_event.observations if o.kind == "scale"]
        assert len(item_obs) == 10  # All 10 PHQ-9 items
        assert len(scale_obs) == 2  # total and severity scales

    def test_process_returns_diagnostics(
        self,
        processor: QuestionnaireProcessor,
        complete_form_response: dict,
        binding_spec,
        measures: dict,
    ) -> None:
        """Test that processing returns proper diagnostics."""
        result = processor.process(
            form_response=complete_form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=True,
        )

        diag = result.diagnostics
        assert diag.form_submission_id == "sub_12345"
        assert diag.form_id == "googleforms::1FAIpQLSe_example"
        assert diag.binding_id == "example_intake"
        assert len(diag.measures) == 2

    def test_process_with_deterministic_ids(
        self,
        processor: QuestionnaireProcessor,
        complete_form_response: dict,
        binding_spec,
        measures: dict,
    ) -> None:
        """Test that deterministic IDs produce consistent results."""
        result1 = processor.process(
            form_response=complete_form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=True,
        )
        result2 = processor.process(
            form_response=complete_form_response,
            binding_spec=binding_spec,
            measures=measures,
            deterministic_ids=True,
        )

        # Event IDs should be the same
        for e1, e2 in zip(result1.events, result2.events):
            assert e1.measurement_event_id == e2.measurement_event_id


class TestValidateMeasure:
    """Tests for measure validation."""

    def test_validate_valid_questionnaire(
        self,
        processor: QuestionnaireProcessor,
        measures: dict,
    ) -> None:
        """Test validation of a valid questionnaire measure."""
        errors = processor.validate_measure(measures["phq9"])
        assert errors == []

    def test_validate_wrong_kind(self, processor: QuestionnaireProcessor) -> None:
        """Test validation fails for wrong kind."""
        from final_form.registry.models import MeasureSpec

        measure = MeasureSpec(
            type="measure_spec",
            measure_id="test",
            version="1.0.0",
            name="Test",
            kind="lab_panel",  # Wrong kind for questionnaire domain
            items=[],
            scales=[],
        )

        errors = processor.validate_measure(measure)
        assert len(errors) == 1
        assert "lab_panel" in errors[0]
        assert "not supported" in errors[0]

    def test_validate_missing_items(self, processor: QuestionnaireProcessor) -> None:
        """Test validation fails for measure with no items."""
        from final_form.registry.models import MeasureSpec

        measure = MeasureSpec(
            type="measure_spec",
            measure_id="test",
            version="1.0.0",
            name="Test",
            kind="questionnaire",
            items=[],  # No items
            scales=[],
        )

        errors = processor.validate_measure(measure)
        assert any("at least one item" in e for e in errors)

    def test_validate_item_without_response_map(
        self,
        processor: QuestionnaireProcessor,
    ) -> None:
        """Test validation fails for item without response_map."""
        from final_form.registry.models import MeasureItem, MeasureSpec

        measure = MeasureSpec(
            type="measure_spec",
            measure_id="test",
            version="1.0.0",
            name="Test",
            kind="questionnaire",
            items=[
                MeasureItem(
                    item_id="item1",
                    position=1,
                    text="Question 1",
                    response_map={},  # Empty response map
                )
            ],
            scales=[],
        )

        errors = processor.validate_measure(measure)
        assert any("response_map" in e for e in errors)

    def test_validate_scale_references_unknown_item(
        self,
        processor: QuestionnaireProcessor,
    ) -> None:
        """Test validation fails for scale referencing unknown item."""
        from final_form.registry.models import MeasureItem, MeasureScale, MeasureSpec

        measure = MeasureSpec(
            type="measure_spec",
            measure_id="test",
            version="1.0.0",
            name="Test",
            kind="questionnaire",
            items=[
                MeasureItem(
                    item_id="item1",
                    position=1,
                    text="Question 1",
                    response_map={"yes": 1, "no": 0},
                )
            ],
            scales=[
                MeasureScale(
                    scale_id="total",
                    name="Total",
                    items=["item1", "item99"],  # item99 doesn't exist
                    method="sum",
                    interpretations=[],
                )
            ],
        )

        errors = processor.validate_measure(measure)
        assert any("item99" in e for e in errors)
