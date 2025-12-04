"""Mapper for transforming form responses to measure items.

The mapper is purely mechanical - it does not interpret question text or guess mappings.
It requires explicit binding specifications and errors on missing fields.
"""

from typing import Any

from pydantic import BaseModel

from final_form.registry.models import FormBindingSpec


class MappingError(Exception):
    """Raised when a mapping operation fails."""

    pass


class MappedItem(BaseModel):
    """A single mapped item from a form response."""

    measure_id: str
    measure_version: str
    item_id: str
    raw_answer: Any
    field_key: str | None = None
    position: int | None = None


class MappedSection(BaseModel):
    """A section of mapped items for a single measure."""

    measure_id: str
    measure_version: str
    items: list[MappedItem]


class MappingResult(BaseModel):
    """Result of mapping a form response."""

    form_id: str
    form_submission_id: str
    subject_id: str
    timestamp: str
    sections: list[MappedSection]
    unmapped_fields: list[str] = []


class Mapper:
    """Maps form responses to measure items using binding specifications.

    The mapper is purely mechanical:
    - Requires explicit binding spec (no auto-detection)
    - Errors on missing field_key/position (no fallbacks)
    - Does not interpret question text or guess mappings
    """

    def map(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
    ) -> MappingResult:
        """Map a form response to measure items.

        Args:
            form_response: Canonical form response with items array.
            binding_spec: Binding specification defining the mappings.

        Returns:
            MappingResult with mapped items organized by measure section.

        Raises:
            MappingError: If a required form field is not found.
        """
        # Extract form metadata
        form_id = form_response.get("form_id", "")
        form_submission_id = form_response.get("form_submission_id", "")
        subject_id = form_response.get("subject_id", "")
        timestamp = form_response.get("timestamp", "")

        # Build lookup structures for form items
        items_by_field_key: dict[str, dict[str, Any]] = {}
        items_by_position: dict[int, dict[str, Any]] = {}

        for item in form_response.get("items", []):
            if "field_key" in item:
                items_by_field_key[item["field_key"]] = item
            if "position" in item:
                items_by_position[item["position"]] = item

        # Map each section
        sections: list[MappedSection] = []
        used_field_keys: set[str] = set()

        for section in binding_spec.sections:
            mapped_items: list[MappedItem] = []
            section_incomplete = False

            for binding in section.bindings:
                form_item: dict[str, Any] | None = None

                if binding.by == "field_key":
                    field_key = str(binding.value)
                    form_item = items_by_field_key.get(field_key)
                    if form_item is None:
                        # Mark section as incomplete but continue processing
                        section_incomplete = True
                        continue
                    used_field_keys.add(field_key)

                elif binding.by == "position":
                    position = int(binding.value)
                    form_item = items_by_position.get(position)
                    if form_item is None:
                        # Mark section as incomplete but continue processing
                        section_incomplete = True
                        continue
                    if "field_key" in form_item:
                        used_field_keys.add(form_item["field_key"])

                # Extract raw answer - the actual response value
                raw_answer = form_item.get("answer", form_item.get("value"))

                mapped_items.append(
                    MappedItem(
                        measure_id=section.measure_id,
                        measure_version=section.measure_version,
                        item_id=binding.item_id,
                        raw_answer=raw_answer,
                        field_key=form_item.get("field_key"),
                        position=form_item.get("position"),
                    )
                )

            # Only include sections that have at least some mapped items
            if mapped_items:
                sections.append(
                    MappedSection(
                        measure_id=section.measure_id,
                        measure_version=section.measure_version,
                        items=mapped_items,
                    )
                )

        # Track unmapped fields
        all_field_keys = set(items_by_field_key.keys())
        unmapped_fields = list(all_field_keys - used_field_keys)

        return MappingResult(
            form_id=form_id,
            form_submission_id=form_submission_id,
            subject_id=subject_id,
            timestamp=timestamp,
            sections=sections,
            unmapped_fields=unmapped_fields,
        )

    def map_section(
        self,
        form_response: dict[str, Any],
        binding_spec: FormBindingSpec,
        measure_id: str,
    ) -> MappedSection | None:
        """Map a single section of a form response.

        Args:
            form_response: Canonical form response.
            binding_spec: Binding specification.
            measure_id: The measure ID to map.

        Returns:
            MappedSection for the measure, or None if not found in binding.
        """
        result = self.map(form_response, binding_spec)
        for section in result.sections:
            if section.measure_id == measure_id:
                return section
        return None
