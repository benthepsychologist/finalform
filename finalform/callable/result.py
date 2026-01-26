"""CallableResult model for the finalform callable protocol."""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class CallableResult(BaseModel):
    """Result returned by the finalform execute() interface.

    Represents the output of a scoring/transformation operation.
    Exactly one of `items` or `items_ref` must be set (XOR constraint).

    Attributes:
        schema_version: Version of the CallableResult schema.
        items: List of measurement items (inline payload).
        items_ref: Reference to artifact store (reserved for future use).
        stats: Processing statistics.
    """

    schema_version: str = "1.0"
    items: list[dict] | None = None
    items_ref: str | None = None
    stats: dict = {}

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_items_xor_items_ref(self) -> CallableResult:
        """Ensure exactly one of items or items_ref is set."""
        has_items = self.items is not None
        has_items_ref = self.items_ref is not None

        if has_items and has_items_ref:
            raise ValueError("Cannot set both 'items' and 'items_ref'; use exactly one")
        if not has_items and not has_items_ref:
            raise ValueError("Must set exactly one of 'items' or 'items_ref'")

        return self

    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        result: dict = {"schema_version": self.schema_version}
        if self.items is not None:
            result["items"] = self.items
        if self.items_ref is not None:
            result["items_ref"] = self.items_ref
        if self.stats:
            result["stats"] = self.stats
        return result
