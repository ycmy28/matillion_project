# GCTS Append Historization Adjustment Plan

## Purpose

This note revisits the current GCTS recommendation based on the latest direction from the tech lead:

- do not create new history tables
- keep using the existing `T_GCTS_*` stage tables
- change staging behavior to append and retain history
- adjust downstream jobs so Presentation behavior stays controlled

This document is based on:

- `gcts_full.json`
- `ticket_requirement.txt`
- `gcts_pipeline_assessment.md`
- `gcts_recommended_implementation_sequence.md`

## Short Recommendation

Given the current Matillion pipeline design, the cleanest way to support the tech lead's direction is:

1. keep `T_GCTS_RESPONSE`, `T_GCTS_OPTIONS`, `T_GCTS_QUESTION_MAP`, and `T_GCTS_COUNTRY_CATEGORY` as the only GCTS stage tables
2. stop sending GCTS through the shared delete/update stage-sync behavior
3. append new rows from `T_LOAD_GCTS_*` into `T_GCTS_*`
4. move current/latest selection logic into the 3 target integration jobs:
   - `trn_v_int_dim_gcts_question`
   - `trn_v_int_dim_gcts_option`
   - `trn_v_int_fact_gcts_response`

My recommendation is to bypass the shared `orc_load_stage_objects -> orc_run_group_calc -> orc_update_indicator` path for GCTS, instead of modifying that shared framework unless your team explicitly wants a reusable GCTS-specific mode inside it.

## Why This Is The Best Fit For The Current Pipeline

In the current export:

- `orc_ingestion_gcts` runs:
  - `orc_ingestion_s3_main - Response table`
  - `orc_ingestion_s3_main_v2 - Other than Response table`
  - `orc_load_stage_objects 0`
- `orc_load_stage_objects` calls `orc_run_group_calc`
- `orc_run_group_calc` calls `orc_update_indicator`
- `orc_update_indicator` contains:
  - `Delete records from Stage table`
  - `Create queries to delete and insert records`
  - `Check track changes`
  - `tmpt_trn_create_history_table`

That shared path is built for synchronized stage maintenance, not simple append historization.

If you keep GCTS in that path, you will be fighting the framework.

## What Should Change

## 1. `orc_ingestion_gcts`

### Change

Adjust this job so GCTS no longer depends on `orc_load_stage_objects 0` for populating `T_GCTS_*`.

### Current behavior

After S3 ingestion finishes, `orc_ingestion_gcts` passes GCTS load data into the shared stage-sync framework.

### Suggested new behavior

After:

- `orc_ingestion_s3_main - Response table`
- `orc_ingestion_s3_main_v2 - Other than Response table`

run a GCTS-specific append step that inserts from load tables into stage tables.

### Recommendation

Replace the GCTS use of:

- `orc_load_stage_objects 0`

with either:

- a new GCTS-specific orchestration job, for example `orc_append_stage_gcts`

or:

- a small set of direct SQL / transformation append steps inside `orc_ingestion_gcts`

The new job should do only append insertion, not delete/update reconciliation.

## 2. Shared stage-sync path

### Remove or bypass for GCTS

For GCTS only, stop using:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

### Why

Those jobs are the source of the current delete/update behavior.

### Strong suggestion

Do not change the shared logic globally unless there is already an accepted pattern for source-specific branching.

For this request, bypass is safer than refactoring a shared template job that other pipelines probably still depend on.

## 3. `orc_update_indicator`

### No longer needed for GCTS append historization

The following components represent logic that conflicts with append-only staging:

- `Delete records from Stage table`
- `Create queries to delete and insert records`
- `Check track changes`
- `tmpt_trn_create_history_table`

### Suggestion

Leave them unchanged for other pipelines, but do not call this job from GCTS anymore.

## 4. Disabled initial-load path in `orc_ingestion_gcts`

### Components

- `trn_load_gcts_from_do`
- `Get the list of source files`
- `Load Stage Layer - Node`

### Suggestion

No change is required for normal implementation.

