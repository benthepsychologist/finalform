"""Pydantic models for measure and binding specifications."""

from typing import Literal

from pydantic import BaseModel, Field


class Interpretation(BaseModel):
    """Score interpretation band."""

    min: int
    max: int
    label: str
    severity: int | None = None
    description: str | None = None


class MeasureScale(BaseModel):
    """Scale definition within a measure."""

    scale_id: str
    name: str
    items: list[str]
    method: Literal["sum", "average", "sum_then_double"]
    reversed_items: list[str] = Field(default_factory=list)
    min: int | None = None
    max: int | None = None
    missing_allowed: int = 0
    missing_strategy: Literal["fail", "skip", "prorate"] = "fail"
    interpretations: list[Interpretation]


class MeasureItem(BaseModel):
    """Item (question) definition within a measure."""

    item_id: str
    position: int
    text: str
    response_map: dict[str, int]
    aliases: dict[str, str] = Field(default_factory=dict)


class MeasureSpec(BaseModel):
    """Complete measure specification."""

    type: Literal["measure_spec"]
    measure_id: str
    version: str
    name: str
    kind: Literal["questionnaire", "scale", "inventory", "checklist", "lab_panel", "vital", "wearable"]
    locale: str | None = None
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    items: list[MeasureItem]
    scales: list[MeasureScale]

    def get_item(self, item_id: str) -> MeasureItem | None:
        """Get an item by its ID."""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def get_scale(self, scale_id: str) -> MeasureScale | None:
        """Get a scale by its ID."""
        for scale in self.scales:
            if scale.scale_id == scale_id:
                return scale
        return None


class Binding(BaseModel):
    """Single item binding mapping form field to measure item."""

    item_id: str
    by: Literal["field_key", "position"]
    value: str | int


class BindingSection(BaseModel):
    """Section of bindings for a single measure."""

    name: str | None = None
    measure_id: str
    measure_version: str
    bindings: list[Binding]


class FormBindingSpec(BaseModel):
    """Complete form binding specification."""

    type: Literal["form_binding_spec"]
    form_id: str
    binding_id: str
    version: str
    description: str | None = None
    sections: list[BindingSection]

    def get_section_for_measure(self, measure_id: str) -> BindingSection | None:
        """Get the binding section for a specific measure."""
        for section in self.sections:
            if section.measure_id == measure_id:
                return section
        return None
