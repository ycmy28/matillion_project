# GCTS Implementation Checklist And SQL Draft

## Short Answer

No, it is not fully “all done” from an implementation-readiness perspective.

There are still important things left to do before safe deployment:

- retrieve the real Matillion definitions for the 3 target transformations
- confirm the exact GCTS source tables and output objects
- confirm where staging deletion is currently triggered
- validate the real data pattern of `_ETL_LOAD_DATETIME`
- regression-check downstream Presentation Layer outputs

That said, the business request is clear enough to prepare:

- an implementation checklist
- a draft SQL design for the 3 transformations

This document provides both.

## Assumptions For This Draft

Because the current local export does not include the real GCTS transformation bodies, the SQL below is a design draft based on the business rules you gave.

Assumptions used here:

- `trn_v_int_dim_gcts_question` reads from `T_GCTS_QUESTION_MAP`
- `trn_v_int_dim_gcts_option` reads from a GCTS option table such as `T_GCTS_OPTION`
- `trn_v_int_fact_gcts_response` reads from `T_GCTS_RESPONSE`
- `_ETL_LOAD_DATETIME` is the load-version timestamp that identifies replacement batches
- for question and option, the desired rule is “latest load only”
- for response, the desired rule is:
  - keep all rows for groups whose max load is before `2026-04-01`
  - keep only latest-load rows for groups whose max load is on or after `2026-04-01`

If the real transformation uses different table names, joins, or aliases, the logic below should be adapted, not copied blindly.

## What Still Needs To Be Done

Before build or deployment, these checks are still needed:

1. Confirm the actual SQL/component design of:
   - `trn_v_int_dim_gcts_question`
   - `trn_v_int_dim_gcts_option`
   - `trn_v_int_fact_gcts_response`
2. Confirm whether GCTS ingestion currently calls shared stage-delete logic.
3. Confirm the business grain of:
   - question
   - option
   - response
4. Validate that `_ETL_LOAD_DATETIME` is the correct field for replacement-batch logic.
5. Confirm whether the cutoff should be exactly `2026-04-01 00:00:00`.
6. Confirm downstream PL dependencies and expected row-count behavior.

## Recommended Implementation Order

1. Stop and map the current transformation logic from Matillion.
2. Check whether stage deletion must be disabled in ingestion/staging jobs.
3. Implement `trn_v_int_dim_gcts_question`.
4. Implement `trn_v_int_dim_gcts_option`.
5. Implement `trn_v_int_fact_gcts_response`.
6. Run validation queries before and after changes.
7. Run downstream regression checks for Presentation Layer.

## Detailed Implementation Checklist

### Phase 1. Discovery

- Export or capture the current component graph for all 3 transformations.
- Identify source tables, joins, filters, calculators, and target objects.
- Confirm whether each target is a table, view, or transient intermediate object.
- Confirm the exact option table name if it is not literally `T_GCTS_OPTION`.

### Phase 2. Staging Change Assessment

- Trace `orc_ingestion_gcts`.
- Check whether it calls:
  - `orc_load_stage_objects`
  - `orc_run_group_calc`
  - `orc_update_indicator`
- Confirm whether GCTS stage objects currently:
  - soft-delete rows
  - physically delete rows
  - overwrite by batch
- Identify which stage objects must stop deletion behavior.

### Phase 3. Data Profiling

- For `T_GCTS_QUESTION_MAP`, inspect:
  - duplicate business keys across multiple `_ETL_LOAD_DATETIME`
  - row count by load timestamp
- For the option source table, inspect the same.
- For `T_GCTS_RESPONSE`, inspect:
  - count of rows by `YEAR, MONTH, COUNTRYCATEGORYID, _ETL_LOAD_DATETIME`
  - count of distinct `_ETL_LOAD_DATETIME` per `YEAR, MONTH, COUNTRYCATEGORYID`
  - groups before and after `2026-04-01`

### Phase 4. Transformation Update

- Update `trn_v_int_dim_gcts_question` to source only latest `_ETL_LOAD_DATETIME`.
- Update `trn_v_int_dim_gcts_option` to source only latest `_ETL_LOAD_DATETIME`.
- Update `trn_v_int_fact_gcts_response` using a two-branch union design.
- Keep downstream Presentation Layer jobs unchanged unless testing shows breakage.

### Phase 5. Validation

- Compare row counts before and after for all 3 outputs.
- Validate sample business keys.
- Validate a sample of response groups:
  - one group before cutoff
  - one group exactly around cutoff
  - one group after cutoff
- Validate downstream PL totals and known reports.

## SQL Design Draft

## 1. Draft For `trn_v_int_dim_gcts_question`

### Business Rule

Only keep rows from `T_GCTS_QUESTION_MAP` for the latest `_ETL_LOAD_DATETIME`.

### Simplest Draft

```sql
SELECT
    A,
    B,
    C
FROM T_GCTS_QUESTION_MAP
WHERE _ETL_LOAD_DATETIME = (
    SELECT MAX(_ETL_LOAD_DATETIME)
    FROM T_GCTS_QUESTION_MAP
);
```

