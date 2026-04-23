# GCTS Staging History And Prerequisites

## Purpose

This note answers two questions:

1. Why was delete / soft-delete behavior likely used in the GCTS staging layer?
2. What should be done first if the new requirement is to keep historical data in staging without unintentionally changing Presentation Layer results?

This note is based on the fuller export:

- `gcts_full.json`
- `ticket_requirement.txt`
- `GCTS Data Model/Full Physical Report.html`

and should be read together with:

- `gcts_pipeline_assessment.md`

## Jira Context

This note supports:

- `DODECOM-7399` - Assess GCTS pipeline

and prepares the follow-up implementation tickets:

- `DODECOM-7400` - Adjust `trn_v_int_dim_gcts_question`
- `DODECOM-7401` - Adjust `trn_v_int_dim_gcts_option`
- `DODECOM-7402` - Adjust `trn_v_int_fact_gcts_response`

The parent business objective from `DODECOM-7398` is:

- keep historical GCTS data available
- stop deletion activity in staging
- preserve Presentation Layer behavior as much as possible

## Extra Context From The Ticket And Data Model

The ticket text adds these useful operating assumptions:

- Kantar pushes 4 tables:
  - Responses
  - Options
  - Question Map
  - Country Category
- each push cycle should contain 1 file per table
- more than 1 push cycle can happen in a month
- the supplied ticket text describes:
  - Responses = Delta
  - Options = Full
  - Question Map = Full
- the Country Category availability-type line appears incomplete in the provided text and should be reconfirmed

The data model adds an important architectural clue:

- the original modeled downstream design was based on active/current stage views such as:
  - `V_GCTS_OPTIONS`
  - `V_GCTS_QUESTION_MAP`
  - `V_GCTS_RESPONSE`
- model notes also reference `_ETL_ACTIVE_FLAG=true`

That means the original design assumption was closer to:

- active-view-based staging consumption

not:

- full historical retained staging consumption

This explains why the new requirement creates an architectural change, not just a small SQL update.

## Part 1. Why Previous Engineering Likely Used Delete Logic In Staging

The delete or soft-delete behavior in staging was most likely intentional.

It was probably designed to make the staging layer behave like a:

- current-state layer
- synchronized active layer
- controlled latest-version layer

rather than a:

- raw historical landing layer
- permanent full-retention archive

## What In The Export Suggests This

The GCTS ingestion flow still calls the shared framework:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

Inside `orc_update_indicator`, the export includes components such as:

- `Delete records from Stage table`
- `Create queries to delete and insert records`
- `Check track changes`
- `tmpt_trn_create_history_table`

That is not the pattern of a simple append-only landing zone. It is the pattern of a managed staging framework that compares source and target and then decides how to keep the stage layer aligned.

The data model supports this interpretation as well, because the modeled downstream logic was documented against active stage views and `_ETL_ACTIVE_FLAG=true`, which is exactly the kind of design that often depends on stage update/delete handling.

## Most Likely Original Design Intent

The previous engineer was probably solving one or more of these needs.

### 1. Keep stage as the latest valid business state

If a new source file replaces older data, the stage layer is updated so downstream jobs read only the latest active version.

### 2. Prevent duplicate active rows

If the source re-sends a file, or sends a newer replacement batch, the framework can mark old rows as deleted or remove them from the active stage dataset.

### 3. Support track-changes logic

The framework name and components suggest it was built to:

- compare data
- determine what changed
- update indicators
- maintain history or delete/reinsert rows when necessary

### 4. Make downstream integration and presentation easier

If stage always exposes only the current active picture, downstream transformations become simpler because they do not need to separate:

- old loads
- new loads
- replacement batches
- historical superseded rows

## Why This Now Conflicts With The New Requirement

Your current business requirement is different from that original design.

The new requirement is effectively:

- keep all Kantar-delivered historical data in staging
- stop deletion activity in staging
- preserve Presentation Layer behavior by moving the filtering / latest-selection logic into the right transformations

So the design intent is changing from:

- `staging = current active synchronized state`

to:

- `staging = retained historical source data`

That is why the old delete logic may have made sense before, but now becomes the wrong behavior for this use case.

## Short Conclusion

The previous engineer likely used delete or soft-delete in staging to keep the stage layer aligned to the latest active business state and to simplify downstream consumption.

It was probably not accidental.

The issue is not that the old design was irrational. The issue is that the business requirement has changed.

---

## Part 2. What Should Be Done First Before Adjusting The 3 Transformations

If the goal is:

- keep historical data in staging
- but avoid changing Presentation Layer results unexpectedly

then yes, there are prerequisites that should be completed **before** changing:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

## Short Answer

Do **not** start by editing the 3 transformations immediately.

First, confirm how GCTS ingestion currently shapes and deletes stage data, and define what the new “historical staging” contract should be.

Otherwise there is a real risk that:

- staging keeps more history
- but the 3 transformations still interpret the data incorrectly
- or Presentation Layer row counts change unexpectedly

This matters even more because the Jira requirement suggests mixed source behavior:

- Responses behave like delta data
- Options and Question Map behave like full data

So the retained-history design may not have the same downstream handling rule for every object.

## Recommended Prerequisites

## 1. Confirm The New Staging Contract

Before changing any transformation, define exactly what “keep historical data” means.

Questions to settle:

- Should every file load remain in stage forever?
- Should superseded rows remain physically present but inactive?
- Should `_ETL_ACTIVE_FLAG` still be maintained?
- Should `_ETL_RECORD_INDICATOR = 'D'` still exist at all for GCTS?
- Should stage be append-only, or append-with-flags?

