# final-form

Clinical questionnaire scoring library with structured output.

## Installation

```bash
pip install final-form
# or
uv add final-form
```

## Quick Start

Process a canonical form submission (from canonizer) for a specific measure:

```python
from pathlib import Path
from final_form.input import FormInputClient, process_form_submission
from final_form.registry import MeasureRegistry

# Setup
client = FormInputClient(Path("form-mappings"))
registry = MeasureRegistry(Path("measure-registry"))

# 1. Configure mapping: tell final-form where PHQ-9 lives in this form
client.save_item_map(
    form_id="client_intake_v3",
    measure_id="phq9",
    item_map={
        "entry.111111": "phq9_item1",
        "entry.222222": "phq9_item2",
        # ... map all fields to item IDs
    }
)

# 2. Canonical form submission (from canonizer)
canonical = {
    "form_id": "client_intake_v3",
    "submission_id": "subm_123",
    "respondent": {"id": "contact-uuid", "display": "Jane Doe"},
    "submitted_at": "2025-12-01T12:34:56Z",
    "items": [
        {"field_id": "entry.111111", "raw_value": "more than half the days"},
        {"field_id": "entry.222222", "raw_value": "nearly every day"},
        # ... more items
    ],
}

# 3. Process for PHQ-9
result = process_form_submission(
    canonical,
    measure_id="phq9",
    form_input_client=client,
    measure_registry=registry,
)

print(result.success)  # True
for obs in result.events[0].observations:
    if obs.kind == "scale":
        print(f"{obs.code}: {obs.value} -> {obs.label}")
# phq9_total: 8.0 -> "Mild"
```

## API Reference

### process_form_submission (Recommended)

High-level API for processing canonical form submissions from canonizer.

```python
from final_form.input import FormInputClient, process_form_submission
from final_form.registry import MeasureRegistry

result = process_form_submission(
    form_submission,                    # Canonical form dict from canonizer
    measure_id="phq9",                  # Which measure to extract and score
    form_input_client=client,           # FormInputClient instance
    measure_registry=registry,          # MeasureRegistry instance
    measure_version="1.0.0",            # Optional (defaults to latest)
    form_id="override_form_id",         # Optional (defaults to form_submission["form_id"])
    item_map_override={"f1": "item1"},  # Optional (bypasses FormInputClient lookup)
    strict=True,                        # Optional (fail on unmapped fields)
)
```

**Canonical form submission format** (from canonizer):

```python
{
    "form_id": "client_intake_v3",
    "submission_id": "subm_123",
    "respondent": {"id": "contact-uuid", "display": "Jane Doe"},
    "submitted_at": "2025-12-01T12:34:56Z",
    "items": [
        {
            "field_id": "entry.111111",
            "question_text": "Little interest or pleasure...",  # optional
            "raw_value": "more than half the days",
        },
    ],
    "meta": {"source_system": "google_forms"},  # optional
}
```

### FormInputClient

Local storage for field_id → item_id mappings. Stores one JSON file per (form_id, measure_id) pair.

```python
from final_form.input import FormInputClient

client = FormInputClient(Path("form-mappings"))

# Save a mapping
client.save_item_map(
    form_id="client_intake_v3",
    measure_id="phq9",
    item_map={
        "entry.111111": "phq9_item1",
        "entry.222222": "phq9_item2",
    }
)

# Retrieve a mapping
item_map = client.get_item_map("client_intake_v3", "phq9")
# Returns {"entry.111111": "phq9_item1", ...} or None

# List configured measures for a form
measures = client.list_mappings("client_intake_v3")
# Returns ["phq9", "gad7", ...]

# Delete a mapping
client.delete_item_map("client_intake_v3", "phq9")

# Record resolution events (for future fuzzy matching analytics)
client.record_resolution_event(
    form_id="client_intake_v3",
    measure_id="phq9",
    field_id="entry.111111",
    candidate_item_id="phq9_item1",
    accepted=True,
    reason="exact match",
)
```

**Storage layout:**

```
form-mappings/
  client_intake_v3/
    phq9.json
    gad7.json
  another_form/
    pss_10.json
```

Each mapping file:

```json
{
  "form_id": "client_intake_v3",
  "measure_id": "phq9",
  "item_map": {
    "entry.111111": "phq9_item1",
    "entry.222222": "phq9_item2"
  },
  "meta": {
    "created_at": "2025-12-01T10:00:00Z",
    "updated_at": "2025-12-01T10:00:00Z"
  }
}
```

### Exceptions

```python
from final_form.input import (
    MissingFormIdError,    # form_id not in submission and not provided
    MissingItemMapError,   # no mapping configured for (form_id, measure_id)
    UnmappedFieldError,    # form has fields not in item_map (strict=True)
)
```

**Error behavior:**

| Condition | `strict=True` (default) | `strict=False` |
|-----------|------------------------|----------------|
| No mapping configured | `MissingItemMapError` | `MissingItemMapError` |
| Form has unmapped fields | `UnmappedFieldError` | Skip + warn in diagnostics |
| Missing form_id | `MissingFormIdError` | `MissingFormIdError` |

### Pipeline (Lower-level)

For processing pre-bound forms with static binding specs.

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
┌──────────────────────────────────────────────────────────────────┐
│                     RECOMMENDED FLOW                              │
└──────────────────────────────────────────────────────────────────┘

  Google Forms / Typeform / etc.
              │
              ▼
       ┌─────────────┐
       │  canonizer  │  Normalizes raw form → canonical shape
       └──────┬──────┘
              │
              ▼
  canonical_form_submission (field_id, raw_value, ...)
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    final-form                                    │
│                                                                  │
│  ┌─────────────────┐      ┌──────────────────┐                  │
│  │ FormInputClient │ ───▶ │ field_id→item_id │  (local storage) │
│  └─────────────────┘      └──────────────────┘                  │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────┐                                │
│  │ process_form_submission()   │  One measure at a time         │
│  └──────────────┬──────────────┘                                │
│                 │                                                │
│                 ▼                                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           QuestionnaireProcessor                         │    │
│  │                                                          │    │
│  │  1. Map      field_id → item_id (via FormInputClient)    │    │
│  │  2. Recode   raw_value → numeric (via response_map)      │    │
│  │  3. Validate Completeness checks                         │    │
│  │  4. Score    sum / average / reverse / prorate           │    │
│  │  5. Interpret Severity bands → labels                    │    │
│  │  6. Build    MeasurementEvent + Observations             │    │
│  └──────────────┬──────────────────────────────────────────┘    │
│                 │                                                │
│                 ▼                                                │
│  ProcessingResult(events, diagnostics, success)                  │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
       ┌─────────────┐
       │  lorchestra │  Orchestrates multiple measures per form
       └─────────────┘
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
