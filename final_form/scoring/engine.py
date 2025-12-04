"""Scoring engine for computing scale scores.

The engine is generic - it reads all scoring rules from the measure spec.
No per-questionnaire code is allowed.
"""

from typing import Literal

from pydantic import BaseModel

from final_form.recoding.recoder import RecodedSection
from final_form.registry.models import MeasureSpec
from final_form.scoring.methods import compute_score, prorate_score
from final_form.scoring.reverse import apply_reverse_scoring, get_max_value_for_item


class ScoringError(Exception):
    """Raised when scoring fails."""

    pass


class ScaleScore(BaseModel):
    """A computed scale score."""

    scale_id: str
    name: str
    value: float | None
    method: Literal["sum", "average", "sum_then_double"]
    items_used: int
    items_total: int
    missing_items: list[str]
    reversed_items: list[str]
    prorated: bool = False
    error: str | None = None


class ScoringResult(BaseModel):
    """Result of scoring all scales in a measure."""

    measure_id: str
    measure_version: str
    scales: list[ScaleScore]

    def get_scale(self, scale_id: str) -> ScaleScore | None:
        """Get a scale score by its ID."""
        for scale in self.scales:
            if scale.scale_id == scale_id:
                return scale
        return None


class ScoringEngine:
    """Generic scoring engine that computes scale scores from recoded items.

    The engine reads all scoring rules from the measure specification:
    - Which items belong to each scale
    - Which items are reverse scored
    - The scoring method (sum, average, sum_then_double)
    - How many missing items are allowed

    No per-questionnaire code is allowed. All behavior is data-driven.
    """

    def score(
        self,
        section: RecodedSection,
        measure: MeasureSpec,
    ) -> ScoringResult:
        """Compute all scale scores for a recoded section.

        Args:
            section: The recoded section with numeric values.
            measure: The measure specification.

        Returns:
            ScoringResult with scores for all scales.
        """
        # Build lookup for item values
        item_values: dict[str, int | float | None] = {}
        for item in section.items:
            item_values[item.item_id] = item.value

        # Score each scale
        scale_scores: list[ScaleScore] = []
        for scale in measure.scales:
            score = self._score_scale(scale, item_values, measure)
            scale_scores.append(score)

        return ScoringResult(
            measure_id=section.measure_id,
            measure_version=section.measure_version,
            scales=scale_scores,
        )

    def _score_scale(
        self,
        scale,
        item_values: dict[str, int | float | None],
        measure: MeasureSpec,
    ) -> ScaleScore:
        """Score a single scale."""
        # Collect values for items in this scale
        values: dict[str, int | float] = {}
        missing_items: list[str] = []

        for item_id in scale.items:
            value = item_values.get(item_id)
            if value is None:
                missing_items.append(item_id)
            else:
                values[item_id] = value

        # Check if too many items are missing
        if len(missing_items) > scale.missing_allowed:
            strategy = getattr(scale, "missing_strategy", "fail")
            if strategy == "skip":
                # Skip silently - return null score with no error
                return ScaleScore(
                    scale_id=scale.scale_id,
                    name=scale.name,
                    value=None,
                    method=scale.method,
                    items_used=len(values),
                    items_total=len(scale.items),
                    missing_items=missing_items,
                    reversed_items=scale.reversed_items,
                    prorated=False,
                    error=None,
                )
            else:
                # "fail" or "prorate" - report the error
                return ScaleScore(
                    scale_id=scale.scale_id,
                    name=scale.name,
                    value=None,
                    method=scale.method,
                    items_used=len(values),
                    items_total=len(scale.items),
                    missing_items=missing_items,
                    reversed_items=scale.reversed_items,
                    prorated=False,
                    error=f"Too many missing items: {len(missing_items)} missing, "
                    f"{scale.missing_allowed} allowed",
                )

        # If no values at all, can't score
        if not values:
            return ScaleScore(
                scale_id=scale.scale_id,
                name=scale.name,
                value=None,
                method=scale.method,
                items_used=0,
                items_total=len(scale.items),
                missing_items=missing_items,
                reversed_items=scale.reversed_items,
                prorated=False,
                error="No values available for scoring",
            )

        # Apply reverse scoring if needed
        if scale.reversed_items:
            # Get max value from first item's response map
            # (assuming all items in scale have same response range)
            first_item_id = scale.items[0]
            first_item_spec = measure.get_item(first_item_id)
            if first_item_spec:
                max_value = get_max_value_for_item(first_item_spec.response_map)
                values = apply_reverse_scoring(values, scale.reversed_items, max_value)

        # Get list of values in scale order
        value_list = [values[item_id] for item_id in scale.items if item_id in values]

        # Compute score
        prorated = len(missing_items) > 0
        if prorated:
            score_value = prorate_score(value_list, scale.method, len(scale.items))
        else:
            score_value = compute_score(value_list, scale.method)

        return ScaleScore(
            scale_id=scale.scale_id,
            name=scale.name,
            value=score_value,
            method=scale.method,
            items_used=len(values),
            items_total=len(scale.items),
            missing_items=missing_items,
            reversed_items=scale.reversed_items,
            prorated=prorated,
            error=None,
        )

    def score_scale(
        self,
        section: RecodedSection,
        measure: MeasureSpec,
        scale_id: str,
    ) -> ScaleScore | None:
        """Score a single scale.

        Args:
            section: The recoded section.
            measure: The measure specification.
            scale_id: The scale to score.

        Returns:
            ScaleScore for the specified scale, or None if not found.
        """
        scale = measure.get_scale(scale_id)
        if scale is None:
            return None

        # Build lookup for item values
        item_values: dict[str, int | float | None] = {}
        for item in section.items:
            item_values[item.item_id] = item.value

        return self._score_scale(scale, item_values, measure)
