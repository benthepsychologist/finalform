---
version: "0.1"
tier: B
title: Final Form v0.1.0 - Questionnaire Semantic Processing Engine
owner: benthepsychologist
goal: Build the final-form semantic processing engine that transforms canonical JSON input into fully scored, normalized, validated, research-ready canonical output
labels: [questionnaires, scoring, semantic-processing, v0]
project_slug: final-form
spec_version: 1.0.0
created: 2025-11-17T14:53:29.020741+00:00
updated: 2025-11-17T17:00:00.000000+00:00
orchestrator_contract: "standard"
repo:
  working_branch: "feat/final-form-initial-spec"
---

# Final Form v0.1.0 - Questionnaire Semantic Processing Engine

## Objective

Build the **final-form** semantic processing engine that transforms canonical JSON input into fully scored, normalized, validated, research-ready canonical output.

final-form is the authoritative semantic data engine sitting between canonizer and vector-projector in the pipeline. It performs deterministic, domain-aware processing including cleaning, normalization, scoring, interpretation, and semantic validation. Once data passes through final-form, no further cleaning or scoring occurs downstream.

**v0.1.0 Scope:**
- **Questionnaire Measure Schema:** Create `org.canonical/questionnaire_measure` schema in canonizer-registry
- **Questionnaire Registry:** Registry with ~13 standard mental health instruments (PHQ-9, GAD-7, MSI, etc.)
- **Form Mapping Registry:** Mapping files that connect form instances to measures (item ID mappings, value recodings)
- **Generic Scoring Engine:** Single scoring engine that interprets registry rules (no per-questionnaire scorers)
- **Full Pipeline:** Mapping, cleaning, normalization, scoring, interpretation with diagnostics
- **CLI:** Batch processing with explicit form→measure mappings

## Acceptance Criteria

**Registry & Schema:**
- [ ] `org.canonical/questionnaire_measure` schema created in canonizer-registry
- [ ] Questionnaire registry contains ~13 standard measures with full definitions
- [ ] Registry validates against questionnaire_measure schema
- [ ] Measures use correct item prefixes (phq_9_, gad_7_, etc. with underscores)
- [ ] Form mapping schema created for form→measure mappings
- [ ] Example form mappings created (Google Forms, Typeform, etc.)

**Scoring Engine:**
- [ ] Generic scoring engine interprets all scoring methods (sum, average, sum_then_double)
- [ ] Reverse scoring handled generically
- [ ] Multi-subscale questionnaires supported (e.g., PHLMS, FSCRS)
- [ ] Deterministic scoring: same input → same output

**Mapping & Recoding:**
- [ ] Mapper applies mapping JSON: platform IDs → canonical IDs
- [ ] Value recoding handles both numeric and text answer values
- [ ] Errors clearly when item or value not in mapping
- [ ] Mapping files are simple, explicit contracts (no fuzzy matching)

**Pipeline & CLI:**
- [ ] Canonical JSON → final-form JSON with zero ambiguity
- [ ] CLI can process JSONL batch inputs with mapping file specified
- [ ] CLI command: `final-form run --in forms.jsonl --out final.jsonl --mapping path/to/mapping.json`
- [ ] Clear error messages and per-record diagnostics

**Quality & Testing:**
- [ ] Golden test suite passes with 100% accuracy (test PHQ-9, GAD-7, MSI, PHLMS-10)
- [ ] Versioned, repeatable outputs with provenance metadata
- [ ] CI green (lint + unit tests)
- [ ] 80% test coverage achieved
- [ ] Integration test with canonizer output passes

## Context

### Background

The research pipeline currently lacks a deterministic, version-controlled semantic processing layer. Data flows from canonizer (structural normalization) directly to analysis, requiring researchers to implement ad-hoc cleaning, scoring, and validation logic repeatedly.

final-form fills this gap by providing:
- **Deterministic processing:** Replayable, diffable transformations across versions
- **Semantic authority:** Single source of truth for scoring and interpretation
- **Research-ready outputs:** Fully validated, annotated, analysis-ready data
- **Clear separation of concerns:** Structural (canonizer) → Semantic (final-form) → Representation (vector-projector)

