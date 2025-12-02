# Instrument Registry

This registry contains validated instrument specifications for psychological assessments.

## Structure

```
instrument-registry/
└── instruments/
    ├── phq9/
    │   └── 1-0-0.json
    └── gad7/
        └── 1-0-0.json
```

## Versioning

Each instrument spec is versioned using SemVer (e.g., `1.0.0` stored as `1-0-0.json`).

## Schema

All instrument specs must validate against `schemas/instrument_spec.schema.json`.

## Available Instruments

| ID | Name | Version | Items |
|----|------|---------|-------|
| phq9 | Patient Health Questionnaire-9 | 1.0.0 | 10 (9 symptom + 1 severity) |
| gad7 | Generalized Anxiety Disorder-7 | 1.0.0 | 8 (7 symptom + 1 severity) |
