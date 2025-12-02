---
version: "0.1"
tier: C
title: Domain-Modular Architecture Refactor
owner: lifeos
goal: Refactor final-form from questionnaire-only to domain-modular architecture supporting questionnaire, lab, vital, and wearable measure types
labels: [architecture, refactor]
project_slug: final-form
spec_version: 1.0.0
created: 2025-12-02T11:54:44.712112+00:00
updated: 2025-12-02T11:54:44.712112+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/domain-modular-architecture-refactor"
---

# Domain-Modular Architecture Refactor

## Objective

> Refactor final-form from a questionnaire-only processor to a domain-modular, registry-driven processor supporting multiple measurement domains (questionnaire, lab, vital, wearable). All domains share a unified output contract (MeasurementEvent + Observations) while maintaining domain-specific processing logic, specs, and diagnostics.

## Acceptance Criteria

- [ ] CI green (lint + unit + type check)
- [ ] All existing tests pass after refactor
- [ ] New directory structure: `core/` + `domains/questionnaire/`
- [ ] `DomainProcessor` protocol defined and implemented for questionnaire
- [ ] Domain router working with `measure_spec["kind"]` dispatch
- [ ] Terminology renamed: `instrument` → `measure` throughout
- [ ] Stub modules created for `domains/lab/`, `domains/vital/`, `domains/wearable/`
- [ ] CLI updated to use new entry point
- [ ] 70%+ test coverage maintained

## Context

### Background

Final-form was built as a questionnaire scoring engine, but the vision is broader: it should handle any measurement domain (lab results, vital signs, wearables) with the same guarantees:

- **Registry-driven**: Semantic knowledge lives in specs, not code
- **Deterministic**: Same inputs → same outputs
- **FHIR-aligned**: MeasurementEvent + Observation[] output contract
- **Explicit**: No runtime inference; domain selected by `measure_spec["kind"]`

Current implementation has questionnaire-specific concepts ("items", "scales", "recoding") hardcoded throughout. This refactor extracts shared infrastructure to `core/` and isolates questionnaire logic to `domains/questionnaire/`, creating a clean pattern for future domains.

### Key Architectural Decisions

1. **Domain selection**: `measure_spec["kind"]` field determines which processor handles the input
2. **Binding specs**: Conceptually universal (all domains have mappings), but `binding_spec: dict | None` in protocol—domains can treat None as identity mapping
3. **Return type**: Keep existing `ProcessingResult` (events + diagnostics + success)
4. **Terminology**: "measure" instead of "instrument" throughout
5. **Diagnostics**: Shared base types in core; domain-specific codes in domain modules
6. **Router**: Static dict mapping kind → processor (no plugin system)

### Constraints

- This is a refactor, not a rewrite—questionnaire logic stays intact
- No new features; just reorganization
- Maintain backwards compatibility for CLI interface
- No changes to output schema (MeasurementEvent, Observation)

## Plan

### Step 1: Terminology Rename (instrument → measure) [G0: Plan Approval]

**Prompt:**

Rename all `instrument` references to `measure` across the codebase:
- `InstrumentSpec` → `MeasureSpec`
- `InstrumentRegistry` → `MeasureRegistry`
- `instrument_id` → `measure_id`
- `instrument_version` → `measure_version`
- `instrument-registry/` directory → `measure-registry/`
- CLI flags: `--instrument-registry` → `--measure-registry`
- All internal references in code, tests, and specs

Update JSON schema files and spec files accordingly.

**Commands:**

```bash
ruff check .
pytest -q
```

**Outputs:**

- All files renamed and updated
- Tests passing with new terminology

### Step 2: Create core/ Module Structure [G0: Plan Approval]

**Prompt:**

Create the `core/` module with shared infrastructure extracted from current code:

```
final_form/core/
├── __init__.py
├── models.py         # MeasurementEvent, Observation, ProcessingResult, Source, Telemetry
├── diagnostics.py    # DiagnosticMessage, ProcessingDiagnostics (base types)
├── registry.py       # Generic spec loading (measures, bindings)
├── domain.py         # DomainProcessor protocol
├── router.py         # kind → processor mapping
└── pipeline.py       # Unified entry point
```

Extract and move:
- `MeasurementEvent`, `Observation` models to `core/models.py`
- Base diagnostic types to `core/diagnostics.py`
- Registry loading logic to `core/registry.py`

**Outputs:**

- `final_form/core/` module created
- Shared types extracted

### Step 3: Create domains/questionnaire/ Module [G1: Code Readiness]

**Prompt:**

Move questionnaire-specific logic into `domains/questionnaire/`:

```
final_form/domains/questionnaire/
├── __init__.py
├── processor.py      # QuestionnaireProcessor implementing DomainProcessor
├── models.py         # Questionnaire-specific spec models
├── mapping.py        # Form → measure item mapping
├── recoding.py       # Text → numeric conversion
├── scoring.py        # Scale computation
├── interpretation.py # Severity band lookup
└── diagnostics.py    # Questionnaire-specific diagnostic codes
```

The `QuestionnaireProcessor` should:
- Implement `DomainProcessor` protocol
- Orchestrate mapping → recoding → validation → scoring → interpretation → building
- Return `ProcessingResult`

**Commands:**

```bash
ruff check .
pytest -q
```

