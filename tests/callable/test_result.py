"""Tests for the CallableResult model."""

import pytest

from finalform.callable import CallableResult


class TestCallableResult:
    """Tests for CallableResult model."""

    def test_create_with_items(self) -> None:
        """Test creating CallableResult with items."""
        result = CallableResult(items=[{"key": "value"}])

        assert result.schema_version == "1.0"
        assert result.items == [{"key": "value"}]
        assert result.items_ref is None
        assert result.stats == {}

    def test_create_with_empty_items(self) -> None:
        """Test creating CallableResult with empty items list."""
        result = CallableResult(items=[])

        assert result.items == []
        assert result.items_ref is None

    def test_create_with_items_ref(self) -> None:
        """Test creating CallableResult with items_ref."""
        result = CallableResult(items_ref="artifact://bucket/key")

        assert result.items is None
        assert result.items_ref == "artifact://bucket/key"

    def test_create_with_stats(self) -> None:
        """Test creating CallableResult with stats."""
        stats = {"input": 10, "output": 10, "skipped": 0, "errors": 0}
        result = CallableResult(items=[], stats=stats)

        assert result.stats == stats

    def test_schema_version_default(self) -> None:
        """Test that schema_version defaults to 1.0."""
        result = CallableResult(items=[])

        assert result.schema_version == "1.0"

    def test_schema_version_custom(self) -> None:
        """Test custom schema_version."""
        result = CallableResult(schema_version="2.0", items=[])

        assert result.schema_version == "2.0"

    def test_xor_constraint_both_set_raises(self) -> None:
        """Test that setting both items and items_ref raises ValueError."""
        with pytest.raises(ValueError, match="Cannot set both"):
            CallableResult(items=[], items_ref="artifact://bucket/key")

    def test_xor_constraint_neither_set_raises(self) -> None:
        """Test that setting neither items nor items_ref raises ValueError."""
        with pytest.raises(ValueError, match="Must set exactly one"):
            CallableResult()

    def test_xor_constraint_items_none_items_ref_none_raises(self) -> None:
        """Test explicit None values still enforce XOR."""
        with pytest.raises(ValueError, match="Must set exactly one"):
            CallableResult(items=None, items_ref=None)

    def test_to_dict_with_items(self) -> None:
        """Test to_dict excludes None values."""
        result = CallableResult(
            items=[{"a": 1}],
            stats={"input": 1, "output": 1},
        )
        d = result.to_dict()

        assert d == {
            "schema_version": "1.0",
            "items": [{"a": 1}],
            "stats": {"input": 1, "output": 1},
        }
        assert "items_ref" not in d

    def test_to_dict_with_items_ref(self) -> None:
        """Test to_dict with items_ref."""
        result = CallableResult(items_ref="artifact://foo")
        d = result.to_dict()

        assert d == {
            "schema_version": "1.0",
            "items_ref": "artifact://foo",
        }
        assert "items" not in d

    def test_to_dict_empty_stats_excluded(self) -> None:
        """Test to_dict excludes empty stats."""
        result = CallableResult(items=[])
        d = result.to_dict()

        assert "stats" not in d

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            CallableResult(items=[], unknown_field="value")


class TestCallableResultImport:
    """Tests for CallableResult import from top-level package."""

    def test_import_from_callable(self) -> None:
        """Test importing from finalform.callable."""
        from finalform.callable import CallableResult as CR

        assert CR is not None
        result = CR(items=[])
        assert result.schema_version == "1.0"

    def test_import_from_top_level(self) -> None:
        """Test importing from finalform."""
        from finalform import CallableResult as CR

        assert CR is not None
        result = CR(items=[])
        assert result.schema_version == "1.0"
