# GCTS Recommended Implementation Sequence

## Purpose

This document turns the current GCTS assessment into a practical delivery sequence for the team.

It is designed for the specific goal of:

- keeping historical Kantar data in staging
- stopping GCTS staging deletion behavior
- preserving Presentation Layer results as much as possible
- updating the 3 targeted transformations safely

This should be read together with:

- `gcts_pipeline_assessment.md`
- `gcts_staging_history_prerequisites.md`
- `ticket_requirement.txt`
- `GCTS Data Model/Full Physical Report.html`

## Jira Context

This implementation sequence is intended to support:

- `DODECOM-7399` - Assess GCTS pipeline

and prepare the next change tickets:

- `DODECOM-7400` - Adjust `trn_v_int_dim_gcts_question`
- `DODECOM-7401` - Adjust `trn_v_int_dim_gcts_option`
- `DODECOM-7402` - Adjust `trn_v_int_fact_gcts_response`

The parent business objective from `DODECOM-7398` is:

- keep historical GCTS data from Kantar available
- stop deletion activity in staging
- keep Presentation Layer behavior as stable as possible

## Extra Source Context

Besides the Matillion export, this delivery sequence is informed by:

### 1. Jira requirement text

The supplied ticket text adds these operational assumptions:

- Kantar pushes 4 GCTS tables:
  - Responses
  - Options
  - Question Map
  - Country Category
- each push cycle should contain 1 file per table
- there may be multiple push cycles in one month
- source data behavior is described as:
  - Responses = Delta
  - Options = Full
  - Question Map = Full
- the Country Category availability-type line appears incomplete in the provided text and should be reconfirmed

### 2. Data model report

The latest PowerDesigner report shows that the original modeled downstream design was built around:

- active/current stage views such as `V_GCTS_OPTIONS`, `V_GCTS_QUESTION_MAP`, and `V_GCTS_RESPONSE`
- `_ETL_ACTIVE_FLAG=true` usage in documented source SQL
- the same key-generation patterns currently implemented in Matillion

This matters because the implementation sequence is not just about adding latest-load filters. It is about shifting from an old active-view staging model toward retained stage history without breaking downstream expectations.

## Scope

Primary target jobs:

