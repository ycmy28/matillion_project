# GCTS Historical Staging Options

## Purpose

This document compares the main design options for keeping historical GCTS data in Snowflake staging while still supporting the current and future implementation plan.

It is intended to align with the existing documents in `gcts_full`, especially:

- `gcts_pipeline_assessment.md`
- `gcts_staging_history_prerequisites.md`
- `gcts_recommended_implementation_sequence.md`

## Context

The current GCTS pipeline was originally designed around:

- active/current stage behavior
- stage views such as `V_GCTS_*`
- shared stage delete/update logic
- downstream integration and presentation jobs that expect curated current-state inputs

The new business requirement changes that direction:

- keep historical GCTS data
- stop deletion activity in staging
- keep Presentation Layer behavior as stable as possible

That means the team needs a staging-history strategy that works for both:

- current implementation constraints
- future adjustment of:
  - `trn_v_int_dim_gcts_question`
  - `trn_v_int_dim_gcts_option`
  - `trn_v_int_fact_gcts_response`

## Important Constraint

S3 should not be treated as the guaranteed long-term history store.

Reason:

- the GCTS pipeline uses S3 ingestion templates
- some template behavior can delete processed source files
- even if not every GCTS path deletes source files today, the pipeline is not designed as a durable archive mechanism

So if historical retention is required, the safest place to preserve it is Snowflake.

## Option 1. Append History Directly Into Existing `T_GCTS_*` Stage Tables

### Description

Use the current GCTS stage tables as both:

- the retained history store
- the source for downstream current/latest logic

In this design, the existing `T_GCTS_*` tables become multi-version tables that contain all historical loads.

### How it fits the current pipeline

- requires the smallest physical-model change
- reuses current stage table names
- requires the largest logical change in downstream interpretation

### Pros

- simplest object design
- lowest additional storage footprint
- no need to create a second layer of historical tables
- fastest to start implementing

### Cons

- highest downstream regression risk
- changes the meaning of existing stage tables immediately
- all stage consumers must now handle historical versions correctly
- current views and tests may stop representing the right business state
- fact/dim transformations become more sensitive to filtering mistakes
- harder to rollback cleanly

### Current implementation impact

- high
- stage meaning changes immediately
- hidden dependencies on `T_GCTS_*` may break

### Future implementation impact

- high
- the 3 target jobs must carry more responsibility for correcting upstream history accumulation
- any missed filter could change Presentation Layer outputs

### Cost / performance view

- lowest storage cost
- potentially higher compute/query cost over time as stage tables grow
- higher engineering/support cost due to regression risk

### Best use case

Use only if:

- the team wants the smallest physical design change
- downstream dependencies are fully known
- and the team accepts higher implementation risk

## Option 2. Create Separate Historical Load Tables (`HL`) And Keep Current Stage Logic Separate

### Description

Create a dedicated historical layer or table set for GCTS, for example:

- `HL_GCTS_RESPONSE`
- `HL_GCTS_OPTIONS`
- `HL_GCTS_QUESTION_MAP`
- `HL_GCTS_COUNTRY_CATEGORY`

These tables become the retained history store, while the existing stage/current objects continue to represent the active/current version.

### How it fits the current pipeline

- preserves the old current-stage assumption better
- introduces a new layer specifically for retention
- makes history explicit and isolated

### Pros

- lowest downstream regression risk
- preserves current-state consumption pattern more easily
- easier rollback
- easier to validate history separately from current-state logic
- easier to optimize historical storage independently

### Cons

- more objects to manage
- more storage usage
- ingestion design becomes more complex
- team must maintain both current-state and historical paths

### Current implementation impact

- medium
- current jobs can often stay closer to existing behavior
- staging retention becomes a separate concern

### Future implementation impact

- medium
- the 3 target jobs can be adjusted in a controlled way
- history can be validated separately before changing downstream logic

### Cost / performance view

- higher storage cost than Option 1
- lower downstream compute pressure if current-state objects stay lean
- lower engineering/support risk cost

### Best use case

Use if:

- preserving current downstream behavior is a priority
- the team wants a safer migration path
- history needs to be retained clearly and explicitly

## Option 3. Hybrid: Historical Tables Plus Controlled Current Views Or Current Tables

### Description

This is the recommended balance.

In this design:

- historical rows are retained in dedicated history tables
- current-stage views or current-stage tables expose the active/latest business slice
- the 3 target transformations apply the approved visibility rules intentionally

In practice, this means:

1. retain all history in Snowflake
2. stop GCTS-specific delete/remove behavior for historical storage
3. keep a current-facing layer for downstream jobs
4. update the 3 target jobs where the business rule explicitly requires it

### How it fits the current pipeline

