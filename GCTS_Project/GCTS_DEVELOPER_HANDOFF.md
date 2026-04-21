# GCTS Developer Handoff

## Purpose

This document converts the GCTS assessment and design into a concrete developer handoff for implementation in Matillion.

Scope:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`
- related note for staging-layer deletion behavior

This handoff is intended to help the Matillion developer execute the changes with minimal ambiguity.

## Business Objective

Implement GCTS changes so that:

- all data sent by Kantar remains available in Staging Layer
- no more deletion activity happens in GCTS Staging Layer
- Presentation Layer behavior remains unchanged
- integration-layer logic is adjusted as follows:
  - `trn_v_int_dim_gcts_question`: use only latest `_ETL_LOAD_DATETIME`
  - `trn_v_int_dim_gcts_option`: use only latest `_ETL_LOAD_DATETIME`
  - `trn_v_int_fact_gcts_response`: apply mixed old/new logic by `YEAR, MONTH, COUNTRYCATEGORYID`

## Important Delivery Warning

The local export used for assessment does **not** include the actual definitions of the 3 target transformation jobs.

So before coding:

- open each job in Matillion
- confirm actual source objects
- confirm actual component names
- confirm target object names

This handoff gives the intended implementation pattern, but final component names and exact SQL must be aligned to the real jobs in Matillion.

## Overall Workstreams

There are 2 separate but related workstreams.

### Workstream 1. Staging behavior

Goal:

- disable GCTS staging deletion behavior

Likely jobs to inspect:

- `orc_ingestion_gcts`
- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`
- `tmpt_trn_create_history_table`

### Workstream 2. Integration transformations

Goal:

- change source logic for the 3 target transformations without changing PL jobs

Target jobs:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

## Delivery Sequence

Recommended implementation order:

1. inspect current jobs in Matillion
2. snapshot current SQL and row counts
3. implement `trn_v_int_dim_gcts_question`
4. implement `trn_v_int_dim_gcts_option`
5. implement `trn_v_int_fact_gcts_response`
6. validate outputs
7. inspect and disable GCTS staging deletion logic
8. regression-test downstream Presentation Layer

Reason for this order:

- dimensions are simpler and lower risk
- fact change is more complex and should be done after the dimension pattern is stable
- staging deletion change should be carefully isolated because it can affect more than one object

---

## Pre-Implementation Checklist

Before making any edits, complete all items below.

- Identify the current source tables used in each of the 3 jobs.
- Confirm whether the option source is really `T_GCTS_OPTION`.
- Confirm whether the question source is really `T_GCTS_QUESTION_MAP`.
- Confirm whether the fact source is really `T_GCTS_RESPONSE`.
- Confirm how each job publishes output:
  - create view
  - rewrite table
  - table update
- Capture current row counts for the 3 outputs.
- Capture sample row counts by `_ETL_LOAD_DATETIME`.
- Capture sample counts for `YEAR, MONTH, COUNTRYCATEGORYID` in response.
- Confirm whether existing downstream jobs reference these outputs directly.

---

## Job 1: `trn_v_int_dim_gcts_question`

## Objective

Only expose rows from the latest `_ETL_LOAD_DATETIME` in the question source.

## Developer Action Plan

### Step 1. Open the current transformation

Check:

- current source component name
- whether the source is `Table Input`, `View`, or another upstream component
- whether downstream logic already contains filtering or dedup

### Step 2. Implement source-side filtering

Preferred approach:

- replace or adjust the source `Table Input` SQL so that only latest batch rows are returned

Preferred SQL:

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

### Step 3. Keep downstream components unchanged

Do not change unless necessary:

- `Calculator`
- `Filter`
- `Join`
- `Select`
- `Rename`
- target output component

### Step 4. Validate output

Check:

- output contains only one `_ETL_LOAD_DATETIME`
- that timestamp equals source `MAX(_ETL_LOAD_DATETIME)`
- row count matches the source latest batch row count

## If The Job Is Purely Visual

Use this component flow:

```text
Table Input - Question Source
Aggregate - Max Load Datetime
Join - Latest Only
Select
Existing downstream flow
Target
```

