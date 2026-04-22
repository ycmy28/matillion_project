# GCTS Short Checklist

## Purpose

This is the short version of the GCTS action plan before changing:

- `trn_v_int_dim_gcts_question`
- `trn_v_int_dim_gcts_option`
- `trn_v_int_fact_gcts_response`

## Do This First

1. Confirm the new staging rule.
   - Decide whether GCTS staging becomes append-only or append-with-flags.
   - Confirm whether `_ETL_LOAD_DATETIME` is the main versioning field.

2. Identify where GCTS staging delete/update happens.
   - Trace:
     - `orc_ingestion_gcts`
     - `orc_load_stage_objects`
     - `orc_run_group_calc`
     - `orc_update_indicator`
   - Decide how GCTS will stop deleting stage history.

3. Capture the current baseline.
   - Save row counts for stage, integration, and presentation.
   - Save counts by `_ETL_LOAD_DATETIME`.
   - Save response counts by `YEAR, MONTH, COUNTRYCATEGORYID`.

4. Confirm the exact business rules for the 3 target jobs.
   - Question: latest global batch or latest per business key?
   - Option: latest global batch or latest per business key?
   - Fact: confirm the `2026-04-01` cutoff rule.

5. Confirm unit-test impact.
   - Current tests assume active stage counts match PL counts.
   - Decide how tests should work after stage history is retained.

## Then Do This

6. Adjust ingestion/staging behavior first in lower environment.
   - Stop GCTS-specific delete/update behavior.
   - Keep historical rows in stage.

7. Adjust the 3 transformations.
   - `trn_v_int_dim_gcts_question`
   - `trn_v_int_dim_gcts_option`
   - `trn_v_int_fact_gcts_response`

8. Update the unit test job.
   - Make tests validate the new intended output, not raw retained stage counts.

9. Run end-to-end validation.
   - Compare before/after counts.
   - Validate sample business outputs.
   - Confirm PL behavior remains acceptable.

## Release Reminder

10. Release ingestion + transformation + unit-test changes together.

## Key Principle

Do not treat this as only 3 SQL changes.

The staging behavior must be clarified first, or the dimension and fact changes may be designed against the wrong upstream logic.
