"""Tests for the validation layer."""

from pathlib import Path

import pytest

from final_form.recoding import RecodedItem, RecodedSection
from final_form.registry import MeasureRegistry
from final_form.validation import ValidationResult, Validator


@pytest.fixture
def validator() -> Validator:
    """Create a validator instance."""
    return Validator()


@pytest.fixture
def phq9_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the PHQ-9 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("phq9", "1.0.0")


@pytest.fixture
def complete_phq9_section() -> RecodedSection:
    """A complete PHQ-9 section with all 10 items."""
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
                missing=False,
            )
            for i in range(1, 11)
        ],
    )


@pytest.fixture
def partial_phq9_section() -> RecodedSection:
    """A partial PHQ-9 section with 1 missing item."""
    items = [
        RecodedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id=f"phq9_item{i}",
            value=1,
            raw_answer="several days",
            missing=False,
        )
        for i in range(1, 10)  # Missing item 10
    ]
    # Also mark item 9 as missing (null value)
    items[8] = RecodedItem(
        measure_id="phq9",
        measure_version="1.0.0",
        item_id="phq9_item9",
        value=None,
        raw_answer=None,
        missing=True,
    )
    return RecodedSection(
        measure_id="phq9",
        measure_version="1.0.0",
        items=items,
    )


class TestValidator:
    """Tests for the Validator class."""

    def test_validate_complete_section(
        self, validator: Validator, phq9_spec, complete_phq9_section: RecodedSection
    ) -> None:
        """Test validating a complete section."""
        result = validator.validate(complete_phq9_section, phq9_spec)

        assert isinstance(result, ValidationResult)
        assert result.valid is True
        assert result.completeness == 1.0
        assert result.missing_items == []
        assert result.out_of_range_items == []
        assert result.errors == []

    def test_validate_partial_section(
        self, validator: Validator, phq9_spec, partial_phq9_section: RecodedSection
    ) -> None:
        """Test validating a partial section with missing items."""
        result = validator.validate(partial_phq9_section, phq9_spec)

        assert result.valid is True  # Still valid, just incomplete
        assert result.completeness == 0.8  # 8/10 items present
        assert "phq9_item9" in result.missing_items
        assert "phq9_item10" in result.missing_items
        assert result.missing_count == 2

    def test_validate_out_of_range(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test validation catches out-of-range values."""
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    value=99,  # Out of range (valid: 0-3)
                    raw_answer=99,
                    missing=False,
                )
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(2, 11)
            ],
        )

        result = validator.validate(section, phq9_spec)

        assert result.valid is False
        assert "phq9_item1" in result.out_of_range_items
        assert result.has_errors is True
        assert any("out of range" in e.lower() for e in result.errors)

    def test_validate_completeness_calculation(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test completeness calculation."""
        # Create section with half the items
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(1, 6)  # Only items 1-5
            ],
        )

        result = validator.validate(section, phq9_spec)

        assert result.completeness == 0.5  # 5/10 items

    def test_validate_for_scale(
        self, validator: Validator, phq9_spec, complete_phq9_section: RecodedSection
    ) -> None:
        """Test validating for a specific scale."""
        result = validator.validate_for_scale(
            complete_phq9_section, phq9_spec, "phq9_total"
        )

        assert result.valid is True
        assert result.completeness == 1.0
        assert result.missing_items == []

    def test_validate_for_scale_with_missing(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test scale validation with missing items."""
        # Create section missing item 1 (part of phq9_total scale)
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(2, 11)  # Missing item 1
            ],
        )

        result = validator.validate_for_scale(section, phq9_spec, "phq9_total")

        # phq9_total allows 1 missing, so still valid
        assert result.valid is True
        assert "phq9_item1" in result.missing_items
        assert result.completeness == 8 / 9  # 8/9 items in total scale

    def test_validate_for_scale_too_many_missing(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test scale validation fails with too many missing items."""
        # Create section missing items 1 and 2 (phq9_total allows only 1 missing)
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(3, 11)  # Missing items 1 and 2
            ],
        )

        result = validator.validate_for_scale(section, phq9_spec, "phq9_total")

        assert result.valid is False
        assert "phq9_item1" in result.missing_items
        assert "phq9_item2" in result.missing_items
        assert any("too many missing" in e.lower() for e in result.errors)

    def test_validate_for_unknown_scale(
        self, validator: Validator, phq9_spec, complete_phq9_section: RecodedSection
    ) -> None:
        """Test validation for unknown scale."""
        result = validator.validate_for_scale(
            complete_phq9_section, phq9_spec, "unknown_scale"
        )

        assert result.valid is False
        assert any("unknown scale" in e.lower() for e in result.errors)

    def test_validation_result_properties(self) -> None:
        """Test ValidationResult properties."""
        result = ValidationResult(
            measure_id="phq9",
            valid=False,
            completeness=0.8,
            missing_items=["item1", "item2"],
            out_of_range_items=["item3"],
            errors=["Some error"],
        )

        assert result.missing_count == 2
        assert result.has_errors is True

    def test_validation_result_no_errors(self) -> None:
        """Test ValidationResult has_errors when no errors."""
        result = ValidationResult(
            measure_id="phq9",
            valid=True,
            completeness=1.0,
            missing_items=[],
            out_of_range_items=[],
            errors=[],
        )

        assert result.has_errors is False

    def test_validate_negative_value(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test validation catches negative values."""
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item1",
                    value=-1,  # Negative, out of range
                    raw_answer=-1,
                    missing=False,
                )
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(2, 11)
            ],
        )

        result = validator.validate(section, phq9_spec)

        assert result.valid is False
        assert "phq9_item1" in result.out_of_range_items

    def test_validate_severity_item(
        self, validator: Validator, phq9_spec
    ) -> None:
        """Test validation of severity item (item 10)."""
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=1,
                    raw_answer="several days",
                    missing=False,
                )
                for i in range(1, 10)
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item10",
                    value=2,  # "very difficult" = 2
                    raw_answer="very difficult",
                    missing=False,
                )
            ],
        )

        result = validator.validate(section, phq9_spec)

        assert result.valid is True
        assert "phq9_item10" not in result.out_of_range_items