### Preferred CTE Draft

This is easier to maintain in Matillion SQL components:

```sql
WITH latest_load AS (
    SELECT MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime
    FROM T_GCTS_QUESTION_MAP
)
SELECT
    src.*
FROM T_GCTS_QUESTION_MAP src
INNER JOIN latest_load l
    ON src._ETL_LOAD_DATETIME = l.max_etl_load_datetime;
```

### What To Check Before Finalizing

- does the current job already join to other lookup tables?
- should “latest” be global for the whole table, or per business key?
- does the downstream dimension expect only one batch at a time?

If the correct behavior is “latest per business key” rather than “latest global table batch,” the SQL must be adjusted.

## 2. Draft For `trn_v_int_dim_gcts_option`

### Business Rule

Only keep rows from the option source for the latest `_ETL_LOAD_DATETIME`.

### Simplest Draft

```sql
SELECT
    A,
    B,
    C
FROM T_GCTS_OPTION
WHERE _ETL_LOAD_DATETIME = (
    SELECT MAX(_ETL_LOAD_DATETIME)
    FROM T_GCTS_OPTION
);
```

### Preferred CTE Draft

```sql
WITH latest_load AS (
    SELECT MAX(_ETL_LOAD_DATETIME) AS max_etl_load_datetime
    FROM T_GCTS_OPTION
)
SELECT
    src.*
FROM T_GCTS_OPTION src
INNER JOIN latest_load l
    ON src._ETL_LOAD_DATETIME = l.max_etl_load_datetime;
```

### What To Check Before Finalizing

- confirm the real table name
- confirm whether option rows are versioned globally or per option group
- confirm whether the current transformation already filters inactive/deleted rows

## 3. Draft For `trn_v_int_fact_gcts_response`

### Business Rule

For each `YEAR, MONTH, COUNTRYCATEGORYID`:

- if `MAX(_ETL_LOAD_DATETIME) < '2026-04-01'`, keep all rows as-is
- if `MAX(_ETL_LOAD_DATETIME) >= '2026-04-01'`, keep only rows from that max `_ETL_LOAD_DATETIME`
- union both result sets

### Recommended SQL Draft

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
SELECT * FROM new_logic;
```

### Why This Design Fits The Requirement

- `response_group_max` computes the latest batch per `YEAR, MONTH, COUNTRYCATEGORYID`
- `old_logic` preserves all historical rows for old groups
- `new_logic` limits new groups to only the latest replacement batch
- `UNION ALL` combines the two business behaviors without deduplicating valid rows

### Optional Safer Variant

If the source columns may contain nulls in grouping fields, add null handling explicitly:

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
    r.*
FROM T_GCTS_RESPONSE r
INNER JOIN response_group_max g
    ON NVL(r.YEAR, -1) = NVL(g.YEAR, -1)
   AND NVL(r.MONTH, -1) = NVL(g.MONTH, -1)
   AND NVL(r.COUNTRYCATEGORYID, -1) = NVL(g.COUNTRYCATEGORYID, -1)
WHERE (
        g.max_etl_load_datetime < TO_TIMESTAMP_NTZ('2026-04-01')
      )
   OR (
        g.max_etl_load_datetime >= TO_TIMESTAMP_NTZ('2026-04-01')
    AND r._ETL_LOAD_DATETIME = g.max_etl_load_datetime
      );
```

This is compact, but the two-CTE branch version is usually clearer for maintenance.

## Suggested Validation SQL

## 1. Question / Option Latest Load Check

```sql
SELECT MAX(_ETL_LOAD_DATETIME)
FROM T_GCTS_QUESTION_MAP;
```

```sql
SELECT _ETL_LOAD_DATETIME, COUNT(*)
FROM T_GCTS_QUESTION_MAP
GROUP BY _ETL_LOAD_DATETIME
ORDER BY _ETL_LOAD_DATETIME DESC;
```

Repeat the same for the option source table.

## 2. Response Group Pattern Check

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

## 3. Response Cutover Split Check

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

## Matillion Implementation Notes

- If the transformation currently uses a `Table Input` plus downstream components, the easiest change may be to replace the source SQL with one of the CTE designs above.
- If the transformation currently uses multiple joins/calculators after the source read, consider creating a staging CTE or subquery component first, then keep the downstream logic unchanged.
- For `trn_v_int_fact_gcts_response`, keep the union logic in one SQL component if possible so the rule is transparent.
- Do not change Presentation Layer jobs yet unless regression testing proves it is required.

## Final Recommendation

What is left is mostly implementation discovery and validation, not business clarification.

The best next move is:

1. obtain the real definitions of the 3 Matillion transformations
2. compare them against this SQL draft
3. adapt the draft into the real Matillion component design

This draft is a strong starting point, but it still needs to be aligned with the actual GCTS jobs before deployment.
