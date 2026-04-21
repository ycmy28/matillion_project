# GCTS Matillion Pipeline Assessment

## Scope

This assessment is based on the exported Matillion JSON file:

- `/Users/ycmy28/Documents/Matillion_PMI/GCTS_Project/GCTS.json`

The main pipeline identified in the export is:

- `pipe_e2e_master_gcts`

## Executive Summary

`pipe_e2e_master_gcts` is the top-level orchestration entry point for the GCTS package in this export. Its visible flow is very short:

1. Start
2. Run `orc_ingestion_gcts`
3. On success, run `orc_harmonization_pipeline_gcts`

So the intended end-to-end behavior is:

- ingest GCTS source data first
- then run harmonization / downstream processing

However, the export is only partially self-contained. The definitions of:

- `orc_ingestion_gcts`
- `orc_harmonization_pipeline_gcts`

are referenced by the master job but are not embedded as full orchestration objects in this JSON export. Because of that, this file lets us confirm the top-level control flow, but it does not fully expose the detailed GCTS business transformation logic.

## Confirmed Master Pipeline Flow

### Pipeline Location in the Export

```text
ROOT
└── 01_PIPELINE_ORC
    └── 01_MASTER_PIPELINE
        └── CONS_GCTS_Pipeline
            └── pipe_e2e_master_gcts
```

### Confirmed Orchestration Sequence

```text
Start
  |
  v
orc_ingestion_gcts
  |
  v
orc_harmonization_pipeline_gcts
```

### What This Means

The master pipeline is acting as an end-to-end controller, not as a transformation-heavy job by itself. Its purpose is to ensure that:

- data ingestion finishes first
- harmonization only starts after ingestion succeeds

This is a standard Matillion orchestration pattern where the master pipeline coordinates sub-jobs rather than doing the row-level work directly.

## What Is Actually Included in the Export

Besides the master pipeline, the JSON contains reusable template jobs under:

```text
ROOT/05_TEMPLATE_JOBS/09_INGESTION
```

The included jobs are:

- `orc_load_stage_objects`
- `orc_run_group_calc`
- `orc_update_indicator`
- `tmpt_trn_create_history_table`
- `orc_ingestion_s3_main`
- `sub_orc_ingestion_s3`
- `sub_orc_ingestion_s3_stage_layer`
- `sub_orc_ingestion_s3_load_data`
- `orc_ingestion_s3_main_v2`
- `sub_orc_ingestion_s3_v2`
- `sub_orc_ingestion_s3_stage_layer_v2`
- `sub_orc_ingestion_s3_load_data_v2`

These appear to be shared ingestion and soft-delete/history-building templates that GCTS likely depends on.

## Inferred Functional Design

Based on the included template jobs, the GCTS flow most likely follows this operating model:

1. Read source files from S3 or an external stage
2. Create raw load tables
3. Load file content into raw/load-layer tables
4. Add ETL metadata
5. Move data from load layer into stage layer
6. Apply change-tracking / soft-delete handling
7. Run harmonization logic after staging is ready

## Included Template Data Flow

### 1. S3 Ingestion Controller

The included orchestration templates `orc_ingestion_s3_main` and `orc_ingestion_s3_main_v2` show a reusable ingestion pattern:

```text
Start
  |
  v
Variable Management
  |
  v
Grid Iterator
  |
  v
sub_orc_ingestion_s3(_v2)
```

This means ingestion is metadata-driven. A grid variable supplies a list of tables / prefixes, and the same logic is reused across multiple source objects.

### 2. Per-Object Ingestion

`sub_orc_ingestion_s3` and `sub_orc_ingestion_s3_v2` perform per-table ingestion:

```text
Filter table column
  -> Variable Management
  -> Create Load Table
  -> Add Load Layer Metadata - Load Table
  -> Decide default stage vs external stage
  -> Iterate files
  -> Load each file
  -> Delete temporary raw-load tables
  -> Optionally load stage layer per table
```

This shows that the pipeline is designed to:

- derive load-table structure from metadata
- support both default-stage and external-stage loading
- iterate file-by-file when needed
- optionally stage data immediately after each file or table load

### 3. File Load Logic

`sub_orc_ingestion_s3_load_data` and `_v2` reveal the file-level logic:

```text
Create Raw Load Table
  -> Parse File Config
  -> If CSV:
       -> If Default Stage -> load CSV
       -> else -> load CSV from external stage
  -> If JSON:
       -> load JSON from external stage
  -> Add Load Layer Metadata
  -> Insert into Load table
  -> Optionally trigger stage-layer load
```

