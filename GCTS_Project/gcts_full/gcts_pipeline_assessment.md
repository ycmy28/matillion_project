# GCTS Pipeline Assessment

## Purpose

This file reassesses the GCTS pipeline using the fuller Matillion export:

- `gcts_full.json`
- `ticket_requirement.txt`
- `GCTS Data Model/Full Physical Report.html`

It also reuses the intent and open questions captured earlier in:

- `GCTS_PIPELINE_ASSESSMENT.md`
- `GCTS_CHANGE_READINESS_ASSESSMENT.md`
- `GCTS_IMPLEMENTATION_CHECKLIST_AND_SQL_DRAFT.md`
- `GCTS_MATILLION_COMPONENT_ORIENTED_DESIGN.md`
- `GCTS_DEVELOPER_HANDOFF.md`
- `GCTS_SUMMARY_AND_EFFORT_ESTIMATE.md`

The main difference is that `gcts_full.json` now includes the actual GCTS-specific staging, integration, harmonization, and unit-test jobs that were missing from the earlier `GCTS.json`.

## Jira Context

The current assessment task is:

- `DODECOM-7399` - Assess GCTS pipeline

The assessment sits under:

- `DODECOM-7398` - Historical data of GCTS

And it is intended to prepare the next implementation tickets:

- `DODECOM-7400` - Adjust `trn_v_int_dim_gcts_question`
- `DODECOM-7401` - Adjust `trn_v_int_dim_gcts_option`
- `DODECOM-7402` - Adjust `trn_v_int_fact_gcts_response`

So the main success criterion for this document is not only to describe the pipeline, but to answer the ticket question:

- what should be done first before the dim/fact adjustment work begins?

## Additional Resources Used

Besides the Matillion export, this assessment now also uses:

### 1. Jira ticket requirement text

The supplied ticket text adds these business clarifications:

- the overall goal is to keep all GCTS data sent by Kantar available
- no more deletion activity should happen in Staging Layer
- Presentation Layer should remain as-is
- the expected follow-up change is to adjust question, option, and fact logic
- Kantar pushes 4 tables:
  - Responses
  - Options
  - Question Map
  - Country Category
- each push cycle should contain 1 file per table
- there may be more than 1 push cycle in a month
- the ticket text explicitly states:
  - Responses = Delta
  - Options = Full
  - Question Map = Full
- the provided text appears truncated for the Country Category availability-type line, so that specific point should be reconfirmed from Jira / Confluence

### 2. Data model report

The latest PowerDesigner physical report adds useful cross-checks:

- GCTS has a modeled star shape around:
  - `DIM_GCTS_OPTION`
  - `DIM_GCTS_QUESTION`
  - `FACT_GCTS_RESPONSE`
- model notes still reference stage views such as:
  - `V_GCTS_OPTIONS`
  - `V_GCTS_QUESTION_MAP`
  - `V_GCTS_COUNTRY_CATEGORY`
  - `V_GCTS_RESPONSE`
- model notes explicitly show `_ETL_ACTIVE_FLAG=true` in some documented source SQL
- model notes show the same key-generation logic seen in the Matillion jobs:
  - question key from `MD5(variableid||COUNTRYCATEGORYID)`
  - option key from `MD5(variableid||COUNTRYCATEGORYID||RESPONSENAME)`

This is important because it confirms that the original design was view-based and active-row-oriented, which matches the current staging delete / update framework.

## Executive Summary

The earlier conclusion that the GCTS export was too incomplete for meaningful job-level assessment is no longer true for `gcts_full.json`.

With the fuller export, we can now confirm:

1. The real end-to-end controller is still:
   - `pipe_e2e_master_gcts`
   - `orc_ingestion_gcts`
   - `orc_harmonization_pipeline_gcts`
2. The requested GCTS transformation jobs are present:
   - `trn_v_int_dim_gcts_question`
   - `trn_v_int_dim_gcts_option`
   - `trn_v_int_fact_gcts_response`
3. GCTS staging still appears tied to the shared soft-delete / indicator-update framework:
   - `orc_load_stage_objects`
   - `orc_run_group_calc`
   - `orc_update_indicator`
4. The current implementation does **not** fully match the requested business change:
   - question is already deduplicated by latest load, but only per generated key
   - option does not filter by latest `_ETL_LOAD_DATETIME`
   - fact does not implement the `2026-04-01` mixed old/new logic
   - stage deletion/update handling still appears active
5. The ticket and data model both reinforce that the old GCTS design was built around active/current stage views, not retained full history stage behavior.

## Confirmed Job Inventory

### Master pipeline

- `pipe_e2e_master_gcts`

### Staging

- `orc_ingestion_gcts`
- `trn_backup_gcts_data_ocean`
- `trn_load_gcts_from_do`

