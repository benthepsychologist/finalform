# final-form

Clinical questionnaire scoring library with structured output.

## Installation

```bash
pip install final-form
# or
uv add final-form
```

## Quick Start

```python
from pathlib import Path
from final_form.pipeline import Pipeline, PipelineConfig

# Configure the pipeline
config = PipelineConfig(
    measure_registry_path=Path("measure-registry"),
    binding_registry_path=Path("form-binding-registry"),
    binding_id="example_intake",  # Your form binding ID
)

pipeline = Pipeline(config)

# Process a form submission
result = pipeline.process({
    "form_id": "googleforms::1FAIpQLSe_example",
    "form_submission_id": "sub_123",
    "subject_id": "patient_456",
    "timestamp": "2025-01-15T10:30:00Z",
    "items": [
        {"field_key": "entry.123456001", "answer": "several days"},
        {"field_key": "entry.123456002", "answer": "not at all"},
        # ... more items
    ],
})

# Access results
print(result.success)  # True
for event in result.events:
    print(f"{event.measure_id}: {event.observations}")
```

## API Reference

### Pipeline

The main entry point for processing forms.

```python
from final_form.pipeline import Pipeline, PipelineConfig

config = PipelineConfig(
    measure_registry_path=Path("measure-registry"),      # Required
    binding_registry_path=Path("form-binding-registry"), # Required
    binding_id="my_intake_form",                         # Required
    binding_version="1.0.0",                             # Optional (defaults to latest)
    measure_schema_path=Path("schemas/measure_spec.schema.json"),  # Optional
    binding_schema_path=Path("schemas/form_binding_spec.schema.json"),  # Optional
    deterministic_ids=False,                             # Optional (for testing)
)

pipeline = Pipeline(config)
```

#### `pipeline.process(form_response) -> ProcessingResult`

Process a single form submission.

**Input format:**

```python
{
    "form_id": str,              # Form platform identifier
    "form_submission_id": str,   # Unique submission ID
    "subject_id": str,           # Patient/participant ID
    "timestamp": str,            # ISO 8601 timestamp
    "items": [
        {
            "field_key": str,    # Form field identifier
            "answer": str,       # Response text (e.g., "several days")
        },
        # ... more items
    ],
}
```

**Output:**

```python
ProcessingResult(
    form_submission_id="sub_123",
    success=True,
    events=[MeasurementEvent(...)],
    diagnostics=ProcessingDiagnostics(...),
)
```

#### `pipeline.process_batch(form_responses) -> list[ProcessingResult]`

Process multiple form submissions.

### Output Models

#### MeasurementEvent

One event per measure in the form:

```python
MeasurementEvent(
    schema_="com.lifeos.measurement_event.v1",
    measurement_event_id="uuid",
    measure_id="phq9",
    measure_version="1.0.0",
    subject_id="patient_456",
    timestamp="2025-01-15T10:30:00Z",
    source=Source(...),
    observations=[Observation(...)],
    telemetry=Telemetry(...),
)
```

#### Observation

Individual item values and scale scores:

```python
# Item observation
Observation(
    schema_="com.lifeos.observation.v1",
    observation_id="uuid",
    measure_id="phq9",
    code="phq9_item1",
    kind="item",
    value=2,
    value_type="integer",
    raw_answer="more than half the days",
    missing=False,
)

# Scale observation
Observation(
    schema_="com.lifeos.observation.v1",
    observation_id="uuid",
    measure_id="phq9",
    code="phq9_total",
    kind="scale",
    value=12.0,
    value_type="integer",
    label="Moderate",  # Interpretation label
    missing=False,
)
```

### Direct Processor Access

For lower-level control, use the domain processor directly:

```python
from final_form.registry import MeasureRegistry
from final_form.domains.questionnaire import QuestionnaireProcessor
from final_form.registry.models import FormBindingSpec, BindingSection, Binding

# Load measure spec
registry = MeasureRegistry(Path("measure-registry"))
spec = registry.get("phq9", "1.0.0")

# Create binding programmatically
binding = FormBindingSpec(
    type="form_binding_spec",
    form_id="my-form",
    binding_id="my-binding",
    version="1.0.0",
    sections=[
        BindingSection(
            measure_id="phq9",
            measure_version="1.0.0",
            bindings=[
                Binding(item_id="phq9_item1", by="field_key", value="q1"),
                Binding(item_id="phq9_item2", by="field_key", value="q2"),
                # ... more bindings
            ],
        )
    ],
)

# Process
processor = QuestionnaireProcessor()
result = processor.process(
    form_response={...},
    binding_spec=binding,
    measures={"phq9": spec},
)
```