This work establishes the foundation for all semantic processing in the research platform.

### Constraints

- Must validate inputs using canonizer-registry schemas
- Must be runnable standalone (CLI, notebook, script) without full stack
- Must maintain backward compatibility with canonical schemas
- No external API calls or side effects (pure semantic transformations)
- Scoring logic must be versioned and reproducible
- Questionnaire measure schema must be created in canonizer-registry (schemas only)
- Questionnaire measure instances live in separate questionnaire-registry repo
- canonizer-registry = schemas, questionnaire-registry = instances
- final-form consumes both registries (schemas for validation, instances for data)
- No per-questionnaire scorer classes (use generic scoring engine)
- v0 implements ~13 measures, not 30

### Input & Output Contracts

**Inputs:**
- `org.canonical/form_response` (from canonizer)
- Validated against canonizer-registry schemas
- JSONL format for batch processing
- **IMPORTANT:** Canonical forms contain heterogeneous data:
  - `question_id` may be: platform IDs (`"entry.123456"`), canonical IDs (`"phq_9_1"`), or missing
  - `question_text` may be used when IDs are unavailable or non-semantic
  - `answer_value` may be: numeric (`1`), text (`"Several days"`), or numeric-as-string (`"1"`)
  - Canonization handles **schema** normalization, not semantic recoding

**Mapping Files:**
- Form provenance ID → measure ID mappings
- Item ID mappings: platform-specific IDs → canonical measure item IDs
- Question text mappings (fallback when IDs unavailable)
- Value recoding rules (if needed beyond anchor label matching)
- Stored in canonizer-registry alongside measure definitions

**Outputs:**
- `org.canonical/questionnaire_response` (semantic, scored, validated, final)
- Diagnostics object (errors, warnings, missingness summaries)
- JSONL format matching input structure

### Questionnaire Registry Architecture

**Schema Definition:**
The `org.canonical/questionnaire_measure` schema defines a single questionnaire measure with:
- Metadata (name, description, interpretation, instructions)
- Item prefix (e.g., `phq_9_` with underscore)
- Anchors (response scale with min, max, labels)
- Items (list of item text strings)
- Scores (one or more subscales with scoring rules)
  - `included_items`: array of item numbers
  - `reversed_items`: array of item numbers to reverse
  - `scoring.method`: "sum" | "average" | "sum_then_double"
  - `scoring.min`, `scoring.max`: valid range
  - `scoring.higher_is_better`: boolean
  - `ranges`: interpretation bands with min, max, label, severity, description

**Registry Repository:**
The questionnaire registry is a **separate repository** (`~/questionnaire-registry`) containing a `measures.json` file with ~13 instruments:
- `phq_9`: Patient Health Questionnaire-9
- `gad_7`: Generalized Anxiety Disorder-7
- `msi`: McLean Screening Instrument for BPD
- `safe`: Therapy Process Assessment Scale - Safety Subscale
- `phlms_10`: Philadelphia Mindfulness Scale (10-item, 2 subscales)
- `joy`: Joy and Curiosity Scale
- `sleep_disturbances`: Sleep Disturbances Scale
- `trauma_exposure`: Traumatic Experiences Questionnaire
- `ptsd_screen`: PTSD Screener (PC-PTSD-5 style)
- `ipip_neo_60_c`: IPIP-NEO-60 Conscientiousness (7 subscales)
- `fscrs`: Forms of Self-Criticizing/Attacking and Self-Reassuring Scale (4 subscales)
- `pss_10`: Perceived Stress Scale (10-item)
- `dts`: Distress Tolerance Scale (Short Form)
- `cfs`: Cognitive Flexibility Scale (12-item)

**Generic Scoring Engine:**
Final-form implements ONE scoring engine that:
1. Loads measure definition from registry by item prefix
2. Maps form items to measure items using prefix matching
3. Applies reverse scoring for specified items
4. Computes subscale scores using the method specified in registry
5. Applies interpretation ranges
6. Handles missing data and partial responses

