"""Recoder for transforming raw answers to numeric values.

The recoder transforms text responses to numeric values using the measure's
response_map. It does not perform fuzzy matching - text must match exactly
(after normalization and alias resolution).
"""

from typing import Any

from pydantic import BaseModel

from final_form.mapping.mapper import MappedItem, MappedSection, MappingResult
from final_form.registry.models import MeasureSpec


class RecodingError(Exception):
    """Raised when a recoding operation fails."""

    pass


class RecodedItem(BaseModel):
    """A recoded item with numeric value."""

    measure_id: str
    measure_version: str
    item_id: str
    value: int | float | None
    raw_answer: Any
    missing: bool = False
    field_key: str | None = None
    position: int | None = None


class RecodedSection(BaseModel):
    """A section of recoded items for a single measure."""

    measure_id: str
    measure_version: str
    items: list[RecodedItem]


class RecodingResult(BaseModel):
    """Result of recoding a mapped form response."""

    form_id: str
    form_submission_id: str
    subject_id: str
    timestamp: str
    sections: list[RecodedSection]


class Recoder:
    """Recodes raw answers to numeric values using measure specifications.

    The recoder is strict:
    - Text must match response_map exactly (after normalization)
    - Aliases are resolved to canonical text before lookup
    - No fuzzy matching or guessing
    """

    def recode(
        self,
        mapping_result: MappingResult,
        measures: dict[str, MeasureSpec],
    ) -> RecodingResult:
        """Recode all mapped items to numeric values.

        Args:
            mapping_result: Result from the mapping engine.
            measures: Dictionary of measure_id -> MeasureSpec.

        Returns:
            RecodingResult with numeric values for all items.

        Raises:
            RecodingError: If a text value cannot be recoded.
        """
        sections: list[RecodedSection] = []

        for mapped_section in mapping_result.sections:
            measure = measures.get(mapped_section.measure_id)
            if measure is None:
                raise RecodingError(
                    f"Measure spec not found: {mapped_section.measure_id}"
                )

            recoded_items = self._recode_section(mapped_section, measure)
            sections.append(
                RecodedSection(
                    measure_id=mapped_section.measure_id,
                    measure_version=mapped_section.measure_version,
                    items=recoded_items,
                )
            )

        return RecodingResult(
            form_id=mapping_result.form_id,
            form_submission_id=mapping_result.form_submission_id,
            subject_id=mapping_result.subject_id,
            timestamp=mapping_result.timestamp,
            sections=sections,
        )

    def _recode_section(
        self,
        section: MappedSection,
        measure: MeasureSpec,
    ) -> list[RecodedItem]:
        """Recode all items in a section."""
        recoded_items: list[RecodedItem] = []

        for mapped_item in section.items:
            recoded_item = self._recode_item(mapped_item, measure)
            recoded_items.append(recoded_item)

        return recoded_items

    def _recode_item(
        self,
        mapped_item: MappedItem,
        measure: MeasureSpec,
    ) -> RecodedItem:
        """Recode a single mapped item."""
        item_spec = measure.get_item(mapped_item.item_id)
        if item_spec is None:
            raise RecodingError(
                f"Item not found in measure spec: {mapped_item.item_id} "
                f"in measure {measure.measure_id}"
            )

        raw_answer = mapped_item.raw_answer
        value: int | float | None = None
        missing = False

        # Handle missing/null values
        if raw_answer is None or raw_answer == "":
            missing = True
            value = None
        # Handle numeric values (int or float)
        elif isinstance(raw_answer, (int, float)) and not isinstance(raw_answer, bool):
            value = self._validate_numeric(raw_answer, item_spec, mapped_item.item_id)
        # Handle string values
        elif isinstance(raw_answer, str):
            value = self._recode_string(raw_answer, item_spec, mapped_item.item_id)
        else:
            raise RecodingError(
                f"Unsupported answer type for item {mapped_item.item_id}: "
                f"{type(raw_answer).__name__}"
            )

        return RecodedItem(
            measure_id=mapped_item.measure_id,
            measure_version=mapped_item.measure_version,
            item_id=mapped_item.item_id,
            value=value,
            raw_answer=raw_answer,
            missing=missing,
            field_key=mapped_item.field_key,
            position=mapped_item.position,
        )

    def _validate_numeric(
        self,
        value: int | float,
        item_spec: Any,
        item_id: str,
    ) -> int | float:
        """Validate a numeric value against the response map range."""
        # Get valid range from response_map values
        valid_values = list(item_spec.response_map.values())
        min_val = min(valid_values)
        max_val = max(valid_values)

        if not (min_val <= value <= max_val):
            raise RecodingError(
                f"Value {value} out of range [{min_val}, {max_val}] for item {item_id}"
            )

        return value

    def _recode_string(
        self,
        raw_answer: str,
        item_spec: Any,
        item_id: str,
    ) -> int:
        """Recode a string answer to a numeric value."""
        # Try to parse as numeric first
        try:
            numeric = float(raw_answer)
            if numeric.is_integer():
                numeric = int(numeric)
            return self._validate_numeric(numeric, item_spec, item_id)
        except ValueError:
            pass

        # Normalize: lowercase and strip whitespace
        normalized = raw_answer.lower().strip()

        # Check aliases first to resolve to canonical text
        if item_spec.aliases and normalized in item_spec.aliases:
            canonical = item_spec.aliases[normalized]
            normalized = canonical.lower().strip()

        # Build lowercase response map for lookup
        response_map_lower = {k.lower().strip(): v for k, v in item_spec.response_map.items()}

        if normalized not in response_map_lower:
            valid_responses = list(item_spec.response_map.keys())
            raise RecodingError(
                f"Unknown response '{raw_answer}' for item {item_id}. "
                f"Valid responses: {valid_responses}"
            )

        return response_map_lower[normalized]

    def recode_section(
        self,
        mapped_section: MappedSection,
        measure: MeasureSpec,
    ) -> RecodedSection:
        """Recode a single section.

        Args:
            mapped_section: The mapped section to recode.
            measure: The measure specification.

        Returns:
            RecodedSection with numeric values.
        """
        recoded_items = self._recode_section(mapped_section, measure)
        return RecodedSection(
            measure_id=mapped_section.measure_id,
            measure_version=mapped_section.measure_version,
            items=recoded_items,
        )
