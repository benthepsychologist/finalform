"""Builder for MeasurementEvent and Observation JSON structures.

Constructs FHIR-aligned output structures from processed measure data.
These are JSON-serializable Pydantic models - actual event emission is
handled downstream by lorchestra.
"""

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from final_form import __version__
from final_form.interpretation.interpreter import InterpretationResult
from final_form.recoding.recoder import RecodedSection
from final_form.registry.models import FormBindingSpec
from final_form.scoring.engine import ScoringResult


class Source(BaseModel):
    """Source information for a measurement event."""

    form_id: str
    form_submission_id: str
    form_correlation_id: str | None = None
    binding_id: str
    binding_version: str


class Telemetry(BaseModel):
    """Processing provenance for a measurement event."""

    processed_at: str
    final_form_version: str
    measure_spec: str
    form_binding_spec: str
    warnings: list[str] = Field(default_factory=list)


class Observation(BaseModel):
    """An individual observation (item value or scale score)."""

    schema_: str = Field(alias="schema", default="com.lifeos.observation.v1")
    observation_id: str
    measure_id: str
    code: str  # item_id or scale_id
    kind: Literal["item", "scale"]
    value: int | float | str | None
    value_type: Literal["integer", "float", "string", "null"]
    label: str | None = None  # interpretation label for scales
    raw_answer: str | None = None  # original answer for items
    position: int | None = None  # item position
    missing: bool = False

    model_config = ConfigDict(populate_by_name=True)


class MeasurementEvent(BaseModel):
    """A complete measurement event for one measure."""

    schema_: str = Field(alias="schema", default="com.lifeos.measurement_event.v1")
    measurement_event_id: str
    measure_id: str
    measure_version: str
    subject_id: str
    timestamp: str
    source: Source
    observations: list[Observation]
    telemetry: Telemetry

    model_config = ConfigDict(populate_by_name=True)


class MeasurementEventBuilder:
    """Builds MeasurementEvent JSON structures from processed data.

    Combines recoded items, scores, and interpretations into a single
    MeasurementEvent with embedded Observations.
    """

    def __init__(self, deterministic_ids: bool = False) -> None:
        """Initialize the builder.

        Args:
            deterministic_ids: If True, generate deterministic UUIDs based on
                               input data (for testing). If False, use random UUIDs.
        """
        self.deterministic_ids = deterministic_ids
        self._id_counter = 0

    def _generate_id(self, seed: str = "") -> str:
        """Generate a UUID for an event or observation."""
        if self.deterministic_ids:
            # Use a deterministic UUID based on seed and counter
            self._id_counter += 1
            namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            return str(uuid.uuid5(namespace, f"{seed}:{self._id_counter}"))
        else:
            return str(uuid.uuid4())

    def build(
        self,
        recoded_section: RecodedSection,
        scoring_result: ScoringResult,
        interpretation_result: InterpretationResult,
        binding_spec: FormBindingSpec,
        form_id: str,
        form_submission_id: str,
        subject_id: str,
        timestamp: str,
        form_correlation_id: str | None = None,
        warnings: list[str] | None = None,
    ) -> MeasurementEvent:
        """Build a MeasurementEvent from processed data.

        Args:
            recoded_section: The recoded items for this measure.
            scoring_result: The computed scale scores.
            interpretation_result: The interpreted scores with labels.
            binding_spec: The binding spec used for processing.
            form_id: The source form ID.
            form_submission_id: The source submission ID.
            subject_id: The subject identifier.
            timestamp: The measurement timestamp.
            form_correlation_id: Optional correlation ID.
            warnings: Optional list of processing warnings.

        Returns:
            A complete MeasurementEvent ready for JSON serialization.
        """
        seed = f"{form_submission_id}:{recoded_section.measure_id}"

        # Build observations for items
        item_observations = self._build_item_observations(recoded_section, seed)

        # Build observations for scales
        scale_observations = self._build_scale_observations(
            scoring_result, interpretation_result, seed
        )

        # Combine all observations
        observations = item_observations + scale_observations

        # Build source
        source = Source(
            form_id=form_id,
            form_submission_id=form_submission_id,
            form_correlation_id=form_correlation_id,
            binding_id=binding_spec.binding_id,
            binding_version=binding_spec.version,
        )

        # Build telemetry
        telemetry = Telemetry(
            processed_at=datetime.now(timezone.utc).isoformat(),
            final_form_version=__version__,
            measure_spec=f"{recoded_section.measure_id}@{recoded_section.measure_version}",
            form_binding_spec=f"{binding_spec.binding_id}@{binding_spec.version}",
            warnings=warnings or [],
        )

        # Build the event
        return MeasurementEvent(
            schema="com.lifeos.measurement_event.v1",
            measurement_event_id=self._generate_id(seed),
            measure_id=recoded_section.measure_id,
            measure_version=recoded_section.measure_version,
            subject_id=subject_id,
            timestamp=timestamp,
            source=source,
            observations=observations,
            telemetry=telemetry,
        )

    def _build_item_observations(
        self,
        recoded_section: RecodedSection,
        seed: str,
    ) -> list[Observation]:
        """Build observations for recoded items."""
        observations: list[Observation] = []

        for item in recoded_section.items:
            value_type = self._get_value_type(item.value)

            obs = Observation(
                schema="com.lifeos.observation.v1",
                observation_id=self._generate_id(f"{seed}:item:{item.item_id}"),
                measure_id=item.measure_id,
                code=item.item_id,
                kind="item",
                value=item.value,
                value_type=value_type,
                raw_answer=str(item.raw_answer) if item.raw_answer is not None else None,
                position=item.position,
                missing=item.missing,
            )
            observations.append(obs)

        return observations

    def _build_scale_observations(
        self,
        scoring_result: ScoringResult,
        interpretation_result: InterpretationResult,
        seed: str,
    ) -> list[Observation]:
        """Build observations for scale scores."""
        observations: list[Observation] = []

        for scale_score in scoring_result.scales:
            # Get interpretation label
            interpreted = interpretation_result.get_score(scale_score.scale_id)
            label = interpreted.label if interpreted else None

            value_type = self._get_value_type(scale_score.value)

            obs = Observation(
                schema="com.lifeos.observation.v1",
                observation_id=self._generate_id(f"{seed}:scale:{scale_score.scale_id}"),
                measure_id=scoring_result.measure_id,
                code=scale_score.scale_id,
                kind="scale",
                value=scale_score.value,
                value_type=value_type,
                label=label,
            )
            observations.append(obs)

        return observations

    def _get_value_type(
        self,
        value: int | float | str | None,
    ) -> Literal["integer", "float", "string", "null"]:
        """Determine the value type for an observation."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "integer"  # Treat bools as int
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            # Check if it's a whole number stored as float
            if value.is_integer():
                return "integer"
            return "float"
        elif isinstance(value, str):
            return "string"
        else:
            return "string"