No per-questionnaire code is needed - the registry is the single source of truth.

### Form Mapping Architecture

**The Mapping Problem:**
Canonical `form_response` data from canonizer contains heterogeneous question identifiers and answer formats:
- Google Forms uses platform IDs like `"entry.123456789"`
- Typeform uses UUIDs like `"a1b2c3d4"`
- Some forms have no usable IDs, only question text
- Answer values may be numeric (0-3) or text ("Not at all")

**Mapping File Schema:**
Each form instance gets a mapping file that bridges form → measure:

```json
{
  "mapping_id": "google_forms_mbc_initial_phq9_v1",
  "form_provenance": {
    "platform": "google_forms",
    "form_id": "1FAIpQLSe_abc123",
    "form_name": "MBC Initial Assessment",
    "version": "1.0"
  },
  "target_measure": "phq_9",
  "item_mappings": [
    {
      "form_question_id": "entry.123456789",
      "form_question_text": "Little interest or pleasure in doing things",
      "canonical_item_id": "phq_9_1",
      "notes": "PHQ-9 item 1"
    },
    {
      "form_question_id": "entry.987654321",
      "form_question_text": "Feeling down, depressed, or hopeless",
      "canonical_item_id": "phq_9_2",
      "notes": "PHQ-9 item 2"
    }
  ],
  "value_mappings": {
    "use_anchor_labels": true,
    "custom_mappings": {}
  }
}
```

**Mapping Registry:**
- Mapping files stored in `~/questionnaire-registry/mappings/`
- Organized by platform and form: `mappings/google_forms/mbc_initial_phq9_v1.json`
- Validated against `org.canonical/form_mapping` schema from canonizer-registry
- CLI accepts `--mapping` flag to specify which mapping file to use

**Mapper Behavior:**
1. Load mapping file specified by user (via `--mapping` flag)
2. For each form item, look up `form_question_id` in `item_mappings`
3. Map to `canonical_item_id` (e.g., `phq_9_1`)
4. Recode `answer_value` using anchor labels or custom value mappings
5. Error if item or value not found in mapping
6. Output: items with canonical IDs and numeric values

**Simple, explicit, deterministic.** No auto-detection, no fuzzy matching. The mapping file is the contract.

## Plan

### Step 1: Create Questionnaire Measure Schema in Canonizer-Registry [G0: Plan Approval]

**Objective:** Define the `org.canonical/questionnaire_measure` JSON schema in canonizer-registry.

**Prompt:**

Create the questionnaire measure schema at `~/canonizer-registry/schemas/org.canonical/questionnaire_measure/jsonschema/1-0-0.json`.

The schema must validate the measure structure including:
- Required fields: name, description, item_prefix, anchors, items, scores
- Optional fields: interpretation, instructions
- Anchors: min, max, labels (object with string keys and string values)
- Items: array of strings
- Scores: object where each key is a subscale ID containing:
  - included_items: array of integers
  - reversed_items: array of integers
  - scoring: object with method (enum: "sum", "average", "sum_then_double"), min, max, higher_is_better
  - ranges: array of range objects with min, max, label, severity, description

Use the Iglu self-describing schema format matching other org.canonical schemas.

Validate the schema against the example measures provided (phq_9, gad_7, etc.).

**Commands:**

```bash
# Validate schema syntax
cd ~/canonizer-registry
python -m jsonschema schemas/org.canonical/questionnaire_measure/jsonschema/1-0-0.json
```

**Outputs:**

- `~/canonizer-registry/schemas/org.canonical/questionnaire_measure/jsonschema/1-0-0.json`

---

### Step 2: Create Questionnaire Registry Repository [G0: Plan Approval]

**Objective:** Create separate questionnaire-registry repository with ~13 standard measures.

**Prompt:**

Create a new repository for questionnaire instances:

1. **Initialize questionnaire-registry:**
   - Create `~/questionnaire-registry/` directory
   - Initialize git repository
   - Create README.md explaining this is the measure instance registry
   - Create directory structure: `measures/`, `mappings/`

2. **Create measures.json:**
   Create `~/questionnaire-registry/measures.json` with top-level `measures` object containing all ~13 measures:
   - phq_9, gad_7, msi, safe, phlms_10, joy, sleep_disturbances, trauma_exposure, ptsd_screen, ipip_neo_60_c, fscrs, pss_10, dts, cfs

   Use the measure definitions provided, ensuring:
   - All item_prefix values use underscores (phq_9_, gad_7_, etc.)
   - All measures validate against `org.canonical/questionnaire_measure` schema from canonizer-registry
   - Scoring rules are complete and accurate
   - Interpretation ranges are clinically valid

3. **Validate against schema:**
   - Reference canonizer-registry schema for validation
   - Create validation script if needed

**Commands:**

```bash
# Create and initialize repo
mkdir -p ~/questionnaire-registry
cd ~/questionnaire-registry
git init
git remote add origin git@github.com:benthepsychologist/questionnaire-registry.git

# Validate measures against canonizer-registry schema
# (validation logic TBD)
```

**Outputs:**

- `~/questionnaire-registry/` (new git repo)
- `~/questionnaire-registry/README.md`
- `~/questionnaire-registry/measures.json`
- `~/questionnaire-registry/.gitignore`

---

### Step 3: Create Form Mapping Schema & Example Mappings [G0: Plan Approval]

**Objective:** Define form mapping schema in canonizer-registry and create example mapping instances in questionnaire-registry.

**Prompt:**

Create the form mapping schema and example mapping files:

1. **Form Mapping Schema (canonizer-registry):**
   Create `~/canonizer-registry/schemas/org.canonical/form_mapping/jsonschema/1-0-0.json`

   The schema must validate:
   - mapping_id: string (unique identifier)
   - form_provenance: object with platform, form_id, form_name, version
   - target_measure: string (measure ID like "phq_9")
   - item_mappings: array of objects with:
     - form_question_id: string (platform-specific ID)
     - form_question_text: string (question text for reference)
     - canonical_item_id: string (target measure item like "phq_9_1")
     - notes: optional string
   - value_mappings: object with:
     - use_anchor_labels: boolean (use measure anchor labels for recoding)
     - custom_mappings: object (custom value transformations if needed)

2. **Example Mapping Files (questionnaire-registry):**
   Create example mappings in `~/questionnaire-registry/mappings/`:
   - `google_forms/mbc_initial_phq9_v1.json` - PHQ-9 from Google Forms
   - `google_forms/mbc_initial_gad7_v1.json` - GAD-7 from Google Forms
   - At least 2-3 example mappings covering different platforms/measures

**Commands:**

```bash
# Create schema in canonizer-registry
cd ~/canonizer-registry
mkdir -p schemas/org.canonical/form_mapping/jsonschema

# Create mapping instances in questionnaire-registry
cd ~/questionnaire-registry
mkdir -p mappings/google_forms

# Validate mapping files against schema (from canonizer-registry)
# (validation logic TBD)
```

**Outputs:**

- `~/canonizer-registry/schemas/org.canonical/form_mapping/jsonschema/1-0-0.json`
- `~/questionnaire-registry/mappings/google_forms/mbc_initial_phq9_v1.json`
- `~/questionnaire-registry/mappings/google_forms/mbc_initial_gad7_v1.json`
- Additional example mapping files in questionnaire-registry

---

### Step 4: Foundation - Package Structure & Registry Loaders [G1: Code Readiness]

**Objective:** Create final-form package scaffold with registry loading from canonizer-registry.

**Prompt:**

Create the Python package structure for final-form:

