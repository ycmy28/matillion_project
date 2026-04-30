# Harmonization JSON Generator Guide

This document explains how to run [generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generate_interactions_package.py), what it is meant to do, and what still needs manual review after generation.

## Scope

This script is intended for non-dimensional harmonization pipeline generation in this working style:

- TDE
- MDE

It is meant to imitate the original notebook flow in [script.ipynb](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/script.ipynb):

- read `table_header - ...xlsx`
- read `table_detail - ...xlsx`
- fill Matillion JSON templates
- generate orchestration/transformation package JSON from metadata

Then it adds the enhancement we validated earlier for Interactions:

- generate a consolidated package export
- optionally generate Interactions unit-test orchestration jobs
- allow the same script to be reused for other categories like GA later

## What Is Preserved From The Notebook

The script still follows the same core metadata-driven behavior as the notebook:

- `table_header` drives source/target table level settings
- `table_detail` drives target columns, formulas, data types, descriptions, classifications, and PKs
- template placeholders are replaced from Excel metadata
- filtered and non-filtered template selection is still driven from header metadata

So the base idea is still the same as the original notebook, but now packaged into a reusable Python CLI.

## Current Recommended Use

There are 2 supported ways to run the script:

- `interactions` preset
  This is the most validated flow.
- `generic` preset
  This is for other categories such as GA, as long as they follow the same metadata pattern.

## Prerequisite

Use the project virtual environment:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python --version
```

## 1. Run Interactions

This is the closest flow to the approved Interactions package.

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py
```

Default Interactions behavior:

- preset: `interactions`
- header file: `table_header - interactions.xlsx`
- detail file: `table_detail - interactions.xlsx`
- output: [INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.generated.json)
- tree path: `02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/INTERACTIONS`
- unit tests: enabled
- top-level transformation jobs: disabled by default

## 2. Run Interactions With Top-Level Transformations

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --include-transformations \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.with_transformations.generated.json
```

Use this only if you explicitly want `transformationJobs` included at the top level of the export.

## 3. Run Another Category Such As GA

For categories other than Interactions, use the `generic` preset.

Example:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --preset generic \
  --header-file "table_header - GA.xlsx" \
  --detail-file "table_detail - GA.xlsx" \
  --package-name GA \
  --tree-path "02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/GA" \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/GA.generated.json
```

That generates:

- [GA.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/GA.generated.json)

Generic mode defaults:

- unit tests: disabled
- top-level transformation jobs: disabled
- templates:
  - `matillion_full.json`
  - `matillion_full_filter.json`

## 4. Run Another Future Category

If a future category follows the same metadata structure, use the same pattern:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --preset generic \
  --header-file "table_header - <CATEGORY>.xlsx" \
  --detail-file "table_detail - <CATEGORY>.xlsx" \
  --package-name <CATEGORY_NAME> \
  --tree-path "02_DATA_WAREHOUSE/03_PRESENTATION/<FOLDER_PATH>" \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/<CATEGORY_NAME>.generated.json
```

## Interactions Validation Status

The Interactions flow was specifically checked against the approved file:

- Approved file: [INTERACTIONS.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.json)
- Generated file: [INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.generated.json)

What matched at a high level:

- same package structure in `jobsTree`
- same count of orchestration jobs
- same TDE/MDE grouping
- same shared-job reference pattern such as `SCD2_DELTA_V3`
- same harmonization grid population pattern

Important reminder:

- the generated file is very similar, but it is not guaranteed to be byte-for-byte identical to the approved export
- regenerated IDs, tags, timestamps, export version, and some SQL text formatting may differ

## Caveats And Manual Checks After Every Run

This script reduces manual work, but the output still must be reviewed after generation.

Always check these items:

- imported/exported Matillion version differences
- shared job references that are not embedded directly in the JSON export
- filter metadata in the header file
- primary keys and BK ordering
- data type mappings from the Excel file
- generated SQL or transformation formulas for table-specific logic
- folder path and package naming in `jobsTree`
- duplicate rows in the header file

## Important Reminders For Metadata

- `primary_key_flag = Y` in the detail file drives the generated PK configuration.
- The script assumes the Excel structure matches the notebook style.
- If filter metadata is incomplete, the non-filter template path is used.
- If a category has extra logic not captured in Excel, the generated JSON will still need manual adjustment.
- Unit-test generation is currently intended for the Interactions pattern only.
- For categories other than Interactions, the script currently focuses on harmonization package generation, not category-specific unit-test logic.

## Known Example Caveat

Current GA metadata contains a duplicate:

- `DIM_DIGITAL_DEVICE` appears twice in [table_header - GA.xlsx](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/table_header%20-%20GA.xlsx)

So the generated GA export will also include it twice unless that metadata is corrected first.

## Recommended Workflow

1. Prepare the `table_header` and `table_detail` Excel files.
2. Run the script with the correct preset.
3. Review the generated JSON file.
4. Compare it with the target/approved pattern if one already exists.
5. Adjust metadata or JSON if category-specific logic is still missing.
6. Only then continue with import or handoff.

## Reference Files

- Script: [generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generate_interactions_package.py)
- Original notebook: [script.ipynb](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/script.ipynb)
- Approved Interactions export: [INTERACTIONS.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.json)
- Generated Interactions export: [INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.generated.json)
- Generated GA export: [GA.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/GA.generated.json)
