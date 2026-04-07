# Interactions Data Pipeline Documentation
**End-to-End Pipeline: DCE2 Interaction Harmonization to Snowflake Presentation Layer**

## Table of Contents
1. [Pipeline Overview](#pipeline-overview)
2. [Architecture](#architecture)
3. [Master Pipeline](#master-pipeline)
4. [Ingestion Layer](#ingestion-layer)
5. [Integration Layer (INT)](#integration-layer-int)
6. [MDE Transformation Logic](#mde-transformation-logic)
7. [TDE Transformation Logic](#tde-transformation-logic)
8. [Presentation Layer (PL)](#presentation-layer-pl)
9. [Data Flow](#data-flow)
10. [Configuration](#configuration)
11. [Error Handling](#error-handling)
12. [Tables and Views](#tables-and-views)
13. [Business Use Cases](#business-use-cases)
14. [Dependencies](#dependencies)
15. [Maintenance and Operations](#maintenance-and-operations)
16. [Contact and Support](#contact-and-support)

---

## Pipeline Overview

**Pipeline Name:** `orc_master_e2e_dce2_lz_pipeline`  
**Source System:** DCE2 interaction data in Snowflake staging  
**Target System:** Snowflake presentation layer  
**Data Domain:** Consumer interactions / engagement events

### Purpose
This pipeline harmonizes DCE2 interaction data from staging into curated integration views and presentation-layer tables. The documented scope covers interaction facts plus related detail entities used to analyze how consumers engage across channels and supporting interaction objects.

The pipeline produces:
- A consolidated interaction table for TDE reporting
- Interaction detail tables for MDE analysis:
  - Device
  - Flavour
  - Product
  - Voucher
- Unit-test orchestration jobs for each published object

### Pipeline Scope Captured in the Export
The `Interactions_matillion.json` export clearly includes:
- The master orchestration entry point
- Integration transformation jobs
- Presentation harmonization jobs
- Unit-test jobs

The export does not expose the same level of ingestion internals as the Google Analytics package, so the ingestion section below is intentionally documented at a higher level.

---

## Architecture

### Layer Structure

```text
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER PIPELINE                              │
│                orc_master_e2e_dce2_lz_pipeline                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────────┐      ┌──────────────────────────┐
│  INGESTION FLOW   │      │   HARMONIZATION LAYER    │
│  (LZ/STG load)    │      │   (INT -> PL)            │
└───────────────────┘      └──────────────────────────┘
                                      │
                          ┌───────────┴───────────┐
                          │                       │
                          ▼                       ▼
                    ┌────────────┐         ┌────────────┐
                    │INTEGRATION │         │PRESENTATION│
                    │   (INT)    │         │   (PL)     │
                    └────────────┘         └────────────┘
```

### Data Layers

| Layer | Database | Schema | Purpose |
|-------|----------|--------|---------|
| **Staging** | `${ev_database_10_staging}` | `STG_DCE2` | Raw interaction objects loaded for processing |
| **Integration** | `${ev_database_20_integration}` | `${ev_data_foundation_schema_20_integration}` | Standardized interaction views |
| **Presentation** | `${ev_database_30_presentation}` | `PL_INTERACTION` | Business-ready SCD2-style curated tables |
| **DQ Support** | `${ev_database_30_presentation}` | `PL_COMMON_LAYER_DQ` | Data-quality companion targets referenced by create-table jobs |

---

## Master Pipeline

### File Location

```text
ROOT/01_PIPELINE_ORC/01_MASTER_PIPELINE/CONS_DCE2_LZ_PIPELINE/
└── orc_master_e2e_dce2_lz_pipeline.ORCHESTRATION
```

### Pipeline Flow

```text
Start
  │
  ├─► Query Tag Start
  │     └─ ALTER SESSION SET query_tag = '${job_name}-${run_history_id}'
  │
  ├─► DISP Ingestion - CONS 1
  │     ├─ jv_source_name = dce2
  │     ├─ jv_output_tenant_name = edp_consumer
  │     └─ triggers downstream harmonization based on ingestion outcomes
  │
  ├─► orc_harmonization_rde_bridge_consumer_rls 0
  │     └─ additional harmonization/bridge step referenced by the master job
  │
  └─► Task History Load
        └─ logs execution status and completes the run
```

### Key Observations

- The master job sets a Snowflake query tag for traceability.
- It dispatches ingestion through a reusable orchestrator component.
- It finishes with task-history logging.
- The detailed per-table ingestion logic is not fully expanded in this export, unlike the Google Analytics export.

---

## Ingestion Layer

### What Is Visible in the Export

The master orchestration contains a component named `DISP Ingestion - CONS 1` with:
- `jv_source_name = dce2`
- `jv_output_tenant_name = edp_consumer`
- `jv_process_table` available for scoped execution
- `gv_trigger_harmonization` as a downstream trigger grid

### Inferred Ingestion Role

Based on the orchestration metadata, the ingestion layer appears to:
- Load DCE2 interaction entities into staging
- Drive harmonization by passing downstream orchestration mappings
- Support selective processing by source table or object

### Staging Objects Used by the Interactions Package

The integration transformations read from these staging tables in `STG_DCE2`:
- `T_DCE2_INTERACTION`
- `T_DCE2_INTERACTION_DEVICE`
- `T_DCE2_INTERACTION_FLAVOUR`
- `T_DCE2_INTERACTION_PRODUCT`
- `T_DCE2_INTERACTION_VOUCHER`

---

## Integration Layer (INT)

### File Location

```text
ROOT/02_DATA_WAREHOUSE/02_INTEGRATION/DCE2/INTERACTIONS/
├── MDE/
│   ├── trn_v_int_mde_consumer_interaction_device.TRANSFORMATION
│   ├── trn_v_int_mde_consumer_interaction_flavour.TRANSFORMATION
│   ├── trn_v_int_mde_consumer_interaction_product.TRANSFORMATION
│   └── trn_v_int_mde_consumer_interaction_voucher.TRANSFORMATION
└── TDE/
    └── trn_v_int_tde_consumer_interaction.TRANSFORMATION
```

### Integration Job Inventory

| Category | Transformation Job | Staging Source | Integration Output |
|----------|--------------------|----------------|--------------------|
| MDE | `trn_v_int_mde_consumer_interaction_device` | `STG_DCE2.T_DCE2_INTERACTION_DEVICE` | `V_INT_MDE_CONSUMER_INTERACTION_DEVICE` |
| MDE | `trn_v_int_mde_consumer_interaction_flavour` | `STG_DCE2.T_DCE2_INTERACTION_FLAVOUR` | `V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR` |
| MDE | `trn_v_int_mde_consumer_interaction_product` | `STG_DCE2.T_DCE2_INTERACTION_PRODUCT` | `V_INT_MDE_CONSUMER_INTERACTION_PRODUCT` |
| MDE | `trn_v_int_mde_consumer_interaction_voucher` | `STG_DCE2.T_DCE2_INTERACTION_VOUCHER` | `V_INT_MDE_CONSUMER_INTERACTION_VOUCHER` |
| TDE | `trn_v_int_tde_consumer_interaction` | `STG_DCE2.T_DCE2_INTERACTION` | `V_INT_TDE_CONSUMER_INTERACTION` |

### Common Transformation Pattern

All five interaction transformations follow the same core pattern:

```text
Staging Table Input
  │
  ├─► Filter - Bad Data Quality
  ├─► Add Tmp Columns for Historization
  ├─► Calculator - column transformations
  ├─► Select Column
  └─► View creation in integration schema
```

### Shared Transformation Controls

Each transformation uses:
- Scalar variable: `jv_source_table`
- Grid variables:
  - `gv_calculator`
  - `gv_table_input_column_list`

This indicates a metadata-driven pattern where column lists and output mappings are controlled through Matillion grids rather than hard-coded component definitions.

### PowerDesigner-Aligned Transformation Rules

The PowerDesigner physical model adds several implementation details that are only implicit in the Matillion JSON:
- Source staging tables are documented as physical inputs under `DB_CONS_STG_PRD.STG_DCE2`
- All five published objects are modeled as `SCD2`
- All five published objects are documented with `Load type: DELTA`
- Every object applies a timestamp quality rule before publication:
  - `TRY_TO_TIMESTAMP_NTZ(date_time) <= __LOAD_TS OR TRY_TO_TIMESTAMP_NTZ(date_time) IS NULL`
- Every object derives `VALID_FROM` with the same general rule:
  - use `INTERACTION_DATETIME` when it is present and the row is the surviving duplicate candidate
  - otherwise fall back to `__LOAD_TS`
- Every object uses duplicate handling based on:
  - `COUNT(*) OVER (...) AS dup_cnt`
  - `ROW_NUMBER() OVER (... ORDER BY __load_ts ASC) AS rn_by_load_ts`

### Historization and Deduplication Logic

The model shows a consistent historization pattern across all interaction entities:

```text
1. Read from staging table in STG_DCE2
2. Parse interaction timestamp with TRY_TO_TIMESTAMP_NTZ(date_time)
3. Exclude records where business timestamp is after ingestion timestamp
4. Partition by object business keys plus interaction timestamp
5. Compute duplicate count and earliest-load row number
6. Set VALID_FROM to interaction timestamp when usable
7. Otherwise set VALID_FROM to __LOAD_TS
8. Publish as SCD2-ready output with VALID_FROM / VALID_TO / ACTIVE_FLAG
```

### Row-Level Security Pattern

The PowerDesigner report also documents an RLS pattern for the presentation objects:
- RLS is implemented through country-based filtering
- RLS uses `MDE_GIGYA_CONSUMER` as the consumer alignment object
- The join condition aligns records by `IDENTITY_UNIQUE_IDENTIFIER_BK` and validity window
- Access is granted when either the consumer country or the interaction country matches `#RLS_LIST_OF_COUNTRIES`

---

## MDE Transformation Logic

The MDE layer publishes interaction detail entities that enrich the primary interaction event with lower-grain supporting attributes.

### 1. Device Interaction View

**Job:** `trn_v_int_mde_consumer_interaction_device`  
**Output:** `V_INT_MDE_CONSUMER_INTERACTION_DEVICE`

PowerDesigner model details:
- Physical source: `DB_CONS_STG_PRD.STG_DCE2.T_DCE2_INTERACTION_DEVICE`
- Source-to-target key mapping:
  - `identity_unique_identifier -> IDENTITY_UNIQUE_IDENTIFIER_BK`
  - `interaction_id -> INTERACTION_IDENTIFIER_BK`
  - `devices_device_id -> DEVICE_IDENTIFIER_BK`
- Duplicate partition:
  - `identity_unique_identifier, interaction_id, devices_device_id, date_time`
- Historization type: `SCD2`
- Load type: `DELTA`
- Target schema: `PL_INTERACTION`

Key mapped columns include:
- `DEVICE_IDENTIFIER_BK`
- `IDENTITY_UNIQUE_IDENTIFIER_BK`
- `INTERACTION_IDENTIFIER_BK`
- `BRAND_FAMILY_NAME`
- `COUNTRY_CODE`
- `DEVICE_DESCRIPTION`
- `DEVICE_TYPE`
- `DEVICE_VERSION`
- `INTERACTION_DATETIME`
- `VALID_FROM`
- `VALID_TO`
- `ACTIVE_FLAG`

Additional model-backed notes:
- `INTERACTION_DATETIME` is derived from `TRY_TO_TIMESTAMP_NTZ(d.date_time)`
- `VALID_FROM` uses `INTERACTION_DATETIME` when the row is valid and selected as the surviving duplicate, otherwise `d.__load_ts`
- The physical table is modeled with a non-enforced primary key on `DEVICE_IDENTIFIER_BK, IDENTITY_UNIQUE_IDENTIFIER_BK, INTERACTION_IDENTIFIER_BK`

### 2. Flavour Interaction View

**Job:** `trn_v_int_mde_consumer_interaction_flavour`  
**Output:** `V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR`

PowerDesigner model details:
- Physical source: `DB_CONS_STG_PRD.STG_DCE2.T_DCE2_INTERACTION_FLAVOUR`
- Source-to-target key mapping:
  - `identity_unique_identifier -> IDENTITY_UNIQUE_IDENTIFIER_BK`
  - `interaction_id -> INTERACTION_IDENTIFIER_BK`
  - `flavours_flavour_refcode -> FLAVOUR_REFERENCE_CODE_BK`
- Duplicate partition:
  - `identity_unique_identifier, interaction_id, flavours_flavour_refcode, date_time`
- Historization type: `SCD2`
- Load type: `DELTA`
- Target schema: `PL_INTERACTION`

Key mapped columns include:
- `FLAVOUR_REFERENCE_CODE_BK`
- `IDENTITY_UNIQUE_IDENTIFIER_BK`
- `INTERACTION_IDENTIFIER_BK`
- `COUNTRY_CODE`
- `FLAVOUR_REFERENCE_NAME`
- `INTERACTION_DATETIME`
- `VALID_FROM`
- `VALID_TO`
- `ACTIVE_FLAG`

Additional model-backed notes:
- `FLAVOUR_REFERENCE_NAME` comes from `flavours_flavour_refname`
- `VALID_FROM` uses the shared timestamp-or-load-ts rule
- The physical table is modeled with a non-enforced primary key on `FLAVOUR_REFERENCE_CODE_BK, IDENTITY_UNIQUE_IDENTIFIER_BK, INTERACTION_IDENTIFIER_BK`

### 3. Product Interaction View

**Job:** `trn_v_int_mde_consumer_interaction_product`  
**Output:** `V_INT_MDE_CONSUMER_INTERACTION_PRODUCT`

PowerDesigner model details:
- Physical source: `DB_CONS_STG_PRD.STG_DCE2.T_DCE2_INTERACTION_PRODUCT`
- Source-to-target key mapping:
  - `identity_unique_identifier -> IDENTITY_UNIQUE_IDENTIFIER_BK`
  - `interaction_id -> INTERACTION_IDENTIFIER_BK`
  - `products_product_id -> PRODUCT_IDENTIFIER_BK`
- Duplicate partition:
  - `identity_unique_identifier, interaction_id, products_product_id, date_time`
- Historization type: `SCD2`
- Load type: `DELTA`
- Target schema: `PL_INTERACTION`

Key mapped columns include:
- `IDENTITY_UNIQUE_IDENTIFIER_BK`
- `INTERACTION_IDENTIFIER_BK`
- `PRODUCT_IDENTIFIER_BK`
- `COUNTRY_CODE`
- `INTERACTION_DATETIME`
- `PRODUCT_NAME`
- `VALID_FROM`
- `VALID_TO`
- `ACTIVE_FLAG`

Additional model-backed notes:
- `PRODUCT_NAME` comes from `products_product_name`
- `PRODUCT_IDENTIFIER_BK` is documented in the model as a derived asset identifier that can align with product code usage in downstream reporting
- The physical table is modeled with a non-enforced primary key on `IDENTITY_UNIQUE_IDENTIFIER_BK, INTERACTION_IDENTIFIER_BK, PRODUCT_IDENTIFIER_BK`

### 4. Voucher Interaction View

**Job:** `trn_v_int_mde_consumer_interaction_voucher`  
**Output:** `V_INT_MDE_CONSUMER_INTERACTION_VOUCHER`

PowerDesigner model details:
- Physical source: `DB_CONS_STG_PRD.STG_DCE2.T_DCE2_INTERACTION_VOUCHER`
- Source-to-target key mapping:
  - `identity_unique_identifier -> IDENTITY_UNIQUE_IDENTIFIER_BK`
  - `interaction_id -> INTERACTION_IDENTIFIER_BK`
  - `vouchers_voucher_id -> VOUCHER_IDENTIFIER_BK`
- Duplicate partition:
  - `identity_unique_identifier, interaction_id, vouchers_voucher_id, date_time`
- Historization type: `SCD2`
- Load type: `DELTA`
- Target schema: `PL_INTERACTION`

Key mapped columns include:
- `IDENTITY_UNIQUE_IDENTIFIER_BK`
- `INTERACTION_IDENTIFIER_BK`
- `VOUCHER_IDENTIFIER_BK`
- `COUNTRY_CODE`
- `INTERACTION_DATETIME`
- `VOUCHER_AMOUNT`
- `VOUCHER_NAME`
- `VALID_FROM`
- `VALID_TO`
- `ACTIVE_FLAG`

Additional model-backed notes:
- `VOUCHER_AMOUNT` is physically modeled as `DECIMAL(38,5)`
- The model documents a left join variant to `MDE_GIGYA_CONSUMER` in the voucher RLS section
- The physical table is modeled with a non-enforced primary key on `IDENTITY_UNIQUE_IDENTIFIER_BK, INTERACTION_IDENTIFIER_BK, VOUCHER_IDENTIFIER_BK`

### Shared MDE Security Pattern

The physical model documents an RLS sharing pattern for MDE outputs:
- `DEVICE`, `FLAVOUR`, and `PRODUCT` use an inner join to `MDE_GIGYA_CONSUMER`
- `VOUCHER` uses a left join in the documented sharing script
- Validity alignment is based on `VALID_FROM >= c.VALID_FROM` and `VALID_FROM < c.VALID_TO`
- Country filtering checks both consumer country and object country

---

## TDE Transformation Logic

### Core Interaction View

**Job:** `trn_v_int_tde_consumer_interaction`  
**Output:** `V_INT_TDE_CONSUMER_INTERACTION`

This transformation creates the consolidated interaction view used by the presentation-layer interaction fact-like table.

PowerDesigner model details:
- Physical source: `DB_CONS_STG_PRD.STG_DCE2.T_DCE2_INTERACTION`
- Source-to-target key mapping:
  - `identity_unique_identifier -> IDENTITY_UNIQUE_IDENTIFIER_BK`
  - `interaction_id -> INTERACTION_IDENTIFIER_BK`
- Duplicate partition:
  - `identity_unique_identifier, interaction_id, date_time`
- Historization type: `SCD2`
- Load type: `DELTA`
- Target schema: `PL_INTERACTION`

Representative output columns include:
- `IDENTITY_UNIQUE_IDENTIFIER_BK`
- `INTERACTION_IDENTIFIER_BK`
- `AGENT_IDENTIFIER`
- `AGE_VERIFICATION_STATUS`
- `APPOINTMENT_IDENTIFIER`
- `BRAND_FAMILY_NAME`
- `CAMPAIGN_IDENTIFIER`
- `CASE_IDENTIFIER`
- `CASE_TYPE`
- `CHANNEL_REFERENCE_CODE`
- `COACH_IDENTIFIER`
- `CONTRACT_IDENTIFIER`
- `CORRELATION_IDENTIFIER`
- `COUNTRY_CODE`
- `CURRENCY_CODE`
- `DOCUMENT_TYPE`
- `EVENT_IDENTIFIER`
- `EXTERNAL_REFERENCE`
- `FINAL_RESULT`
- `INTERACTION_DATETIME`
- `INTERACTION_REASON`
- `INTERACTION_REASON_IDENTIFIER`
- `INTERACTION_TYPE_REFERENCE_CODE`
- `IP_ADDRESS`
- `MARKET_CODE`
- `ORDER_AMOUNT`
- `ORDER_IDENTIFIER`
- `PAYMENT_METHOD`
- `PLATFORM_BRAND`
- `PREFERRED_PLATFORM`
- `PRODUCT_CATEGORY`
- `PRODUCT_CODE`
- `RETAILER_IDENTIFIER`
- `RETAILER_NAME`
- `SOURCE_SYSTEM_IDENTIFIER`
- `VENDOR_NAME`
- `VALID_FROM`
- `VALID_TO`
- `ACTIVE_FLAG`

Additional PowerDesigner-mapped fields include:
- `COUNTRY_REFERENCE_CODE`
- `LOCATION_ADDRESS_COUNTRY_REFERENCE_CODE`
- `MARKET_REFERENCE_CODE`
- `TECH_PARTITION_YEAR`
- `TECH_PARTITION_MONTH`

Selected source-to-target examples from the model:
- `agent_id -> AGENT_IDENTIFIER`
- `channel_refcode -> CHANNEL_REFERENCE_CODE`
- `reason_refcode -> INTERACTION_REASON_REFERENCE_CODE`
- `sap_id -> INTERACTION_SAP_IDENTIFIER`
- `session_id -> INTERACTION_SESSION_IDENTIFIER`
- `state_id -> AGE_VERIFICATION_STATUS`
- `subscription_id -> PARENT_ORDER_CODE`

### Transformation Characteristics

- Applies a bad-data-quality filter before publication
- Adds historization support columns
- Standardizes output through a calculator grid
- Publishes the result as an integration-layer view
- The physical table is modeled with a non-enforced primary key on `IDENTITY_UNIQUE_IDENTIFIER_BK, INTERACTION_IDENTIFIER_BK`
- `ORDER_AMOUNT` is modeled as `DECIMAL(38,5)`

### TDE Row-Level Security Pattern

The physical model documents TDE sharing through:
- a join from `TDE_CONSUMER_INTERACTION` to `MDE_GIGYA_CONSUMER`
- validity-window alignment on `VALID_FROM`
- country-based filtering using `#RLS_LIST_OF_COUNTRIES`

---

## Presentation Layer (PL)

### File Location

```text
ROOT/02_DATA_WAREHOUSE/03_PRESENTATION/DCE2/INTERACTIONS/
├── MDE/
│   ├── orc_harmonization_mde_consumer_interaction_device.ORCHESTRATION
│   ├── orc_harmonization_mde_consumer_interaction_flavour.ORCHESTRATION
│   ├── orc_harmonization_mde_consumer_interaction_product.ORCHESTRATION
│   └── orc_harmonization_mde_consumer_interaction_voucher.ORCHESTRATION
└── TDE/
    └── orc_harmonization_tde_consumer_interaction.ORCHESTRATION
```

### Harmonization Pattern

Each presentation orchestration follows a similar flow:

```text
Start
  │
  ├─► Get Staging Column List
  ├─► Retry - Initial
  ├─► Create Table - <target presentation object>
  │     └─ Loading type = SCD2_DELTA_V3
  ├─► trn_v_int_<...>
  ├─► Truncate Table <target>
  ├─► Delete Transient table 3
  ├─► Delete Tables 0
  └─► On failure: Send an Email with HTML Body type
```

### Presentation Objects

| Category | Harmonization Job | Source Integration View | Target Table | Schema | Primary Business Keys |
|----------|-------------------|-------------------------|--------------|--------|-----------------------|
| MDE | `orc_harmonization_mde_consumer_interaction_device` | `V_INT_MDE_CONSUMER_INTERACTION_DEVICE` | `MDE_CONSUMER_INTERACTION_DEVICE` | `PL_INTERACTION` | `DEVICE_IDENTIFIER_BK`, `IDENTITY_UNIQUE_IDENTIFIER_BK`, `INTERACTION_IDENTIFIER_BK` |
| MDE | `orc_harmonization_mde_consumer_interaction_flavour` | `V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR` | `MDE_CONSUMER_INTERACTION_FLAVOUR` | `PL_INTERACTION` | `FLAVOUR_REFERENCE_CODE_BK`, `IDENTITY_UNIQUE_IDENTIFIER_BK`, `INTERACTION_IDENTIFIER_BK` |
| MDE | `orc_harmonization_mde_consumer_interaction_product` | `V_INT_MDE_CONSUMER_INTERACTION_PRODUCT` | `MDE_CONSUMER_INTERACTION_PRODUCT` | `PL_INTERACTION` | `IDENTITY_UNIQUE_IDENTIFIER_BK`, `INTERACTION_IDENTIFIER_BK`, `PRODUCT_IDENTIFIER_BK` |
| MDE | `orc_harmonization_mde_consumer_interaction_voucher` | `V_INT_MDE_CONSUMER_INTERACTION_VOUCHER` | `MDE_CONSUMER_INTERACTION_VOUCHER` | `PL_INTERACTION` | `IDENTITY_UNIQUE_IDENTIFIER_BK`, `INTERACTION_IDENTIFIER_BK`, `VOUCHER_IDENTIFIER_BK` |
| TDE | `orc_harmonization_tde_consumer_interaction` | `V_INT_TDE_CONSUMER_INTERACTION` | `TDE_CONSUMER_INTERACTION` | `PL_INTERACTION` | `IDENTITY_UNIQUE_IDENTIFIER_BK`, `INTERACTION_IDENTIFIER_BK` |

### Table Descriptions

- `TDE_CONSUMER_INTERACTION`
  - Consolidated overview of consumer engagements across channels in the DCE2 ecosystem.
- `MDE_CONSUMER_INTERACTION_DEVICE`
  - Device-level context for interactions such as onboarding, troubleshooting, replacement, and usage.
- `MDE_CONSUMER_INTERACTION_FLAVOUR`
  - Flavour-level context supporting consumer preference and product-usage analysis.
- `MDE_CONSUMER_INTERACTION_PRODUCT`
  - Product or asset context linked to each consumer interaction.
- `MDE_CONSUMER_INTERACTION_VOUCHER`
  - Voucher usage details supporting promotional and discount analysis.

### Unit Test Jobs

The package also includes a unit-test orchestration per published object:
- `orc_unit_test_mde_consumer_interaction_device`
- `orc_unit_test_mde_consumer_interaction_flavour`
- `orc_unit_test_mde_consumer_interaction_product`
- `orc_unit_test_mde_consumer_interaction_voucher`
- `orc_unit_test_tde_consumer_interaction`

The unit-test jobs share a common structure:
- `Start`
- `Query Result To Grid`
- `Compare Tests Numbers`
- `If`
- `End Success`
- `End Failure`

---

## Data Flow

```text
DCE2 Source / Landing Data
  │
  ▼
Snowflake Staging
STG_DCE2.T_DCE2_INTERACTION*
  │
  ├─► trn_v_int_tde_consumer_interaction
  │     └─► V_INT_TDE_CONSUMER_INTERACTION
  │             └─► TDE_CONSUMER_INTERACTION
  │
  ├─► trn_v_int_mde_consumer_interaction_device
  │     └─► V_INT_MDE_CONSUMER_INTERACTION_DEVICE
  │             └─► MDE_CONSUMER_INTERACTION_DEVICE
  │
  ├─► trn_v_int_mde_consumer_interaction_flavour
  │     └─► V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR
  │             └─► MDE_CONSUMER_INTERACTION_FLAVOUR
  │
  ├─► trn_v_int_mde_consumer_interaction_product
  │     └─► V_INT_MDE_CONSUMER_INTERACTION_PRODUCT
  │             └─► MDE_CONSUMER_INTERACTION_PRODUCT
  │
  └─► trn_v_int_mde_consumer_interaction_voucher
        └─► V_INT_MDE_CONSUMER_INTERACTION_VOUCHER
                └─► MDE_CONSUMER_INTERACTION_VOUCHER
```

---

## Configuration

### Environment Variables Referenced

| Variable | Purpose |
|----------|---------|
| `ev_database_10_staging` | Staging database |
| `ev_database_20_integration` | Integration database |
| `ev_data_foundation_schema_20_integration` | Integration schema |
| `ev_database_30_presentation` | Presentation database |

### Common Orchestration Variables and Grids

| Name | Type | Purpose |
|------|------|---------|
| `jv_transient_has_count_check` | Scalar | Transient row-count / load control flag |
| `gv_transient_column_list` | Grid | Captures column metadata from staging |
| `gv_primary_key_configuration` | Grid | Defines business-key columns for target tables |
| `gv_column_classification_configuration` | Grid | Metadata-driven classification controls |
| `gv_column_description_configuration` | Grid | Metadata-driven descriptions for published columns |

### Transformation Variables and Grids

| Name | Type | Purpose |
|------|------|---------|
| `jv_source_table` | Scalar | Source table identifier |
| `gv_calculator` | Grid | Output column calculations and type casting |
| `gv_table_input_column_list` | Grid | Input column metadata for dynamic table reads |

---

## Error Handling

The presentation orchestration jobs include explicit failure-handling patterns:
- `Retry - Initial` components before the main create/load step
- `End Failure - Presentation table` terminal path
- `Send an Email with HTML Body type` notification component
- `Delete Transient table 3` cleanup component

Additional controls visible in the export:
- Unit-test gates validate row-count or test-result expectations
- Query tagging supports troubleshooting in Snowflake history
- Task history loading supports operational monitoring

---

## Tables and Views

### Staging Tables

- `STG_DCE2.T_DCE2_INTERACTION`
- `STG_DCE2.T_DCE2_INTERACTION_DEVICE`
- `STG_DCE2.T_DCE2_INTERACTION_FLAVOUR`
- `STG_DCE2.T_DCE2_INTERACTION_PRODUCT`
- `STG_DCE2.T_DCE2_INTERACTION_VOUCHER`

### Integration Views

- `V_INT_TDE_CONSUMER_INTERACTION`
- `V_INT_MDE_CONSUMER_INTERACTION_DEVICE`
- `V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR`
- `V_INT_MDE_CONSUMER_INTERACTION_PRODUCT`
- `V_INT_MDE_CONSUMER_INTERACTION_VOUCHER`

### Presentation Tables

- `PL_INTERACTION.TDE_CONSUMER_INTERACTION`
- `PL_INTERACTION.MDE_CONSUMER_INTERACTION_DEVICE`
- `PL_INTERACTION.MDE_CONSUMER_INTERACTION_FLAVOUR`
- `PL_INTERACTION.MDE_CONSUMER_INTERACTION_PRODUCT`
- `PL_INTERACTION.MDE_CONSUMER_INTERACTION_VOUCHER`

### DQ Companion Targets Referenced by the Loader Pattern

- `PL_COMMON_LAYER_DQ.TDE_CONSUMER_INTERACTION_DQ`
- Equivalent DQ targets are implied for other interaction objects by the same loader framework, though not all names are explicitly surfaced in the high-level job tree.

---

## Business Use Cases

- Analyze consumer interaction journeys across channels
- Enrich interactions with device, flavour, product, and voucher context
- Support reporting on service events, commerce events, and engagement activity
- Track operational performance by market, channel, and interaction type
- Enable downstream data products that need historized interaction records

---

## Dependencies

### Upstream Dependencies

- DCE2 ingestion into `STG_DCE2`
- Snowflake environment variables and database schemas
- Master-pipeline dispatch logic through `DISP Ingestion - CONS 1`

### Internal Dependencies

- Integration views must be created before presentation harmonization runs
- Presentation tables depend on loader metadata grids and primary-key configuration
- Unit tests depend on successful publication of the presentation tables

---

## Maintenance and Operations

### Operational Notes

- Use the query tag `${job_name}-${run_history_id}` to trace pipeline execution in Snowflake.
- Validate task-history records after each run.
- Review unit-test results before promoting changes.
- Keep the `gv_primary_key_configuration` grids aligned with business-key definitions.

### Change Impact Areas

Changes to the following areas are likely to affect downstream consumers:
- Staging table structures in `STG_DCE2`
- Calculator grid expressions in integration transformations
- Primary-key configuration in harmonization jobs
- SCD2 loading behavior in the presentation loader framework

---

## Contact and Support

Recommended ownership areas for support:
- Matillion orchestration and transformation logic
- Snowflake schema and table-management framework
- DCE2 source-system ingestion and landing processes
- Data-quality and unit-test ownership for interaction datasets