Package structure:
- `final_form/__init__.py`
- `final_form/registry/__init__.py` - Registry loader
- `final_form/registry/loader.py` - Load measure registry from canonizer-registry
- `final_form/registry/models.py` - Pydantic models for measure definitions
- `final_form/registry/mapping_loader.py` - Load form mapping files
- `final_form/registry/mapping_models.py` - Pydantic models for mapping definitions
- `final_form/io.py` - JSON/JSONL I/O
- `final_form/cli.py` - CLI skeleton with Typer
- `pyproject.toml` - Dependencies (pydantic, typer, jsonschema)

Registry loader should:
- Load questionnaire measures from questionnaire-registry (measures.json)
- Load form mapping files from questionnaire-registry/mappings/
- Load schemas from canonizer-registry for validation
- Validate measures against questionnaire_measure schema (from canonizer-registry)
- Validate mappings against form_mapping schema (from canonizer-registry)
- Provide lookup by measure ID (e.g., "phq_9")
- Provide lookup by mapping ID or file path

CLI skeleton should accept:
- `--in` input JSONL path
- `--out` output JSONL path
- `--mapping` path to mapping file (required)
- `--questionnaire-registry` path to questionnaire-registry (default: ~/questionnaire-registry)
- `--canonizer-registry` path to canonizer-registry (default: ~/canonizer-registry)
- `--diagnostics` optional diagnostics output path

**Commands:**

```bash
cd ~/final-form
pytest tests/test_registry.py -v
pytest tests/test_io.py -v
ruff check final_form/
```

**Outputs:**

- `final_form/__init__.py`
- `final_form/registry/__init__.py`
- `final_form/registry/loader.py`
- `final_form/registry/models.py`
- `final_form/registry/mapping_loader.py`
- `final_form/registry/mapping_models.py`
- `final_form/io.py`
- `final_form/cli.py`
- `pyproject.toml`
- `tests/test_registry.py`
- `tests/test_mapping_loader.py`
- `tests/test_io.py`

---

### Step 5: Item Mapping & Recoding [G1: Code Readiness]

**Objective:** Implement simple mapper that applies mapping JSON to transform form items.

**Prompt:**

Build a simple mapping engine:

**Mapping logic:**
- Load mapping JSON file
- Load target measure from registry
- For each answer in form:
  - Look up `question_id` in mapping's `item_mappings` array
  - Replace `question_id` with `canonical_item_id`
  - If `question_id` not found in mapping: error (unmapped item)

**Value recoding:**
- If `answer_value` is numeric or numeric-as-string: parse to number, validate range
- If `answer_value` is text: look up in measure's anchor labels, convert to number
- If mapping specifies `custom_mappings`: use those instead of anchor labels
- If value not mappable: error (invalid value)

**That's it.** No fuzzy matching, no fallbacks, no heuristics. Just: load mapping JSON, apply transformations, error if something doesn't map.

**Commands:**

```bash
pytest tests/test_mapper.py -v
ruff check final_form/
```

**Outputs:**

- `final_form/mapping/__init__.py`
- `final_form/mapping/mapper.py`
- `tests/test_mapper.py`
- `tests/fixtures/mapping/google_forms_phq9_input.json`
- `tests/fixtures/mapping/google_forms_phq9_expected.json`

---

### Step 6: Validation & Quality Checks [G1: Code Readiness]

**Objective:** Light validation after mapping (stub for future research-focused cleaning).

**Prompt:**

Simple validation layer (minimal - mapper does the real work):

Validation checks:
- Verify all mapped items are present (no missing required items)
- Verify all numeric values are in valid range (anchor.min to anchor.max)
- Flag null/missing values for diagnostics
- That's it

**Note:** This is a stub. Clinical use doesn't need extensive cleaning/normalization. The mapper handles text→numeric conversion and basic validation. Research teams can extend this step in future versions if needed.

**Commands:**

```bash
pytest tests/test_validation.py -v
ruff check final_form/
```

**Outputs:**

- `final_form/validation/__init__.py`
- `final_form/validation/checks.py`
- `tests/test_validation.py`

---

### Step 7: Generic Scoring Engine [G1: Code Readiness]

**Objective:** Implement the generic scoring engine that interprets registry rules.

**Prompt:**

Build the generic scoring engine:

