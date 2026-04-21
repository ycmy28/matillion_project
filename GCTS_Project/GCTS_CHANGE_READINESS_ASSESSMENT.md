# GCTS Change Readiness Assessment

## Purpose

This document assesses what we should check first before implementing the requested GCTS changes for:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

Requested business change summary:

- keep all Kantar data in Staging Layer
- stop deletion activity in Staging Layer
- keep Presentation Layer behavior unchanged
- for `DIM_GCTS_QUESTION` and `DIM_GCTS_OPTION`, read only rows from the latest `_ETL_LOAD_DATETIME`
- for `FACT_GCTS_RESPONSE`, preserve old historical behavior before `2026-04-01`, but use latest-load-only behavior from `2026-04-01` onward, by `YEAR, MONTH, COUNTRYCATEGORYID`

## Most Important Finding First

The current exported file `GCTS.json` is not enough to implement these changes safely.

Why:

- the export confirms the top-level master job `pipe_e2e_master_gcts`
- the export references `orc_ingestion_gcts` and `orc_harmonization_pipeline_gcts`
- but it does **not** include the internal definitions of the GCTS-specific jobs we need to change
- the following requested transformation jobs are not present in the local export:
  - `trn_v_int_dim_gcts_question`
  - `trn_v_int_dim_gcts_option`
  - `trn_v_int_fact_gcts_response`
- the following expected source table names are also not present in the local export:
  - `T_GCTS_RESPONSE`
  - `T_GCTS_QUESTION_MAP`
  - `T_GCTS_OPTION`

So before implementation, the first thing to assess is the missing Matillion job logic itself.

## What We Need To Check First

### 1. Get the Real GCTS Job Definitions

Before changing anything, we need the full definitions for:

- `orc_ingestion_gcts`
- `orc_harmonization_pipeline_gcts`
- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

Reason:

- we need to see the current SQL / component graph
- we need to know the exact source tables actually used
- we need to confirm whether these are table-input jobs, SQL components, calculators, joins, filters, or view builders
- we need to see whether there are already deduplication or `_ETL_LOAD_DATETIME` filters in place

Without this, any implementation would be guesswork.

### 2. Identify Where Staging Deletion Happens

The business request says:

- no more deletion activity in Staging Layer
- keep Presentation Layer as-is