- `orc_ingestion_gcts`
- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`
- `orc_unit_test_gcts`

Shared framework area to assess carefully:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

## Delivery Principle

The safest way to deliver this change is:

1. define the new staging behavior first
2. prepare transformation logic that preserves downstream behavior intentionally
3. validate with baseline comparisons
4. release ingestion and transformation changes as one controlled package

The team should avoid:

- changing only ingestion first
- or changing only the 3 transformations first

because either approach can create a temporary mismatch between stage meaning and downstream logic.

## What This Sequence Is Solving

This plan is specifically designed to resolve the gap identified in the assessment:

- the current pipeline was built around active/current stage consumption
- the requested business change wants historical stage retention
- the downstream dims/fact must still present the intended current or mixed-era result set

So this sequence assumes the team must manage both:

- upstream staging behavior
- downstream visibility logic

## Recommended Phases

## Phase 1. Confirm Design Decisions

### Goal

Lock the business and technical rules before editing jobs.

### Required decisions

1. Confirm the new GCTS staging contract:
   - append-only
   - or append-with-active-flag
2. Confirm whether `_ETL_ACTIVE_FLAG` will still be meaningful after history retention is enabled.
3. Confirm whether `_ETL_LOAD_DATETIME` is the official selector for:
   - latest question data
   - latest option data
   - response cutoff behavior
4. Confirm question rule precisely:
   - latest global batch
   - or latest per business key
5. Confirm fact cutoff interpretation:
   - `< '2026-04-01'`
   - `>= '2026-04-01'`
6. Confirm whether the old active-view logic should remain available through stage views, or whether the 3 target transformations will become the main place where current/latest visibility is enforced.
6. Confirm whether the inactive initial-load path will remain excluded:
   - `trn_load_gcts_from_do`
   - `Get the list of source files`
   - `Load Stage Layer - Node`

### Deliverable

A short signed-off rules summary before development starts.

## Phase 2. Baseline Capture

### Goal

Capture the current behavior before changing anything.

### Capture these baselines

#### Staging

- row counts for:
  - `T_GCTS_QUESTION_MAP`
  - `T_GCTS_OPTIONS`
  - `T_GCTS_COUNTRY_CATEGORY`
  - `T_GCTS_RESPONSE`
- counts by `_ETL_LOAD_DATETIME`
- counts by `_ETL_ACTIVE_FLAG`
- counts of duplicate business keys across multiple loads

#### Integration

- current row counts for:
  - `V_INT_DIM_GCTS_QUESTION`
  - `V_INT_DIM_GCTS_OPTION`
  - `V_INT_FACT_GCTS_RESPONSE`

#### Presentation

- current row counts for:
  - `DIM_GCTS_QUESTION`
  - `DIM_GCTS_OPTION`
  - `FACT_GCTS_RESPONSE`
- duplicate-key checks
- sample reconciliation extracts for known business slices

#### Fact-specific

- counts by:
  - `YEAR`
  - `MONTH`
  - `COUNTRYCATEGORYID`
  - `_ETL_LOAD_DATETIME`
- number of groups with multiple loads before `2026-04-01`
- number of groups with multiple loads on or after `2026-04-01`

### Deliverable

A baseline evidence pack that can be compared after the change.

## Phase 3. Ingestion / Staging Design Adjustment

### Goal

Define how GCTS keeps history in stage without continuing the old delete behavior.

### Main work

Inspect how `orc_ingestion_gcts` passes data into:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

### Decision options

#### Option A. Bypass delete/update framework for GCTS

This is the cleanest option if GCTS no longer wants current-state stage behavior.

Use this if:

- the framework is primarily for delete/update synchronization
- GCTS now wants retained stage history

#### Option B. Add GCTS-specific conditional behavior in the framework

Use this if:

- the framework must remain shared
- bypassing it would be too disruptive
- GCTS needs a special mode such as:
  - no delete
  - no indicator update
  - append-only

### Recommended direction

Prefer the smallest change that isolates GCTS from stage deletion behavior without breaking the shared framework for other pipelines.

### Validation target

After this change, new loads should preserve historical rows in staging instead of deleting or superseding them physically.

At the same time, the downstream pipeline must still be able to expose the correct consumer-facing current/latest result.

## Phase 4. Prepare Transformation Redesign

### Goal

Make integration responsible for controlling what remains visible downstream.

### Job 1. `trn_v_int_dim_gcts_question`

Current state:

- already uses `ROW_NUMBER()`
- already uses `_ETL_LOAD_DATETIME DESC`
- already keeps one row per generated key

Required action:

- confirm whether current per-key latest logic already satisfies the business rule
- if not, adjust it to the approved rule

Possible outcomes:

- no logic change needed, only validation
- small key-grain adjustment needed
- global latest-batch filter needed

### Job 2. `trn_v_int_dim_gcts_option`

Current state:

- no visible latest-load filtering

Required action:

- add latest-load logic explicitly

Recommended pattern:

- use `_ETL_LOAD_DATETIME`
- apply either:
  - latest global batch
  - or latest per approved business grain

This is especially important because the Jira requirement explicitly asks for `MAX(_ETL_LOAD_DATETIME)`-based filtering for this dimension.

### Job 3. `trn_v_int_fact_gcts_response`

Current state:

- no visible cutoff logic
- no visible `_ETL_LOAD_DATETIME` branch

Required action:

- implement two-branch logic:
  - historical branch for groups with `MAX(_ETL_LOAD_DATETIME) < '2026-04-01'`
  - latest-only branch for groups with `MAX(_ETL_LOAD_DATETIME) >= '2026-04-01'`
- combine results with `UNION ALL`

This directly reflects the Jira rule for `DODECOM-7402`, and should be validated against the Kantar delivery pattern where Responses are described as delta data and monthly combinations may receive more than one push cycle.

### Important design rule

Do not redesign the PL load wrappers if it can be avoided.

Keep:

- `orc_harmonization_pipeline_gcts`
- publish/load components for PL

as stable as possible.

## Phase 5. Unit Test Redesign

### Goal

Make validation match the new intended behavior.

### Why this is needed

Current `orc_unit_test_gcts` compares active stage counts to PL counts.

That assumption may no longer hold once staging retains historical data.

### Required changes

Update tests so they validate:

- question output follows approved latest rule
- option output follows approved latest rule
- fact output follows the cutoff rule
- PL counts match expected integration results, not raw retained stage counts

### Suggested test categories

1. Count parity between integration output and PL target
2. Duplicate-key check in PL
3. Latest-load check for question
4. Latest-load check for option
5. Cutoff-logic check for fact

## Phase 6. Lower-Environment Implementation

### Goal

Deploy the full package safely in non-production first.

### Recommended implementation order

1. update ingestion / stage-retention behavior
2. update `trn_v_int_dim_gcts_question` if needed
3. update `trn_v_int_dim_gcts_option`
4. update `trn_v_int_fact_gcts_response`
5. update `orc_unit_test_gcts`
6. run end-to-end lower-environment test

### Why this order

- stage behavior must reflect the new future reality
- integration logic should then be tested against that new reality
- tests should be updated before final signoff

## Phase 7. Validation And Signoff

### Goal

Prove that the change preserves intended PL behavior while keeping historical stage data.

### Required validation

#### Staging validation

- historical rows remain present after a new load
- no unintended stage delete behavior occurs
- metadata fields remain populated correctly

#### Integration validation

- question result matches approved latest rule
- option result matches approved latest rule
- fact result matches approved cutoff rule

#### Presentation validation

- no unexpected drift in:
  - row counts
  - duplicate rates
  - key coverage
- known sample business slices still reconcile

### Business validation

Review sample outputs with stakeholders for:

- old-period response behavior
- new-period response behavior
- question / option dimensional correctness

## Phase 8. Production Release

### Goal

Deploy with low regression risk.

### Recommended release package

Release these together:

- ingestion/staging change
- 3 transformation changes
- unit-test update

Avoid splitting these into separate releases unless there is a very strong operational reason.

## Rollback Strategy

### Goal

Make sure the team can recover if outputs drift unexpectedly.

### Minimum rollback preparation

Before release:

1. snapshot existing job definitions
2. keep baseline count evidence
3. record current unit-test outputs
4. identify whether any post-release backfill would be needed

### Rollback approach

If results are wrong after release:

1. revert transformation logic to prior version
2. revert ingestion/staging behavior to prior version if required
3. rebuild affected integration and presentation objects
4. compare back to baseline counts

## Suggested Team Task Breakdown

### Data / business owner

- approve latest-load definition
- approve cutoff rule interpretation
- approve expected PL behavior

### Matillion engineer

- adjust ingestion orchestration behavior
- update the 3 transformation jobs
- update unit tests

### QA / analyst

- capture baseline
- compare before/after counts
- validate sample business outputs

## Short Implementation Checklist

If the team wants the shortest possible actionable checklist, use this:

1. Freeze business rules and staging contract.
2. Capture baseline counts in stage, integration, and presentation.
3. Disable or bypass GCTS stage delete behavior.
4. Confirm the exact latest-rule for question.
5. Implement latest-rule for option.
6. Implement cutoff-rule for fact.
7. Update unit tests to target integration/PL expectations, not raw stage counts.
8. Validate end-to-end in lower environment.
9. Release ingestion + transformations + tests together.

## Final Recommendation

Treat this as one coordinated GCTS behavior change, not three isolated transformation edits.

The best chance of preserving Presentation Layer output while keeping history in stage is:

- stabilize the ingestion contract first
- push visibility rules into integration
- validate with baseline comparisons
- release the package together

In other words, the implementation sequence should follow the business-ticket order logically, but not literally:

- assess and define staging behavior first
- then implement the dim/fact adjustments with that staging contract in mind
