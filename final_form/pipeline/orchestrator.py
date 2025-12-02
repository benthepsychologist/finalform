"""Pipeline for form processing.

Loads registries, resolves specs, and routes to the appropriate
domain processor based on measure kind.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from final_form.core.factory import create_router
from final_form.core.models import ProcessingResult
from final_form.core.router import DomainRouter
from final_form.registry import BindingRegistry, MeasureRegistry
from final_form.registry.models import MeasureSpec


class PipelineConfig(BaseModel):
    """Configuration for the processing pipeline."""

    measure_registry_path: Path
    binding_registry_path: Path
    binding_id: str
    binding_version: str | None = None
    measure_schema_path: Path | None = None
    binding_schema_path: Path | None = None
    deterministic_ids: bool = False


class Pipeline:
    """Loads specs and routes form processing to domain processors."""

    def __init__(
        self,
        config: PipelineConfig,
        router: DomainRouter | None = None,
    ) -> None:
        """Initialize the pipeline.

        Args:
            config: Pipeline configuration specifying registries and binding.
            router: Optional domain router. If not provided, creates default router.
        """
        self.config = config

        # Load registries
        self.measure_registry = MeasureRegistry(
            config.measure_registry_path,
            schema_path=config.measure_schema_path,
        )
        self.binding_registry = BindingRegistry(
            config.binding_registry_path,
            schema_path=config.binding_schema_path,
        )

        # Load binding spec
        if config.binding_version:
            self.binding_spec = self.binding_registry.get(
                config.binding_id,
                config.binding_version,
            )
        else:
            self.binding_spec = self.binding_registry.get_latest(config.binding_id)

        # Load measure specs
        self.measures: dict[str, MeasureSpec] = {}
        for section in self.binding_spec.sections:
            self.measures[section.measure_id] = self.measure_registry.get(
                section.measure_id,
                section.measure_version,
            )

        # Router
        self.router = router if router is not None else create_router()

    def process(self, form_response: dict[str, Any]) -> ProcessingResult:
        """Process a form response by routing to the appropriate domain processor."""
        return self.router.process(
            form_response=form_response,
            binding_spec=self.binding_spec,
            measures=self.measures,
            deterministic_ids=self.config.deterministic_ids,
        )

    def process_batch(self, form_responses: list[dict[str, Any]]) -> list[ProcessingResult]:
        """Process a batch of form responses."""
        return [self.process(r) for r in form_responses]
