# Harmonization JSON Generator Guide

This guide explains how to run the harmonization JSON generator, how the folder is organized, what Python requirements are needed, and what still must be reviewed after generation.

## Scope

This generator is intended for non-dimensional harmonization pipeline JSON generation in this scope:

- `TDE`
- `MDE`

It is designed to preserve the original metadata-driven behavior from [script.ipynb](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/script.ipynb):

- read `table_header - ...xlsx`
- read `table_detail - ...xlsx`
- fill Matillion JSON templates
- generate orchestration/transformation JSON from metadata

Then it adds the enhancements we validated for Interactions:

- reusable CLI instead of notebook-only execution
- consolidated package output
- optional Interactions unit-test orchestration generation
- reusable generic mode for other categories such as `GA`

## Folder Structure

Current layout:

- root folder
  Keeps metadata Excel files, template JSON files, notebook files, approved reference JSON files, and a compatibility wrapper script.
- [scripts/generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/scripts/generate_interactions_package.py)
  Main implementation.
- [generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generate_interactions_package.py)
  Compatibility wrapper so the old run command still works.
- [docs/generate_interactions_package.md](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/docs/generate_interactions_package.md)
  This guide.
- [generated](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated)
  Generated output JSON files.
- [generator_requirements.txt](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generator_requirements.txt)
  Minimal Python library requirements for this generator.

## Python Requirements

Recommended Python:

- Python `3.10+`

Required libraries:

- `pandas`
- `openpyxl`

Reference file:

- [generator_requirements.txt](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generator_requirements.txt)

If you want to install them manually in the project virtual environment:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/pip install -r matillion_project/harmo_pipeline_generator/generator_requirements.txt
```

If your `venv` already has them, you do not need to reinstall anything.

## Recommended Entrypoint

To preserve the old behavior, use the wrapper path:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py
```

This wrapper simply delegates to the implementation in `scripts/`.

## 1. Run Interactions

This is the most validated flow and the closest to the approved Interactions package.

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py
```

Default Interactions behavior:

- preset: `interactions`
- header file: `table_header - interactions.xlsx`
- detail file: `table_detail - interactions.xlsx`
- output: [generated/INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/INTERACTIONS.generated.json)
- tree path: `02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/INTERACTIONS`
- unit tests: enabled
- top-level transformation jobs: disabled by default

## 2. Run Interactions With Top-Level Transformations

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --include-transformations \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/INTERACTIONS.with_transformations.generated.json
```

Use this only if you explicitly want top-level `transformationJobs` included in the export.

## 3. Run GA Or Another Category

For categories other than Interactions, use the `generic` preset.

Example for GA:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --preset generic \
  --header-file "table_header - GA.xlsx" \
  --detail-file "table_detail - GA.xlsx" \
  --package-name GA \
  --tree-path "02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/GA" \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/GA.generated.json
```

That generates:

- [generated/GA.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/GA.generated.json)

Generic mode defaults:

- unit tests: disabled
- top-level transformation jobs: disabled
- templates:
  - `matillion_full.json`
  - `matillion_full_filter.json`

## 4. Run A Future Category

If another category follows the same metadata structure, use the same pattern:

```bash
cd /Users/ycmy28/Documents/Matillion_PMI
./venv/bin/python matillion_project/harmo_pipeline_generator/generate_interactions_package.py \
  --preset generic \
  --header-file "table_header - <CATEGORY>.xlsx" \
  --detail-file "table_detail - <CATEGORY>.xlsx" \
  --package-name <CATEGORY_NAME> \
  --tree-path "02_DATA_WAREHOUSE/03_PRESENTATION/<FOLDER_PATH>" \
  --output /Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/<CATEGORY_NAME>.generated.json
```

## What Is Preserved From The Notebook

The script still follows the same core metadata-driven behavior as the original notebook:

- `table_header` drives source/target table-level settings
- `table_detail` drives target columns, formulas, data types, descriptions, classifications, and PKs
- filtered and non-filtered template choice still comes from header metadata
- placeholders are still replaced from Excel-driven metadata

So the generation approach remains generic in the same spirit as the notebook, while the Interactions preset adds the approved package-style enhancement layer.

## Interactions Validation Status

The Interactions flow was compared against the approved file:

- Approved file: [INTERACTIONS.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.json)
- Generated file: [generated/INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/INTERACTIONS.generated.json)

High-level similarity confirmed:

- same `jobsTree` package shape
- same orchestration job count
- same `TDE` / `MDE` grouping pattern
- same shared-job reference pattern such as `SCD2_DELTA_V3`
- same harmonization grid population pattern

Important reminder:

- the generated file is very similar, but not guaranteed to be byte-for-byte identical
- regenerated IDs, tags, timestamps, export version, and some SQL text formatting may differ

## Caveats And Manual Checks After Every Run

This script reduces manual work, but the generated file still needs manual review after every run.

Always check:

- Matillion export version differences
- shared jobs or shared components referenced externally and not embedded directly in the JSON export
- filter metadata completeness in the header file
- PK and BK ordering
- data type mappings from the Excel metadata
- generated SQL or transformation formulas for category-specific logic
- `jobsTree` folder path and package naming
- duplicated metadata rows in header files
- whether the generated output still needs final JSON adjustments before leader review or Matillion import

## Important Metadata Reminders

- `primary_key_flag = Y` in the detail file drives generated PK configuration.
- the script assumes the Excel schema matches the notebook style
- if filter metadata is incomplete, the non-filter template path is used
- if a category has logic not represented in Excel or templates, manual adjustment is still needed
- unit-test generation is currently intended for the Interactions pattern only
- for non-Interactions categories, the current supported target is harmonization package generation rather than category-specific unit-test logic

## Known Example Caveat

Current GA metadata contains a duplicate:

- `DIM_DIGITAL_DEVICE` appears twice in [table_header - GA.xlsx](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/table_header%20-%20GA.xlsx)

So the generated GA export will also include it twice unless the metadata is corrected first.

## Recommended Workflow

1. Prepare or update the `table_header` and `table_detail` Excel files.
2. Run the generator with the right preset.
3. Review the generated file under `generated/`.
4. Compare it with an approved or target pattern if one exists.
5. Adjust metadata or final JSON if category-specific logic is still missing.
6. Only then continue with handoff, review, or Matillion import.

## Reference Files

- Wrapper script: [generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generate_interactions_package.py)
- Main implementation: [scripts/generate_interactions_package.py](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/scripts/generate_interactions_package.py)
- Original notebook: [script.ipynb](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/script.ipynb)
- Approved Interactions export: [INTERACTIONS.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/INTERACTIONS.json)
- Generated Interactions export: [generated/INTERACTIONS.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/INTERACTIONS.generated.json)
- Generated Interactions export with transformations: [generated/INTERACTIONS.with_transformations.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/INTERACTIONS.with_transformations.generated.json)
- Generated GA export: [generated/GA.generated.json](/Users/ycmy28/Documents/Matillion_PMI/matillion_project/harmo_pipeline_generator/generated/GA.generated.json)
