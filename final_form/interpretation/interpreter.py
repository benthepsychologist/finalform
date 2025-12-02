"""Interpreter for applying score interpretation bands.

Looks up interpretation labels from the measure spec based on score ranges.
"""

from pydantic import BaseModel

from final_form.registry.models import MeasureSpec
from final_form.scoring.engine import ScaleScore, ScoringResult


class InterpretedScore(BaseModel):
    """A scale score with interpretation label."""

    scale_id: str
    name: str
    value: float | None
    label: str | None
    interpretation_min: int | None = None
    interpretation_max: int | None = None
    error: str | None = None


class InterpretationResult(BaseModel):
    """Result of interpreting all scale scores."""

    measure_id: str
    measure_version: str
    scores: list[InterpretedScore]

    def get_score(self, scale_id: str) -> InterpretedScore | None:
        """Get an interpreted score by scale ID."""
        for score in self.scores:
            if score.scale_id == scale_id:
                return score
        return None


class Interpreter:
    """Applies interpretation bands to scale scores.

    The interpreter reads interpretation ranges from the measure spec
    and matches scale scores to their corresponding labels.
    """

    def interpret(
        self,
        scoring_result: ScoringResult,
        measure: MeasureSpec,
    ) -> InterpretationResult:
        """Interpret all scale scores.

        Args:
            scoring_result: The scoring result with scale scores.
            measure: The measure specification.

        Returns:
            InterpretationResult with labels for all scores.
        """
        interpreted_scores: list[InterpretedScore] = []

        for scale_score in scoring_result.scales:
            interpreted = self._interpret_scale(scale_score, measure)
            interpreted_scores.append(interpreted)

        return InterpretationResult(
            measure_id=scoring_result.measure_id,
            measure_version=scoring_result.measure_version,
            scores=interpreted_scores,
        )

    def _interpret_scale(
        self,
        scale_score: ScaleScore,
        measure: MeasureSpec,
    ) -> InterpretedScore:
        """Interpret a single scale score."""
        # If no value, can't interpret
        if scale_score.value is None:
            return InterpretedScore(
                scale_id=scale_score.scale_id,
                name=scale_score.name,
                value=None,
                label=None,
                error=scale_score.error or "No score available",
            )

        # Get scale spec
        scale_spec = measure.get_scale(scale_score.scale_id)
        if scale_spec is None:
            return InterpretedScore(
                scale_id=scale_score.scale_id,
                name=scale_score.name,
                value=scale_score.value,
                label=None,
                error=f"Scale not found in measure spec: {scale_score.scale_id}",
            )

        # Find matching interpretation range
        score_value = scale_score.value
        for interp in scale_spec.interpretations:
            if interp.min <= score_value <= interp.max:
                return InterpretedScore(
                    scale_id=scale_score.scale_id,
                    name=scale_score.name,
                    value=score_value,
                    label=interp.label,
                    interpretation_min=interp.min,
                    interpretation_max=interp.max,
                    error=None,
                )

        # No matching range found
        return InterpretedScore(
            scale_id=scale_score.scale_id,
            name=scale_score.name,
            value=score_value,
            label=None,
            error=f"Score {score_value} does not match any interpretation range",
        )

    def interpret_scale(
        self,
        scale_score: ScaleScore,
        measure: MeasureSpec,
    ) -> InterpretedScore:
        """Interpret a single scale score.

        Args:
            scale_score: The scale score to interpret.
            measure: The measure specification.

        Returns:
            InterpretedScore with label.
        """
        return self._interpret_scale(scale_score, measure)

    def get_label(
        self,
        scale_id: str,
        value: float,
        measure: MeasureSpec,
    ) -> str | None:
        """Get the interpretation label for a score value.

        Args:
            scale_id: The scale ID.
            value: The score value.
            measure: The measure specification.

        Returns:
            The interpretation label, or None if not found.
        """
        scale_spec = measure.get_scale(scale_id)
        if scale_spec is None:
            return None

        for interp in scale_spec.interpretations:
            if interp.min <= value <= interp.max:
                return interp.label

        return None
