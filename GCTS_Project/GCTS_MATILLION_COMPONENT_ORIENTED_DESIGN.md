# GCTS Matillion Component-Oriented Design

## Purpose

This document translates the requested GCTS transformation changes into a Matillion component-oriented design for these 3 objects:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

The goal is to describe how the adjustment can be implemented in Matillion transformation jobs, not just in SQL.

## Scope Of Requested Adjustment

### 1. `trn_v_int_dim_gcts_question`

Requirement:

- source from `T_GCTS_QUESTION_MAP`
- only keep data from the latest `_ETL_LOAD_DATETIME`

### 2. `trn_v_int_dim_gcts_option`

Requirement:

- source from the GCTS option source table
- only keep data from the latest `_ETL_LOAD_DATETIME`

### 3. `trn_v_int_fact_gcts_response`

Requirement:

- source from `T_GCTS_RESPONSE`
- for each `YEAR, MONTH, COUNTRYCATEGORYID`:
  - if `MAX(_ETL_LOAD_DATETIME) < '2026-04-01'`, keep all rows
  - if `MAX(_ETL_LOAD_DATETIME) >= '2026-04-01'`, keep only rows from the latest `_ETL_LOAD_DATETIME`
- union both result sets

## Important Limitation

This is a design draft, because the local export does not contain the actual component graphs of the three transformation jobs.

So the safest design principle is:

- change as little of the downstream mapping as possible
- insert the new filtering logic near the source side of each transformation
- leave existing downstream calculators, joins, renames, and target-output components unchanged where possible

## General Design Strategy

For all 3 jobs, the preferred approach is:

1. keep the current target/output portion of the transformation as-is
2. adjust only the source acquisition part
3. create a filtered source dataset first
4. feed that filtered dataset into the existing downstream transformation flow

This minimizes regression risk.

---

## Design For `trn_v_int_dim_gcts_question`

## Business Intent

The dimension should only expose records from the latest batch in `T_GCTS_QUESTION_MAP`.

## Recommended Matillion Design

### Option A. Preferred: Single `Table Input` With CTE

This is the simplest and lowest-risk design if the current transformation already starts from a SQL-based input.

### Component Flow

```text
Table Input
  -> Existing downstream components
  -> Target / Create View / Rewrite Table
```

### `Table Input` SQL Draft

```sql
WITH latest_load AS (
    SELECT MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime
    FROM T_GCTS_QUESTION_MAP
)
SELECT
    src.*
FROM T_GCTS_QUESTION_MAP src
INNER JOIN latest_load l
    ON src._ETL_LOAD_DATETIME = l.max_etl_load_datetime
```

### Why This Is Preferred

- minimal component changes
- easy to read
- easy to test
- existing downstream logic can remain unchanged

## Option B. Pure Component Style

Use this if the team prefers visual components over SQL-heavy `Table Input`.

### Component Flow

```text
Table Input - Question Source
Aggregate - Get Max Load Datetime
Join - Keep Only Latest Load
Select / Rename
Existing downstream components
Target
```

### Component Details

#### 1. `Table Input - Question Source`

Source:

- `T_GCTS_QUESTION_MAP`

Columns:

- all columns currently used by the transformation
- must include `_ETL_LOAD_DATETIME`

#### 2. `Aggregate - Get Max Load Datetime`

Input:

- from `Table Input - Question Source`

Configuration:

- no group-by columns
- aggregation:
  - `MAX(_ETL_LOAD_DATETIME)` as `MAX_ETL_LOAD_DATETIME`

Result:

- one-row dataset containing latest load timestamp

#### 3. `Join - Keep Only Latest Load`

Join type:

- inner join

Join condition:

- `QuestionSource._ETL_LOAD_DATETIME = MaxLoad.MAX_ETL_LOAD_DATETIME`

Result:

- only rows from latest load survive

#### 4. `Select / Rename`

Purpose:

- keep only required columns
- preserve existing names expected by downstream logic

#### 5. Existing downstream components

Keep unchanged if possible:

- calculators
- filters
- joins to lookups
- output components

## Best Recommendation For Question

Use `Option A` unless the existing transformation is already strongly component-driven and hard to refactor around a SQL input.

---

## Design For `trn_v_int_dim_gcts_option`

## Business Intent

The option dimension should only expose rows from the latest batch of the option source table.

## Recommended Matillion Design

The design is almost identical to question.

## Option A. Preferred: Single `Table Input` With CTE

### Component Flow

```text
Table Input
  -> Existing downstream components
  -> Target / Create View / Rewrite Table
```

### `Table Input` SQL Draft

