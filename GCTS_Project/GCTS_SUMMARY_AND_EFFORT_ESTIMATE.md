# GCTS Summary And Effort Estimate

## Purpose

This file consolidates the current GCTS assessment into a single summary with:

- business objective
- confirmed findings
- proposed solution direction
- remaining unknowns
- implementation sequence
- effort estimate

Related files created in this folder:

- `GCTS_PIPELINE_ASSESSMENT.md`
- `GCTS_CHANGE_READINESS_ASSESSMENT.md`
- `GCTS_IMPLEMENTATION_CHECKLIST_AND_SQL_DRAFT.md`
- `GCTS_MATILLION_COMPONENT_ORIENTED_DESIGN.md`
- `GCTS_DEVELOPER_HANDOFF.md`

## Business Request Summary

The requested change is:

- keep all data sent by Kantar available in GCTS Staging Layer
- stop deletion activity in GCTS Staging Layer
- keep Presentation Layer behavior unchanged
- adjust 3 integration transformations:
  - `trn_v_int_dim_gcts_question`
  - `trn_v_int_dim_gcts_option`
  - `trn_v_int_fact_gcts_response`

Detailed business rules:

- `trn_v_int_dim_gcts_question`
  - only keep rows from the latest `_ETL_LOAD_DATETIME`
- `trn_v_int_dim_gcts_option`
  - only keep rows from the latest `_ETL_LOAD_DATETIME`
- `trn_v_int_fact_gcts_response`
  - group by `YEAR, MONTH, COUNTRYCATEGORYID`
  - if `MAX(_ETL_LOAD_DATETIME) < '2026-04-01'`, keep all rows
  - if `MAX(_ETL_LOAD_DATETIME) >= '2026-04-01'`, keep only rows from the latest `_ETL_LOAD_DATETIME`
  - union both result sets

## Confirmed Findings

Based on the exported file `GCTS.json`:

- the confirmed master pipeline is `pipe_e2e_master_gcts`
- the visible master flow is:
  - `Start`
  - `orc_ingestion_gcts`
  - `orc_harmonization_pipeline_gcts`
- the export includes shared ingestion and partial-delete framework jobs
- the export does **not** include the actual definitions of:
  - `trn_v_int_dim_gcts_question`
  - `trn_v_int_dim_gcts_option`
  - `trn_v_int_fact_gcts_response`
- the export also does **not** include the expected `T_GCTS_*` objects mentioned in the change request

## Key Conclusion

The business change is understandable, but the current export is incomplete for direct implementation.

This means:

- we can define the design
- we can prepare developer handoff material
- we can estimate the effort
- but final implementation must still verify the real Matillion job definitions and real source tables

## Proposed Solution Direction

The change should be handled in 2 workstreams.

### Workstream 1. Staging behavior

Goal:

- stop GCTS staging deletion behavior
- keep all Kantar data available in stage

Likely area to inspect:

- `orc_ingestion_gcts`
- shared delete/history framework jobs used by staging

### Workstream 2. Integration transformations

Goal:

- adjust only source-side logic of the 3 transformations
- keep downstream Presentation Layer unchanged if possible

Recommended transformation approach:

- `trn_v_int_dim_gcts_question`
  - filter to latest `_ETL_LOAD_DATETIME`
- `trn_v_int_dim_gcts_option`
  - filter to latest `_ETL_LOAD_DATETIME`
- `trn_v_int_fact_gcts_response`
  - use grouped max logic with old/new split and `UNION ALL`

## Recommended Technical Pattern

Safest pattern:

- implement the new rule near the source side of each transformation
- keep downstream calculators, joins, renames, and output components unchanged where possible

Preferred implementation style:

- use `Table Input` with CTE-based SQL for the new filters

Alternative implementation style:

- use Matillion visual components such as:
  - `Aggregate`
  - `Join`
  - `Filter`
  - `Union All`

## What Still Needs To Be Confirmed

Before implementation, the following still need confirmation:

1. the real current component graph of the 3 transformation jobs
2. the exact source table names used in those jobs
3. whether GCTS staging currently uses shared delete/update logic
4. the actual business grain of question, option, and response data
5. whether `_ETL_LOAD_DATETIME` is the correct replacement-batch indicator
6. the exact cutoff interpretation for `2026-04-01`
7. downstream Presentation Layer dependencies

