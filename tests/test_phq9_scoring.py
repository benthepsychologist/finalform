"""PHQ-9 specific scoring tests.

These tests validate that PHQ-9 scoring works correctly according to
the published scoring guidelines, using the generic scoring engine.
"""

from pathlib import Path

import pytest

from final_form.recoding import RecodedItem, RecodedSection
from final_form.registry import MeasureRegistry
from final_form.scoring import ScoringEngine


@pytest.fixture
def engine() -> ScoringEngine:
    """Create a scoring engine instance."""
    return ScoringEngine()


@pytest.fixture
def phq9_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the PHQ-9 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("phq9", "1.0.0")


def make_phq9_section(
    values: list[int],
    severity_value: int = 0,
) -> RecodedSection:
    """Create a PHQ-9 section with specified values.

    Args:
        values: List of 9 values for items 1-9.
        severity_value: Value for item 10 (severity).

    Returns:
        RecodedSection with the specified values.
    """
    items = [
        RecodedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id=f"phq9_item{i+1}",
            value=v,
            raw_answer=str(v),
        )
        for i, v in enumerate(values)
    ]
    items.append(
        RecodedItem(
            measure_id="phq9",
            measure_version="1.0.0",
            item_id="phq9_item10",
            value=severity_value,
            raw_answer=str(severity_value),
        )
    )
    return RecodedSection(
        measure_id="phq9",
        measure_version="1.0.0",
        items=items,
    )


class TestPHQ9Scoring:
    """Tests for PHQ-9 scoring calculations."""

    def test_minimal_depression(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test minimal depression score (0-4)."""
        # All items = 0, total = 0
        section = make_phq9_section([0, 0, 0, 0, 0, 0, 0, 0, 0])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 0.0
        # Score 0-4 is "Minimal"

    def test_mild_depression(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test mild depression score (5-9)."""
        # Items: 5 × 1 = 5
        section = make_phq9_section([1, 1, 1, 1, 1, 0, 0, 0, 0])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 5.0
        # Score 5-9 is "Mild"

    def test_moderate_depression(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test moderate depression score (10-14)."""
        # Items: 5 × 2 = 10
        section = make_phq9_section([2, 2, 2, 2, 2, 0, 0, 0, 0])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 10.0
        # Score 10-14 is "Moderate"

    def test_moderately_severe_depression(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test moderately severe depression score (15-19)."""
        # Items: 5 × 3 = 15
        section = make_phq9_section([3, 3, 3, 3, 3, 0, 0, 0, 0])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 15.0
        # Score 15-19 is "Moderately severe"

    def test_severe_depression(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test severe depression score (20-27)."""
        # Items: 7 × 3 = 21
        section = make_phq9_section([3, 3, 3, 3, 3, 3, 3, 0, 0])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 21.0
        # Score 20-27 is "Severe"

    def test_maximum_score(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test maximum PHQ-9 score (27)."""
        # All items = 3
        section = make_phq9_section([3, 3, 3, 3, 3, 3, 3, 3, 3])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 27.0

    def test_severity_scale(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test PHQ-9 severity scale (item 10 only)."""
        section = make_phq9_section([1, 1, 1, 1, 1, 1, 1, 1, 1], severity_value=2)
        result = engine.score(section, phq9_spec)
        severity = result.get_scale("phq9_severity")

        assert severity is not None
        assert severity.value == 2.0  # "very difficult"
        assert severity.items_used == 1
        assert severity.items_total == 1

    def test_scoring_uses_sum_method(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test that PHQ-9 total uses sum method."""
        section = make_phq9_section([1, 2, 1, 2, 1, 2, 1, 2, 1])  # Sum = 13
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.method == "sum"
        assert total.value == 13.0

    def test_item10_not_in_total(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test that item 10 is not included in total score."""
        # All symptom items = 0, severity = 3
        section = make_phq9_section([0, 0, 0, 0, 0, 0, 0, 0, 0], severity_value=3)
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.value == 0.0  # Item 10 not included
        assert total.items_total == 9  # Only 9 items in total scale

    def test_phq9_has_no_reversed_items(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test that PHQ-9 has no reverse-scored items."""
        section = make_phq9_section([1, 1, 1, 1, 1, 1, 1, 1, 1])
        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.reversed_items == []

    def test_prorated_score_with_one_missing(self, engine: ScoringEngine, phq9_spec) -> None:
        """Test prorated PHQ-9 score with one missing item."""
        # 8 items = 2 each, 1 missing
        items = [
            RecodedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id=f"phq9_item{i}",
                value=2,
                raw_answer="2",
            )
            for i in range(1, 9)
        ]
        items.append(
            RecodedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item9",
                value=None,
                raw_answer=None,
                missing=True,
            )
        )
        items.append(
            RecodedItem(
                measure_id="phq9",
                measure_version="1.0.0",
                item_id="phq9_item10",
                value=0,
                raw_answer="0",
            )
        )
        section = RecodedSection(
            measure_id="phq9",
            measure_version="1.0.0",
            items=items,
        )

        result = engine.score(section, phq9_spec)
        total = result.get_scale("phq9_total")

        assert total is not None
        assert total.prorated is True
        assert total.items_used == 8
        # Prorated: 16 * (9/8) = 18
        assert total.value == 18.0