## Suggested Component Names

- `TI_GCTS_QUESTION_SOURCE`
- `AGG_GCTS_QUESTION_MAX_LOAD`
- `JN_GCTS_QUESTION_LATEST_ONLY`
- `SEL_GCTS_QUESTION_OUTPUT`

## Validation SQL

```sql
SELECT MAX(_ETL_LOAD_DATETIME) FROM T_GCTS_QUESTION_MAP;
```

```sql
SELECT _ETL_LOAD_DATETIME, COUNT(*)
FROM T_GCTS_QUESTION_MAP
GROUP BY _ETL_LOAD_DATETIME
ORDER BY _ETL_LOAD_DATETIME DESC;
```

---

## Job 2: `trn_v_int_dim_gcts_option`

## Objective

Only expose rows from the latest `_ETL_LOAD_DATETIME` in the option source.

## Developer Action Plan

### Step 1. Open the current transformation

Confirm:

- actual source table name
- source component type
- current filters / joins / mapping logic

### Step 2. Implement source-side latest-load filter

Preferred SQL:

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

If actual source name differs, replace `T_GCTS_OPTION` with the real source table.

### Step 3. Keep downstream mapping unchanged

Do not modify downstream components unless the changed source shape forces it.

### Step 4. Validate output

Check:

- output contains only one `_ETL_LOAD_DATETIME`
- timestamp equals source max load
- row count matches the latest source batch

## If The Job Is Purely Visual

Use this component flow:

```text
Table Input - Option Source
Aggregate - Max Load Datetime
Join - Latest Only
Select
Existing downstream flow
Target
```

## Suggested Component Names

- `TI_GCTS_OPTION_SOURCE`
- `AGG_GCTS_OPTION_MAX_LOAD`
- `JN_GCTS_OPTION_LATEST_ONLY`
- `SEL_GCTS_OPTION_OUTPUT`

## Validation SQL

```sql
SELECT MAX(_ETL_LOAD_DATETIME) FROM T_GCTS_OPTION;
```

```sql
SELECT _ETL_LOAD_DATETIME, COUNT(*)
FROM T_GCTS_OPTION
GROUP BY _ETL_LOAD_DATETIME
ORDER BY _ETL_LOAD_DATETIME DESC;
```

---

## Job 3: `trn_v_int_fact_gcts_response`

## Objective

Apply mixed behavior based on grouped `MAX(_ETL_LOAD_DATETIME)` by:

- `YEAR`
- `MONTH`
- `COUNTRYCATEGORYID`

Rule:

- if group max `< '2026-04-01'`, keep all rows
- if group max `>= '2026-04-01'`, keep only latest-load rows

## Developer Action Plan

### Step 1. Open the current transformation

Check:

- source component name
- whether current logic already aggregates or deduplicates
- whether downstream logic depends on multiple batches being present

### Step 2. Implement the cutover logic near source

Preferred approach:

- use one `Table Input` with explicit CTE branches

Preferred SQL:

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

### Step 3. Keep downstream logic stable

After the source component:

- keep calculators unchanged
- keep lookup joins unchanged
- keep output logic unchanged

Only remove helper fields if the source logic introduces them into downstream flow.

### Step 4. Validate the cutoff logic

Need to validate at least 3 samples:

- one group where max load is before `2026-04-01`
- one group where max load is after `2026-04-01`
- one group near the cutoff boundary

Check:

- old groups keep all rows
- new groups keep only latest-load rows
- no unexpected duplicate removal occurs

## If The Team Wants A Visual Component Design

Use this flow:

```text
Table Input - Response Source
Aggregate - Max Load Per Group
Join - Response With Group Max
Filter - Old Groups
Filter - New Groups
Filter - New Groups Latest Rows Only
Union All
Select
Existing downstream flow
Target
```

## Suggested Component Names

- `TI_GCTS_RESPONSE_SOURCE`
- `AGG_GCTS_RESPONSE_GROUP_MAX`
- `JN_GCTS_RESPONSE_WITH_GROUP_MAX`
- `FLT_GCTS_RESPONSE_OLD_GROUPS`
- `FLT_GCTS_RESPONSE_NEW_GROUPS`
- `FLT_GCTS_RESPONSE_NEW_GROUPS_LATEST_ONLY`
- `UN_GCTS_RESPONSE_FINAL`
- `SEL_GCTS_RESPONSE_OUTPUT`