## Supported Measures

| Measure | Items | Scales | Features |
|---------|-------|--------|----------|
| `phq9` | 10 | 2 | PHQ-9 depression screener |
| `gad7` | 8 | 2 | GAD-7 anxiety screener |
| `pss_10` | 10 | 1 | Perceived Stress Scale (4 reversed items) |
| `fscrs` | 22 | 4 | Self-Criticizing/Reassuring Scale |
| `ipip_neo_60_c` | 12 | 7 | IPIP-NEO Conscientiousness (1 composite + 6 facets) |
| `phlms_10` | 10 | 2 | Philadelphia Mindfulness Scale (sum_then_double) |
| `msi` | 10 | 1 | McLean Screening Instrument for BPD |
| `safe` | 4 | 1 | TPAS Safety Subscale |
| `joy` | 8 | 1 | Joy and Curiosity Scale |
| `sleep_disturbances` | 4 | 1 | Sleep Disturbances Scale |
| `trauma_exposure` | 17 | 1 | Life Events Checklist |
| `ptsd_screen` | 5 | 1 | PC-PTSD-5 Style Screener |

## CLI Usage

```bash
final-form run \
  --in forms.jsonl \
  --out measurements.jsonl \
  --binding example_intake \
  --measure-registry ./measure-registry \
  --form-binding-registry ./form-binding-registry \
  --diagnostics diagnostics.jsonl
```

## Registries

### Measure Registry

Located at `measure-registry/measures/<measure_id>/<version>.json`:

```json
{
  "type": "measure_spec",
  "measure_id": "phq9",
  "version": "1.0.0",
  "name": "Patient Health Questionnaire-9",
  "kind": "questionnaire",
  "items": [
    {
      "item_id": "phq9_item1",
      "position": 1,
      "text": "Little interest or pleasure in doing things",
      "response_map": {
        "not at all": 0,
        "several days": 1,
        "more than half the days": 2,
        "nearly every day": 3
      }
    }
  ],
  "scales": [
    {
      "scale_id": "phq9_total",
      "name": "PHQ-9 Total",
      "items": ["phq9_item1", "phq9_item2", ...],
      "method": "sum",
      "reversed_items": [],
      "min": 0,
      "max": 27,
      "interpretations": [
        {"min": 0, "max": 4, "label": "Minimal", "severity": 0},
        {"min": 5, "max": 9, "label": "Mild", "severity": 1},
        {"min": 10, "max": 14, "label": "Moderate", "severity": 2},
        {"min": 15, "max": 19, "label": "Moderately Severe", "severity": 3},
        {"min": 20, "max": 27, "label": "Severe", "severity": 4}
      ]
    }
  ]
}
```

### Form Binding Registry

Located at `form-binding-registry/bindings/<binding_id>/<version>.json`:

```json
{
  "type": "form_binding_spec",
  "form_id": "googleforms::1FAIpQLSe_example",
  "binding_id": "example_intake",
  "version": "1.0.0",
  "sections": [
    {
      "measure_id": "phq9",
      "measure_version": "1.0.0",
      "bindings": [
        {"item_id": "phq9_item1", "by": "field_key", "value": "entry.123456001"},
        {"item_id": "phq9_item2", "by": "field_key", "value": "entry.123456002"}
      ]
    }
  ]
}
```

## Processing Pipeline

```
form_response
     │
     ▼
┌─────────────────┐
│    Pipeline     │  Loads specs, routes by measure.kind
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DomainRouter   │  questionnaire | lab | vital | wearable
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              QuestionnaireProcessor                      │
│                                                          │
│  1. Map      Form fields → measure items (via binding)   │
│  2. Recode   Text answers → numeric values               │
│  3. Validate Completeness and range checks               │
│  4. Score    Compute scale scores (sum/avg/prorate)      │
│  5. Interpret Apply severity bands and labels            │
│  6. Build    Generate MeasurementEvent + Observations    │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
ProcessingResult(events, diagnostics, success)
```

## Scoring Methods

- **sum**: Add all item values
- **average**: Mean of item values
- **sum_then_double**: Sum items then multiply by 2 (e.g., PHLMS-10)
- **Reverse scoring**: Automatically handled for items in `reversed_items`
- **Proration**: Missing items prorated when within `missing_allowed` threshold

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=final_form

# Type checking
uv run mypy final_form

# Linting
uv run ruff check final_form
```

## License

MIT