They are already disabled and marked as special initial-load behavior. I would keep them disabled unless the team separately decides to redesign the one-time backfill process.

## How To Make The Insertion Appending

## Recommended pattern

Append from `STG_LOAD_GCTS.T_LOAD_GCTS_*` into `STG_GCTS.T_GCTS_*`.

That means the GCTS stage tables become the retained history tables.

## Practical Matillion approach

Create one append step per table after the S3 load completes:

- `T_LOAD_GCTS_RESPONSE` -> `T_GCTS_RESPONSE`
- `T_LOAD_GCTS_OPTIONS` -> `T_GCTS_OPTIONS`
- `T_LOAD_GCTS_QUESTION_MAP` -> `T_GCTS_QUESTION_MAP`
- `T_LOAD_GCTS_COUNTRY_CATEGORY` -> `T_GCTS_COUNTRY_CATEGORY`

The exact `T_LOAD_GCTS_*` names for non-response tables are inferred from the response pattern and should be confirmed in the environment.

## Append SQL shape

Use plain insert-select behavior:

```sql
insert into STG_GCTS.T_GCTS_QUESTION_MAP
(
  COUNTRYCATEGORYID,
  VARIABLEID,
  QUESTIONCODE,
  TOPLEVELFIELD,
  FIRSTLEVELITERATOR,
  FIRSTLEVELFLD,
  FIRSTLEVELLABEL,
  SECONDLEVELITERATOR,
  SECONDLEVELFLD,
  SECONDLEVELLABEL,
  DATAPATTERN,
  CREATEDDATE,
  _ETL_LOAD_DATETIME,
  _ETL_LOAD_FILE_NAME
)
select
  COUNTRYCATEGORYID,
  VARIABLEID,
  QUESTIONCODE,
  TOPLEVELFIELD,
  FIRSTLEVELITERATOR,
  FIRSTLEVELFLD,
  FIRSTLEVELLABEL,
  SECONDLEVELITERATOR,
  SECONDLEVELFLD,
  SECONDLEVELLABEL,
  DATAPATTERN,
  CREATEDDATE,
  _ETL_LOAD_DATETIME,
  _ETL_LOAD_FILE_NAME
from STG_LOAD_GCTS.T_LOAD_GCTS_QUESTION_MAP;
```

Apply the same pattern for options, country category, and response.

## Metadata guidance

For append historization, the important control columns are:

- `_ETL_LOAD_DATETIME`
- `_ETL_LOAD_FILE_NAME` or equivalent file identifier

`_ETL_ACTIVE_FLAG` should no longer be treated as the main control mechanism for GCTS if old rows are never being inactivated by the stage-sync framework.

My suggestion:

- keep the column if it already exists and is needed for compatibility
- stop relying on it for GCTS business selection logic
- use `_ETL_LOAD_DATETIME` as the authoritative load-version selector

## What Should Be Adjusted Downstream

## 1. `trn_v_int_dim_gcts_question`

### What I found

This job already does the right pattern structurally:

- source: `T_GCTS_QUESTION_MAP`
- computes `ROW_NUMBER()`
- partitions by `DIM_GCTS_QUESTION_MAP_KEY`
- orders by `_ETL_LOAD_DATETIME desc`
- filters `RN = 1`

### Impact

This job is already fairly close to append-history-ready.

### Suggested adjustment

Keep the current row-number logic, but confirm the business rule:

- latest per generated key

not:

- one global max load for the whole table

The current Matillion implementation is per key, which is usually safer than a table-wide `MAX(_ETL_LOAD_DATETIME)` filter.

### Optional cleanup

Document explicitly in the job note that this transformation is now the official current-state selector for question data.

## 2. `trn_v_int_dim_gcts_option`

### What I found

This job currently reads from `T_GCTS_OPTIONS` but does not apply latest-load filtering.

Visible components are:

- `V_GCTS_OPTIONS`
- `Generate DIM_GCTS_OPTIONS_KEY`
- `Reorder columns`
- `Filter all Nulls`

There is no row-number or max-load filter here today.

### Required adjustment

Add the same type of latest-record selection used in question:

- derive business key `DIM_GCTS_OPTION_KEY`
- apply `ROW_NUMBER() over (partition by DIM_GCTS_OPTION_KEY order by _ETL_LOAD_DATETIME desc)`
- filter `RN = 1`

### Why

Because options are full-file pushes, append history in `T_GCTS_OPTIONS` will create multiple versions for the same option key across loads.

Without this adjustment, Presentation-facing option output can duplicate or drift.

## 3. `trn_v_int_fact_gcts_response`

### What I found

This job currently reads directly from `T_GCTS_RESPONSE` and joins to:

- `DIM_GCTS_QUESTION`
- `DIM_GCTS_OPTION`
- country / market lookups

There is no visible load-version control on response today.

### Required adjustment

Implement the ticket rule here:

1. group by:
   - `YEAR`
   - `MONTH`
   - `COUNTRYCATEGORYID`
2. get `MAX(_ETL_LOAD_DATETIME)` for each group
3. if group max is before `2026-04-01`, keep all rows for that group
4. if group max is on or after `2026-04-01`, keep only rows from that max load
5. union both sets

### Why this is the right place

Once staging becomes append-only, response history will accumulate by design. The mixed old/new handling belongs in the fact transformation, not in staging.

## 4. `orc_unit_test_gcts`

### Suggested adjustment

Update unit tests so they validate the new contract:

- stage row counts increase after new loads
- stage history is retained
- question output keeps one current row per question key
- option output keeps one current row per option key
- response output follows the `2026-04-01` split rule

## Suggested Step Approach

## Phase 1. Baseline

Capture before-change counts for:

- `T_GCTS_RESPONSE`
- `T_GCTS_OPTIONS`
- `T_GCTS_QUESTION_MAP`
- `T_GCTS_COUNTRY_CATEGORY`
- `V_INT_DIM_GCTS_QUESTION`
- `V_INT_DIM_GCTS_OPTION`
- `V_INT_FACT_GCTS_RESPONSE`

Also capture counts by `_ETL_LOAD_DATETIME`.

## Phase 2. Build append-only staging path

In `orc_ingestion_gcts`:

1. keep the S3 ingestion steps as they are
2. remove GCTS dependency on `orc_load_stage_objects 0`
3. add GCTS append steps from `T_LOAD_GCTS_*` to `T_GCTS_*`

## Phase 3. Validate staging only

Run one controlled batch and confirm:

- old stage data remains
- new rows are appended
- no delete/update behavior happens in `T_GCTS_*`

## Phase 4. Adjust integration jobs

Implement:

1. keep `trn_v_int_dim_gcts_question` latest-per-key behavior
2. add latest-per-key behavior to `trn_v_int_dim_gcts_option`
3. add mixed historical/current selection logic to `trn_v_int_fact_gcts_response`

## Phase 5. Re-test presentation outputs

Compare row counts and sample business slices against the baseline.

The goal is:

- staging history changes
- Presentation business behavior stays intentional

## Phase 6. Clean handoff notes

Document clearly that for GCTS:

- `T_GCTS_*` now means historical retained stage
- current-state selection happens in integration
- `_ETL_LOAD_DATETIME` is the main selector

## What I Would Not Recommend

I would not recommend these as the first choice:

- changing all shared delete/update template behavior globally
- relying on `_ETL_ACTIVE_FLAG` as the main history selector after append-only staging
- leaving `trn_v_int_dim_gcts_option` unchanged after append historization
- putting response mixed-era filtering into staging

## Final Suggested Delivery Decision

If the team wants the smallest-risk implementation that still follows the tech lead's direction, I would proceed like this:

1. keep existing `T_GCTS_*` tables
2. bypass `orc_load_stage_objects` for GCTS
3. append from `T_LOAD_GCTS_*` into `T_GCTS_*`
4. use `_ETL_LOAD_DATETIME` as the history control column
5. adjust `question`, `option`, and `response` integration logic to expose the right current/business slice

That gives you append historization without creating new tables, and it keeps the scope localized to the real GCTS touchpoints in the current Matillion pipeline.
