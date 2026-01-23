"""Tests for the scoring engine."""

from pathlib import Path

import pytest

from finalform.recoding import RecodedItem, RecodedSection
from finalform.registry import MeasureRegistry
from finalform.scoring import (
    ScaleScore,
    ScoringEngine,
    ScoringResult,
    apply_reverse_scoring,
    compute_score,
)
from finalform.scoring.methods import prorate_score


@pytest.fixture
def engine() -> ScoringEngine:
    """Create a scoring engine instance."""
    return ScoringEngine()


@pytest.fixture
def phq9_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the PHQ-9 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("phq9", "1.0.0")


class TestComputeScore:
    """Tests for compute_score function."""

    def test_sum_method(self) -> None:
        """Test sum scoring method."""
        values = [1, 2, 3, 4]
        result = compute_score(values, "sum")
        assert result == 10.0

    def test_average_method(self) -> None:
        """Test average scoring method."""
        values = [1, 2, 3, 4]
        result = compute_score(values, "average")
        assert result == 2.5

    def test_sum_then_double_method(self) -> None:
        """Test sum_then_double scoring method."""
        values = [1, 2, 3, 4]
        result = compute_score(values, "sum_then_double")
        assert result == 20.0

    def test_empty_values_raises(self) -> None:
        """Test that empty values raises error."""
        with pytest.raises(ValueError, match="empty"):
            compute_score([], "sum")

    def test_unknown_method_raises(self) -> None:
        """Test that unknown method raises error."""
        with pytest.raises(ValueError, match="Unknown"):
            compute_score([1, 2], "invalid")


class TestProrateScore:
    """Tests for prorate_score function."""

    def test_prorate_sum(self) -> None:
        """Test prorated sum score."""
        # 8 values out of 10 total, sum is 16
        values = [2, 2, 2, 2, 2, 2, 2, 2]
        result = prorate_score(values, "sum", 10)
        # Expected: 16 * (10/8) = 20
        assert result == 20.0

    def test_prorate_average(self) -> None:
        """Test prorated average score."""
        # Average doesn't need prorating
        values = [2, 2, 2, 2]
        result = prorate_score(values, "average", 10)
        assert result == 2.0

    def test_prorate_sum_then_double(self) -> None:
        """Test prorated sum_then_double score."""
        values = [2, 2, 2, 2]  # 4 out of 5 items, sum is 8
        result = prorate_score(values, "sum_then_double", 5)
        # Expected: 8 * (5/4) * 2 = 20
        assert result == 20.0


class TestApplyReverseScoring:
    """Tests for apply_reverse_scoring function."""

    def test_reverse_single_item(self) -> None:
        """Test reversing a single item."""
        values = {"item1": 1, "item2": 2, "item3": 3}
        result = apply_reverse_scoring(values, ["item2"], min_value=0, max_value=3)
        assert result["item1"] == 1  # unchanged
        assert result["item2"] == 1  # (3 + 0) - 2 = 1
        assert result["item3"] == 3  # unchanged

    def test_reverse_multiple_items(self) -> None:
        """Test reversing multiple items."""
        values = {"item1": 0, "item2": 1, "item3": 2, "item4": 3}
        result = apply_reverse_scoring(values, ["item1", "item3"], min_value=0, max_value=3)
        assert result["item1"] == 3  # (3 + 0) - 0 = 3
        assert result["item2"] == 1  # unchanged
        assert result["item3"] == 1  # (3 + 0) - 2 = 1
        assert result["item4"] == 3  # unchanged

    def test_reverse_nonexistent_item(self) -> None:
        """Test reversing item not in values (should be ignored)."""
        values = {"item1": 1}
        result = apply_reverse_scoring(values, ["item2"], min_value=0, max_value=3)
        assert result == {"item1": 1}

    def test_reverse_preserves_original(self) -> None:
        """Test that original dict is not modified."""
        values = {"item1": 1}
        apply_reverse_scoring(values, ["item1"], min_value=0, max_value=3)
        assert values["item1"] == 1  # Original unchanged

    def test_reverse_1_to_5_scale(self) -> None:
        """Test reverse scoring with 1-5 scale (non-zero-based)."""
        values = {"item1": 1, "item2": 2, "item3": 3, "item4": 4, "item5": 5}
        result = apply_reverse_scoring(
            values, ["item1", "item3", "item5"], min_value=1, max_value=5
        )
        assert result["item1"] == 5  # (5 + 1) - 1 = 5
        assert result["item2"] == 2  # unchanged
        assert result["item3"] == 3  # (5 + 1) - 3 = 3 (neutral stays neutral)
        assert result["item4"] == 4  # unchanged
        assert result["item5"] == 1  # (5 + 1) - 5 = 1