From the previous assessment, the export includes reusable staging delete / historization logic in:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`
- `tmpt_trn_create_history_table`

So we need to check whether GCTS currently uses these shared jobs.

Specific questions to answer:

- does `orc_ingestion_gcts` call `orc_load_stage_objects` or `orc_update_indicator`?
- does GCTS stage loading currently mark records as deleted with `_ETL_RECORD_INDICATOR = 'D'`?
- does it physically delete records from stage tables?
- is the deletion behavior generic across all GCTS stage objects or only some objects?

This is critical because the requested transformation changes only make sense if we understand how stage data changes after each load.

### 3. Confirm the Grain of Each Target Object

Before changing the three transformations, we need to validate the business grain and technical grain of their source tables.

We should check:

- `T_GCTS_QUESTION_MAP`
  - what is the unique business grain?
  - can one business key exist in multiple `_ETL_LOAD_DATETIME` versions?
- `T_GCTS_OPTION` or the real option source table
  - same question: what is the business grain?
- `T_GCTS_RESPONSE`
  - is the intended grain one row per answer, respondent, question, or some other combination?
  - can multiple files create multiple versions for the same `YEAR, MONTH, COUNTRYCATEGORYID`?

This matters because “latest `_ETL_LOAD_DATETIME` only” can accidentally remove valid rows if the grain is misunderstood.

### 4. Validate the Meaning of `_ETL_LOAD_DATETIME`

We need to confirm what `_ETL_LOAD_DATETIME` actually represents in GCTS.

Check:

- is it the file ingestion timestamp?
- is it the stage insert timestamp?
- can the same source file create multiple `_ETL_LOAD_DATETIME` values?
- is it populated consistently across stage and integration objects?
- is it precise enough to represent replacement batches correctly?

This is especially important for `FACT_GCTS_RESPONSE`, because the requested logic depends entirely on comparing grouped maximum `_ETL_LOAD_DATETIME`.

### 5. Confirm the Cutover Rule for `FACT_GCTS_RESPONSE`

The fact logic depends on a cutover date of `2026-04-01`.

We need to confirm:

- is this cutoff compared against `MAX(_ETL_LOAD_DATETIME)` as a timestamp?
- should it be interpreted as `2026-04-01 00:00:00`?
- which timezone should apply?
- is the comparison inclusive exactly as written:
  - `< '2026-04-01'` = old behavior
  - `>= '2026-04-01'` = latest-only behavior

This should be clarified in the job design to avoid silent boundary issues.

### 6. Check Downstream Dependency Impact

The request says:

- keep Presentation Layer as-is

That means we must verify whether PL jobs assume current integration-layer row counts or duplication patterns.

For each of the three transformations, we should check:

- what downstream jobs consume them?
- are these outputs materialized as views or tables?
- do downstream jobs expect multiple historical stage versions?
- will latest-only filtering change record counts or surrogate key behavior?

This is the key impact check before implementation.

## What We Can Assess Right Now

Based on the local export, we can already say:

1. The GCTS pipeline is orchestration-led:
   - `pipe_e2e_master_gcts -> orc_ingestion_gcts -> orc_harmonization_pipeline_gcts`
2. The export contains shared ingestion and soft-delete templates.
3. The export does **not** contain the actual GCTS transformation jobs requested for change.
4. Therefore, we can prepare the implementation approach, but we cannot safely code or fully specify the exact Matillion edits yet.

## Recommended Execution Order

This is the order I recommend before making changes.

### Step 1. Retrieve a fuller GCTS export or inspect the jobs directly in Matillion

Must-have objects:

- `orc_ingestion_gcts`
- `orc_harmonization_pipeline_gcts`
- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

This is the first thing to do because all later analysis depends on the actual current logic.

### Step 2. Trace where stage deletion is triggered for GCTS

Goal:

- identify whether GCTS currently calls the shared delete/history framework
- identify exactly which stage tables are affected

This tells us whether the business change needs:

- only harmonization changes
- or also ingestion/staging framework changes

### Step 3. Inspect the current SQL logic of the three target transformations

For each job, document:

- source tables
- joins
- filters
- dedup logic
- output object name
- whether `_ETL_LOAD_DATETIME` is already used

This creates the baseline before change.

### Step 4. Validate stage data patterns with sample queries

Run checks on the real source tables:

- count distinct business keys
- count duplicate business keys across `_ETL_LOAD_DATETIME`
- inspect multiple loads per key
- inspect `YEAR, MONTH, COUNTRYCATEGORYID` groups in `T_GCTS_RESPONSE`
- measure how many groups have:
  - one load only
  - multiple loads before `2026-04-01`
  - multiple loads on or after `2026-04-01`

This step proves whether the business logic matches real data.

### Step 5. Design the new integration-layer logic

Recommended design direction:

- `trn_v_int_dim_gcts_question`
  - source from `T_GCTS_QUESTION_MAP`
  - filter to rows where `_ETL_LOAD_DATETIME = MAX(_ETL_LOAD_DATETIME)` for the intended business scope
- `trn_v_int_dim_gcts_option`
  - same pattern for the option source
- `trn_v_int_fact_gcts_response`
  - split logic into two branches:
    - branch A: groups with `MAX(_ETL_LOAD_DATETIME) < '2026-04-01'`, keep all rows
    - branch B: groups with `MAX(_ETL_LOAD_DATETIME) >= '2026-04-01'`, keep only rows from the latest `_ETL_LOAD_DATETIME`
  - union branch A and branch B

But the exact SQL should only be finalized after Steps 1 to 4.

### Step 6. Regression-check downstream PL outputs

Because Presentation Layer should remain unchanged, verify:

- row counts
- key counts
- duplicate behavior
- known business totals

Do this before and after the change.

## Practical “Do First” List

If we want the shortest safe path, this is what to do first:

1. Get the full Matillion export or screenshots / SQL of the 3 transformation jobs.
2. Get the full definition of `orc_ingestion_gcts` and `orc_harmonization_pipeline_gcts`.
3. Confirm whether GCTS uses the shared staging delete framework.
4. Run source-data profiling on `T_GCTS_QUESTION_MAP`, option source, and `T_GCTS_RESPONSE`.
5. Only then design the SQL/component changes.

## Suggested Questions To Answer During Assessment

These are the questions that should be answered before implementation:

- What are the exact source tables for the three transformations?
- Are the three jobs implemented as views, table rebuilds, or staged SQL transformations?
- What is the exact business key for question, option, and response?
- Does `_ETL_LOAD_DATETIME` represent replacement-batch versioning correctly?
- Does GCTS staging currently delete, soft-delete, or overwrite data?
- Which downstream PL jobs consume the three integration outputs?
- Will latest-only filtering change historical analytics unexpectedly?

## Final Recommendation

The correct first move is **not** to edit the transformations yet.

The correct first move is to obtain the missing GCTS-specific job definitions and trace whether GCTS currently uses the shared staging delete framework.

After that, the safest implementation order is:

1. assess current stage deletion behavior
2. inspect the three current transformation definitions
3. validate data patterns in source tables
4. implement dimension changes
5. implement fact cutover logic
6. run downstream regression checks

At the moment, the change is well-defined from a business perspective, but the local export is still incomplete from an implementation perspective.
