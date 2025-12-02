"""Measure registry for loading and caching measure specifications."""

import json
from pathlib import Path

import jsonschema

from final_form.registry.models import MeasureSpec


class MeasureNotFoundError(Exception):
    """Raised when a measure specification is not found."""

    pass


class MeasureValidationError(Exception):
    """Raised when a measure specification fails validation."""

    pass


class MeasureRegistry:
    """Registry for loading and caching measure specifications.

    Loads measure specs from a directory structure:
        <registry_path>/measures/<measure_id>/<version>.json

    Where version uses dashes instead of dots (e.g., 1-0-0.json for 1.0.0).
    """

    def __init__(
        self,
        registry_path: Path | str,
        schema_path: Path | str | None = None,
    ) -> None:
        """Initialize the measure registry.

        Args:
            registry_path: Path to the measure registry directory.
            schema_path: Optional path to the measure_spec schema for validation.
        """
        self.registry_path = Path(registry_path)
        self.measures_path = self.registry_path / "measures"
        self._cache: dict[tuple[str, str], MeasureSpec] = {}
        self._schema: dict | None = None

        if schema_path:
            with open(schema_path) as f:
                self._schema = json.load(f)

    def _version_to_filename(self, version: str) -> str:
        """Convert version string to filename (1.0.0 -> 1-0-0.json)."""
        return version.replace(".", "-") + ".json"

    def _get_spec_path(self, measure_id: str, version: str) -> Path:
        """Get the path to a measure spec file."""
        filename = self._version_to_filename(version)
        return self.measures_path / measure_id / filename

    def get(self, measure_id: str, version: str) -> MeasureSpec:
        """Get a measure specification by ID and version.

        Args:
            measure_id: The measure identifier (e.g., 'phq9').
            version: The version string (e.g., '1.0.0').

        Returns:
            The loaded MeasureSpec.

        Raises:
            MeasureNotFoundError: If the measure spec file doesn't exist.
            MeasureValidationError: If the spec fails schema validation.
        """
        cache_key = (measure_id, version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        spec_path = self._get_spec_path(measure_id, version)
        if not spec_path.exists():
            raise MeasureNotFoundError(
                f"Measure spec not found: {measure_id}@{version} "
                f"(expected at {spec_path})"
            )

        with open(spec_path) as f:
            data = json.load(f)

        # Validate against schema if available
        if self._schema:
            try:
                jsonschema.validate(data, self._schema)
            except jsonschema.ValidationError as e:
                raise MeasureValidationError(
                    f"Measure spec validation failed for {measure_id}@{version}: {e.message}"
                ) from e

        spec = MeasureSpec.model_validate(data)
        self._cache[cache_key] = spec
        return spec

    def list_measures(self) -> list[str]:
        """List all available measure IDs."""
        if not self.measures_path.exists():
            return []
        return [d.name for d in self.measures_path.iterdir() if d.is_dir()]

    def list_versions(self, measure_id: str) -> list[str]:
        """List all available versions for a measure."""
        measure_path = self.measures_path / measure_id
        if not measure_path.exists():
            return []
        versions = []
        for f in measure_path.glob("*.json"):
            # Convert filename back to version (1-0-0.json -> 1.0.0)
            version = f.stem.replace("-", ".")
            versions.append(version)
        return sorted(versions)

    def get_latest(self, measure_id: str) -> MeasureSpec:
        """Get the latest version of a measure.

        Args:
            measure_id: The measure identifier.

        Returns:
            The latest MeasureSpec.

        Raises:
            MeasureNotFoundError: If no versions exist.
        """
        versions = self.list_versions(measure_id)
        if not versions:
            raise MeasureNotFoundError(f"No versions found for measure: {measure_id}")
        # Simple string sort works for semver if all have same number of digits
        latest = versions[-1]
        return self.get(measure_id, latest)
