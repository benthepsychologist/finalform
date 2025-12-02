"""Tests for the recoding engine."""

from pathlib import Path

import pytest

from final_form.mapping import MappedItem, MappedSection, MappingResult
from final_form.recoding import RecodedItem, Recoder, RecodingError, RecodingResult
from final_form.registry import MeasureRegistry


@pytest.fixture
def recoder() -> Recoder:
    """Create a recoder instance."""
    return Recoder()


@pytest.fixture
def phq9_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the PHQ-9 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("phq9", "1.0.0")


@pytest.fixture
def gad7_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the GAD-7 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("gad7", "1.0.0")


@pytest.fixture
def phq9_mapped_section() -> MappedSection:
    """A mapped PHQ-9 section with text answers."""
    return MappedSection(
        measure_id="phq9",
        measure_version="1.0.0",
        items=[
            MappedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item1",
                raw_answer="several days",
                field_key="entry.1",
            ),
            MappedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item2",
                raw_answer="not at all",
                field_key="entry.2",
            ),
            MappedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item3",
                raw_answer="more than half the days",
                field_key="entry.3",
            ),
            MappedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item4",
                raw_answer="nearly every day",
                field_key="entry.4",
            ),
        ],
    )


@pytest.fixture
def complete_mapping_result() -> MappingResult:
    """A complete mapping result with PHQ-9 section."""
    return MappingResult(
        form_id="test_form",
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
                        item_id=f"phq9_item{i}",
                        raw_answer="several days",
                    )
                    for i in range(1, 10)
                ] + [
                    MappedItem(
                        measure_id="phq9",
                        measure_version="1.0.0",
                        item_id="phq9_item10",
                        raw_answer="somewhat difficult",
                    )
                ],
            )
        ],
    )


class TestRecoder:
    """Tests for the Recoder class."""

    def test_recode_text_answers(
        self, recoder: Recoder, phq9_spec, phq9_mapped_section: MappedSection
    ) -> None:
        """Test recoding text answers to numeric values."""
        result = recoder.recode_section(phq9_mapped_section, phq9_spec)

        assert result.measure_id == "phq9"
        assert len(result.items) == 4

        # Check values
        assert result.items[0].value == 1  # several days
        assert result.items[1].value == 0  # not at all
        assert result.items[2].value == 2  # more than half the days
        assert result.items[3].value == 3  # nearly every day

    def test_recode_preserves_metadata(
        self, recoder: Recoder, phq9_spec, phq9_mapped_section: MappedSection
    ) -> None:
        """Test that recoding preserves item metadata."""
        result = recoder.recode_section(phq9_mapped_section, phq9_spec)

        item = result.items[0]
        assert item.item_id == "phq9_item1"
        assert item.raw_answer == "several days"
        assert item.field_key == "entry.1"
        assert item.missing is False

    def test_recode_numeric_answers(self, recoder: Recoder, phq9_spec) -> None:
        """Test recoding numeric answers (pass through)."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer=2,
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 2

    def test_recode_numeric_string(self, recoder: Recoder, phq9_spec) -> None:
        """Test recoding numeric strings."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="2",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 2

    def test_recode_case_insensitive(self, recoder: Recoder, phq9_spec) -> None:
        """Test that text matching is case insensitive."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="SEVERAL DAYS",
                ),
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item2",
                    raw_answer="Not At All",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 1
        assert result.items[1].value == 0

    def test_recode_strips_whitespace(self, recoder: Recoder, phq9_spec) -> None:
        """Test that text is stripped of whitespace."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="  several days  ",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 1

    def test_recode_uses_aliases(self, recoder: Recoder, phq9_spec) -> None:
        """Test that aliases are resolved before lookup."""
        # PHQ-9 has alias: "more than half of the days" -> "more than half the days"
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="more than half of the days",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 2

    def test_recode_missing_value(self, recoder: Recoder, phq9_spec) -> None:
        """Test that missing/null values are marked."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer=None,
                ),
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item2",
                    raw_answer="",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value is None
        assert result.items[0].missing is True
        assert result.items[1].value is None
        assert result.items[1].missing is True

    def test_error_on_unknown_text(self, recoder: Recoder, phq9_spec) -> None:
        """Test that unknown text raises RecodingError."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="invalid response",
                ),
            ],
        )

        with pytest.raises(RecodingError) as exc_info:
            recoder.recode_section(section, phq9_spec)

        assert "invalid response" in str(exc_info.value)
        assert "phq9_item1" in str(exc_info.value)

    def test_error_includes_valid_responses(self, recoder: Recoder, phq9_spec) -> None:
        """Test that error message includes valid responses."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer="wrong",
                ),
            ],
        )

        with pytest.raises(RecodingError) as exc_info:
            recoder.recode_section(section, phq9_spec)

        error_msg = str(exc_info.value)
        assert "not at all" in error_msg.lower() or "Valid responses" in error_msg

    def test_error_on_out_of_range_numeric(self, recoder: Recoder, phq9_spec) -> None:
        """Test that out-of-range numeric values raise error."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    raw_answer=99,
                ),
            ],
        )

        with pytest.raises(RecodingError) as exc_info:
            recoder.recode_section(section, phq9_spec)

        assert "out of range" in str(exc_info.value).lower()

    def test_recode_full_mapping_result(
        self, recoder: Recoder, phq9_spec, complete_mapping_result: MappingResult
    ) -> None:
        """Test recoding a full mapping result."""
        result = recoder.recode(
            complete_mapping_result,
            {"phq9": phq9_spec},
        )

        assert isinstance(result, RecodingResult)
        assert result.form_id == "test_form"
        assert result.subject_id == "contact::abc"
        assert len(result.sections) == 1
        assert len(result.sections[0].items) == 10

    def test_recode_severity_item(self, recoder: Recoder, phq9_spec) -> None:
        """Test recoding PHQ-9 item 10 (severity)."""
        section = MappedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                MappedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item10",
                    raw_answer="somewhat difficult",
                ),
            ],
        )

        result = recoder.recode_section(section, phq9_spec)
        assert result.items[0].value == 1

    def test_error_on_missing_instrument(self, recoder: Recoder) -> None:
        """Test error when instrument spec is missing."""
        mapping_result = MappingResult(
            form_id="test",
            form_submission_id="test",
            subject_id="test",
            timestamp="2025-01-15T10:30:00Z",
            sections=[
                MappedSection(
                    measure_id="missing",
                    measure_version="1.0.0",
                    items=[],
                )
            ],
        )

        with pytest.raises(RecodingError) as exc_info:
            recoder.recode(mapping_result, {})

        assert "not found" in str(exc_info.value).lower()


class TestRecodedItem:
    """Tests for RecodedItem model."""

    def test_recoded_item_attributes(self) -> None:
        """Test RecodedItem has expected attributes."""
        item = RecodedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id="phq9_item1",
            value=2,
            raw_answer="more than half the days",
            missing=False,
        )

        assert item.measure_id == "phq9"
        assert item.value == 2
        assert item.raw_answer == "more than half the days"
        assert item.missing is False

    def test_recoded_item_missing(self) -> None:
        """Test RecodedItem with missing value."""
        item = RecodedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id="phq9_item1",
            value=None,
            raw_answer=None,
            missing=True,
        )

        assert item.value is None
        assert item.missing is True