## Validation SQL

```sql
SELECT
    YEAR,
    MONTH,
    COUNTRYCATEGORYID,
    COUNT(DISTINCT _ETL_LOAD_DATETIME) AS load_versions,
    MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime,
    COUNT(*) AS row_count
FROM T_GCTS_RESPONSE
GROUP BY
    YEAR,
    MONTH,
    COUNTRYCATEGORYID
ORDER BY
    YEAR,
    MONTH,
    COUNTRYCATEGORYID;
```

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
)
SELECT
    CASE
        WHEN max_etl_load_datetime < TO_TIMESTAMP_NTZ('2026-04-01') THEN 'OLD_LOGIC'
        ELSE 'NEW_LOGIC'
    END AS rule_bucket,
    COUNT(*) AS group_count
FROM response_group_max
GROUP BY 1;
```

---

## Staging Deletion Workstream

## Objective

Ensure GCTS stage data is no longer deleted or soft-deleted during ingestion/staging processing.

## Developer Action Plan

### Step 1. Open `orc_ingestion_gcts`

Check whether it calls any of these shared jobs:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

### Step 2. Trace GCTS stage objects through the shared framework

Identify:

- which GCTS objects are passed through the deletion/update indicator logic
- whether the framework:
  - marks `_ETL_RECORD_INDICATOR = 'D'`
  - deletes rows from stage
  - creates delete/history tables

### Step 3. Decide the least invasive change

Preferred options, in order:

1. bypass delete/update flow only for GCTS objects
2. skip GCTS object routing into the delete framework
3. add conditional logic so delete/update indicator does not execute for GCTS

Avoid:

- broad change that disables delete behavior for unrelated domains

### Step 4. Validate stage retention

Check:

- multiple Kantar-delivered loads remain present in GCTS stage
- no rows are marked deleted for GCTS stage objects
- harmonization still runs successfully

---

## Testing And Validation Plan

## Before Change

Capture:

- current row count of each transformation output
- current distinct `_ETL_LOAD_DATETIME` counts
- current sample counts for response groups
- current stage row counts for GCTS source tables

## After Dimension Changes

For question and option:

- confirm only latest load remains in integration output
- confirm row count equals latest source batch
- confirm downstream joins still work

## After Fact Change

For response:

- confirm old groups still return all rows
- confirm new groups return only latest-load rows
- confirm `UNION ALL` result shape matches downstream expectation

## After Staging Change

- confirm old stage rows are retained
- confirm no delete markers are applied to GCTS stage data
- confirm integration transformations still complete successfully

## After End-To-End Run

- compare downstream Presentation Layer row counts
- compare known business totals or dashboard totals
- confirm no unexpected drop in reporting outputs

---

## Deployment Notes

- promote dimension changes first
- promote fact change after dimension validation
- promote staging deletion change separately if possible
- if available, use a lower environment first with representative GCTS data
- retain a rollback copy of current SQL/component design before editing

## Rollback Strategy

If unexpected output changes occur:

1. restore original source SQL / original source-side component flow
2. rerun transformation
3. compare row counts to baseline
4. only then revisit the adjusted logic

For staging changes:

- rollback should restore original routing into delete/update framework

---

## Developer Deliverables

The developer should provide back:

- screenshot or export of updated component graph for each job
- final SQL used in each adjusted source component
- before/after row counts
- sample validation evidence for response old/new group logic
- confirmation of how GCTS staging deletion was disabled

## Final Handoff Summary

The safest implementation approach is:

- put the new filtering logic at the source side of each transformation
- leave downstream transformation logic unchanged where possible
- treat staging deletion disablement as a separate GCTS-specific orchestration change

Implementation priority:

1. `trn_v_int_dim_gcts_question`
2. `trn_v_int_dim_gcts_option`
3. `trn_v_int_fact_gcts_response`
4. staging delete-disable change
5. full regression validation
