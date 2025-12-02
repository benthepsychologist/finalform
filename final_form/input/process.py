"""High-level API for processing canonical form submissions.

This module provides the main entrypoint for processing forms that come
from canonizer. It handles the mapping from canonical form shape to
final-form's internal processing.
"""

from pathlib import Path
from typing import Any

from final_form.core.models import ProcessingResult
from final_form.domains.questionnaire import QuestionnaireProcessor
from final_form.input.client import FormInputClient
from final_form.registry import MeasureRegistry
from final_form.registry.models import Binding, BindingSection, FormBindingSpec


class MissingItemMapError(Exception):
    """Raised when no item mapping is configured for a form/measure pair."""

    pass


class MissingFormIdError(Exception):
    """Raised when form_id cannot be determined."""

    pass


class UnmappedFieldError(Exception):
    """Raised when a form field has no mapping and strict mode is enabled."""

    pass


def process_form_submission(
    form_submission: dict[str, Any],
    *,
    measure_id: str,
    form_input_client: FormInputClient,
    measure_registry: MeasureRegistry,
    measure_version: str | None = None,
    form_id: str | None = None,
    item_map_override: dict[str, str] | None = None,
    strict: bool = True,
) -> ProcessingResult:
    """Process a canonical form submission for a single measure.

    Takes a canonical form_submission (as defined by canonizer) and processes
    it for the specified measure, using the field_id -> item_id mapping from
    FormInputClient.

    Args:
        form_submission: Canonical form submission dict with shape:
            {
                "form_id": str,
                "submission_id": str,
                "respondent": {"id": str, "display": str},
                "submitted_at": str,  # ISO 8601
                "items": [
                    {
                        "field_id": str,
                        "question_text": str | None,
                        "raw_value": str,
                    },
                    ...
                ],
                "meta": {...}  # optional
            }
        measure_id: The measure to process (e.g., "phq9", "gad7").
        form_input_client: Client for retrieving field_id -> item_id mappings.
        measure_registry: Registry for loading measure specs.
        measure_version: Specific measure version to use (default: latest).
        form_id: Override form_id (default: use form_submission["form_id"]).
        item_map_override: Override the item map entirely (bypasses FormInputClient).
        strict: If True, fail on unmapped fields. If False, skip and warn.

    Returns:
        ProcessingResult with events and diagnostics.

    Raises:
        MissingFormIdError: If form_id cannot be determined.
        MissingItemMapError: If no mapping is configured and no override provided.
        UnmappedFieldError: If strict=True and form contains fields not in item_map.
    """
    # 1. Determine form_id
    resolved_form_id = form_id or form_submission.get("form_id")
    if not resolved_form_id:
        raise MissingFormIdError(
            "form_id not provided and not found in form_submission. "
            "Either pass form_id argument or ensure form_submission contains 'form_id'."
        )

    # 2. Resolve item map
    if item_map_override is not None:
        item_map = item_map_override
    else:
        item_map = form_input_client.get_item_map(resolved_form_id, measure_id)

    if item_map is None:
        raise MissingItemMapError(
            f"No item mapping configured for (form_id={resolved_form_id!r}, measure_id={measure_id!r}). "
            f"Either provide item_map_override or configure a mapping via FormInputClient.save_item_map()."
        )

    # 3. Load measure spec
    if measure_version:
        measure_spec = measure_registry.get(measure_id, measure_version)
    else:
        measure_spec = measure_registry.get_latest(measure_id)

    # 4. Build internal form response from canonical shape
    # Adapt canonical -> final-form internal format
    internal_items = []
    unmapped_fields = []

    for item in form_submission.get("items", []):
        field_id = item.get("field_id")
        if not field_id:
            continue

        item_id = item_map.get(field_id)
        if item_id is None:
            unmapped_fields.append(field_id)
            continue  # Skip unmapped fields (will check strict below)

        internal_items.append({
            "field_key": field_id,
            "answer": item.get("raw_value"),
        })

    # Fail fast in strict mode if there are unmapped fields
    if strict and unmapped_fields:
        raise UnmappedFieldError(
            f"Form contains fields not in item_map for measure {measure_id!r}: {unmapped_fields}. "
            f"Either add these fields to the item_map or set strict=False to skip them."
        )

    # Build internal form response
    internal_form_response = {
        "form_id": resolved_form_id,
        "form_submission_id": form_submission.get("submission_id", "unknown"),
        "subject_id": form_submission.get("respondent", {}).get("id", "unknown"),
        "timestamp": form_submission.get("submitted_at", ""),
        "items": internal_items,
    }

    # 5. Build binding spec for this single measure
    binding_spec = FormBindingSpec(
        type="form_binding_spec",
        form_id=resolved_form_id,
        binding_id=f"_auto_{resolved_form_id}_{measure_id}",
        version="1.0.0",
        sections=[
            BindingSection(
                measure_id=measure_id,
                measure_version=measure_spec.version,
                bindings=[
                    Binding(item_id=item_id, by="field_key", value=field_id)
                    for field_id, item_id in item_map.items()
                ],
            )
        ],
    )

    # 6. Process via questionnaire processor
    processor = QuestionnaireProcessor()
    result = processor.process(
        form_response=internal_form_response,
        binding_spec=binding_spec,
        measures={measure_id: measure_spec},
    )

    # 7. Add unmapped fields to diagnostics if any
    if unmapped_fields and result.diagnostics:
        # Record as warning in diagnostics
        for field_id in unmapped_fields:
            result.diagnostics.warnings.append(
                f"Unmapped field in form submission: {field_id}"
            )

    return result
