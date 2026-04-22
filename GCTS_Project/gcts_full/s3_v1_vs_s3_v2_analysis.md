# S3 v1 vs S3 v2 Analysis

## Files Compared

- `s3_v1.json`
- `s3_v2.json`

## Executive Summary

`S3 v2` is mostly an evolution of `S3 v1`, not a full redesign. The overall orchestration layout is still the same:

- main orchestration job
- table-level ingestion subjob
- load-data subjob
- stage-layer subjob

The most important functional changes are:

1. The file lineage / processed-file metadata column was renamed from `OCDI_SOURCE_FILE_NAME` to `_ETL_LOAD_FILE_NAME`.
2. The stage-layer orchestration in `v2` adds an extra component called `Load Stage Layer Rev5`.
3. Job and folder names were versioned with `_v2` / `Rev5`, but most variables, grids, and control-flow structure remain the same.

## High-Confidence Differences

### 1. Metadata column rename

This is the clearest behavioral change across the workflow.

In `s3_v1`:

- load-table metadata uses `OCDI_SOURCE_FILE_NAME`
- raw-load metadata uses `OCDI_SOURCE_FILE_NAME`
- processed-file lookup reads `OCDI_SOURCE_FILE_NAME`
- generated query reads `ocdi_source_file_name`

In `s3_v2`:

- load-table metadata uses `_ETL_LOAD_FILE_NAME`
- raw-load metadata uses `_ETL_LOAD_FILE_NAME`
- processed-file lookup reads `_ETL_LOAD_FILE_NAME`
- generated query reads `_etl_load_file_name`

### 2. New stage-layer component in v2

`sub_orc_ingestion_s3_stage_layer_v2` contains one extra component that does not exist in `v1`:

- `Load Stage Layer Rev5`

Observations:

- `Load Stage Layer - Node 0` still exists in `v2`
- both components are triggered from `If - Any table with new data`
- `Generate Query` now waits on `Load Stage Layer Rev5`, not on `Load Stage Layer - Node 0`
- both stage-layer components use schema-drift handling and the same `gv_source_objects` mapping

This suggests `v2` introduces an additional stage-load path rather than simply renaming the original node.

## Job-Level Comparison

### Main orchestration

`orc_ingestion_s3_main` vs `orc_ingestion_s3_main_v2`

- Same 4-component pattern
- Same variables and grids
- Only substantive difference is that the child orchestration now points to `sub_orc_ingestion_s3_v2`

### Table-level ingestion orchestration

`sub_orc_ingestion_s3` vs `sub_orc_ingestion_s3_v2`

- Same 15-component structure
- Same variables and grids
- Child orchestration names were updated to `_v2`
- One detected parameter difference in `File Iterator - file list` is only mapping order, not behavior
- `Add Load Layer Metadata - Load Table` changed the metadata column from `OCDI_SOURCE_FILE_NAME` to `_ETL_LOAD_FILE_NAME`

### Stage-layer orchestration

`sub_orc_ingestion_s3_stage_layer` vs `sub_orc_ingestion_s3_stage_layer_v2`

- `v2` has 10 components vs 9 in `v1`
- New component: `Load Stage Layer Rev5`
- `Generate Query` changed from:
  - `ocdi_source_file_name`
  to:
  - `_etl_load_file_name`
- `Get Processed File Name` grid mapping changed from:
  - `TABLE_NAME, OCDI_SOURCE_FILE_NAME`
  to:
  - `TABLE_NAME, _ETL_LOAD_FILE_NAME`

### Load-data orchestration

`sub_orc_ingestion_s3_load_data` vs `sub_orc_ingestion_s3_load_data_v2`

- Same 14-component structure
- Same variables and grids
- Child stage-layer orchestration renamed to `_v2`
- `Add Load Layer Metadata` changed the metadata column from `OCDI_SOURCE_FILE_NAME` to `_ETL_LOAD_FILE_NAME`

## Impact Assessment

### Functional impact

If downstream logic, audit tables, reports, or existing SQL still expect `OCDI_SOURCE_FILE_NAME`, `v2` may break that dependency unless those consumers are updated to `_ETL_LOAD_FILE_NAME`.

### Processed-file deletion logic

The delete-from-S3 logic still reads filenames from `gv_processed_file`. Because `v2` also updates the query and grid mapping to `_ETL_LOAD_FILE_NAME`, that flow appears internally consistent.

### Migration risk

The biggest migration risk is not the orchestration structure itself. It is the metadata column rename, because it changes how loaded files are tracked in staging/load tables.

The second risk is the new `Load Stage Layer Rev5` component, because it adds another stage-layer execution path. Without runtime testing, this should be treated as a meaningful behavior change.

## What Did Not Materially Change

- top-level orchestration design
- main variables and grid definitions
- CSV/JSON branching pattern
- per-table iteration pattern
- delete-source-file option
- external-stage vs default-stage branching

## Recommendation

Before replacing `v1` with `v2`, verify these points in a lower environment:

1. All downstream objects that previously referenced `OCDI_SOURCE_FILE_NAME` are updated to `_ETL_LOAD_FILE_NAME`.
2. `Load Stage Layer Rev5` is expected and does not duplicate or conflict with `Load Stage Layer - Node 0`.
3. File deletion still removes the correct S3 objects after stage processing completes.

## Conclusion

`S3 v2` is largely backward-similar in structure, but it is not a cosmetic rename. The export shows one clear metadata-model change and one clear stage-layer execution change:

- `OCDI_SOURCE_FILE_NAME` was replaced by `_ETL_LOAD_FILE_NAME`
- a second stage-layer component (`Load Stage Layer Rev5`) was added into the success path

Those are the two areas that deserve focused validation before adoption.
