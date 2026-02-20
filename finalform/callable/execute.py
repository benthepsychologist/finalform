"""Execute interface for the finalform callable protocol.

Provides the in-proc execute() function that lorchestra calls directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finalform.callable.result import CallableResult
from finalform.config import get_binding_registry_path, get_measure_registry_path
from finalform.pipeline import Pipeline, PipelineConfig


def execute(params: dict[str, Any]) -> dict[str, Any]:
    """Score/transform canonical items into measurement rows.

    This is the primary interface for lorchestra to call finalform directly
    (no JSON-RPC wrapper). It processes form responses and returns a
    CallableResult dict with measurement items.

    Args:
        params: Dictionary containing:
            - instrument: str - The instrument/measure ID (e.g., "phq9")
            - items: list[dict] - Canonical items to score/transform, formatted
              as a form response (e.g., {"form_id": "...", "items": {...}})
            - config: dict - Optional configuration overrides:
                - binding_id: str - Binding ID to use (defaults to instrument)
                - binding_version: str - Specific version (optional)
                - measure_registry_path: str - Override measure registry path
                - binding_registry_path: str - Override binding registry path
                - deterministic_ids: bool - Use deterministic IDs for testing

    Returns:
        CallableResult dict with:
            - schema_version: "1.0"
            - items: list[dict] - Measurement rows (MeasurementEvents serialized)
            - stats: dict - Processing statistics

    Raises:
        ValueError: If required parameters are missing or invalid.
        KeyError: If instrument/binding not found in registry.
        Exception: Any processing errors (lorchestra classifies as Transient/Permanent).
    """
    # Extract parameters
    instrument = params.get("instrument")
    if not instrument:
        raise ValueError("'instrument' is required in params")

    items = params.get("items")
    if items is None:
        raise ValueError("'items' is required in params")

    config = params.get("config", {})

    # Resolve registry paths
    measure_registry_path = Path(
        config.get("measure_registry_path", get_measure_registry_path())
    )
    binding_registry_path = Path(
        config.get("binding_registry_path", get_binding_registry_path())
    )

    # Resolve binding ID (defaults to instrument if not specified)
    binding_id = config.get("binding_id", instrument)
    binding_version = config.get("binding_version")
    deterministic_ids = config.get("deterministic_ids", False)

    # Build pipeline config
    pipeline_config = PipelineConfig(
        measure_registry_path=measure_registry_path,
        binding_registry_path=binding_registry_path,
        binding_id=binding_id,
        binding_version=binding_version,
        deterministic_ids=deterministic_ids,
    )

    # Create pipeline and process
    pipeline = Pipeline(pipeline_config)

    # items can be a single form response or list of form responses
    # Handle empty items gracefully - nothing to score
    if isinstance(items, list) and len(items) == 0:
        results = []
    elif isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
        # Check if it's a list of form responses or a single form response dict
        # A form response typically has 'form_id' or 'items' keys
        if "form_id" in items[0] or "items" in items[0]:
            # List of form responses - process as batch
            results = pipeline.process_batch(items)
        else:
            # Single form response passed as items=dict
            results = [pipeline.process(items[0])]
    elif isinstance(items, dict):
        # Single form response
        results = [pipeline.process(items)]
    else:
        raise ValueError("'items' must be a form response dict or list of form responses")

    # Convert ProcessingResults to measurement items
    measurement_items: list[dict[str, Any]] = []
    input_count = len(results)
    output_count = 0
    skipped_count = 0
    error_count = 0

    for result in results:
        if result.success:
            for event in result.events:
                # Serialize MeasurementEvent to dict
                measurement_items.append(event.model_dump(by_alias=True))
                output_count += 1
        else:
            error_count += 1

    # Build stats
    stats = {
        "input": input_count,
        "output": output_count,
        "skipped": skipped_count,
        "errors": error_count,
    }

    # Build and return CallableResult
    # v0: always return items inline (items_ref deferred until artifact store)
    result = CallableResult(
        schema_version="1.0",
        items=measurement_items,
        stats=stats,
    )

    return result.to_dict()