Important observations:

- default file type variable is `json`
- CSV and JSON are both supported
- load-layer metadata is added before insertion into the final load table
- stage-layer loading can happen immediately depending on `jv_load_stage_per_file`

### 4. Stage Layer Load

`sub_orc_ingestion_s3_stage_layer` and `_v2` show the stage-load pattern:

```text
Get the list of source files
  -> Check if data needs processing
  -> If yes, run stage-layer load
  -> Generate cleanup query
  -> Optionally remove processed source files
```

This indicates the framework prevents unnecessary stage reloads and can clean up processed files after successful load.

## Soft Delete / Historization Logic Included in the Export

The `Partial Delete` template jobs show how stage records can be marked or rebuilt when source deltas indicate change.

### Flow

```text
orc_load_stage_objects
  -> determine run group
  -> iterate source objects
  -> orc_update_indicator
```

`orc_update_indicator` contains the main change-handling logic:

- derive source and target table names
- fetch business key from metadata view `V_DATA_OBJECT`
- inspect column datatypes from `INFORMATION_SCHEMA.COLUMNS`
- split compare columns into varchar vs non-varchar logic
- build dynamic SQL
- either:
  - soft-delete existing stage rows by setting `_ETL_RECORD_INDICATOR = 'D'`
  - or delete/reinsert records based on earliest load timestamps

### Included Transformation

The only transformation job physically included in the export is:

- `tmpt_trn_create_history_table`

Its logic is simple:

1. run a SQL query stored in `jv_sql_string_1`
2. write the result into a target delete/history table

This means the template is used as a helper step inside the larger update / soft-delete orchestration.

## Important Assessment: What The GCTS Pipeline Most Likely Does

From the visible structure, the intended GCTS end-to-end pipeline is:

1. `pipe_e2e_master_gcts` starts the end-to-end run
2. `orc_ingestion_gcts` ingests raw GCTS source data into Snowflake load/stage layers
3. shared ingestion templates likely perform file discovery, raw load creation, metadata enrichment, and stage loading
4. shared partial-delete logic likely handles change tracking and history/deletion indicators in stage
5. `orc_harmonization_pipeline_gcts` then transforms staged GCTS data into downstream harmonized outputs

In short, the data flow is best understood as:

```text
GCTS source files
  -> raw load tables
  -> load layer
  -> stage layer
  -> harmonization pipeline
  -> curated downstream outputs
```

## What Cannot Be Confirmed From This Export Alone

This is the biggest limitation in the file.

The export does not include the actual internal job definitions for:

- `orc_ingestion_gcts`
- `orc_harmonization_pipeline_gcts`

Because of that, the following are not directly confirmable from this JSON:

- exact GCTS source object names
- actual GCTS staging schema/table names
- business transformation rules inside harmonization
- final target schemas/tables/views published by GCTS
- column-level mappings
- any GCTS-specific joins, filters, deduplication rules, or calculations

## Evidence That The Included Templates Are Generic, Not GCTS-Specific

Several default variable values in the included template jobs refer to other domains, for example:

- `STG_LOAD_IXOPAY`
- `POSTBUY`
- `T_E2OPEN_E2ASPDLEVELFCST`
- `T_LOAD_AW_CUSTOMER`

This strongly suggests the export includes reusable shared framework jobs rather than a complete GCTS-only package. So these templates tell us how the framework works, but not the full GCTS business mapping.

## Final Conclusion

Yes, the main pipeline is `pipe_e2e_master_gcts`.

What it does, based on the exported JSON, is:

- orchestrate the GCTS end-to-end processing
- run GCTS ingestion first
- then run GCTS harmonization

What we can confidently say about the data flow:

- it is orchestration-led
- it uses reusable metadata-driven S3/external-stage ingestion patterns
- it supports JSON and CSV loading
- it includes stage-layer loading and optional source-file cleanup
- it includes reusable soft-delete/history logic for staged objects

What we cannot fully validate from this export:

- the detailed GCTS business transformation logic inside ingestion and harmonization
- the exact final GCTS target tables/views

## Recommended Next Step

To produce a full GCTS data-flow document with source-to-target mapping, the next export should also include:

- the full definition of `orc_ingestion_gcts`
- the full definition of `orc_harmonization_pipeline_gcts`
- any GCTS-specific transformation jobs called by harmonization

With that, it would be possible to document:

- exact source objects
- stage/intermediate/final tables
- transformation sequence
- column-level mapping and business rules
