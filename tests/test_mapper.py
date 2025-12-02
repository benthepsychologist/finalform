"""Tests for the mapping engine."""

from pathlib import Path

import pytest

from final_form.mapping import MappedItem, Mapper, MappingError, MappingResult
from final_form.registry import BindingRegistry


@pytest.fixture
def mapper() -> Mapper:
    """Create a mapper instance."""
    return Mapper()


@pytest.fixture
def example_binding(binding_registry_path: Path, binding_schema_path: Path):
    """Load the example_intake binding spec."""
    registry = BindingRegistry(binding_registry_path, schema_path=binding_schema_path)
    return registry.get("example_intake", "1.0.0")


@pytest.fixture
def complete_phq9_response() -> dict:
    """A complete PHQ-9 form response with all 10 items."""
    return {
        "form_id": "googleforms::1FAIpQLSe_example",
        "form_submission_id": "sub_12345",
        "subject_id": "contact::abc123",
        "timestamp": "2025-01-15T10:30:00Z",
        "items": [
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
            # GAD-7 items
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


class TestMapper:
    """Tests for the Mapper class."""

    def test_map_complete_form(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test mapping a complete form response."""
        result = mapper.map(complete_phq9_response, example_binding)

        assert isinstance(result, MappingResult)
        assert result.form_id == "googleforms::1FAIpQLSe_example"
        assert result.form_submission_id == "sub_12345"
        assert result.subject_id == "contact::abc123"
        assert len(result.sections) == 2  # PHQ-9 and GAD-7

    def test_map_phq9_section(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test mapping PHQ-9 section."""
        result = mapper.map(complete_phq9_response, example_binding)

        phq9_section = next(s for s in result.sections if s.measure_id == "phq9")
        assert phq9_section.measure_version == "1.0.0"
        assert len(phq9_section.items) == 10  # All 10 PHQ-9 items

        # Check first item
        item1 = next(i for i in phq9_section.items if i.item_id == "phq9_item1")
        assert item1.raw_answer == "several days"
        assert item1.field_key == "entry.123456001"

    def test_map_gad7_section(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test mapping GAD-7 section."""
        result = mapper.map(complete_phq9_response, example_binding)

        gad7_section = next(s for s in result.sections if s.measure_id == "gad7")
        assert gad7_section.measure_version == "1.0.0"
        assert len(gad7_section.items) == 8  # All 8 GAD-7 items

    def test_map_preserves_raw_answers(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test that raw answers are preserved exactly."""
        result = mapper.map(complete_phq9_response, example_binding)

        phq9_section = next(s for s in result.sections if s.measure_id == "phq9")

        expected_answers = {
            "phq9_item1": "several days",
            "phq9_item2": "not at all",
            "phq9_item3": "more than half the days",
            "phq9_item4": "nearly every day",
            "phq9_item10": "somewhat difficult",
        }

        for item_id, expected in expected_answers.items():
            item = next(i for i in phq9_section.items if i.item_id == item_id)
            assert item.raw_answer == expected

    def test_error_on_missing_field_key(
        self, mapper: Mapper, example_binding
    ) -> None:
        """Test that missing field_key raises MappingError."""
        incomplete_response = {
            "form_id": "googleforms::1FAIpQLSe_example",
            "form_submission_id": "sub_12345",
            "subject_id": "contact::abc123",
            "timestamp": "2025-01-15T10:30:00Z",
            "items": [
                # Missing entry.123456001 (phq9_item1)
                {"field_key": "entry.123456002", "answer": "not at all"},
            ],
        }

        with pytest.raises(MappingError) as exc_info:
            mapper.map(incomplete_response, example_binding)

        assert "field_key='entry.123456001'" in str(exc_info.value)
        assert "phq9_item1" in str(exc_info.value)

    def test_error_message_includes_context(
        self, mapper: Mapper, example_binding
    ) -> None:
        """Test that error messages include helpful context."""
        incomplete_response = {
            "form_id": "test",
            "form_submission_id": "test",
            "subject_id": "test",
            "timestamp": "2025-01-15T10:30:00Z",
            "items": [],
        }

        with pytest.raises(MappingError) as exc_info:
            mapper.map(incomplete_response, example_binding)

        error_msg = str(exc_info.value)
        assert "measure" in error_msg.lower()
        assert "phq9" in error_msg

    def test_map_with_numeric_answers(
        self, mapper: Mapper, example_binding
    ) -> None:
        """Test mapping form responses with numeric answers."""
        response = {
            "form_id": "googleforms::1FAIpQLSe_example",
            "form_submission_id": "sub_12345",
            "subject_id": "contact::abc123",
            "timestamp": "2025-01-15T10:30:00Z",
            "items": [
                {"field_key": f"entry.1234560{i:02d}", "answer": i % 4}
                for i in range(1, 11)
            ] + [
                {"field_key": f"entry.7890120{i:02d}", "answer": i % 4}
                for i in range(1, 9)
            ],
        }

        result = mapper.map(response, example_binding)

        phq9_section = next(s for s in result.sections if s.measure_id == "phq9")
        assert phq9_section.items[0].raw_answer == 1
        assert phq9_section.items[3].raw_answer == 0  # 4 % 4

    def test_map_tracks_unmapped_fields(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test that unmapped form fields are tracked."""
        # Add an extra field that's not in the binding
        response = complete_phq9_response.copy()
        response["items"] = response["items"] + [
            {"field_key": "entry.extra_field", "answer": "extra value"}
        ]

        result = mapper.map(response, example_binding)

        assert "entry.extra_field" in result.unmapped_fields

    def test_map_section_returns_specific_instrument(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test map_section returns only the requested instrument."""
        section = mapper.map_section(
            complete_phq9_response, example_binding, "phq9"
        )

        assert section is not None
        assert section.measure_id == "phq9"
        assert len(section.items) == 10

    def test_map_section_returns_none_for_unknown_instrument(
        self, mapper: Mapper, example_binding, complete_phq9_response: dict
    ) -> None:
        """Test map_section returns None for unknown instrument."""
        section = mapper.map_section(
            complete_phq9_response, example_binding, "unknown"
        )

        assert section is None


class TestMappedItem:
    """Tests for MappedItem model."""

    def test_mapped_item_attributes(self) -> None:
        """Test MappedItem has expected attributes."""
        item = MappedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id="phq9_item1",
            raw_answer="several days",
            field_key="entry.123",
            position=1,
        )

        assert item.measure_id == "phq9"
        assert item.measure_version == "1.0.0"
        assert item.item_id == "phq9_item1"
        assert item.raw_answer == "several days"
        assert item.field_key == "entry.123"
        assert item.position == 1

    def test_mapped_item_optional_fields(self) -> None:
        """Test MappedItem with optional fields."""
        item = MappedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id="phq9_item1",
            raw_answer="several days",
        )

        assert item.field_key is None
        assert item.position is None
