#!/usr/bin/env python3
"""Convert assessment_registry.json to measure_spec format.

Reads the legacy assessment registry and converts each measure
to the final-form measure_spec schema format.
"""

import json
from pathlib import Path


def convert_measure(measure_id: str, measure_data: dict) -> dict:
    """Convert a single measure to measure_spec format."""

    # Build items
    items = []
    anchors = measure_data.get("anchors", {})
    anchor_labels = anchors.get("labels", {})

    # Create response_map from anchor labels
    # Normalize: lowercase keys, integer values
    response_map = {}
    for value_str, label in anchor_labels.items():
        # Handle numeric or float keys
        try:
            value = int(float(value_str))
        except ValueError:
            value = int(value_str)
        response_map[label.lower()] = value

    for i, item_text in enumerate(measure_data.get("items", []), start=1):
        item_id = f"{measure_id}_item{i}"
        items.append({
            "item_id": item_id,
            "position": i,
            "text": item_text,
            "response_map": response_map.copy(),
            "aliases": {}
        })

    # Build scales
    scales = []
    scores_data = measure_data.get("scores", {})

    for scale_id, scale_data in scores_data.items():
        included_items = scale_data.get("included_items", [])
        reversed_items = scale_data.get("reversed_items", [])
        scoring = scale_data.get("scoring", {})
        ranges = scale_data.get("ranges", [])

        # Convert item numbers to item_ids
        scale_items = [f"{measure_id}_item{i}" for i in included_items]
        scale_reversed = [f"{measure_id}_item{i}" for i in reversed_items]

        # Determine method
        method = scoring.get("method", "sum")

        # Build interpretations from ranges
        # Map severity strings to integers
        severity_map = {
            "minimal": 0,
            "mild": 1,
            "moderate": 2,
            "moderately_severe": 3,
            "severe": 4,
            "low": 1,
            "high": 3,
        }

        interpretations = []
        for i, r in enumerate(ranges):
            sev_str = r.get("severity", "")
            sev_int = severity_map.get(sev_str, i)  # Default to index if unknown

            interp = {
                "min": r["min"],
                "max": r["max"],
                "label": r["label"],
            }
            if sev_int is not None:
                interp["severity"] = sev_int
            if r.get("description"):
                interp["description"] = r["description"]

            interpretations.append(interp)

        # Determine missing_allowed (default to 1 for longer scales, 0 for short)
        num_items = len(included_items)
        missing_allowed = 1 if num_items >= 5 else 0

        scales.append({
            "scale_id": scale_id,
            "name": scale_data.get("name", scale_id.replace("_", " ").title()),
            "items": scale_items,
            "method": method,
            "reversed_items": scale_reversed,
            "min": scoring.get("min", 0),
            "max": scoring.get("max"),
            "missing_allowed": missing_allowed,
            "interpretations": interpretations
        })

    # Determine kind based on measure characteristics
    kind = "questionnaire"  # Default

    return {
        "type": "measure_spec",
        "measure_id": measure_id,
        "version": "1.0.0",
        "name": measure_data.get("name", measure_id),
        "kind": kind,
        "locale": "en-US",
        "aliases": [],
        "description": measure_data.get("description", ""),
        "items": items,
        "scales": scales
    }


def main():
    # Load source registry
    source_path = Path("/workspace/tools/assessment/config/assessment_registry.json")
    with open(source_path) as f:
        registry = json.load(f)

    measures = registry.get("measures", {})

    # Output directory
    output_dir = Path("/workspace/final-form/measure-registry/measures")

    # Skip measures we already have or that have incomplete data
    skip_measures = {"phq_9", "gad_7", "dts", "cfs"}  # phq_9/gad_7 exist, dts/cfs have incomplete format

    converted = []

    for measure_id, measure_data in measures.items():
        if measure_id in skip_measures:
            print(f"Skipping {measure_id} (already exists or incomplete)")
            continue

        # Skip measures with non-standard format
        if "items" not in measure_data or not isinstance(measure_data["items"], list):
            print(f"Skipping {measure_id} (non-standard format)")
            continue

        print(f"Converting {measure_id}...")

        try:
            spec = convert_measure(measure_id, measure_data)

            # Create output directory
            measure_dir = output_dir / measure_id
            measure_dir.mkdir(parents=True, exist_ok=True)

            # Write spec
            output_path = measure_dir / "1-0-0.json"
            with open(output_path, "w") as f:
                json.dump(spec, f, indent=2)

            converted.append(measure_id)
            print(f"  -> {output_path}")

        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nConverted {len(converted)} measures:")
    for m in converted:
        print(f"  - {m}")


if __name__ == "__main__":
    main()
