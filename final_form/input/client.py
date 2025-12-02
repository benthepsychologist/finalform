"""FormInputClient for managing field_id -> item_id mappings.

This client stores and retrieves mappings that tell final-form which
form fields correspond to which measure items. It's local, deterministic,
and file-based.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FormInputClient:
    """Local helper for resolving form field -> item_id mappings.

    Stores mappings per (form_id, measure_id) pair in a local directory.
    """

    def __init__(self, storage_path: Path | str) -> None:
        """Initialize the client.

        Args:
            storage_path: Directory where mappings are stored.
                          Will be created if it doesn't exist.
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Resolution events log (append-only)
        self._events_path = self.storage_path / "_resolution_events.jsonl"

    def _get_mapping_path(self, form_id: str, measure_id: str) -> Path:
        """Get the path to a mapping file."""
        # Sanitize form_id for filesystem (replace problematic chars)
        safe_form_id = form_id.replace("/", "_").replace(":", "_")
        form_dir = self.storage_path / safe_form_id
        form_dir.mkdir(parents=True, exist_ok=True)
        return form_dir / f"{measure_id}.json"

    def get_item_map(
        self,
        form_id: str,
        measure_id: str,
    ) -> dict[str, str] | None:
        """Return mapping field_id -> item_id for this (form_id, measure_id).

        Args:
            form_id: The form identifier (e.g., "client_intake_v3").
            measure_id: The measure identifier (e.g., "phq9").

        Returns:
            Dict mapping field_id to item_id, or None if not configured.
        """
        path = self._get_mapping_path(form_id, measure_id)
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)

        return data.get("item_map", None)

    def save_item_map(
        self,
        form_id: str,
        measure_id: str,
        item_map: dict[str, str],
    ) -> None:
        """Persist mapping for this (form_id, measure_id).

        Overwrites any existing mapping.

        Args:
            form_id: The form identifier.
            measure_id: The measure identifier.
            item_map: Dict mapping field_id to item_id.
        """
        path = self._get_mapping_path(form_id, measure_id)
        now = datetime.now(timezone.utc).isoformat()

        # Load existing to preserve created_at if it exists
        created_at = now
        if path.exists():
            with open(path) as f:
                existing = json.load(f)
                created_at = existing.get("meta", {}).get("created_at", now)

        data = {
            "form_id": form_id,
            "measure_id": measure_id,
            "item_map": item_map,
            "meta": {
                "created_at": created_at,
                "updated_at": now,
            },
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def list_mappings(self, form_id: str) -> list[str]:
        """List all measure_ids with mappings for a form.

        Args:
            form_id: The form identifier.

        Returns:
            List of measure_ids that have mappings configured.
        """
        safe_form_id = form_id.replace("/", "_").replace(":", "_")
        form_dir = self.storage_path / safe_form_id
        if not form_dir.exists():
            return []

        return [f.stem for f in form_dir.glob("*.json") if not f.name.startswith("_")]

    def delete_item_map(
        self,
        form_id: str,
        measure_id: str,
    ) -> bool:
        """Delete a mapping.

        Args:
            form_id: The form identifier.
            measure_id: The measure identifier.

        Returns:
            True if deleted, False if it didn't exist.
        """
        path = self._get_mapping_path(form_id, measure_id)
        if path.exists():
            path.unlink()
            return True
        return False

    def record_resolution_event(
        self,
        form_id: str,
        measure_id: str,
        field_id: str,
        candidate_item_id: str,
        accepted: bool,
        reason: str | None = None,
    ) -> None:
        """Record a resolution event for future analysis.

        Append-only log to support future fuzzy helpers and analytics.

        Args:
            form_id: The form identifier.
            measure_id: The measure identifier.
            field_id: The form field being resolved.
            candidate_item_id: The proposed item_id.
            accepted: Whether the resolution was accepted.
            reason: Optional reason for the decision.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "form_id": form_id,
            "measure_id": measure_id,
            "field_id": field_id,
            "candidate_item_id": candidate_item_id,
            "accepted": accepted,
            "reason": reason,
        }

        with open(self._events_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def get_resolution_events(
        self,
        form_id: str | None = None,
        measure_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve resolution events, optionally filtered.

        Args:
            form_id: Filter by form_id (optional).
            measure_id: Filter by measure_id (optional).

        Returns:
            List of resolution event dicts.
        """
        if not self._events_path.exists():
            return []

        events = []
        with open(self._events_path) as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if form_id and event.get("form_id") != form_id:
                        continue
                    if measure_id and event.get("measure_id") != measure_id:
                        continue
                    events.append(event)

        return events
