"""Tests for form input handling (FormInputClient and process_form_submission)."""

import json
from pathlib import Path

import pytest

from final_form.input import (
    FormInputClient,
    MissingFormIdError,
    MissingItemMapError,
    UnmappedFieldError,
    process_form_submission,
)
from final_form.registry import MeasureRegistry


@pytest.fixture
def temp_storage(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage = tmp_path / "form-mappings"
    storage.mkdir()
    return storage


@pytest.fixture
def form_input_client(temp_storage: Path) -> FormInputClient:
    """Create a FormInputClient with temp storage."""
    return FormInputClient(temp_storage)


@pytest.fixture
def measure_registry(project_root: Path) -> MeasureRegistry:
    """Create measure registry."""
    return MeasureRegistry(
        project_root / "measure-registry",
        schema_path=project_root / "schemas" / "measure_spec.schema.json",
    )


class TestFormInputClient:
    """Tests for FormInputClient."""

    def test_save_and_get_item_map(self, form_input_client: FormInputClient) -> None:
        """Test saving and retrieving an item map."""
        item_map = {
            "entry.111111": "phq9_item1",
            "entry.222222": "phq9_item2",
        }

        form_input_client.save_item_map("intake_v1", "phq9", item_map)
        retrieved = form_input_client.get_item_map("intake_v1", "phq9")

        assert retrieved == item_map

    def test_get_nonexistent_returns_none(self, form_input_client: FormInputClient) -> None:
        """Test that getting a nonexistent mapping returns None."""
        result = form_input_client.get_item_map("nonexistent_form", "phq9")
        assert result is None

    def test_save_overwrites_existing(self, form_input_client: FormInputClient) -> None:
        """Test that saving overwrites existing mapping."""
        form_input_client.save_item_map("intake_v1", "phq9", {"a": "b"})
        form_input_client.save_item_map("intake_v1", "phq9", {"c": "d"})

        retrieved = form_input_client.get_item_map("intake_v1", "phq9")
        assert retrieved == {"c": "d"}

    def test_list_mappings(self, form_input_client: FormInputClient) -> None:
        """Test listing mappings for a form."""
        form_input_client.save_item_map("intake_v1", "phq9", {"a": "b"})
        form_input_client.save_item_map("intake_v1", "gad7", {"c": "d"})

        mappings = form_input_client.list_mappings("intake_v1")
        assert set(mappings) == {"phq9", "gad7"}

    def test_list_mappings_empty(self, form_input_client: FormInputClient) -> None:
        """Test listing mappings for a form with none."""
        mappings = form_input_client.list_mappings("nonexistent")
        assert mappings == []

    def test_delete_item_map(self, form_input_client: FormInputClient) -> None:
        """Test deleting a mapping."""
        form_input_client.save_item_map("intake_v1", "phq9", {"a": "b"})
        assert form_input_client.delete_item_map("intake_v1", "phq9") is True
        assert form_input_client.get_item_map("intake_v1", "phq9") is None

    def test_delete_nonexistent_returns_false(self, form_input_client: FormInputClient) -> None:
        """Test deleting a nonexistent mapping returns False."""
        assert form_input_client.delete_item_map("nonexistent", "phq9") is False

    def test_sanitizes_form_id(self, form_input_client: FormInputClient) -> None:
        """Test that form_id with special chars is sanitized."""
        form_input_client.save_item_map("google/forms:123", "phq9", {"a": "b"})
        retrieved = form_input_client.get_item_map("google/forms:123", "phq9")
        assert retrieved == {"a": "b"}

    def test_record_resolution_event(self, form_input_client: FormInputClient) -> None:
        """Test recording resolution events."""
        form_input_client.record_resolution_event(
            form_id="intake_v1",
            measure_id="phq9",
            field_id="entry.111",
            candidate_item_id="phq9_item1",
            accepted=True,
            reason="exact match",
        )

        events = form_input_client.get_resolution_events()
        assert len(events) == 1
        assert events[0]["form_id"] == "intake_v1"
        assert events[0]["accepted"] is True

    def test_get_resolution_events_filtered(self, form_input_client: FormInputClient) -> None:
        """Test filtering resolution events."""
        form_input_client.record_resolution_event("form1", "phq9", "f1", "i1", True)
        form_input_client.record_resolution_event("form2", "gad7", "f2", "i2", False)

        phq9_events = form_input_client.get_resolution_events(measure_id="phq9")
        assert len(phq9_events) == 1
        assert phq9_events[0]["measure_id"] == "phq9"


class TestProcessFormSubmission:
    """Tests for process_form_submission."""

    @pytest.fixture
    def canonical_submission(self) -> dict:
        """Create a canonical form submission."""
        return {
            "form_id": "client_intake_v3",
            "submission_id": "subm_123",
            "respondent": {"id": "contact-uuid", "display": "Jane Doe"},
            "submitted_at": "2025-12-01T12:34:56Z",
            "items": [
                {
                    "field_id": "entry.111111",
                    "question_text": "Little interest or pleasure in doing things",
                    "raw_value": "more than half the days",
                },
                {
                    "field_id": "entry.222222",
                    "question_text": "Feeling down, depressed, or hopeless",
                    "raw_value": "nearly every day",
                },
                {
                    "field_id": "entry.333333",
                    "question_text": "Trouble falling or staying asleep",
                    "raw_value": "several days",
                },
                {
                    "field_id": "entry.444444",
                    "question_text": "Feeling tired or having little energy",
                    "raw_value": "several days",
                },
                {
                    "field_id": "entry.555555",
                    "question_text": "Poor appetite or overeating",
                    "raw_value": "not at all",
                },
                {
                    "field_id": "entry.666666",
                    "question_text": "Feeling bad about yourself",
                    "raw_value": "not at all",
                },
                {
                    "field_id": "entry.777777",
                    "question_text": "Trouble concentrating",
                    "raw_value": "several days",
                },
                {
                    "field_id": "entry.888888",
                    "question_text": "Moving or speaking slowly",
                    "raw_value": "not at all",
                },
                {
                    "field_id": "entry.999999",
                    "question_text": "Thoughts of self-harm",
                    "raw_value": "not at all",
                },
                {
                    "field_id": "entry.101010",
                    "question_text": "How difficult have these problems made things",
                    "raw_value": "somewhat difficult",
                },
            ],
            "meta": {"source_system": "google_forms"},
        }

    @pytest.fixture
    def phq9_item_map(self) -> dict[str, str]:
        """Create PHQ-9 item map."""
        return {
            "entry.111111": "phq9_item1",
            "entry.222222": "phq9_item2",
            "entry.333333": "phq9_item3",
            "entry.444444": "phq9_item4",
            "entry.555555": "phq9_item5",
            "entry.666666": "phq9_item6",
            "entry.777777": "phq9_item7",
            "entry.888888": "phq9_item8",
            "entry.999999": "phq9_item9",
            "entry.101010": "phq9_item10",
        }

    def test_process_with_item_map_override(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test processing with explicit item_map_override."""
        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            item_map_override=phq9_item_map,
        )

        assert result.success is True
        assert len(result.events) == 1

        event = result.events[0]
        assert event.measure_id == "phq9"

        # Find the scale observation
        scale_obs = [o for o in event.observations if o.kind == "scale" and o.code == "phq9_total"]
        assert len(scale_obs) == 1
        # 2 + 3 + 1 + 1 + 0 + 0 + 1 + 0 + 0 = 8 (Mild)
        assert scale_obs[0].value == 8.0
        assert scale_obs[0].label == "Mild"

    def test_process_with_saved_mapping(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test processing using a saved mapping from FormInputClient."""
        # Save the mapping
        form_input_client.save_item_map("client_intake_v3", "phq9", phq9_item_map)

        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
        )

        assert result.success is True
        assert len(result.events) == 1

    def test_missing_item_map_raises(
        self,
        canonical_submission: dict,
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that missing item map raises MissingItemMapError."""
        with pytest.raises(MissingItemMapError) as exc_info:
            process_form_submission(
                canonical_submission,
                measure_id="phq9",
                form_input_client=form_input_client,
                measure_registry=measure_registry,
            )

        assert "client_intake_v3" in str(exc_info.value)
        assert "phq9" in str(exc_info.value)

    def test_missing_form_id_raises(
        self,
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that missing form_id raises MissingFormIdError."""
        submission_without_form_id = {
            "submission_id": "subm_123",
            "items": [],
        }

        with pytest.raises(MissingFormIdError):
            process_form_submission(
                submission_without_form_id,
                measure_id="phq9",
                form_input_client=form_input_client,
                measure_registry=measure_registry,
            )

    def test_form_id_override(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that form_id argument overrides submission form_id."""
        # Save mapping under different form_id
        form_input_client.save_item_map("override_form", "phq9", phq9_item_map)

        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            form_id="override_form",  # Override
        )

        assert result.success is True

    def test_measure_version_selection(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test explicit measure version selection."""
        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            measure_version="1.0.0",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            item_map_override=phq9_item_map,
        )

        assert result.success is True
        assert result.events[0].measure_version == "1.0.0"

    def test_respondent_propagated(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that respondent info is propagated to output."""
        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            item_map_override=phq9_item_map,
        )

        assert result.events[0].subject_id == "contact-uuid"

    def test_submission_id_propagated(
        self,
        canonical_submission: dict,
        phq9_item_map: dict[str, str],
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that submission_id is propagated."""
        result = process_form_submission(
            canonical_submission,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            item_map_override=phq9_item_map,
        )

        assert result.form_submission_id == "subm_123"

    def test_unmapped_field_strict_raises(
        self,
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that unmapped fields raise UnmappedFieldError in strict mode.

        This test locks in the fail-fast behavior: if a form contains fields
        that aren't in the item_map and strict=True, we must raise an error.
        """
        # Save a partial mapping (missing some fields)
        form_input_client.save_item_map(
            "client_intake_v3",
            "phq9",
            {"entry.111111": "phq9_item1"},  # Only one field mapped
        )

        canonical = {
            "form_id": "client_intake_v3",
            "submission_id": "subm_123",
            "respondent": {"id": "contact-uuid"},
            "submitted_at": "2025-12-01T12:34:56Z",
            "items": [
                {"field_id": "entry.111111", "raw_value": "more than half the days"},
                {"field_id": "entry.999999", "raw_value": "noise"},  # Unmapped field
            ],
        }

        with pytest.raises(UnmappedFieldError) as exc_info:
            process_form_submission(
                canonical,
                measure_id="phq9",
                form_input_client=form_input_client,
                measure_registry=measure_registry,
                strict=True,
            )

        # Verify error message contains the unmapped field
        assert "entry.999999" in str(exc_info.value)

    def test_unmapped_field_non_strict_skips(
        self,
        form_input_client: FormInputClient,
        measure_registry: MeasureRegistry,
    ) -> None:
        """Test that unmapped fields are skipped (not raised) when strict=False."""
        # Save a complete mapping for the PHQ-9 items we care about
        form_input_client.save_item_map(
            "client_intake_v3",
            "phq9",
            {
                "entry.111111": "phq9_item1",
                "entry.222222": "phq9_item2",
                "entry.333333": "phq9_item3",
                "entry.444444": "phq9_item4",
                "entry.555555": "phq9_item5",
                "entry.666666": "phq9_item6",
                "entry.777777": "phq9_item7",
                "entry.888888": "phq9_item8",
                "entry.999999": "phq9_item9",
                "entry.101010": "phq9_item10",
            },
        )

        canonical = {
            "form_id": "client_intake_v3",
            "submission_id": "subm_123",
            "respondent": {"id": "contact-uuid"},
            "submitted_at": "2025-12-01T12:34:56Z",
            "items": [
                {"field_id": "entry.111111", "raw_value": "not at all"},
                {"field_id": "entry.222222", "raw_value": "not at all"},
                {"field_id": "entry.333333", "raw_value": "not at all"},
                {"field_id": "entry.444444", "raw_value": "not at all"},
                {"field_id": "entry.555555", "raw_value": "not at all"},
                {"field_id": "entry.666666", "raw_value": "not at all"},
                {"field_id": "entry.777777", "raw_value": "not at all"},
                {"field_id": "entry.888888", "raw_value": "not at all"},
                {"field_id": "entry.999999", "raw_value": "not at all"},
                {"field_id": "entry.101010", "raw_value": "not difficult at all"},
                {"field_id": "entry.EXTRA", "raw_value": "extra noise"},  # Unmapped
            ],
        }

        # Should NOT raise with strict=False
        result = process_form_submission(
            canonical,
            measure_id="phq9",
            form_input_client=form_input_client,
            measure_registry=measure_registry,
            strict=False,
        )

        assert result.success is True
        # Unmapped field should be noted in warnings
        assert any("entry.EXTRA" in w for w in result.diagnostics.warnings)
