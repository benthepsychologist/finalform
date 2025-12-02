"""GAD-7 specific scoring tests.

These tests validate that GAD-7 scoring works correctly according to
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
def gad7_spec(measure_registry_path: Path, measure_schema_path: Path):
    """Load the GAD-7 instrument spec."""
    registry = MeasureRegistry(measure_registry_path, schema_path=measure_schema_path)
    return registry.get("gad7", "1.0.0")


def make_gad7_section(
    values: list[int],
    severity_value: int = 0,
) -> RecodedSection:
    """Create a GAD-7 section with specified values.

    Args:
        values: List of 7 values for items 1-7.
        severity_value: Value for item 8 (severity).

    Returns:
        RecodedSection with the specified values.
    """
    items = [
        RecodedItem(
            measure_id="gad7",
            measure_version="1.0.0",
            item_id=f"gad7_item{i+1}",
            value=v,
            raw_answer=str(v),
        )
        for i, v in enumerate(values)
    ]
    items.append(
        RecodedItem(
            measure_id="gad7",
            measure_version="1.0.0",
            item_id="gad7_item8",
            value=severity_value,
            raw_answer=str(severity_value),
        )
    )
    return RecodedSection(
        measure_id="gad7",
        measure_version="1.0.0",
        items=items,
    )


class TestGAD7Scoring:
    """Tests for GAD-7 scoring calculations."""

    def test_minimal_anxiety(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test minimal anxiety score (0-4)."""
        # All items = 0, total = 0
        section = make_gad7_section([0, 0, 0, 0, 0, 0, 0])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 0.0
        # Score 0-4 is "Minimal"

    def test_mild_anxiety(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test mild anxiety score (5-9)."""
        # Items: 5 × 1 + 2 × 0 = 5
        section = make_gad7_section([1, 1, 1, 1, 1, 0, 0])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 5.0
        # Score 5-9 is "Mild"

    def test_moderate_anxiety(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test moderate anxiety score (10-14)."""
        # Items: 5 × 2 = 10
        section = make_gad7_section([2, 2, 2, 2, 2, 0, 0])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 10.0
        # Score 10-14 is "Moderate"

    def test_severe_anxiety(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test severe anxiety score (15-21)."""
        # Items: 5 × 3 = 15
        section = make_gad7_section([3, 3, 3, 3, 3, 0, 0])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 15.0
        # Score 15-21 is "Severe"

    def test_maximum_score(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test maximum GAD-7 score (21)."""
        # All items = 3
        section = make_gad7_section([3, 3, 3, 3, 3, 3, 3])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 21.0

    def test_severity_scale(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test GAD-7 severity scale (item 8 only)."""
        section = make_gad7_section([1, 1, 1, 1, 1, 1, 1], severity_value=2)
        result = engine.score(section, gad7_spec)
        severity = result.get_scale("gad7_severity")

        assert severity is not None
        assert severity.value == 2.0  # "very difficult"
        assert severity.items_used == 1
        assert severity.items_total == 1

    def test_scoring_uses_sum_method(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test that GAD-7 total uses sum method."""
        section = make_gad7_section([1, 2, 1, 2, 1, 2, 1])  # Sum = 10
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.method == "sum"
        assert total.value == 10.0

    def test_item8_not_in_total(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test that item 8 is not included in total score."""
        # All symptom items = 0, severity = 3
        section = make_gad7_section([0, 0, 0, 0, 0, 0, 0], severity_value=3)
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 0.0  # Item 8 not included
        assert total.items_total == 7  # Only 7 items in total scale

    def test_gad7_has_no_reversed_items(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test that GAD-7 has no reverse-scored items."""
        section = make_gad7_section([1, 1, 1, 1, 1, 1, 1])
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.reversed_items == []

    def test_prorated_score_with_one_missing(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test prorated GAD-7 score with one missing item."""
        # 6 items = 2 each, 1 missing
        items = [
            RecodedItem(
                measure_id="gad7",
                measure_version="1.0.0",
                item_id=f"gad7_item{i}",
                value=2,
                raw_answer="2",
            )
            for i in range(1, 7)
        ]
        items.append(
            RecodedItem(
                measure_id="gad7",
                measure_version="1.0.0",
                item_id="gad7_item7",
                value=None,
                raw_answer=None,
                missing=True,
            )
        )
        items.append(
            RecodedItem(
                measure_id="gad7",
                measure_version="1.0.0",
                item_id="gad7_item8",
                value=0,
                raw_answer="0",
            )
        )
        section = RecodedSection(
            measure_id="gad7",
            measure_version="1.0.0",
            items=items,
        )

        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.prorated is True
        assert total.items_used == 6
        # Prorated: 12 * (7/6) = 14
        assert total.value == 14.0

    def test_gad7_score_at_boundary(self, engine: ScoringEngine, gad7_spec) -> None:
        """Test GAD-7 scores at interpretation boundaries."""
        # Test score of 4 (boundary between minimal and mild)
        section = make_gad7_section([1, 1, 1, 1, 0, 0, 0])  # Sum = 4
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 4.0

        # Test score of 9 (boundary between mild and moderate)
        section = make_gad7_section([2, 2, 2, 2, 1, 0, 0])  # Sum = 9
        result = engine.score(section, gad7_spec)
        total = result.get_scale("gad7_total")

        assert total is not None
        assert total.value == 9.0