class TestScoringEngine:
    """Tests for the ScoringEngine class."""

    def test_score_all_scales(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test scoring all scales."""
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
                )
                for i in range(1, 11)
            ],
        )

        result = engine.score(section, phq9_spec)

        assert isinstance(result, ScoringResult)
        assert result.measure_id == "phq9"
        assert len(result.scales) == 2  # total + severity

    def test_score_phq9_total(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test PHQ-9 total score calculation."""
        # All items answered "several days" (1)
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
                )
                for i in range(1, 11)
            ],
        )

        result = engine.score(section, phq9_spec)
        total_score = result.get_scale("phq9_total")

        assert total_score is not None
        assert total_score.value == 9.0  # 9 items × 1 = 9
        assert total_score.items_used == 9
        assert total_score.items_total == 9
        assert total_score.missing_items == []
        assert total_score.prorated is False

    def test_score_with_missing_items(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test scoring with missing items (within allowed)."""
        # Items 1-8 present, item 9 missing (1 missing, 1 allowed)
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id=f"phq9_item{i}",
                    value=2,
                    raw_answer="more than half the days",
                )
                for i in range(1, 9)
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item9",
                    value=None,
                    raw_answer=None,
                    missing=True,
                )
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item10",
                    value=1,
                    raw_answer="somewhat difficult",
                )
            ],
        )

        result = engine.score(section, phq9_spec)
        total_score = result.get_scale("phq9_total")

        assert total_score is not None
        assert total_score.value is not None  # Can still score with 1 missing
        assert total_score.items_used == 8
        assert "phq9_item9" in total_score.missing_items
        assert total_score.prorated is True
        # Prorated: 8 items * 2 = 16, prorated to 9 items = 18
        assert total_score.value == 18.0

    def test_score_too_many_missing(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test scoring fails with too many missing items."""
        # Items 1-7 present, items 8-9 missing (2 missing, 1 allowed)
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
                )
                for i in range(1, 8)
            ] + [
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item8",
                    value=None,
                    raw_answer=None,
                    missing=True,
                ),
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item9",
                    value=None,
                    raw_answer=None,
                    missing=True,
                ),
                RecodedItem(
                    measure_id="phq9",
                    measure_version="1.0.0",
                    item_id="phq9_item10",
                    value=1,
                    raw_answer="somewhat difficult",
                ),
            ],
        )

        result = engine.score(section, phq9_spec)
        total_score = result.get_scale("phq9_total")

        assert total_score is not None
        assert total_score.value is None
        assert total_score.error is not None
        assert "too many missing" in total_score.error.lower()

    def test_score_single_scale(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test scoring a single scale."""
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
                )
                for i in range(1, 11)
            ],
        )

        score = engine.score_scale(section, phq9_spec, "phq9_severity")

        assert score is not None
        assert score.scale_id == "phq9_severity"
        assert score.value == 1.0  # Item 10 = 1

    def test_score_nonexistent_scale(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test scoring nonexistent scale returns None."""
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=[],
        )

        score = engine.score_scale(section, phq9_spec, "nonexistent")

        assert score is None


class TestScaleScore:
    """Tests for ScaleScore model."""

    def test_scale_score_attributes(self) -> None:
        """Test ScaleScore has expected attributes."""
        score = ScaleScore(
            scale_id="test_scale",
            name="Test Scale",
            value=15.0,
            method="sum",
            items_used=9,
            items_total=9,
            missing_items=[],
            reversed_items=[],
            prorated=False,
            error=None,
        )

        assert score.scale_id == "test_scale"
        assert score.value == 15.0
        assert score.method == "sum"
        assert score.items_used == 9

    def test_scale_score_with_error(self) -> None:
        """Test ScaleScore with error."""
        score = ScaleScore(
            scale_id="test_scale",
            name="Test Scale",
            value=None,
            method="sum",
            items_used=5,
            items_total=9,
            missing_items=["item6", "item7", "item8", "item9"],
            reversed_items=[],
            prorated=False,
            error="Too many missing items",
        )

        assert score.value is None
        assert score.error is not None