## Recommended Delivery Sequence

1. inspect the real 3 transformation jobs in Matillion
2. inspect `orc_ingestion_gcts` and trace staging delete behavior
3. capture baseline row counts and sample outputs
4. implement `trn_v_int_dim_gcts_question`
5. implement `trn_v_int_dim_gcts_option`
6. implement `trn_v_int_fact_gcts_response`
7. validate integration outputs
8. disable or bypass GCTS-specific staging deletion logic
9. run end-to-end regression checks on Presentation Layer outputs

## Summary Of Deliverables Already Prepared

The following implementation support artifacts are already prepared in this folder:

- pipeline assessment
- readiness assessment
- implementation checklist
- SQL draft
- Matillion component-oriented design
- developer handoff

So the team already has the documentation needed to start technical implementation once the real jobs are opened in Matillion.

## Effort Estimate

## Estimation Basis

This estimate assumes:

- one developer familiar with Matillion and Snowflake
- access to the real GCTS jobs in Matillion
- no major redesign outside the 3 transformations and GCTS-specific staging behavior
- test data or lower-environment execution is available

## Effort By Work Item

### 1. Discovery And Validation

Activities:

- inspect the 3 transformation jobs
- inspect `orc_ingestion_gcts`
- confirm source tables and current logic
- collect baseline row counts

Estimated effort:

- `0.5 to 1.0 day`

### 2. `trn_v_int_dim_gcts_question`

Activities:

- apply latest-load filtering logic
- unit test
- validate row counts

Estimated effort:

- `0.25 to 0.5 day`

### 3. `trn_v_int_dim_gcts_option`

Activities:

- apply latest-load filtering logic
- unit test
- validate row counts

Estimated effort:

- `0.25 to 0.5 day`

### 4. `trn_v_int_fact_gcts_response`

Activities:

- implement grouped max cutoff logic
- test both old and new branches
- validate sample groups and totals

Estimated effort:

- `0.5 to 1.0 day`

### 5. Staging Deletion Adjustment

Activities:

- trace GCTS-specific delete path
- implement bypass/disable logic
- validate stage retention behavior

Estimated effort:

- `0.5 to 1.0 day`

### 6. Regression Testing

Activities:

- rerun affected flows
- compare before/after outputs
- validate Presentation Layer impact

Estimated effort:

- `0.5 to 1.0 day`

## Total Estimated Effort

### Best-Case

If the real jobs are straightforward and the staging delete logic is easy to isolate:

- `2.5 days`

### Most Likely

If there is moderate validation and a normal amount of Matillion adjustment/testing:

- `3.0 to 4.0 days`

### Higher-Risk Case

If the real jobs differ significantly from the request, or the staging delete logic is reused in a complex shared framework:

- `4.5 to 6.0 days`

## Suggested Planning View

For planning purposes, a good working estimate is:

- `4 developer days`

This is a reasonable middle estimate covering:

- job inspection
- transformation updates
- staging behavior update
- validation
- regression support

## Risks That Can Increase Effort

- target transformations are more complex than expected
- source table names differ from the request
- staging delete logic is embedded in shared framework and not easily isolated for GCTS only
- downstream PL jobs rely on current duplicate/history behavior
- `_ETL_LOAD_DATETIME` is not a clean batch replacement indicator
- insufficient lower-environment test data

## Risks That Can Reduce Effort

- the 3 transformations already use simple source-side `Table Input` SQL
- GCTS delete behavior is controlled by one obvious shared orchestration step
- downstream PL jobs are insulated from integration-layer row-count changes

## Recommended Next Step

The next practical step is:

1. open the real GCTS jobs in Matillion
2. compare them against the prepared handoff/design files
3. confirm the actual source tables
4. then start implementation with:
   - `trn_v_int_dim_gcts_question`
   - `trn_v_int_dim_gcts_option`
   - `trn_v_int_fact_gcts_response`
   - staging delete-disable change

## Final Summary

The change is well-defined enough to move into implementation planning.

Current status:

- analysis completed
- design completed
- developer handoff completed
- effort estimated

Main constraint:

- final build still depends on access to the actual GCTS Matillion job definitions, because the current export does not include them.
