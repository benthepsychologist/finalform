"""Validation checks for recoded data.

Validates completeness, range, and flags missing items.
"""

from pydantic import BaseModel

from final_form.recoding.recoder import RecodedSection
from final_form.registry.models import MeasureSpec


class ValidationResult(BaseModel):
    """Result of validating a recoded section."""

    measure_id: str
    valid: bool
    completeness: float  # 0.0 to 1.0
    missing_items: list[str]
    out_of_range_items: list[str]
    errors: list[str]

    @property
    def missing_count(self) -> int:
        """Number of missing items."""
        return len(self.missing_items)

    @property
    def has_errors(self) -> bool:
        """Whether there are any validation errors."""
        return len(self.errors) > 0 or len(self.out_of_range_items) > 0


class Validator:
    """Validates recoded data for completeness and correctness.

    Checks:
    1. Completeness: All items in measure spec are present
    2. Range: All values within valid range (0 to max anchor value)
    3. Missing: Flags and counts missing items
    """

    def validate(
        self,
        section: RecodedSection,
        measure: MeasureSpec,
    ) -> ValidationResult:
        """Validate a recoded section against the measure spec.

        Args:
            section: The recoded section to validate.
            measure: The measure specification.

        Returns:
            ValidationResult with validation status and details.
        """
        errors: list[str] = []
        missing_items: list[str] = []
        out_of_range_items: list[str] = []

        # Build set of item IDs in the recoded section
        recoded_item_ids = {item.item_id for item in section.items}

        # Build set of expected item IDs from measure
        expected_item_ids = {item.item_id for item in measure.items}

        # Check for missing items (in measure but not in recoded)
        for item_id in expected_item_ids:
            if item_id not in recoded_item_ids:
                missing_items.append(item_id)

        # Check for items marked as missing
        for item in section.items:
            if item.missing:
                if item.item_id not in missing_items:
                    missing_items.append(item.item_id)

        # Validate each item
        for item in section.items:
            if item.missing or item.value is None:
                continue

            # Get item spec for range validation
            item_spec = measure.get_item(item.item_id)
            if item_spec is None:
                errors.append(f"Unknown item: {item.item_id}")
                continue

            # Get valid range from response_map
            valid_values = list(item_spec.response_map.values())
            min_val = min(valid_values)
            max_val = max(valid_values)

            # Check if value is in valid range
            if not (min_val <= item.value <= max_val):
                out_of_range_items.append(item.item_id)
                errors.append(
                    f"Item {item.item_id}: value {item.value} "
                    f"out of range [{min_val}, {max_val}]"
                )

        # Calculate completeness
        total_items = len(expected_item_ids)
        present_items = total_items - len(missing_items)
        completeness = present_items / total_items if total_items > 0 else 1.0

        # Determine overall validity
        # Valid if no errors, no out-of-range, and completeness is acceptable
        valid = len(errors) == 0 and len(out_of_range_items) == 0

        return ValidationResult(
            measure_id=section.measure_id,
            valid=valid,
            completeness=completeness,
            missing_items=sorted(missing_items),
            out_of_range_items=sorted(out_of_range_items),
            errors=errors,
        )

    def validate_for_scale(
        self,
        section: RecodedSection,
        measure: MeasureSpec,
        scale_id: str,
    ) -> ValidationResult:
        """Validate a section for a specific scale.

        Checks only the items that are part of the specified scale.

        Args:
            section: The recoded section to validate.
            measure: The measure specification.
            scale_id: The scale to validate for.

        Returns:
            ValidationResult for the scale's items only.
        """
        scale = measure.get_scale(scale_id)
        if scale is None:
            return ValidationResult(
                measure_id=section.measure_id,
                valid=False,
                completeness=0.0,
                missing_items=[],
                out_of_range_items=[],
                errors=[f"Unknown scale: {scale_id}"],
            )

        errors: list[str] = []
        missing_items: list[str] = []
        out_of_range_items: list[str] = []

        # Build lookup for recoded items
        recoded_items_by_id = {item.item_id: item for item in section.items}

        # Check each item in the scale
        for item_id in scale.items:
            recoded_item = recoded_items_by_id.get(item_id)

            if recoded_item is None:
                missing_items.append(item_id)
                continue

            if recoded_item.missing or recoded_item.value is None:
                missing_items.append(item_id)
                continue

            # Get item spec for range validation
            item_spec = measure.get_item(item_id)
            if item_spec is None:
                errors.append(f"Unknown item in scale: {item_id}")
                continue

            # Check range
            valid_values = list(item_spec.response_map.values())
            min_val = min(valid_values)
            max_val = max(valid_values)

            if not (min_val <= recoded_item.value <= max_val):
                out_of_range_items.append(item_id)
                errors.append(
                    f"Item {item_id}: value {recoded_item.value} "
                    f"out of range [{min_val}, {max_val}]"
                )

        # Calculate completeness for this scale
        total_items = len(scale.items)
        present_items = total_items - len(missing_items)
        completeness = present_items / total_items if total_items > 0 else 1.0

        # Check if missing count is acceptable for this scale
        missing_allowed = scale.missing_allowed
        too_many_missing = len(missing_items) > missing_allowed

        valid = (
            len(errors) == 0
            and len(out_of_range_items) == 0
            and not too_many_missing
        )

        if too_many_missing:
            errors.append(
                f"Too many missing items for scale {scale_id}: "
                f"{len(missing_items)} missing, {missing_allowed} allowed"
            )

        return ValidationResult(
            measure_id=section.measure_id,
            valid=valid,
            completeness=completeness,
            missing_items=sorted(missing_items),
            out_of_range_items=sorted(out_of_range_items),
            errors=errors,
        )