### Integration

- `trn_v_int_dim_gcts_country`
- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

### Presentation / orchestration

- `orc_harmonization_pipeline_gcts`
- `orc_unit_test_gcts`

## Actual End-To-End Flow

### 1. Master controller

The top-level flow is exactly:

```text
Start
  -> orc_ingestion_gcts
  -> orc_harmonization_pipeline_gcts
```

So the platform still follows the same high-level contract identified in the earlier assessment:

- ingest first
- harmonize and publish after ingestion succeeds

### 2. Staging orchestration

`orc_ingestion_gcts` is more complex than the old export suggested.

Confirmed components:

- sets S3 path dynamically from environment
- runs `orc_ingestion_s3_main` for `RESPONSE`
- runs `orc_ingestion_s3_main_v2` for:
  - `QUESTION_MAP`
  - `OPTIONS`
  - `COUNTRY_CATEGORY`
- calls `orc_load_stage_objects`
- adds `OCDI_SOURCE_FILE_NAME` columns to several stage tables
- also contains an inactive initial-load path with:
  - `trn_load_gcts_from_do`
  - `Get the list of source files`
  - `Load Stage Layer - Node`

## Important Architectural Finding

There appear to be **two response-related paths** inside `orc_ingestion_gcts`, but only one should be considered active for normal scheduled execution.

1. an active S3-template path for `RESPONSE`
2. a separate initial-load path built around:
   - `trn_load_gcts_from_do`
   - `Get the list of source files`
   - `Load Stage Layer - Node`

However, the fuller export confirms that the second path is explicitly disabled:

- `trn_load_gcts_from_do` -> `activationStatus: DISABLED`
- `Get the list of source files` -> `activationStatus: DISABLED`
- `Load Stage Layer - Node` -> `activationStatus: DISABLED`

The export also contains a note above that path:

- `** Only run this to get initial data for GCTS **`

So for assessment purposes, the safest interpretation is:

- this path exists for initial-load or special-case use
- it is not part of the current normal scheduled run path
- it should be excluded from the primary operational assessment unless the team plans to reactivate it

## Staging Delete / Soft-Delete Assessment

The earlier assessment suspected that GCTS might still be using the shared delete/update framework. `gcts_full.json` now confirms that suspicion more strongly.

`orc_ingestion_gcts` explicitly calls:

- `orc_load_stage_objects`

That job iterates into:

- `orc_run_group_calc`

Which in turn iterates into:

- `orc_update_indicator`

And `orc_update_indicator` contains components such as:

- `Delete records from Stage table`
- `Create queries to delete and insert records`
- `Check track changes`
- `tmpt_trn_create_history_table`

So from a control-flow perspective, the current GCTS ingestion still appears connected to stage update / delete / historization logic.

### Updated conclusion on staging behavior

Based on the fuller export, the prior recommendation still stands and is now stronger:

- if the business requirement is to keep all Kantar data in staging
- and stop deletion activity in staging

then GCTS staging behavior almost certainly needs adjustment in the ingestion layer, not only in the 3 integration transformations.

## Data Model Cross-Check

The data model report helps validate which parts of the pipeline are long-standing design choices versus recent implementation details.

### What aligns between data model and Matillion export

- the same core downstream objects are present:
  - `DIM_GCTS_QUESTION`
  - `DIM_GCTS_OPTION`
  - `FACT_GCTS_RESPONSE`
- the same key derivation rules appear in both the model notes and current jobs
- the fact design depends on the question and option dimensions

### What the data model suggests about historical behavior

The model documentation still references stage **views** and active-row filtering rather than a retained-history raw stage pattern.

Examples from the report:

- `select * from ... STG_GCTS.V_GCTS_OPTIONS where _ETL_ACTIVE_FLAG=true`
- question logic based on `V_GCTS_QUESTION_MAP`
- response logic based on `V_GCTS_RESPONSE`

This strongly suggests the modeled design assumed:

- stage views represent current active rows
- downstream dims/fact consume curated active-stage outputs

That is consistent with the delete/update framework seen in Matillion, and it explains why a retained-history staging requirement now creates design tension.

### Implementation implication

If the new requirement is to keep history in staging, then one of these must happen:

1. the stage views must still expose the correct active/current subset while raw history is retained underneath
2. or the downstream transformations must take over the responsibility of selecting the correct current/latest subset

The Jira follow-up tickets point toward the second option for question, option, and fact.

## Transformation Assessment

## 1. `trn_v_int_dim_gcts_question`

### What it does now

The current transformation reads:

- `STG_GCTS.T_GCTS_QUESTION_MAP`
- `STG_GCTS.T_GCTS_COUNTRY_CATEGORY`
- shared `DIM_COUNTRY`