```sql
WITH latest_load AS (
    SELECT MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime
    FROM T_GCTS_OPTION
)
SELECT
    src.*
FROM T_GCTS_OPTION src
INNER JOIN latest_load l
    ON src._ETL_LOAD_DATETIME = l.max_etl_load_datetime
```

## Option B. Pure Component Style

### Component Flow

```text
Table Input - Option Source
Aggregate - Get Max Load Datetime
Join - Keep Only Latest Load
Select / Rename
Existing downstream components
Target
```

### Component Details

#### 1. `Table Input - Option Source`

Source:

- real GCTS option source table

Must include:

- all used business columns
- `_ETL_LOAD_DATETIME`

#### 2. `Aggregate - Get Max Load Datetime`

Configuration:

- no group-by
- `MAX(_ETL_LOAD_DATETIME)` as `MAX_ETL_LOAD_DATETIME`

#### 3. `Join - Keep Only Latest Load`

Join type:

- inner join

Join condition:

- `OptionSource._ETL_LOAD_DATETIME = MaxLoad.MAX_ETL_LOAD_DATETIME`

#### 4. `Select / Rename`

Purpose:

- preserve required output schema

## Best Recommendation For Option

Implement using the same design pattern as question so both dimensions remain consistent and easy to support.

---

## Design For `trn_v_int_fact_gcts_response`

## Business Intent

The fact requires a split-rule design:

- old groups keep all rows
- new groups keep only latest batch rows

This is more complex than question and option, so the design should be explicit and readable.

## Preferred Design: CTE-Based `Table Input`

This is the cleanest option for maintainability.

### Component Flow

```text
Table Input - Response Source With Cutover Logic
  -> Existing downstream components
  -> Target / Create View / Rewrite Table
```

### `Table Input` SQL Draft

```sql
WITH response_group_max AS (
    SELECT
        YEAR,
        MONTH,
        COUNTRYCATEGORYID,
        MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime
    FROM T_GCTS_RESPONSE
    GROUP BY
        YEAR,
        MONTH,
        COUNTRYCATEGORYID
),
old_logic AS (
    SELECT
        r.*
    FROM T_GCTS_RESPONSE r
    INNER JOIN response_group_max g
        ON r.YEAR = g.YEAR
       AND r.MONTH = g.MONTH
       AND r.COUNTRYCATEGORYID = g.COUNTRYCATEGORYID
    WHERE g.max_etl_load_datetime < TO_TIMESTAMP_NTZ('2026-04-01')
),
new_logic AS (
    SELECT
        r.*
    FROM T_GCTS_RESPONSE r
    INNER JOIN response_group_max g
        ON r.YEAR = g.YEAR
       AND r.MONTH = g.MONTH
       AND r.COUNTRYCATEGORYID = g.COUNTRYCATEGORYID
       AND r._ETL_LOAD_DATETIME = g.max_etl_load_datetime
    WHERE g.max_etl_load_datetime >= TO_TIMESTAMP_NTZ('2026-04-01')
)
SELECT * FROM old_logic
UNION ALL
SELECT * FROM new_logic
```

## Why This Is Preferred

- the rule is readable in one place
- branch logic is explicit
- easy to compare against business wording
- easier to test than a large visual-only branching flow

## Alternative: Visual Branch Design In Components

If the team wants the cutover logic visually represented in Matillion components, use the following branch structure.

### Component Flow

```text
Table Input - Response Source
  -> Aggregate - Max Load Per Group
  -> Join - Response With Group Max
      -> Filter - Old Groups
      -> Filter - New Groups
           -> Filter / Join - Keep Only Latest Load Rows
  -> Union All
  -> Existing downstream components
  -> Target
```

## Component Design In Detail

### 1. `Table Input - Response Source`

Source:

- `T_GCTS_RESPONSE`

Must include:

- all columns used by downstream transformation
- `YEAR`
- `MONTH`
- `COUNTRYCATEGORYID`
- `_ETL_LOAD_DATETIME`

### 2. `Aggregate - Max Load Per Group`

Input:

- `Table Input - Response Source`

Group by:

- `YEAR`
- `MONTH`
- `COUNTRYCATEGORYID`

Aggregate:

- `MAX(_ETL_LOAD_DATETIME)` as `MAX_ETL_LOAD_DATETIME`

Output:

- one row per `YEAR, MONTH, COUNTRYCATEGORYID`

### 3. `Join - Response With Group Max`

Join type:

- inner join

Join conditions:

- `Response.YEAR = GroupMax.YEAR`
- `Response.MONTH = GroupMax.MONTH`
- `Response.COUNTRYCATEGORYID = GroupMax.COUNTRYCATEGORYID`

Output columns should include:

- all original response columns
- `MAX_ETL_LOAD_DATETIME`

This creates an enriched stream where each response row knows the group’s latest load timestamp.