Core functionality:
- Load measure definition from registry
- Map form items to measure items using item_prefix
- Extract item values by matching question_id or question_text
- Apply reverse scoring for items in reversed_items array
- Compute subscale scores using the method from scoring.method:
  - "sum": sum of item values
  - "average": mean of item values
  - "sum_then_double": sum then multiply by 2
- Validate computed scores are in range (scoring.min to scoring.max)
- Apply interpretation ranges to assign severity labels
- Handle partial responses (missing items):
  - Flag missing items
  - Compute scores if enough items present (configurable threshold)
  - Add missingness metadata

Support multi-subscale measures:
- Compute all subscales defined in measure.scores
- Each subscale can have different included_items and reversed_items
- Each subscale has independent interpretation ranges

The scoring engine should be completely generic - no questionnaire-specific code.

**Commands:**

```bash
pytest tests/test_scoring.py -v --cov=final_form.scoring
pytest tests/fixtures/phq9/test_phq9_scoring.py -v
pytest tests/fixtures/gad7/test_gad7_scoring.py -v
pytest tests/fixtures/phlms10/test_phlms10_scoring.py -v
```

**Outputs:**

- `final_form/scoring/__init__.py`
- `final_form/scoring/engine.py`
- `final_form/scoring/reverse.py`
- `final_form/scoring/methods.py`
- `tests/test_scoring.py`
- `tests/fixtures/phq9/test_phq9_scoring.py`
- `tests/fixtures/gad7/test_gad7_scoring.py`
- `tests/fixtures/phlms10/test_phlms10_scoring.py`
- `tests/fixtures/phq9/valid_responses.json`
- `tests/fixtures/gad7/valid_responses.json`
- `tests/fixtures/phlms10/valid_responses.json`

---

### Step 8: Interpretation & Metadata Layer [G1: Code Readiness]

**Objective:** Add severity interpretation and metadata annotation.

**Prompt:**

Implement the interpretation layer:

Interpretation:
- Apply ranges from measure.scores[subscale].ranges
- Match computed score to appropriate range (min <= score <= max)
- Add severity classification field (minimal, mild, moderate, severe, etc.)
- Add interpretation label and description

Metadata annotation:
- Add provenance fields (final-form version, processing timestamp)
- Add data quality fields:
  - completeness percentage
  - missing_items count and list
  - out_of_range_items count and list
  - invalid_items count and list
- Add scoring metadata:
  - measure_id (e.g., "phq_9")
  - measure_name
  - subscale scores with interpretations
  - scoring_method used

Quality flags:
- "complete": all items present and valid
- "partial": some items missing but score computable
- "invalid": too many missing items or critical errors
- "out_of_range": some values outside valid range

**Commands:**

```bash
pytest tests/test_interpretation.py -v
pytest tests/test_metadata.py -v
```

**Outputs:**

- `final_form/interpretation/__init__.py`
- `final_form/interpretation/ranges.py`
- `final_form/interpretation/metadata.py`
- `tests/test_interpretation.py`
- `tests/test_metadata.py`

---

### Step 9: Output Builders & Diagnostics [G1: Code Readiness]

**Objective:** Build final canonical output structures and diagnostics.

**Prompt:**

Create output emitters:

Canonical output builder:
- Build final `org.canonical/questionnaire_response` object
- Include all original form_response fields
- Add scores object with all subscale scores
- Add interpretations object with severity labels
- Add metadata object with provenance and quality metrics
- Ensure output validates against canonical schema

Diagnostics builder:
- Build diagnostic object for each processed record
- Include errors array (critical issues preventing scoring)
- Include warnings array (non-critical issues)
- Include missingness details (which items, count, percentage)
- Include out-of-range details (which items, values, expected range)
- Include processing metadata (time, measure detected, score computed)

Diagnostic output modes:
- Per-record diagnostics (JSONL parallel to output)
- Aggregate diagnostics (summary JSON with statistics)

**Commands:**

```bash
pytest tests/test_emitters.py tests/test_diagnostics.py -v
```