Then it:

- generates `DIM_GCTS_QUESTION_MAP_KEY`
- joins question rows to country metadata
- applies `ROW_NUMBER()`
- partitions by `DIM_GCTS_QUESTION_MAP_KEY`
- orders by `_ETL_LOAD_DATETIME DESC`
- keeps only `RN = 1`
- unions fixed unknown / not-applicable rows
- creates `V_INT_DIM_GCTS_QUESTION`

### Assessment against request

This job is **partially aligned** with the requested change, but not exactly the same.

It already applies latest-load logic, but the logic is:

- latest `_ETL_LOAD_DATETIME` per generated key

not:

- latest `_ETL_LOAD_DATETIME` for the whole source table

That is an important distinction.

### Additional design observation

The generated key is based on:

- `VARIABLEID`
- `COUNTRYCATEGORYID`

But the metadata description suggests the business identity may also involve things like:

- `QUESTIONCODE`
- `FIRSTLEVELITERATOR`
- `SECONDLEVELITERATOR`

If that broader grain is truly required, the current dedup key may be too coarse. That should be validated before any change is finalized.

## 2. `trn_v_int_dim_gcts_option`

### What it does now

The current transformation reads:

- `STG_GCTS.T_GCTS_OPTIONS`

Then it:

- filters out rows where all important fields are null
- generates `DIM_GCTS_OPTION_KEY`
- reorders columns
- unions fixed unknown / not-applicable rows
- creates `V_INT_DIM_GCTS_OPTION`

### Assessment against request

This job is **not yet aligned** with the requested change.

There is no visible:

- `_ETL_LOAD_DATETIME` source column
- latest-load filter
- `ROW_NUMBER()` logic
- grouped max-load logic

So based on the export, `trn_v_int_dim_gcts_option` still exposes all currently available stage rows, not latest-load-only rows.

## 3. `trn_v_int_fact_gcts_response`

### What it does now

The current transformation reads:

- `STG_GCTS.T_GCTS_RESPONSE`

Then it joins to:

- `PL_MARKETRESEARCH.DIM_GCTS_QUESTION`
- `PL_MARKETRESEARCH.DIM_GCTS_OPTION`
- country mapping from `T_GCTS_COUNTRY_CATEGORY` and `DIM_COUNTRY`
- `DIM_MARKET_SDD`

Then it calculates:

- `DIM_DATE_KEY`
- dimension foreign keys with `-1` / `-2` handling
- numeric conversions for weights
- `OPEN_ANSWER`

Finally it creates:

- `V_INT_FACT_GCTS_RESPONSE`

### Assessment against request

This job is **not aligned** with the requested fact rule.

The requested rule was:

- before `2026-04-01`: keep old historical behavior
- on or after `2026-04-01`: keep latest load only by `YEAR, MONTH, COUNTRYCATEGORYID`

But the current transformation shows no visible logic for:

- `_ETL_LOAD_DATETIME`
- max-load grouping
- cutoff comparison with `2026-04-01`
- split old/new branch
- `UNION ALL` of historical branch and latest-only branch

So the mixed-era fact behavior is not implemented in the current export.

## Data Ocean / Response Preparation Assessment

`trn_load_gcts_from_do` is still useful context because it reveals response-specific logic kept in the project, but it should not be treated as part of the active scheduled pipeline.

The disabled job:

- reads `FACT_DPAAS_NCPT_RESPONSE`
- restricts to country categories where `CATEGORY = 'Prevalence'` and `_ETL_ACTIVE_FLAG = TRUE`
- keeps max source file by `COUNTRYCATEGORYID, YEAR, QUARTER`
- also filters to available `SCMQY`
- ranks latest answer by `ID DESC`
- keeps `rn = 1`
- adds ETL fields
- rewrites `STG_LOAD_GCTS.T_LOAD_GCTS_RESPONSE`

### Why this still matters

This logic shows how an initial-load or edge-case response preparation path was designed.

For normal scheduled-run assessment, it can be excluded. Still, if the team ever plans to re-enable it, the final requested business change for `FACT_GCTS_RESPONSE` should not be implemented blindly without checking how this logic interacts with:

- stage-layer retention
- `_ETL_LOAD_DATETIME`
- file-based replacement behavior
- the `2026-04-01` cutoff requirement

## Harmonization / Presentation Assessment

`orc_harmonization_pipeline_gcts` confirms the publish sequence:

```text
Start
  -> trn_v_int_dim_gcts_question
  -> DIM_GCTS_QUESTION
  -> trn_v_int_dim_gcts_option
  -> DIM_GCTS_OPTION
  -> trn_v_int_fact_gcts_response
  -> FACT_GCTS_RESPONSE
```

Plus:

- `trn_v_int_dim_gcts_country`
- `DIM_GCTS_COUNTRY`
- one-off `ALTER TABLE` for `FACT_GCTS_RESPONSE.OPEN_ANSWER`

This means the PL layer is still driven by the integration views, which is good for the requested change. It supports the earlier design idea:

- keep PL load wrappers largely unchanged
- change the source-side logic in integration and staging

## Unit Test Assessment

The fuller export also includes `orc_unit_test_gcts`.

Current tests compare:

- active staging counts vs PL counts for:
  - `DIM_GCTS_OPTION`
  - `DIM_GCTS_QUESTION`
  - `FACT_GCTS_RESPONSE`
- duplicate-key checks in PL objects

### Important implication

If the requested business change is implemented:

- latest-only for question
- latest-only for option
- mixed old/new logic for fact

then the current unit tests may no longer be valid, because they assume target row counts should match current active staging counts.

So unit-test adjustment should be part of the implementation scope.

## Fit-Gap Against The Business Request

## Request 1. Keep all Kantar data in staging

Current status:

- **not confirmed / likely not satisfied**

Reason:

- GCTS still calls `orc_load_stage_objects`
- that leads into `orc_update_indicator`
- and that framework includes delete/update/historization behavior

## Request 2. Stop deletion activity in staging

Current status:

- **likely not satisfied**

Reason:

- explicit stage delete/update components are still present in the called framework

## Request 3. Keep presentation behavior unchanged

Current status:

- **mostly achievable**

Reason:

- PL load wrappers can probably remain as-is
- but unit tests and source row-count assumptions may need revision

## Request 4. `trn_v_int_dim_gcts_question` should use latest `_ETL_LOAD_DATETIME`

Current status:

- **partially satisfied**

Reason:

- current job already keeps latest `_ETL_LOAD_DATETIME` per generated key
- but this is not the same as a global latest-load filter

## Request 5. `trn_v_int_dim_gcts_option` should use latest `_ETL_LOAD_DATETIME`

Current status:

- **not satisfied**

Reason:

- no visible latest-load logic in the current job

## Request 6. `trn_v_int_fact_gcts_response` should apply mixed old/new logic from `2026-04-01`

Current status:

- **not satisfied**

Reason:

- no visible cutoff logic
- no visible `_ETL_LOAD_DATETIME`-based branch

## Revised Key Conclusions

Compared with the old assessment, the new position is:

1. We now **do have** the real GCTS jobs needed for detailed assessment.
2. The earlier “missing job definition” warning is obsolete for `gcts_full.json`.
3. The staging-delete concern was valid and remains a major issue.
4. The requested transformation changes are only partially present today:
   - question: partly there
   - option: not there
   - fact: not there
5. The response ingestion design includes a separate `trn_load_gcts_from_do` preparation path, but that path is currently disabled and should be treated as inactive for normal scheduled-run assessment.
6. The Jira requirement and the data model both indicate that the main architectural tension is this:
   - old design assumption = active/current stage views
   - new requirement = historical stage retention with unchanged PL outcomes

## Recommended Next Steps

1. Trace exactly how GCTS uses `orc_load_stage_objects` and decide how to bypass or disable stage delete/update behavior for this pipeline.
2. Clarify whether question latest-load logic should be:
   - global latest batch
   - or latest row per business key
3. Update `trn_v_int_dim_gcts_option` to include explicit latest-load logic.
4. Update `trn_v_int_fact_gcts_response` to implement the `2026-04-01` cutoff rule by `YEAR, MONTH, COUNTRYCATEGORYID`.
5. Update `orc_unit_test_gcts` so tests reflect the new business behavior rather than simple active-stage-to-PL row parity.
6. Only if the initial-load path is ever reactivated, reassess `trn_load_gcts_from_do` together with the new fact rule so logic is not duplicated or contradicted.

## Final Conclusion

`gcts_full.json` gives a much clearer and more actionable picture than the earlier `GCTS.json`.

The current GCTS pipeline is real, specific, and assessable. It also shows that the requested business change is **not** just a small SQL tweak in one place. The real implementation scope is:

- staging-retention behavior
- option transformation logic
- fact transformation logic
- likely question-grain confirmation
- unit-test updates

For `DODECOM-7399`, the main answer is now clear:

- the first thing to do is not to jump directly into the 3 transformation tickets
- the first thing to do is to define how GCTS staging will stop deleting data while still allowing downstream logic to expose the intended current/latest result set

So the refreshed assessment is:

- the earlier documentation was directionally useful
- but `gcts_full.json` shows the actual implementation gap more precisely
- the Jira text clarifies the exact successor tickets and source-data behavior
- the data model confirms that the original design was built around active-view consumption
- and confirms that both staging and integration layers need attention