### 4. `Filter - Old Groups`

Condition:

- `MAX_ETL_LOAD_DATETIME < TO_TIMESTAMP_NTZ('2026-04-01')`

Purpose:

- keep all rows for old groups

No additional latest-load filter is applied here.

### 5. `Filter - New Groups`

Condition:

- `MAX_ETL_LOAD_DATETIME >= TO_TIMESTAMP_NTZ('2026-04-01')`

Purpose:

- isolate groups where only latest-batch rows should remain

### 6. `Filter - Keep Only Latest Load Rows`

Input:

- from `Filter - New Groups`

Condition:

- `_ETL_LOAD_DATETIME = MAX_ETL_LOAD_DATETIME`

Purpose:

- remove older rows inside new groups

### 7. `Union All`

Inputs:

- `Filter - Old Groups`
- `Filter - Keep Only Latest Load Rows`

Behavior:

- union all rows

Important:

- use `UNION ALL` behavior, not deduplicating union
- preserve identical column order and datatypes from both branches

### 8. `Select / Rename`

Purpose:

- reorder columns if needed
- remove helper column `MAX_ETL_LOAD_DATETIME` before downstream logic

### 9. Existing downstream components

Keep unchanged where possible:

- calculators
- joins
- derived keys
- output component

## Best Recommendation For Response

Prefer the single `Table Input` with CTE unless:

- the current job is already visually split into multiple branches
- the team strongly prefers visual branch logic for maintainability

If visual traceability is important for auditors or support teams, the branch design is a good alternative.

---

## Staging-Layer Adjustment Design Note

The business request also says:

- no more deletion activity in Staging Layer

That change most likely belongs in orchestration / staging jobs, not in the three integration transformations.

Based on the previous assessment, the likely staging-side candidates to inspect are:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`
- `tmpt_trn_create_history_table`

So the full implementation should probably be split into 2 workstreams:

### Workstream A. Staging behavior

- disable or bypass GCTS stage deletion logic
- ensure all Kantar-delivered rows remain available in stage

### Workstream B. Integration transformation behavior

- question: latest load only
- option: latest load only
- response: cutoff-based old/new logic

This separation is important because the transformation changes alone do not stop staging deletion.

---

## Recommended Build Sequence In Matillion

## Phase 1. Snapshot Current Jobs

- export screenshots or JSON of all 3 current transformations
- save current SQL from source components
- record current row counts for outputs

## Phase 2. Implement Dimensions First

### `trn_v_int_dim_gcts_question`

- insert latest-load source filter
- run sample test
- compare row counts

### `trn_v_int_dim_gcts_option`

- apply same pattern
- run sample test
- compare row counts

Reason:

- dimension changes are simpler and lower risk

## Phase 3. Implement Fact Logic

### `trn_v_int_fact_gcts_response`

- implement CTE source design or branch-based visual design
- validate old groups and new groups separately
- verify no accidental record loss before cutoff

## Phase 4. Handle Staging Deletion Separately

- inspect GCTS usage of shared partial-delete framework
- disable deletion only for GCTS-relevant stage objects
- retest harmonization output after staging change

## Phase 5. Regression Test Presentation Layer

- check downstream PL jobs
- compare business totals
- validate known reports / dashboards

---

## Validation Checklist By Object

## `trn_v_int_dim_gcts_question`

- confirm only one `_ETL_LOAD_DATETIME` remains in output
- confirm it is the global latest load
- confirm row count matches latest source batch
- confirm downstream joins still work

## `trn_v_int_dim_gcts_option`

- confirm only one `_ETL_LOAD_DATETIME` remains in output
- confirm it is the global latest load
- confirm row count matches latest source batch
- confirm downstream joins still work

## `trn_v_int_fact_gcts_response`

- confirm old groups still retain all rows
- confirm new groups retain only latest-batch rows
- confirm cutoff boundary `2026-04-01` behaves exactly as expected
- confirm helper column is removed before final output
- confirm output grain is unchanged

---

## Final Recommendation

For all 3 objects, the safest Matillion implementation pattern is:

- modify the source-side logic first
- preserve the existing downstream transformation structure
- use SQL-based `Table Input` for the filtering logic unless the existing jobs are already strongly visual/component-driven

Recommended pattern by object:

- `trn_v_int_dim_gcts_question`
  - use `Table Input` with latest-load CTE
- `trn_v_int_dim_gcts_option`
  - use `Table Input` with latest-load CTE
- `trn_v_int_fact_gcts_response`
  - use `Table Input` with cutoff-based CTE, or visual branching if readability in Matillion canvas is preferred

The staging deletion change should be treated as a separate but related adjustment in the GCTS ingestion/staging orchestration.