**Outputs:**

- `final_form/domains/questionnaire/` module created
- All questionnaire logic moved and working

### Step 4: Implement Domain Router [G1: Code Readiness]

**Prompt:**

Implement the domain router in `core/router.py`:

```python
DOMAIN_PROCESSORS: dict[str, type[DomainProcessor]] = {
    "questionnaire": QuestionnaireProcessor,
}

def get_processor(kind: str) -> DomainProcessor:
    if kind not in DOMAIN_PROCESSORS:
        raise ValueError(f"Unknown measure kind: {kind}")
    return DOMAIN_PROCESSORS[kind]()
```

Update `core/pipeline.py` to:
1. Load measure spec
2. Extract `kind` from spec
3. Route to appropriate domain processor
4. Return `ProcessingResult`

**Commands:**

```bash
ruff check .
pytest -q
```

**Outputs:**

- Router implemented and tested
- Pipeline using router for dispatch

### Step 5: Create Domain Stubs [G1: Code Readiness]

**Prompt:**

Create stub modules for future domains:

```
final_form/domains/lab/
├── __init__.py
└── processor.py      # LabProcessor stub (raises NotImplementedError)

final_form/domains/vital/
├── __init__.py
└── processor.py      # VitalProcessor stub

final_form/domains/wearable/
├── __init__.py
└── processor.py      # WearableProcessor stub
```

Each stub should:
- Define a processor class implementing `DomainProcessor`
- Have `domain` attribute set appropriately
- Raise `NotImplementedError("Lab domain not yet implemented")` in `process()`

Register stubs in router (they'll error if called, which is correct).

**Outputs:**

- Stub modules created
- Stubs registered in router

### Step 6: Update CLI and Entry Points [G2: Pre-Release]

**Prompt:**

Update CLI to use new structure:
- Change `--instrument-registry` to `--measure-registry`
- Update imports to use `core/` and `domains/`
- Ensure `final-form run` works with new architecture

Update `pyproject.toml` entry points if needed.

**Commands:**

```bash
final-form --help
final-form run --help
ruff check .
pytest -q
```

**Outputs:**

- CLI updated and working
- All commands functional

### Step 7: Update Tests [G2: Pre-Release]

**Prompt:**

Update all tests to:
- Use new import paths (`final_form.core.*`, `final_form.domains.questionnaire.*`)
- Use new terminology (`measure` instead of `instrument`)
- Add tests for:
  - Domain router
  - DomainProcessor protocol compliance
  - Pipeline with router dispatch

**Commands:**

```bash
pytest -v --cov=final_form --cov-report=term-missing
```

**Outputs:**

- All tests passing
- Coverage >= 70%

### Step 8: Update Documentation [G4: Post-Implementation]

**Prompt:**

Update documentation to reflect new architecture:
- README.md: Update terminology and structure
- FINAL-FORM-ARCH.md: Document domain-modular architecture
- Inline docstrings for new modules

**Outputs:**

- `artifacts/governance/decision-log.md` with key decisions
- Updated README and architecture docs

## Models & Tools

**Tools:** bash, pytest, ruff, mypy

**Models:** Claude (implementation), review as needed

## Repository

**Branch:** `feat/domain-modular-architecture-refactor`

**Merge Strategy:** squash

## File Touch Summary

### New Files
- `final_form/core/__init__.py`
- `final_form/core/models.py`
- `final_form/core/diagnostics.py`
- `final_form/core/registry.py`
- `final_form/core/domain.py`
- `final_form/core/router.py`
- `final_form/core/pipeline.py`
- `final_form/domains/__init__.py`
- `final_form/domains/questionnaire/__init__.py`
- `final_form/domains/questionnaire/processor.py`
- `final_form/domains/questionnaire/models.py`
- `final_form/domains/questionnaire/mapping.py`
- `final_form/domains/questionnaire/recoding.py`
- `final_form/domains/questionnaire/scoring.py`
- `final_form/domains/questionnaire/interpretation.py`
- `final_form/domains/questionnaire/diagnostics.py`
- `final_form/domains/lab/__init__.py`
- `final_form/domains/lab/processor.py`
- `final_form/domains/vital/__init__.py`
- `final_form/domains/vital/processor.py`
- `final_form/domains/wearable/__init__.py`
- `final_form/domains/wearable/processor.py`

### Modified Files
- `final_form/__init__.py`
- `final_form/cli.py`
- `final_form/io.py`
- `instrument-registry/` → `measure-registry/` (rename)
- `schemas/instrument_spec.schema.json` → `schemas/measure_spec.schema.json`
- All test files (import paths, terminology)
- `README.md`
- `FINAL-FORM-ARCH.md`

### Deleted Files (after move)
- `final_form/registry/` (moved to core/ and domains/)
- `final_form/mapping/` (moved to domains/questionnaire/)
- `final_form/recoding/` (moved to domains/questionnaire/)
- `final_form/scoring/` (moved to domains/questionnaire/)
- `final_form/interpretation/` (moved to domains/questionnaire/)
- `final_form/validation/` (moved to domains/questionnaire/)
- `final_form/builders/` (split between core/ and domains/)
- `final_form/diagnostics/` (split between core/ and domains/)
- `final_form/pipeline/` (moved to core/)
