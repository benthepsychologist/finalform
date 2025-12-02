"""Tests for the interpretation layer."""

from pathlib import Path

import pytest

from final_form.interpretation import InterpretationResult, InterpretedScore, Interpreter
from final_form.registry import MeasureRegistry
from final_form.scoring import ScaleScore, ScoringResult


@pytest.fixture
def interpreter() -> Interpreter:
    """Create an interpreter instance."""
    return Interpreter()


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


def make_scale_score(
    scale_id: str,
    name: str,
    value: float | None,
    error: str | None = None,
) -> ScaleScore:
    """Create a ScaleScore for testing."""
    return ScaleScore(
        scale_id=scale_id,
        name=name,
        value=value,
        method="sum",
        items_used=9,
        items_total=9,
        missing_items=[],
        reversed_items=[],
        prorated=False,
        error=error,
    )


def make_scoring_result(scales: list[ScaleScore]) -> ScoringResult:
    """Create a ScoringResult for testing."""
    return ScoringResult(
        measure_id="phq9",
        measure_version="1.0.0",
        scales=scales,
    )


class TestInterpreter:
    """Tests for the Interpreter class."""

    def test_interpret_phq9_minimal(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test PHQ-9 minimal interpretation (0-4)."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 3.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Minimal"
        assert result.interpretation_min == 0
        assert result.interpretation_max == 4

    def test_interpret_phq9_mild(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test PHQ-9 mild interpretation (5-9)."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 7.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Mild"
        assert result.interpretation_min == 5
        assert result.interpretation_max == 9

    def test_interpret_phq9_moderate(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test PHQ-9 moderate interpretation (10-14)."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 12.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Moderate"
        assert result.interpretation_min == 10
        assert result.interpretation_max == 14

    def test_interpret_phq9_moderately_severe(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test PHQ-9 moderately severe interpretation (15-19)."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 17.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Moderately severe"
        assert result.interpretation_min == 15
        assert result.interpretation_max == 19

    def test_interpret_phq9_severe(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test PHQ-9 severe interpretation (20-27)."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 24.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Severe"
        assert result.interpretation_min == 20
        assert result.interpretation_max == 27

    def test_interpret_at_boundary_lower(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test interpretation at lower boundary."""
        # Score of exactly 5 should be "Mild" (5-9 range)
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 5.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Mild"

    def test_interpret_at_boundary_upper(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test interpretation at upper boundary."""
        # Score of exactly 9 should be "Mild" (5-9 range)
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 9.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label == "Mild"

    def test_interpret_gad7_minimal(self, interpreter: Interpreter, gad7_spec) -> None:
        """Test GAD-7 minimal interpretation (0-4)."""
        scoring_result = ScoringResult(
            measure_id="gad7",
            measure_version="1.0.0",
            scales=[make_scale_score("gad7_total", "GAD-7 Total Score", 2.0)],
        )
        result = interpreter.interpret(scoring_result, gad7_spec)
        total = result.get_score("gad7_total")

        assert total is not None
        assert total.label == "Minimal"

    def test_interpret_gad7_severe(self, interpreter: Interpreter, gad7_spec) -> None:
        """Test GAD-7 severe interpretation (15-21)."""
        scoring_result = ScoringResult(
            measure_id="gad7",
            measure_version="1.0.0",
            scales=[make_scale_score("gad7_total", "GAD-7 Total Score", 18.0)],
        )
        result = interpreter.interpret(scoring_result, gad7_spec)
        total = result.get_score("gad7_total")

        assert total is not None
        assert total.label == "Severe"

    def test_interpret_null_value(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test interpretation with null value."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", None, error="Missing items")
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.label is None
        assert result.error is not None

    def test_interpret_multiple_scales(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test interpreting multiple scales."""
        scoring_result = make_scoring_result([
            make_scale_score("phq9_total", "PHQ-9 Total Score", 12.0),
            make_scale_score("phq9_severity", "PHQ-9 Functional Severity", 2.0),
        ])

        result = interpreter.interpret(scoring_result, phq9_spec)

        assert len(result.scores) == 2

        total = result.get_score("phq9_total")
        assert total is not None
        assert total.label == "Moderate"

        severity = result.get_score("phq9_severity")
        assert severity is not None
        assert severity.label == "Very difficult"

    def test_get_label_helper(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test get_label helper method."""
        label = interpreter.get_label("phq9_total", 15.0, phq9_spec)
        assert label == "Moderately severe"

    def test_get_label_unknown_scale(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test get_label with unknown scale."""
        label = interpreter.get_label("unknown_scale", 10.0, phq9_spec)
        assert label is None

    def test_interpret_preserves_metadata(self, interpreter: Interpreter, phq9_spec) -> None:
        """Test that interpretation preserves score metadata."""
        score = make_scale_score("phq9_total", "PHQ-9 Total Score", 10.0)
        result = interpreter.interpret_scale(score, phq9_spec)

        assert result.scale_id == "phq9_total"
        assert result.name == "PHQ-9 Total Score"
        assert result.value == 10.0


class TestInterpretedScore:
    """Tests for InterpretedScore model."""

    def test_interpreted_score_attributes(self) -> None:
        """Test InterpretedScore has expected attributes."""
        score = InterpretedScore(
            scale_id="test_scale",
            name="Test Scale",
            value=15.0,
            label="Moderate",
            interpretation_min=10,
            interpretation_max=19,
            error=None,
        )

        assert score.scale_id == "test_scale"
        assert score.value == 15.0
        assert score.label == "Moderate"
        assert score.interpretation_min == 10
        assert score.interpretation_max == 19

    def test_interpreted_score_with_error(self) -> None:
        """Test InterpretedScore with error."""
        score = InterpretedScore(
            scale_id="test_scale",
            name="Test Scale",
            value=None,
            label=None,
            error="No score available",
        )

        assert score.value is None
        assert score.label is None
        assert score.error is not None


class TestInterpretationResult:
    """Tests for InterpretationResult model."""

    def test_get_score_found(self) -> None:
        """Test get_score when score exists."""
        result = InterpretationResult(
            measure_id="phq9",
            measure_version="1.0.0",
            scores=[
                InterpretedScore(
                    scale_id="phq9_total",
                    name="PHQ-9 Total Score",
                    value=10.0,
                    label="Moderate",
                ),
            ],
        )

        score = result.get_score("phq9_total")
        assert score is not None
        assert score.label == "Moderate"

    def test_get_score_not_found(self) -> None:
        """Test get_score when score doesn't exist."""
        result = InterpretationResult(
            measure_id="phq9",
            measure_version="1.0.0",
            scores=[],
        )

        score = result.get_score("nonexistent")
        assert score is None
