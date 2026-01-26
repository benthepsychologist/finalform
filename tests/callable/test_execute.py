"""Tests for the execute() interface."""

from pathlib import Path

import pytest

from finalform import execute
from finalform.callable import CallableResult


@pytest.fixture
def form_response_phq9_gad7() -> dict:
    """A complete form response with both PHQ-9 and GAD-7."""
    items = []

    # PHQ-9 answers (10 items) - binding uses entry.123456001 through entry.123456010
    phq9_answers = ["not at all"] * 9 + ["not difficult at all"]
    for i, answer in enumerate(phq9_answers, 1):
        items.append({
            "field_key": f"entry.123456{i:03d}",
            "position": i,
            "answer": answer,
        })

    # GAD-7 answers (8 items) - binding uses entry.789012001 through entry.789012008
    gad7_answers = ["not at all"] * 7 + ["not difficult at all"]
    for i, answer in enumerate(gad7_answers, 1):
        items.append({
            "field_key": f"entry.789012{i:03d}",
            "position": 10 + i,
            "answer": answer,
        })

    return {
        "form_id": "googleforms::test_form",
        "form_submission_id": "sub_test_execute",
        "subject_id": "contact::test123",
        "timestamp": "2025-01-15T10:30:00Z",
        "items": items,
    }


class TestExecuteInterface:
    """Tests for execute() function interface."""

    def test_execute_returns_dict(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute returns a dict."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
                "deterministic_ids": True,
            },
        })

        assert isinstance(result, dict)

    def test_execute_returns_schema_version(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute result includes schema_version."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        assert result["schema_version"] == "1.0"

    def test_execute_returns_items_not_items_ref(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that v0 returns items, not items_ref."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        assert "items" in result
        assert "items_ref" not in result
        assert isinstance(result["items"], list)

    def test_execute_returns_measurement_events(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute returns MeasurementEvent dicts."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        items = result["items"]
        assert len(items) == 2  # PHQ-9 and GAD-7

        # Check structure of first event
        event = items[0]
        assert "schema" in event
        assert event["schema"] == "com.lifeos.measurement_event.v1"
        assert "measurement_event_id" in event
        assert "measure_id" in event
        assert "observations" in event

    def test_execute_returns_stats(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute returns processing stats."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        assert "stats" in result
        stats = result["stats"]
        assert "input" in stats
        assert "output" in stats
        assert "skipped" in stats
        assert "errors" in stats

    def test_execute_stats_values(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute stats have correct values."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        stats = result["stats"]
        assert stats["input"] == 1  # One form response processed
        assert stats["output"] == 2  # Two measurement events (PHQ-9 + GAD-7)
        assert stats["skipped"] == 0
        assert stats["errors"] == 0

    def test_execute_result_validates_as_callable_result(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
        form_response_phq9_gad7: dict,
    ) -> None:
        """Test that execute result can be validated as CallableResult."""
        result = execute({
            "instrument": "example_intake",
            "items": form_response_phq9_gad7,
            "config": {
                "measure_registry_path": str(measure_registry_path),
                "binding_registry_path": str(binding_registry_path),
                "binding_id": "example_intake",
                "binding_version": "1.0.0",
            },
        })

        # Should be able to create CallableResult from the dict
        validated = CallableResult(**result)
        assert validated.schema_version == "1.0"
        assert validated.items is not None
        assert validated.items_ref is None


class TestExecuteErrors:
    """Tests for execute() error handling."""

    def test_execute_missing_instrument_raises(self) -> None:
        """Test that missing instrument raises ValueError."""
        with pytest.raises(ValueError, match="'instrument' is required"):
            execute({"items": []})

    def test_execute_missing_items_raises(self) -> None:
        """Test that missing items raises ValueError."""
        with pytest.raises(ValueError, match="'items' is required"):
            execute({"instrument": "phq9"})

    def test_execute_invalid_binding_raises(
        self,
        measure_registry_path: Path,
        binding_registry_path: Path,
    ) -> None:
        """Test that invalid binding_id raises exception."""
        with pytest.raises(Exception):  # FileNotFoundError or similar
            execute({
                "instrument": "nonexistent_instrument",
                "items": {"form_id": "test", "items": []},
                "config": {
                    "measure_registry_path": str(measure_registry_path),
                    "binding_registry_path": str(binding_registry_path),
                    "binding_id": "nonexistent_binding",
                },
            })


class TestExecuteImport:
    """Tests for execute() import from top-level package."""

    def test_import_from_callable(self) -> None:
        """Test importing from finalform.callable."""
        from finalform.callable import execute as exec_fn

        assert exec_fn is not None
        assert callable(exec_fn)

    def test_import_from_top_level(self) -> None:
        """Test importing from finalform."""
        from finalform import execute as exec_fn

        assert exec_fn is not None
        assert callable(exec_fn)
