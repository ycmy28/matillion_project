# GCTS Risk Of No Assessment Or No Adjustment

## Purposes

This document explains what can happen if:

- the GCTS assessment is not performed properly
- the requested transformation adjustments are not implemented

The focus is on business impact, data impact, and technical risk.

## Context

Requested business intent:

- keep all Kantar data available in GCTS Staging Layer
- stop deletion activity in Staging Layer
- keep Presentation Layer behavior unchanged
- adjust 3 integration transformations:
  - `trn_v_int_dim_gcts_question`
  - `trn_v_int_dim_gcts_option`
  - `trn_v_int_fact_gcts_response`

If this is not assessed and not adjusted correctly, there is a high risk that the system continues to behave in a way that no longer matches the business requirement.

## Short Summary

If we do nothing:

- GCTS staging may continue deleting or soft-deleting data
- Consumer Node may lose historical Kantar-delivered records from stage
- the 3 integration outputs may continue to show outdated or duplicated records
- reporting may not reflect the intended old-vs-new Kantar load behavior
- future troubleshooting becomes harder because data loss and logic mismatch remain hidden

## Risk If We Skip The Assessment

## 1. We Might Change The Wrong Job

The current export does not include the full target job definitions.

If we skip assessment:

- we may implement change in the wrong transformation
- we may edit only integration logic while the real issue is in staging deletion
- we may miss shared framework jobs that are actually causing the problem

Consequence:

- effort is spent, but the business issue remains unresolved

## 2. We Might Misunderstand The Source Table Or Grain

If we do not inspect the real source tables and transformation logic:

- we may apply “latest `_ETL_LOAD_DATETIME` only” at the wrong level
- we may treat a table-level max as correct when the real logic should be per business key
- we may accidentally remove valid records

Consequence:

- silent data loss in integration outputs
- broken dimensional completeness
- inconsistent reporting behavior

## 3. We Might Break Presentation Layer Indirectly

The request says to keep Presentation Layer as-is.

If the assessment is skipped:

- row counts may change unexpectedly in integration
- downstream PL jobs may receive fewer or differently-shaped records
- dashboards or published outputs may change without warning

Consequence:

- business users may see unexplained movement in metrics
- trust in the data product may decline

## 4. We Might Miss The Real Staging Delete Mechanism

If we do not trace the orchestration and shared framework:

- staging delete logic may continue running
- data may still be marked deleted or removed in stage
- transformation-only changes may partially hide the issue but not solve it

Consequence:

- Kantar data is still not fully retained
- root cause remains active in the platform

## Risk If We Do Not Adjust The Transformations

## 1. `trn_v_int_dim_gcts_question` May Continue Returning Wrong Batch Scope

Expected business intent:

- only latest `_ETL_LOAD_DATETIME` should be used

If not adjusted:

- old and new loads may continue to mix together
- duplicate or outdated question records may remain visible
- the dimension may not represent the latest Kantar picture

Business impact:

- analytics using question metadata may become inconsistent
- current reporting may be driven by stale mappings

## 2. `trn_v_int_dim_gcts_option` May Continue Returning Wrong Batch Scope

Expected business intent:

- only latest `_ETL_LOAD_DATETIME` should be used

If not adjusted:

- outdated option records may remain active in integration
- consumers may see options from superseded loads
- dimension logic may drift away from the intended business state

Business impact:

- reporting and downstream joins may use stale option definitions
- interpretation of response data may become less reliable

## 3. `trn_v_int_fact_gcts_response` May Continue Applying One Rule To Two Different Business Eras

Expected business intent:

- old data before `2026-04-01` should retain all versions
- new data from `2026-04-01` onward should keep only latest-load rows per `YEAR, MONTH, COUNTRYCATEGORYID`

If not adjusted:

- new replacement-style loads may still accumulate multiple versions
- response fact may double count or over-retain new data
- historical and current ingestion patterns remain mixed incorrectly

Business impact:

- measures based on response fact may be overstated
- trend analysis may become inconsistent
- users may compare old and new periods incorrectly because the storage logic differs but the transformation does not

## Business Consequences Of Doing Nothing

## 1. Loss Of Confidence In GCTS Data

Users may notice:

- duplicate-looking records
- unexplained count changes
- mismatch between expected Kantar replacement behavior and visible outputs

Consequence:

- manual reconciliations increase
- user trust drops
- support effort rises

## 2. More Manual Investigation Effort

Without assessment and adjustment:

- every future data issue may require repeated root-cause analysis
- support teams may need to compare stage, integration, and presentation repeatedly
- debugging becomes slower because the logic remains misaligned with the business rule

Consequence:

- operational support cost increases

## 3. Rework Later Becomes More Expensive

If the issue is left unresolved:

- more loads accumulate under the wrong logic
- more downstream consumers depend on compromised outputs
- remediation later becomes larger and riskier

Consequence:

- bigger change window later
- more test effort
- more business disruption during cleanup

## Technical Consequences Of Doing Nothing

## 1. Stage And Integration Logic Stay Misaligned

If stage keeps all data only partially, or deletes some records, while integration still assumes old logic:

- source behavior and transformation behavior drift apart

Consequence:

- the pipeline becomes harder to reason about
- defects become more likely in future enhancements

## 2. Duplicate Versions Remain In New Response Loads

If new replacement-style batches are not filtered to latest load:

- multiple versions of the same logical group may coexist in integration

Consequence:

- inflated facts
- inconsistent downstream totals
- possible duplicate joins into Presentation Layer

## 3. Historical Retention May Be Lost In The Wrong Place

If someone later makes a rushed fix without assessment:

- they might remove all older versions globally
- they might destroy legitimate old-history behavior before `2026-04-01`

Consequence:

- valid old data gets lost
- business history becomes incomplete

## Worst-Case Scenario

The worst case is not just “the logic stays wrong.”

The real worst case is:

1. GCTS Staging Layer continues deleting or suppressing Kantar records.
2. The 3 transformation jobs continue exposing a mixture of stale and replacement-style loads.
3. `trn_v_int_fact_gcts_response` overstates new-period data because multiple replacement versions remain included.
4. Downstream Presentation Layer keeps publishing outputs that appear valid but are semantically wrong.
5. Business users make decisions based on duplicated, outdated, or incomplete data.
6. The issue is discovered only much later, after multiple reporting cycles.
7. Remediation then requires:
   - root cause analysis
   - backfill or rebuild
   - user communication
   - report revalidation
   - possible historical restatement

This is the most expensive outcome because the problem affects:

- data correctness
- user trust
- operational support effort
- remediation effort

## Worst Case By Object

## `trn_v_int_dim_gcts_question`

Worst case:

- outdated and latest question mappings are mixed together
- downstream reports use inconsistent question definitions

## `trn_v_int_dim_gcts_option`

Worst case:

- outdated option values stay active
- response interpretation becomes incorrect

## `trn_v_int_fact_gcts_response`

Worst case:

- post-`2026-04-01` data is effectively over-counted because replacement batches stack up
- old-history behavior and new-replacement behavior are merged incorrectly
- fact-level reporting becomes materially wrong

## `Staging Layer`

Worst case:

- historical Kantar deliveries are no longer fully available
- root-cause analysis becomes impossible because source-stage history is missing

## Risk Severity View

### Severity If We Skip Assessment

- `High`

Reason:

- high chance of incomplete or incorrect implementation

### Severity If We Skip Transformation Adjustment

- `High`

Reason:

- direct risk of stale, duplicate, or mis-scoped integration outputs

### Severity If We Skip Staging Deletion Adjustment

- `High`

Reason:

- direct risk of losing retained source history that the business explicitly wants to preserve

## Why The Assessment Matters

The assessment is important because it prevents two common failure modes:

1. fixing only the visible symptom
2. implementing the right idea in the wrong layer

The business request spans both:

- staging behavior
- integration behavior

Without assessment, it is easy to address only one side and still leave the real issue active.

## Final Recommendation

Do not skip the assessment, and do not skip the transformation adjustments.

Minimum safe path:

1. confirm real Matillion job definitions
2. confirm staging delete mechanism for GCTS
3. implement the 3 transformation adjustments
4. validate outputs before and after
5. regression-test Presentation Layer

## Final Summary

If no assessment or adjustment is done, the most likely result is continued logic mismatch.

If things go badly, the worst-case result is:

- retained Kantar history is lost in stage
- new-period response data is overstated or duplicated
- dimensions expose stale mappings
- downstream reporting becomes wrong
- remediation later becomes much more expensive than fixing it now