This is the most important prerequisite because the 3 transformations depend on what stage is supposed to represent.

## 2. Identify Exactly Where GCTS Deletion Happens

Before changing the 3 transformations, trace which parts of GCTS staging currently do delete/update behavior.

Based on the export, the main path to inspect is:

- `orc_ingestion_gcts`
- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`

Goal:

- identify which step marks, deletes, or rebuilds stage records
- determine whether GCTS can bypass this framework
- or whether the framework needs a GCTS-specific switch / condition

If this is not done first, the 3 transformations may be redesigned against an unstable upstream behavior.

## 3. Decide Whether Historical Retention Is Needed For All GCTS Stage Objects

Do not assume the same answer for every table.

The GCTS objects have different roles:

- `T_GCTS_QUESTION_MAP`
- `T_GCTS_OPTIONS`
- `T_GCTS_COUNTRY_CATEGORY`
- `T_GCTS_RESPONSE`

Possible outcome:

- historical retention may be needed for all four
- or only for response
- or only for question / option / response

This point is important because the Jira text suggests the table-delivery behavior is not uniform across all 4 Kantar objects.

This matters because the transformation changes are targeted to question, option, and response only.

## 4. Validate The Control Column Strategy

Before changing the transformations, confirm which metadata columns will be the authoritative history controls.

Likely candidates:

- `_ETL_LOAD_DATETIME`
- `_ETL_ACTIVE_FLAG`
- `_ETL_RECORD_INDICATOR`
- file-name lineage columns such as `OCDI_SOURCE_FILE_NAME` or `_ETL_LOAD_FILE_NAME`

Questions:

- Will `_ETL_LOAD_DATETIME` remain the primary batch/version selector?
- If all history is retained, should `_ETL_ACTIVE_FLAG` still identify current rows?
- Do the target transformations rely on `_ETL_ACTIVE_FLAG`, `_ETL_LOAD_DATETIME`, or both?

The 3 transformation changes should only be done after this is clear.

## 5. Capture A Baseline Before Any Ingestion Change

Before changing staging behavior, capture the current baseline for:

- stage row counts
- integration row counts
- presentation row counts
- duplicate patterns
- `_ETL_LOAD_DATETIME` distributions

At minimum, capture:

- counts by `_ETL_LOAD_DATETIME`
- counts by business key
- counts by `YEAR, MONTH, COUNTRYCATEGORYID` for response
- current PL counts for:
  - `DIM_GCTS_QUESTION`
  - `DIM_GCTS_OPTION`
  - `FACT_GCTS_RESPONSE`

This baseline is necessary so that after changing ingestion, you can prove whether the transformation redesign preserved PL behavior.

## 6. Decide The Order Of Change: Ingestion First Or Transformations First

The safest sequence is usually:

1. define the new staging behavior
2. prepare the new transformation logic
3. change ingestion/staging retention behavior in lower environment
4. run the 3 updated transformations against retained-history stage data
5. compare Presentation Layer outputs before and after

Reason:

- if you change ingestion first without prepared transformation logic, PL output may drift
- if you change transformations first while staging still deletes history, the new logic is not really being tested against the future state

So the practical answer is:

- design both together
- implement in a controlled order
- validate together

## 7. Reassess Unit Tests Before Release

Current `orc_unit_test_gcts` compares active staging counts to PL counts.

If historical staging is retained, those tests may no longer represent the intended rule.

So before final release, decide whether unit tests should check:

- stage active rows
- latest-load rows
- grouped latest rows
- or final expected integration result sets

This is a prerequisite for safe deployment, even if it happens after coding.

## Practical Recommendation For Your Specific Change

If the goal is to keep PL outputs stable while preserving history in stage, the recommended approach is:

### A. First adjust the ingestion/staging rule conceptually

Target behavior:

- keep historical rows in stage
- stop GCTS-specific delete/remove behavior
- preserve enough metadata so current/latest rows can still be selected downstream

### B. Then adjust only the 3 transformations to control what remains visible downstream

Use the transformations to decide what Presentation Layer should still see:

- `trn_v_int_dim_gcts_question`
  - latest-only logic
- `trn_v_int_dim_gcts_option`
  - latest-only logic
- `trn_v_int_fact_gcts_response`
  - mixed old/new logic based on `2026-04-01`

### C. Keep the PL load wrappers unchanged if possible

This remains the safest strategy because:

- `orc_harmonization_pipeline_gcts`
- `DIM_GCTS_QUESTION`
- `DIM_GCTS_OPTION`
- `FACT_GCTS_RESPONSE`

can keep publishing from integration views, while the new filtering happens upstream.

## What Must Be Done Before Editing The 3 Jobs

If you want the shortest possible prerequisite checklist, it is this:

1. Confirm how GCTS will retain history in staging.
2. Confirm where GCTS delete/update behavior must be bypassed or disabled.
3. Confirm `_ETL_LOAD_DATETIME` is the correct versioning field for all 3 target datasets.
4. Capture current baseline counts in stage, integration, and presentation.
5. Confirm whether question latest logic should be global latest batch or latest per business key.
6. Confirm that unit tests will be updated to match the new intended behavior.

## Final Conclusion

Yes, there are important prerequisites before changing the 3 target transformations.

The key principle is:

- do not treat the 3 transformation changes as isolated SQL edits

Because once staging stops deleting history, the meaning of the stage layer changes. That upstream contract must be clarified first, or the downstream transformations may be redesigned against the wrong assumptions.

The safest strategy is:

- define the new staging retention behavior first
- prepare the 3 transformations to preserve PL results intentionally
- validate both together in a lower environment