**Outputs:**

- `final_form/emitters/__init__.py`
- `final_form/emitters/canonical.py`
- `final_form/diagnostics/__init__.py`
- `final_form/diagnostics/models.py`
- `final_form/diagnostics/aggregator.py`
- `tests/test_emitters.py`
- `tests/test_diagnostics.py`

---

### Step 10: CLI Integration & Pipeline Orchestration [G2: Pre-Release]

**Objective:** Connect all components into end-to-end pipeline.

**Prompt:**

Integrate all components into the CLI pipeline:

Pipeline flow:
1. Load measure definitions from questionnaire-registry (measures.json)
2. Load form mapping file (from --mapping argument in questionnaire-registry)
3. Load target measure definition from questionnaire-registry
4. Read JSONL input (form_response records)
5. For each record:
   - Validate against form_response schema
   - **Map & recode:** Apply mapping to transform platform IDs → canonical IDs, values → numeric
   - **Validate:** Check all items present, values in range
   - **Score:** Compute all subscales using generic engine
   - **Interpret:** Apply severity ranges
   - **Emit:** Build canonical questionnaire_response with metadata
   - **Diagnostics:** Capture any issues
6. Write outputs (questionnaire_response JSONL)
7. Write diagnostics (if --diagnostics flag provided)

Error handling:
- Continue processing on per-record errors
- Collect errors in diagnostics
- Log summary statistics at end
- Non-zero exit code if any critical errors

Logging:
- Progress bar for batch processing
- Summary statistics (processed, scored, errors)
- Performance metrics (records/second)

**Commands:**

```bash
pytest tests/test_cli.py -v
pytest tests/integration/test_pipeline.py -v

# Integration test
final-form run \
  --in tests/fixtures/batch/sample.jsonl \
  --out /tmp/output.jsonl \
  --mapping ~/questionnaire-registry/mappings/google_forms/mbc_initial_phq9_v1.json \
  --diagnostics /tmp/diag.jsonl \
  --questionnaire-registry ~/questionnaire-registry \
  --canonizer-registry ~/canonizer-registry
```

**Outputs:**

- `final_form/cli/run.py`
- `final_form/pipeline/__init__.py`
- `final_form/pipeline/orchestrator.py`
- `tests/test_cli.py`
- `tests/integration/test_pipeline.py`
- `tests/fixtures/batch/sample.jsonl`
- `tests/fixtures/batch/sample_mapping.json`

---

### Step 11: Golden Tests & Comprehensive Test Suite [G2: Pre-Release]

**Objective:** Build comprehensive test coverage with golden outputs.

**Prompt:**

Build comprehensive test suite:

Golden test cases (per measure):
- Valid complete responses (all items present, valid values)
- Text anchor responses (need normalization)
- Partial responses (some items missing)
- Out-of-range values (negative, exceeds max)
- Edge cases (all minimum values, all maximum values)
- Mixed valid/invalid items

Multi-measure tests:
- PHQ-9 (single subscale)
- GAD-7 (single subscale)
- PHLMS-10 (two subscales: awareness, acceptance)
- FSCRS (four subscales: inadequacy, self_hatred, self_reassurance, self_criticism)
- IPIP-NEO-60-C (seven subscales)

Integration tests:
- Real canonizer output → final-form pipeline
- Batch processing with mixed measures
- Error recovery and diagnostics

Golden outputs:
- Store expected outputs for each test case
- Assert exact match (determinism check)
- Version golden outputs with schema version

Coverage targets:
- Overall: 80%+
- Scoring engine: 95%+
- Registry loader: 90%+
- Pipeline orchestrator: 85%+

**Commands:**

```bash
pytest tests/ -v --cov=final_form --cov-report=term-missing --cov-report=html
pytest tests/integration/ -v
pytest tests/golden/ -v

# Verify determinism
for i in {1..5}; do
  final-form run --in tests/fixtures/batch/sample.jsonl --out /tmp/run_$i.jsonl
done
diff /tmp/run_1.jsonl /tmp/run_2.jsonl  # Should be identical
```