- aligns best with the old active-view design
- allows the new historical requirement without breaking everything at once
- gives the team a clear separation between:
  - retained history
  - current/latest consumption

### Pros

- best balance of safety and flexibility
- preserves history in Snowflake
- keeps downstream current-state access cleaner
- aligns with the modeled `V_GCTS_*` style of consumption
- easier to test current-state and historical-state logic separately
- lower long-term total cost of ownership than forcing all logic into current stage tables

### Cons

- more design effort than Option 1
- more objects than Option 1
- requires clear governance for:
  - what counts as historical
  - what counts as current
  - where each consumer should read from

### Current implementation impact

- medium
- current pipeline can evolve with less disruption
- easier to map old behavior to new behavior

### Future implementation impact

- best controlled impact
- `trn_v_int_dim_gcts_question` can apply approved latest logic
- `trn_v_int_dim_gcts_option` can apply latest logic cleanly
- `trn_v_int_fact_gcts_response` can apply the `2026-04-01` mixed rule cleanly

### Cost / performance view

- higher storage cost than Option 1
- usually better downstream query performance than Option 1
- better total delivery efficiency when testing, support, and rollback are considered

### Best use case

Use if:

- the team wants the safest practical solution
- Presentation Layer stability matters
- historical retention must be reliable
- the team wants current and historical behavior to be understandable

## Option 4. Keep Current Stage Design, But Rely On S3 As The History Store

### Description

Do not retain full history in Snowflake staging. Instead, rely on the source files in S3 as the historical archive.

### Pros

- lowest Snowflake storage impact
- minimal Snowflake design change

### Cons

- not reliable for this pipeline
- processed S3 files may be deleted
- retrieval/replay becomes operationally difficult
- history is outside the warehouse where transformations run
- not aligned with the business request to keep data available operationally

### Current implementation impact

- low short-term change
- high future operational risk

### Future implementation impact

- poor
- makes debugging, replay, and validation harder
- does not give stable warehouse-side historical access

### Cost / performance view

- low Snowflake storage cost
- poor operational efficiency
- high support/recovery risk

### Recommendation

- not recommended

## Comparison Summary

### Option 1. Append history into existing `T_GCTS_*`

- Storage cost: Low
- Query/performance risk: Medium to High over time
- Engineering risk: High
- Regression risk: High
- Rollback ease: Low

### Option 2. Separate `HL` history tables

- Storage cost: Medium
- Query/performance risk: Low to Medium
- Engineering risk: Medium
- Regression risk: Low to Medium
- Rollback ease: High

### Option 3. Hybrid: `HL` + controlled current layer

- Storage cost: Medium
- Query/performance risk: Low
- Engineering risk: Medium
- Regression risk: Low
- Rollback ease: High

### Option 4. Rely on S3 history

- Storage cost in Snowflake: Low
- Operational risk: High
- Reliability: Low
- Recommended: No

## Recommended Strategy

The recommended strategy is:

- Option 3: Hybrid historical tables plus controlled current views/tables

### Why this is the best fit

It aligns best with both:

- the current implementation
- the future dim/fact adjustment tasks

It works because:

1. the old pipeline was designed around active/current stage consumption
2. the new business request requires historical retention
3. the 3 follow-up tickets require controlled visibility rules, not uncontrolled raw accumulation

### Practical target architecture

Recommended direction:

1. retain all GCTS history in Snowflake history tables
2. stop GCTS-specific delete behavior against the historical store
3. expose current/latest logic through controlled stage views or current-state tables
4. update the 3 target transformations to enforce the approved business rules
5. keep Presentation Layer load wrappers as stable as possible

## Recommendation For The 3 Follow-Up Tasks

If Option 3 is chosen:

### `trn_v_int_dim_gcts_question`

- validate whether current latest-per-key behavior is enough
- if not, adjust to the approved latest-selection rule

### `trn_v_int_dim_gcts_option`

- add explicit latest-load logic

### `trn_v_int_fact_gcts_response`

- implement the cutoff rule:
  - old groups before `2026-04-01` kept as-is
  - new groups on or after `2026-04-01` filtered to latest `_ETL_LOAD_DATETIME`

This gives the team the cleanest separation:

- staging retains history
- integration controls visibility
- presentation remains stable

## Final Conclusion

The practical design options are not all equal.

If the team wants:

- the lowest pure storage cost

then Option 1 is cheaper.

If the team wants:

- the best balance of cost, performance, implementation safety, and alignment with the current pipeline

then Option 3 is the strongest choice.

For GCTS, the best-fit recommendation is:

- retain history in separate historical tables
- keep a controlled current-facing layer
- adjust the 3 target transformations intentionally

That approach fits both the current assessment and the future implementation plan better than turning the existing stage tables directly into raw historical multi-version tables.