**Outputs:**

- `tests/fixtures/phq9/valid_complete.json`
- `tests/fixtures/phq9/text_anchors.json`
- `tests/fixtures/phq9/partial_missing.json`
- `tests/fixtures/phq9/out_of_range.json`
- `tests/fixtures/gad7/` (similar structure)
- `tests/fixtures/phlms10/` (similar structure)
- `tests/fixtures/fscrs/` (similar structure)
- `tests/golden/phq9/` (expected outputs)
- `tests/golden/gad7/` (expected outputs)
- `tests/golden/phlms10/` (expected outputs)
- `tests/integration/test_canonizer_integration.py`
- `tests/golden/test_determinism.py`
- `.github/workflows/ci.yml` (CI configuration)

---

### Step 12: Documentation & Release Preparation [G4: Post-Implementation]

**Objective:** Document architecture, usage, and create release artifacts.

**Prompt:**

Prepare v0.1.0 release:

README:
- Installation instructions
- Quick start examples
- CLI usage
- Architecture overview (link to FINAL-FORM-ARCH.md)

CLI Documentation:
- All commands and flags
- Examples for common use cases
- Auto-detection behavior
- Error handling guide
- Diagnostics interpretation

API Documentation:
- Registry loader API
- Scoring engine API
- Pipeline orchestration API
- Usage in Python scripts/notebooks

Release notes:
- Features implemented
- Measures supported (list all ~13)
- Breaking changes (none for v0.1.0)
- Known limitations
- Future roadmap

Version tagging:
- Update version to 0.1.0 in pyproject.toml
- Create git tag v0.1.0
- Generate changelog

**Commands:**

```bash
# Build package
python -m build

# Verify package
twine check dist/*

# Tag release
git tag -a v0.1.0 -m "Release v0.1.0: Questionnaire Semantic Processing Engine"
```

**Outputs:**

- `README.md`
- `docs/CLI.md`
- `docs/API.md`
- `docs/REGISTRY.md` (registry format documentation)
- `CHANGELOG.md`
- `pyproject.toml` (version updated to 0.1.0)

---

## Models & Tools

**Tools:**
- Python 3.11+
- pytest (testing framework)
- pytest-cov (coverage reporting)
- ruff (linting)
- mypy (type checking)
- typer (CLI framework)
- pydantic >= 2.0 (data validation)
- jsonschema (schema validation)

**Package Dependencies:**
- typer
- pydantic >= 2.0
- jsonschema
- rich (CLI formatting)

**Development Tools:**
- pytest
- pytest-cov
- ruff
- mypy
- black (formatting)

**External Dependencies:**
- canonizer-registry (schema and measure definitions source)

## Repository

**Branch:** `feat/final-form-v0.1.0`

**Merge Strategy:** squash

## Success Criteria

This implementation is successful when:
1. A researcher can run `final-form run --in canonical.jsonl --out final.jsonl` and get deterministic, scored, interpreted outputs for all ~13 measures
2. All golden tests pass with 100% accuracy
3. The same input always produces the same output (determinism verified by repeated runs)
4. Outputs validate against canonical questionnaire_response schema
5. Diagnostics clearly explain any failures or data quality issues
6. The scoring engine is completely generic - no per-questionnaire code exists
7. The registry is the single source of truth - changing scoring rules only requires updating the registry
8. The package can run standalone without the full pipeline stack
9. Test coverage >= 80% overall, 95%+ for scoring engine
10. Zero regressions in CI
11. Documentation is clear and complete

## Future Versions

- **v0.2:** Additional measures, enhanced missingness metrics, subscale validation
- **v0.3:** Measurement event emitter, longitudinal tracking
- **v0.4:** Advanced scoring methods (weighted sums, polynomial transformations)
- **v1.0:** Stable API, SDK wrappers (pandas, arrow integration)
- **v2.0:** Research façade (batch scoring, embeddings integration)
- **v3.0:** Cross-domain expansion (labs, vitals, wearables)
