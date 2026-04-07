# Google Analytics Data Pipeline Documentation
**End-to-End Pipeline: BigQuery Ingestion to Snowflake Data Warehouse**

## Table of Contents
1. [Pipeline Overview](#pipeline-overview)
2. [Architecture](#architecture)
3. [Master Pipeline](#master-pipeline)
4. [Ingestion Layer](#ingestion-layer)
5. [Integration Layer (INT)](#integration-layer-int)
6. [Presentation Layer (PL)](#presentation-layer-pl)
7. [Data Flow](#data-flow)
8. [Tables and Views](#tables-and-views)
9. [Configuration](#configuration)
10. [Error Handling](#error-handling)

---

## Pipeline Overview

**Pipeline Name:** `pipe_e2e_master_google_analytics`  
**Source System:** Google BigQuery (GA4 Dashboard)  
**Target System:** Snowflake Data Warehouse  
**Data Domain:** Web Analytics / Digital Marketing

### Purpose
This pipeline extracts Google Analytics 4 (GA4) data from BigQuery and loads it into Snowflake, transforming raw data through staging, integration, and presentation layers to support analytics and reporting on:
- Monthly website performance metrics by market
- Regional performance tracking
- Session analytics (total, engaged)
- User behavior metrics
- E-commerce conversion rates
- Device and channel analysis

---

## Architecture

### Layer Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER PIPELINE                               │
│            pipe_e2e_master_google_analytics                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────────┐      ┌──────────────────────────┐
│  INGESTION LAYER  │      │   HARMONIZATION LAYER    │
│  (BigQuery → STG) │      │   (INT → PL)             │
└───────────────────┘      └──────────────────────────┘
        │                             │
        │                   ┌─────────┴─────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌────────────┐    ┌────────────┐
│   STAGING     │   │INTEGRATION │    │PRESENTATION│
│   (STG)       │   │   (INT)    │    │   (PL)     │
└───────────────┘   └────────────┘    └────────────┘
```

### Data Layers

| Layer | Database | Schema | Purpose |
|-------|----------|--------|---------|
| **Staging** | `${ev_database_10_staging}` | `STG_GOOGLE_ANALYTICS` | Raw data from BigQuery |
| **Integration** | `${ev_database_20_integration}` | `${ev_data_foundation_schema_20_integration}` | Transformed facts and dimensions |
| **Presentation** | `${ev_database_30_presentation}` | `PL_SOCIALMEDIA` | Business-ready tables and views |

---

## Master Pipeline

### File Location
```
ROOT/01_PIPELINE_ORC/01_MASTER_PIPELINE/CONS_GOOGLE_ANALYTICS/
└── pipe_e2e_master_google_analytics.ORCHESTRATION
```

### Pipeline Flow

```
Start
  │
  ├─► Set Query Tag
  │
  ├─► Run Ingestion (orc_ingestion_bigquery_main)
  │     │
  │     ├─ Set Variables:
  │     │   • jv_secrets_manager_arn_dict (AWS Secrets Manager ARNs)
  │     │   • jv_source = "GOOGLE_ANALYTICS"
  │     │   • jv_snowflake_warehouse
  │     │
  │     └─ Set Grid Variables:
  │         • gv_bigquery_object (table mappings)
  │
  ├─► Run Harmonization (orc_harmonization_master_google_analytics)
  │     │
  │     └─ Transform data to INT and PL layers
  │
  └─► Load ETL Task History
        │
        └─► End
```

### Key Variables

#### Scalar Variables
| Variable | Description | Example Value |
|----------|-------------|---------------|
| `jv_secrets_manager_arn_dict` | AWS Secrets Manager ARNs for each environment | `{"dev":"arn:aws:...", "qas":"arn:aws:...", "prd":"arn:aws:..."}` |
| `jv_source` | Source system identifier | `GOOGLE_ANALYTICS` |
| `jv_snowflake_warehouse` | Snowflake compute warehouse | `${ev_warehouse_10_default}` |

#### Grid Variables
| Grid Variable | Columns | Purpose |
|--------------|---------|---------|
| `gv_bigquery_object` | • snowflake_table<br>• bigquery_dataset<br>• bigquery_table<br>• column_statement<br>• bigquery_update_indicator<br>• snowflake_update_indicator | Maps BigQuery tables to Snowflake tables with column transformations |

### Table Mappings

#### 1. HACK_MONTHLY_MARKET
- **BigQuery Source:** `dashboard_hack.ga4_hack_monthly_market`
- **Snowflake Target:** `HACK_MONTHLY_MARKET`
- **Update Indicator:** `DATE(updated_at)` → `DATE(UPDATED_AT)`

#### 2. HACK_MONTHLY_REGION
- **BigQuery Source:** `dashboard_hack.ga4_hack_monthly_region`
- **Snowflake Target:** `HACK_MONTHLY_REGION`
- **Update Indicator:** `DATE(updated_at)` → `DATE(UPDATED_AT)`

---

## Ingestion Layer

### File Location
```
ROOT/05_TEMPLATE_JOBS/09_INGESTION/BIGQUERY/
├── orc_ingestion_bigquery_main.ORCHESTRATION (Main orchestrator)
└── orc_ingestion_bigquery_iterate_per_table.ORCHESTRATION (Per-table processor)
```

### Process Flow Overview

```
Start
  │
  ├─► PEM File Generator (Python Script)
  │     │
  │     ├─ Fetch credentials from AWS Secrets Manager
  │     ├─ Extract BigQuery service account email
  │     ├─ Generate PEM file: /tmp/private_key_CONS_GOOGLE_ANALYTICS.pem
  │     └─ Store jv_service_account variable
  │
  └─► Grid Iterator (for each table in gv_bigquery_object)
        │
        └─► orc_ingestion_bigquery_iterate_per_table
              │
              ├─ Variable Management (construct table names)
              ├─ Initial vs Incremental Decision
              ├─ Query Construction
              └─ Load data from BigQuery to Snowflake Staging
```

---

## Detailed Ingestion Process

### Per-Table Ingestion Flow

**File:** `orc_ingestion_bigquery_iterate_per_table.ORCHESTRATION`

#### Step-by-Step Process

```
Start
  │
  ├─► 1. Variable Management (Python)
  │     │
  │     ├─ Construct Snowflake schema: STG_{jv_source}
  │     │   Example: STG_GOOGLE_ANALYTICS
  │     │
  │     ├─ Construct Snowflake table: T_{jv_source}_{jv_snowflake_table}
  │     │   Example: T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
  │     │
  │     ├─ Set incremental flag based on update indicators
  │     │
  │     └─ If incremental: construct query to get latest date from Snowflake
  │
  ├─► 2. Initial vs Incremental Decision
  │     │
  │     └─ Check: jv_incremental_flag == 'TRUE' ?
  │
  ├─► 3a. INCREMENTAL LOAD PATH (if TRUE)
  │     │
  │     ├─ Assert Snowflake Table Exists
  │     │   - Database: ${ev_database_10_staging}
  │     │   - Schema: ${jv_snowflake_stage_schema}
  │     │   - Table: ${jv_snowflake_stage_table}
  │     │   - Check: Row count >= 1
  │     │
  │     ├─ Get Latest Date from Snowflake
  │     │   Query: SELECT MAX({jv_snowflake_update_indicator}) as MAX_DATE
  │     │           FROM {database}.{schema}.{table}
  │     │   Store in: jv_snowflake_latest_date
  │     │
  │     └─ Construct Incremental Query (Python)
  │         Query: SELECT {columns},
  │                       UPPER('{jv_source}') AS _ETL_SOURCE,
  │                       CAST({run_history_id} AS INT64) AS _ETL_RUN_ID,
  │                       CAST({job_id} AS INT64) AS _ETL_JOB_ID,
  │                       CURRENT_TIMESTAMP() as _ETL_LOAD_DATETIME
  │                FROM {project}.{dataset}.{table}
  │                WHERE {jv_bigquery_update_indicator} > '{jv_snowflake_latest_date}'
  │
  ├─► 3b. FULL LOAD PATH (if FALSE or assertion fails)
  │     │
  │     └─ Construct Full Load Query (Python)
  │         Query: SELECT {columns},
  │                       UPPER('{jv_source}') AS _ETL_SOURCE,
  │                       CAST({run_history_id} AS INT64) AS _ETL_RUN_ID,
  │                       CAST({job_id} AS INT64) AS _ETL_JOB_ID,
  │                       CURRENT_TIMESTAMP() as _ETL_LOAD_DATETIME
  │                FROM {project}.{dataset}.{table}
  │
  └─► 4. Execute BigQuery Query & Load to Snowflake
        │
        ├─ Authentication: OAuth JWT with PEM file
        ├─ Execute query: ${jv_bigquery_extract_query}
        ├─ Stage to S3: ${ev_aws_external_stage}
        │   - Path: v1/{jv_source_lower}/
        │   - Compression: Gzip
        │
        └─ Load to Snowflake:
            - Database: ${ev_database_10_staging}
            - Schema: ${jv_snowflake_stage_schema}
            - Table: ${jv_snowflake_stage_table}
            - Warehouse: ${jv_snowflake_warehouse}
```

---

### Initial vs Incremental Load Decision Logic

#### Decision Criteria

The pipeline automatically determines whether to perform an **initial (full) load** or an **incremental load** based on the presence of update indicator columns.

**Python Logic:**
```python
def has_value(variable_value):
    if variable_value is not None and variable_value != '':
        return True
    else:
        return False

if has_value(jv_snowflake_update_indicator) and has_value(jv_bigquery_update_indicator):
    # INCREMENTAL MODE
    context.updateVariable('jv_incremental_flag', 'TRUE')
    
    # Construct query to get latest date from Snowflake
    snowflake_get_latest_data_query = f'''
        SELECT MAX({jv_snowflake_update_indicator}) as MAX_DATE 
        FROM {ev_database_10_staging}.{jv_snowflake_stage_schema}.{jv_snowflake_stage_table}
    '''
    context.updateVariable('jv_snowflake_get_latest_date_query', snowflake_get_latest_data_query)
else:
    # FULL LOAD MODE
    context.updateVariable('jv_incremental_flag', 'FALSE')
```

#### Configuration per Table

The incremental behavior is configured in the **grid variable** `gv_bigquery_object` defined in the master pipeline:

| Column | Description | Example Value |
|--------|-------------|---------------|
| `snowflake_table` | Target table name in Snowflake | `HACK_MONTHLY_MARKET` |
| `bigquery_dataset` | Source dataset in BigQuery | `dashboard_hack` |
| `bigquery_table` | Source table in BigQuery | `ga4_hack_monthly_market` |
| `column_statement` | Columns to select from BigQuery | `table_key as TABLE_KEY, region as REGION, ...` |
| `bigquery_update_indicator` | BigQuery column for incremental logic | `DATE(updated_at)` |
| `snowflake_update_indicator` | Snowflake column for incremental logic | `DATE(UPDATED_AT)` |

**For Google Analytics Tables:**

1. **HACK_MONTHLY_MARKET:**
   - BigQuery indicator: `DATE(updated_at)`
   - Snowflake indicator: `DATE(UPDATED_AT)`
   - **Result:** Incremental load enabled

2. **HACK_MONTHLY_REGION:**
   - BigQuery indicator: `DATE(updated_at)`
   - Snowflake indicator: `DATE(UPDATED_AT)`
   - **Result:** Incremental load enabled

---

### Incremental Load Process (Detailed)

#### 1. Assert Snowflake Table Exists

**Component:** Assert Snowflake Table

**Purpose:** Verify that the target Snowflake table exists and has data before attempting incremental load.

**Checks:**
- Table existence in `${ev_database_10_staging}.${jv_snowflake_stage_schema}.${jv_snowflake_stage_table}`
- Row count >= 1 (ensures table is not empty)

**If Assertion Fails:**
- Pipeline branches to **Full Load** path
- Treats as initial load scenario

#### 2. Get Latest Watermark Date

**Component:** Get Latest Date from Snowflake Table

**Query Template:**
```sql
SELECT MAX({jv_snowflake_update_indicator}) as MAX_DATE 
FROM {ev_database_10_staging}.{jv_snowflake_stage_schema}.{jv_snowflake_stage_table}
```

**For HACK_MONTHLY_MARKET:**
```sql
SELECT MAX(DATE(UPDATED_AT)) as MAX_DATE 
FROM DEV_CONS_MATILLION_STG.STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
```

**Output:** 
- Stores maximum date in variable `jv_snowflake_latest_date`
- Example: `2026-03-31`

#### 3. Construct Incremental BigQuery Query

**Component:** Construct Query - Incremental Load (Python)

**Query Template:**
```sql
SELECT 
    {jv_bigquery_column_statement},
    UPPER('{jv_source}') AS _ETL_SOURCE, 
    CAST({run_history_id} AS INT64) AS _ETL_RUN_ID, 
    CAST({job_id} AS INT64) AS _ETL_JOB_ID,
    CURRENT_TIMESTAMP() as _ETL_LOAD_DATETIME
FROM {jv_bigquery_project}.{jv_bigquery_dataset}.{jv_bigquery_table}
WHERE {jv_bigquery_update_indicator} > '{jv_snowflake_latest_date}'
```

**For HACK_MONTHLY_MARKET (Example):**
```sql
SELECT 
    table_key as TABLE_KEY, 
    region as REGION, 
    market as MARKET, 
    month_year as MONTH_YEAR, 
    year_to_date as YEAR_TO_DATE, 
    device_web_info_hostname as DEVICE_WEB_INFO_HOSTNAME, 
    platform_category as PLATFORM_CATEGORY, 
    sub_category as SUB_CATEGORY, 
    session_custom_channel_group as SESSION_CUSTOM_CHANNEL_GROUP, 
    device_category as DEVICE_CATEGORY, 
    total_sessions_monthly as TOTAL_SESSIONS_MONTHLY, 
    engaged_sessions_monthly as ENGAGED_SESSIONS_MONTHLY, 
    users_visit_monthly as USERS_VISIT_MONTHLY, 
    user_purchase_ratio_monthly as USER_PURCHASE_RATIO_MONTHLY, 
    total_sessions_ytd as TOTAL_SESSIONS_YTD, 
    engaged_sessions_ytd as ENGAGED_SESSIONS_YTD, 
    users_visit_ytd as USERS_VISIT_YTD, 
    user_purchase_ratio_ytd as USER_PURCHASE_RATIO_YTD, 
    updated_at as UPDATED_AT,
    UPPER('GOOGLE_ANALYTICS') AS _ETL_SOURCE,
    CAST(123456 AS INT64) AS _ETL_RUN_ID,
    CAST(789012 AS INT64) AS _ETL_JOB_ID,
    CURRENT_TIMESTAMP() as _ETL_LOAD_DATETIME
FROM pmi-rrp-bi-glob-prod-001.dashboard_hack.ga4_hack_monthly_market
WHERE DATE(updated_at) > '2026-03-31'
```

**Key Features:**
- **Incremental Filter:** `WHERE DATE(updated_at) > '{jv_snowflake_latest_date}'`
- **Metadata Columns:** Added for lineage tracking (_ETL_SOURCE, _ETL_RUN_ID, _ETL_JOB_ID, _ETL_LOAD_DATETIME)
- **Date Comparison:** Uses `>` (greater than) to avoid duplicate processing

---

### Full Load Process (Detailed)

#### When Full Load Occurs

1. **No Update Indicators Configured:**
   - `jv_bigquery_update_indicator` is NULL or empty
   - `jv_snowflake_update_indicator` is NULL or empty

2. **Snowflake Table Does Not Exist:**
   - First-time load for this table
   - Assertion check fails

3. **Snowflake Table is Empty:**
   - Table exists but row count < 1
   - Assertion check fails

#### Construct Full Load BigQuery Query

**Component:** Construct Query - Full Load (Python)

**Query Template:**
```sql
SELECT 
    {jv_bigquery_column_statement},
    UPPER('{jv_source}') AS _ETL_SOURCE, 
    CAST({run_history_id} AS INT64) AS _ETL_RUN_ID, 
    CAST({job_id} AS INT64) AS _ETL_JOB_ID,
    CURRENT_TIMESTAMP() as _ETL_LOAD_DATETIME
FROM {jv_bigquery_project}.{jv_bigquery_dataset}.{jv_bigquery_table}
```

**Notice:** No WHERE clause - all data is extracted.

---

### BigQuery to Snowflake Data Transfer

#### Component: Google BigQuery Query

**Authentication:**
- **Method:** OAuth JWT with Service Account
- **PEM File:** `/tmp/private_key_CONS_GOOGLE_ANALYTICS.pem`
- **Service Account:** `matillion@pmi-rrp-bi-glob-prod-001.iam.gserviceaccount.com`

**Connection Parameters:**
```
InitiateOAuth: GETANDREFRESH
AuthScheme: OAuthJWT
OAuthJWTCertType: PEMKEY_FILE
OAuthJWTCert: ${jv_pem_file_path}
OAuthJWTSubject: ${jv_service_account}
OAuthJWTIssuer: ${jv_service_account}
```

**BigQuery Configuration:**
- **Project ID:** `${jv_bigquery_project}` (pmi-rrp-bi-glob-prod-001)
- **Dataset ID:** `${jv_bigquery_project}.${jv_bigquery_dataset}` (pmi-rrp-bi-glob-prod-001.dashboard_hack)
- **SQL Dialect:** Standard SQL

**Staging Configuration:**
- **Platform:** Amazon S3 (via Snowflake External Stage)
- **Stage:** `${ev_aws_external_stage}`
- **Path:** `v1/{jv_source_lower}/` (e.g., v1/google_analytics/)
- **Compression:** Gzip
- **Encryption:** SSE-S3

**Load Configuration:**
- **Target Database:** `${ev_database_10_staging}`
- **Target Schema:** `${jv_snowflake_stage_schema}` (STG_GOOGLE_ANALYTICS)
- **Target Table:** `${jv_snowflake_stage_table}` (T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET)
- **Warehouse:** `${jv_snowflake_warehouse}`
- **Load Type:** Standard (APPEND mode for incremental)

---

### ETL Metadata Columns

Every record loaded from BigQuery to Snowflake includes the following metadata columns for lineage and troubleshooting:

| Column | Data Type | Source | Purpose |
|--------|-----------|--------|---------|
| `_ETL_SOURCE` | STRING | Hardcoded | Source system identifier (e.g., 'GOOGLE_ANALYTICS') |
| `_ETL_RUN_ID` | INT64 | `${run_history_id}` | Matillion run history ID for this execution |
| `_ETL_JOB_ID` | INT64 | `${job_id}` | Matillion job ID |
| `_ETL_LOAD_DATETIME` | TIMESTAMP | `CURRENT_TIMESTAMP()` | BigQuery timestamp when data was extracted |

**Usage:**
- **Data Lineage:** Track which pipeline run loaded each record
- **Troubleshooting:** Identify records from failed or problematic runs
- **Audit:** Maintain complete history of data loads
- **Reprocessing:** Filter by run ID for selective reprocessing

---

### Incremental Load Strategy: Append vs Merge

**Current Strategy: APPEND**

The Google Analytics pipeline uses an **APPEND strategy** for incremental loads:

1. **Staging Layer (STG):**
   - Incremental data is **APPENDED** to existing staging table
   - No deduplication at this layer
   - Staging table grows with each incremental load
   - Allows for historical tracking and reprocessing

2. **Integration/Presentation Layer:**
   - Deduplication and merge logic handled in harmonization
   - Transient delta tables created for each run
   - Final tables use MERGE/UPSERT logic based on business keys

**Advantages:**
- Simple and fast staging loads
- Complete historical record in staging
- Flexibility for reprocessing
- Easy rollback by filtering on `_ETL_RUN_ID`

**Considerations:**
- Staging tables grow over time
- May require periodic archival/purging
- Deduplication happens downstream in harmonization

---

### Data Flow Optimization

#### S3 Staging Layer

**Purpose:** Intermediate storage between BigQuery and Snowflake

**Benefits:**
1. **Decoupling:** BigQuery extraction independent of Snowflake load
2. **Performance:** Parallel file processing by Snowflake
3. **Resilience:** Files persist in S3 if Snowflake load fails
4. **Compression:** Gzip compression reduces data transfer costs

**File Organization:**
```
s3://{bucket}/{ev_aws_external_stage}/
└── v1/
    └── google_analytics/
        ├── file1.csv.gz
        ├── file2.csv.gz
        └── file3.csv.gz
```

#### Load Performance

**Factors Affecting Performance:**
- **BigQuery Query Performance:** Depends on data volume and query complexity
- **Network Transfer:** BigQuery → S3 transfer time
- **Snowflake Warehouse Size:** Determines parallel processing capacity
- **Data Volume:** Number of rows in incremental extract

**Typical Performance (estimates):**
- Initial Load (full): 10-30 minutes depending on table size
- Incremental Load: 2-10 minutes depending on new records
- Staging to Integration: 5-15 minutes (transformation heavy)
- Integration to Presentation: 2-5 minutes (merge operations)

---

### Monitoring Incremental Loads

#### Key Metrics to Track

1. **Watermark Date:**
   ```sql
   SELECT MAX(DATE(UPDATED_AT)) as LATEST_DATE
   FROM STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
   ```

2. **Incremental Load Row Counts:**
   ```sql
   SELECT 
       _ETL_RUN_ID,
       _ETL_LOAD_DATETIME,
       COUNT(*) as ROW_COUNT
   FROM STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
   GROUP BY _ETL_RUN_ID, _ETL_LOAD_DATETIME
   ORDER BY _ETL_LOAD_DATETIME DESC
   LIMIT 10
   ```

3. **Gap Detection:**
   ```sql
   -- Check for date gaps in staging table
   SELECT DISTINCT DATE(UPDATED_AT) as LOAD_DATE
   FROM STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
   ORDER BY LOAD_DATE DESC
   LIMIT 30
   ```

4. **Load Frequency:**
   ```sql
   SELECT 
       DATE(_ETL_LOAD_DATETIME) as LOAD_DATE,
       COUNT(DISTINCT _ETL_RUN_ID) as LOAD_COUNT,
       SUM(CASE WHEN _ETL_RUN_ID IS NOT NULL THEN 1 ELSE 0 END) as TOTAL_ROWS
   FROM STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
   GROUP BY DATE(_ETL_LOAD_DATETIME)
   ORDER BY LOAD_DATE DESC
   LIMIT 7
   ```

---

### Troubleshooting Incremental Loads

#### Common Issues

**Issue 1: No New Data Loaded**

**Symptoms:**
- Pipeline completes successfully
- Zero rows returned from BigQuery
- Staging table unchanged

**Possible Causes:**
1. No new updates in BigQuery since last watermark
2. Watermark date incorrect (too recent)
3. BigQuery update indicator column not updating

**Resolution:**
```sql
-- Check BigQuery for new data
SELECT COUNT(*) as NEW_RECORDS
FROM `pmi-rrp-bi-glob-prod-001.dashboard_hack.ga4_hack_monthly_market`
WHERE DATE(updated_at) > '{last_watermark_date}'
```

---

**Issue 2: Duplicate Records in Staging**

**Symptoms:**
- Same business key appears multiple times
- Row count higher than expected

**Possible Causes:**
1. Multiple pipeline runs with same watermark
2. BigQuery source has duplicates
3. Overlapping incremental windows

**Resolution:**
```sql
-- Identify duplicates by business key
SELECT 
    TABLE_KEY,
    COUNT(*) as COUNT,
    ARRAY_AGG(_ETL_RUN_ID) as RUN_IDS
FROM STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET
GROUP BY TABLE_KEY
HAVING COUNT(*) > 1
ORDER BY COUNT DESC
LIMIT 10
```

---

**Issue 3: Full Load Triggered Unexpectedly**

**Symptoms:**
- Expected incremental load but full load occurred
- Large data volume extracted

**Possible Causes:**
1. Staging table was dropped/truncated
2. Update indicator columns not configured
3. Assertion check failed

**Resolution:**
- Check pipeline logs for assertion failure
- Verify staging table exists: `SHOW TABLES LIKE 'T_GOOGLE_ANALYTICS%'`
- Verify update indicators in grid variable configuration

---

### Best Practices

#### 1. Update Indicator Selection

**Choose columns that:**
- Are reliably updated when data changes
- Use consistent data types (DATE or TIMESTAMP)
- Are indexed in BigQuery for performance
- Have minimal NULL values

**For Google Analytics:**
- ✅ `updated_at` - Reliable timestamp of last update
- ❌ `session_date` - Business date, not technical update timestamp

#### 2. Watermark Management

**Do:**
- Use DATE casting for consistency: `DATE(updated_at)`
- Test incremental logic with various date ranges
- Monitor for gaps in watermark progression

**Don't:**
- Use `>=` in WHERE clause (causes duplicates)
- Manually modify watermark dates without testing
- Skip validation after schema changes

#### 3. Initial Load Planning

**Before Initial Load:**
1. Estimate data volume from BigQuery
2. Allocate appropriate Snowflake warehouse size
3. Configure S3 staging area with sufficient storage
4. Test with LIMIT clause first
5. Schedule during off-peak hours

**During Initial Load:**
- Monitor BigQuery quota usage
- Watch S3 staging area space
- Track Snowflake warehouse credits
- Keep pipeline logs for reference

#### 4. Ongoing Monitoring

**Daily Checks:**
- Verify latest watermark date is current
- Check row counts align with expectations
- Review pipeline execution times

**Weekly Checks:**
- Analyze staging table growth rate
- Review S3 staging area cleanup
- Validate data quality in harmonized tables

**Monthly Checks:**
- Plan staging table archival/purging
- Review and optimize warehouse sizing
- Audit incremental load performance trends

---

### Authentication Process

The pipeline uses **service account authentication** to connect to BigQuery:

1. **Secrets Retrieval:** Fetches service account credentials from AWS Secrets Manager based on environment
2. **PEM File Creation:** Generates a private key file at `/tmp/private_key_CONS_${jv_source}.pem`
3. **Service Account Email:** Extracted as `jv_service_account` (e.g., `matillion@pmi-rrp-bi-glob-prod-001.iam.gserviceaccount.com`)

### BigQuery Connection Details
- **Project:** `pmi-rrp-bi-glob-prod-001`
- **Dataset:** `dashboard_hack`
- **Tables:**
  - `ga4_hack_monthly_market`
  - `ga4_hack_monthly_region`

### Staging Tables Created
- `STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET`
- `STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_REGION`

---

## Integration Layer (INT)

### File Location
```
ROOT/02_DATA_WAREHOUSE/02_INTEGRATION/GOOGLE_ANALYTICS/
├── Dimension/
│   ├── trn_v_int_dim_custom_channel.TRANSFORMATION
│   ├── trn_v_int_dim_digital_device.TRANSFORMATION
│   ├── trn_v_int_dim_ga_mapping_market_country.TRANSFORMATION
│   ├── trn_v_int_dim_ga_mapping_region.TRANSFORMATION
│   ├── trn_v_int_dim_traffic_channel.TRANSFORMATION
│   └── trn_v_int_dim_website_domain.TRANSFORMATION
└── Fact/
    ├── trn_v_int_fact_google_analytics_monthly_performance.TRANSFORMATION
    └── trn_v_int_fact_google_analytics_monthly_performance_region.TRANSFORMATION
```

### Harmonization Master Pipeline

**File:** `ROOT/02_DATA_WAREHOUSE/03_PRESENTATION/GOOGLE_ANALYTICS/orc_harmonization_master_google_analytics.ORCHESTRATION`

### Harmonization Flow

```
Start → Begin Transaction
  │
  ├─► Create Transient Tables (Delta Processing)
  │     │
  │     ├─ TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA
  │     └─ TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION_DELTA
  │
  ├─► Process Dimensions (Parallel Execution)
  │     │
  │     ├─ orc_harmonization_dim_ga_mapping_region
  │     ├─ orc_harmonization_dim_digital_device
  │     ├─ orc_harmonization_dim_website_domain
  │     ├─ orc_harmonization_dim_traffic_channel
  │     ├─ orc_harmonization_dim_custom_channel
  │     └─ orc_harmonization_dim_ga_mapping_market_country
  │
  ├─► Process Facts (Parallel Execution)
  │     │
  │     ├─ orc_harmonization_fact_google_analytics_monthly_performance
  │     └─ orc_harmonization_fact_google_analytics_monthly_performance_region
  │
  ├─► Commit Transaction
  │
  ├─► Truncate Transient Tables
  │
  └─► End Success
```

### Dimension Tables

#### 1. DIM_GA_MAPPING_MARKET_COUNTRY
**Schema:** `PL_SOCIALMEDIA.DIM_GA_MAPPING_MARKET_COUNTRY`

Maps source market names to standardized market keys.

| Column | Type | Description |
|--------|------|-------------|
| `DIM_MARKET_KEY` | TEXT(255) | Surrogate key for market |
| `SOURCE_MARKET_NAME` | TEXT | Original market name from GA4 |

#### 2. DIM_GA_MAPPING_REGION
**Schema:** `PL_SOCIALMEDIA.DIM_GA_MAPPING_REGION`

Maps source region identifiers.

| Column | Type | Description |
|--------|------|-------------|
| `DIM_REGION_KEY` | TEXT(255) | Surrogate key for region |
| `SOURCE_REGION_NAME` | TEXT | Original region name from GA4 |

#### 3. DIM_DIGITAL_DEVICE
**Schema:** `PL_SOCIALMEDIA.DIM_DIGITAL_DEVICE`

Device category dimension (mobile, desktop, tablet).

| Column | Type | Description |
|--------|------|-------------|
| `DIM_DIGITAL_DEVICE_KEY` | TEXT(255) | Surrogate key for device |
| `DIGITAL_DEVICE_NAME` | TEXT | Device category name |

#### 4. DIM_WEBSITE_DOMAIN
**Schema:** `PL_SOCIALMEDIA.DIM_WEBSITE_DOMAIN`

Website hostname/domain dimension.

| Column | Type | Description |
|--------|------|-------------|
| `DIM_WEBSITE_DOMAIN_KEY` | TEXT(255) | Surrogate key for domain |
| `WEBSITE_DOMAIN_NAME` | TEXT | Full website domain |

#### 5. DIM_TRAFFIC_CHANNEL
**Schema:** `PL_SOCIALMEDIA.DIM_TRAFFIC_CHANNEL`

Traffic acquisition channel dimension.

| Column | Type | Description |
|--------|------|-------------|
| `DIM_TRAFFIC_CHANNEL_KEY` | TEXT(255) | Surrogate key for channel |
| `TRAFFIC_CHANNEL_NAME` | TEXT | Channel name (Organic, Direct, etc.) |

#### 6. DIM_CUSTOM_CHANNEL
**Schema:** `PL_SOCIALMEDIA.DIM_CUSTOM_CHANNEL`

Custom channel grouping dimension.

| Column | Type | Description |
|--------|------|-------------|
| `DIM_CUSTOM_CHANNEL_KEY` | TEXT(255) | Surrogate key for custom channel |
| `CUSTOM_CHANNEL_NAME` | TEXT | Custom channel classification |

### Transformation Logic

---

## Dimension Transformation Logic

### 1. DIM_GA_MAPPING_MARKET_COUNTRY Transformation

**Transformation File:** `trn_v_int_dim_ga_mapping_market_country.TRANSFORMATION`

**Purpose:** Maps Google Analytics source market names to standardized DIM_MARKET keys with exception handling for non-standard naming.

#### Source
- **Transient Table:** `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA` (MARKET column)

#### Transformation Steps

1. **Extract Source Market Names**
   - Read MARKET column from transient fact table
   - Apply TRIM to standardize: `TRIM(MARKET) AS SOURCE_MARKET_NAME`
   - Get distinct values

2. **Exception Market Mapping (Hardcoded SQL)**
   - Define exception mappings for markets with non-standard naming
   - Example mappings:
     ```
     'South Cyprus' → 'Cyprus' (country), 'Cyprus' (market)
     'North Cyprus' → 'Turkey' (country), 'Turkish Cyprus' (market)
     'United States' → 'USA', 'USA'
     'Bosnia' → 'Bosnia-Herz.', 'Bosnia & Herz.'
     'United Arab Emirate' → 'UAE', 'UAE'
     'Russia' → 'Russian Fed.', 'Russia'
     ... and more
     ```

3. **Join Exception Mapping (Left Join)**
   - Join source market names with exception mapping
   - `source.SOURCE_MARKET_NAME = exc.SOURCE_MARKET_NAME`

4. **Apply COALESCE Logic**
   - `COALESCE(STD_COUNTRY_NAME, SOURCE_MARKET_NAME)` → STD_COUNTRY_NAME
   - `COALESCE(STD_MARKET_NAME, SOURCE_MARKET_NAME)` → STD_MARKET_NAME
   - If no exception exists, use original SOURCE_MARKET_NAME

5. **Lookup Country from DIM_MARKET**
   - Filter: `ACTIVITY_DESCRIPTION = 'Domestic'` AND `COUNTRY_DESCRIPTION IS NOT NULL`
   - Apply TRIM: `TRIM(COUNTRY_DESCRIPTION) AS COUNTRY_NAME`
   - Get distinct country names

6. **Lookup Market from DIM_MARKET**
   - Filter: `ACTIVITY_DESCRIPTION = 'Domestic'` AND `MARKET_DESCRIPTION IS NOT NULL`
   - Apply TRIM: `TRIM(MARKET_DESCRIPTION) AS MARKET_NAME`
   - Select: `DIM_MARKET_KEY`, `MARKET_NAME`

7. **Final Join**
   - Join standardized names with DIM_MARKET lookups:
     - `source.STD_COUNTRY_NAME = country.COUNTRY_NAME` (left join)
     - `source.STD_MARKET_NAME = market.MARKET_NAME` (left join)

8. **Add Technical Columns**
   - `VALID_FROM = '1900-01-01 00:00:00'::TIMESTAMP_NTZ`
   - `VALID_TO = '9999-12-31 23:59:59'::TIMESTAMP_NTZ`
   - `ACTIVE_FLAG = TRUE::BOOLEAN`

9. **Create Integration View**
   - Output view: `V_INT_DIM_GA_MAPPING_MARKET_COUNTRY`

#### Output Schema
| Column | Type | Formula |
|--------|------|---------|
| `DIM_MARKET_KEY` | TEXT(255) | From DIM_MARKET lookup |
| `SOURCE_MARKET_NAME` | TEXT | Trimmed from GA4 source |
| `MARKET_NAME` | TEXT | Standardized market name |
| `COUNTRY_NAME` | TEXT | Standardized country name |
| `VALID_FROM` | TIMESTAMP_NTZ | Fixed: 1900-01-01 |
| `VALID_TO` | TIMESTAMP_NTZ | Fixed: 9999-12-31 |
| `ACTIVE_FLAG` | BOOLEAN | Fixed: TRUE |

---

### 2. DIM_GA_MAPPING_REGION Transformation

**Transformation File:** `trn_v_int_dim_ga_mapping_region.TRANSFORMATION`

**Purpose:** Maps Google Analytics region names to DIM_REGION keys (similar pattern to market mapping, simplified).

#### Transformation Steps

1. Extract `REGION` from `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION_DELTA`
2. Apply TRIM: `TRIM(REGION) AS SOURCE_REGION_NAME`
3. Lookup `DIM_REGION` from `PL_COMMON_LAYER`
4. Join on region name match
5. Add technical columns (VALID_FROM, VALID_TO, ACTIVE_FLAG)
6. Create view: `V_INT_DIM_GA_MAPPING_REGION`

---

### 3. DIM_DIGITAL_DEVICE Transformation

**Transformation File:** `trn_v_int_dim_digital_device.TRANSFORMATION`

**Purpose:** Create dimension from device categories (mobile, desktop, tablet).

#### Source
- **Transient Table:** `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA` (DEVICE_CATEGORY column)

#### Transformation Steps

1. **Read Source**
   - Read DEVICE_CATEGORY from transient table

2. **Filter Input**
   - Filter: `DEVICE_CATEGORY IS NOT NULL`

3. **Apply Transformations**
   - `DIM_DIGITAL_DEVICE_KEY = MD5(DEVICE_CATEGORY)::TEXT(255)` (hash-based surrogate key)
   - `DIGITAL_DEVICE_NAME = DEVICE_CATEGORY::TEXT(255)`
   - `ACTIVE_FLAG = 'TRUE'::BOOLEAN`
   - `VALID_FROM = '1900-01-01 00:00:00'::TIMESTAMP_NTZ`
   - `VALID_TO = '9999-12-31 23:59:59'::TIMESTAMP_NTZ`

4. **Remove Duplicates**
   - Apply DISTINCT on all columns

5. **Create Integration View**
   - Output view: `V_INT_DIM_DIGITAL_DEVICE`

#### Output Schema
| Column | Type | Formula |
|--------|------|---------|
| `DIM_DIGITAL_DEVICE_KEY` | TEXT(255) | MD5(DEVICE_CATEGORY) |
| `DIGITAL_DEVICE_NAME` | TEXT(255) | DEVICE_CATEGORY |
| `ACTIVE_FLAG` | BOOLEAN | TRUE |
| `VALID_FROM` | TIMESTAMP_NTZ | 1900-01-01 |
| `VALID_TO` | TIMESTAMP_NTZ | 9999-12-31 |

---

### 4. DIM_WEBSITE_DOMAIN Transformation

**Transformation File:** `trn_v_int_dim_website_domain.TRANSFORMATION`

**Purpose:** Create dimension from website hostnames.

#### Transformation Steps (Similar to DIM_DIGITAL_DEVICE)

1. Extract `DEVICE_WEB_INFO_HOSTNAME` from transient table
2. Filter NULL values
3. Generate surrogate key: `MD5(DEVICE_WEB_INFO_HOSTNAME)::TEXT(255)`
4. Rename to `WEBSITE_DOMAIN_NAME`
5. Add technical columns
6. Apply DISTINCT
7. Create view: `V_INT_DIM_WEBSITE_DOMAIN`

---

### 5. DIM_TRAFFIC_CHANNEL Transformation

**Transformation File:** `trn_v_int_dim_traffic_channel.TRANSFORMATION`

**Purpose:** Create dimension from session traffic channels (Organic, Direct, Referral, etc.).

#### Transformation Steps (Similar to DIM_DIGITAL_DEVICE)

1. Extract `SESSION_CUSTOM_CHANNEL_GROUP` from transient table
2. Filter NULL values
3. Generate surrogate key: `MD5(SESSION_CUSTOM_CHANNEL_GROUP)::TEXT(255)`
4. Rename to `TRAFFIC_CHANNEL_NAME`
5. Add technical columns
6. Apply DISTINCT
7. Create view: `V_INT_DIM_TRAFFIC_CHANNEL`

---

### 6. DIM_CUSTOM_CHANNEL Transformation

**Transformation File:** `trn_v_int_dim_custom_channel.TRANSFORMATION`

**Purpose:** Create dimension from custom channel groupings (SUB_CATEGORY).

#### Transformation Steps (Similar to DIM_DIGITAL_DEVICE)

1. Extract `SUB_CATEGORY` from transient table
2. Filter NULL values
3. Generate surrogate key: `MD5(SUB_CATEGORY)::TEXT(255)`
4. Rename to `CUSTOM_CHANNEL_NAME`
5. Add technical columns
6. Apply DISTINCT
7. Create view: `V_INT_DIM_CUSTOM_CHANNEL`

---

## Fact Table Transformation Logic

### 1. FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE

**Transformation File:** `trn_v_int_fact_google_analytics_monthly_performance.TRANSFORMATION`

**Grain:** One row per Market + Month + Platform + Channel + Domain + Device

#### Source
- **Transient Table:** `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA`
- **Sourced From:** `STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET`

#### Transformation Steps

1. **Load Transient Delta Table**
   - Reads from `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA`
   - Contains raw columns from BigQuery:
     - MARKET, MONTH_YEAR, PLATFORM_CATEGORY, SUB_CATEGORY
     - DEVICE_WEB_INFO_HOSTNAME, SESSION_CUSTOM_CHANNEL_GROUP, DEVICE_CATEGORY
     - YEAR_TO_DATE, TABLE_KEY
     - Monthly metrics: TOTAL_SESSIONS_MONTHLY, ENGAGED_SESSIONS_MONTHLY, etc.
     - YTD metrics: TOTAL_SESSIONS_YTD, ENGAGED_SESSIONS_YTD, etc.
     - UPDATED_AT

2. **Lookup Dimensions (Left Joins)**
   - **DIM_GA_MAPPING_MARKET_COUNTRY** → Join: `TRIM(main.MARKET) = TRIM(mc.SOURCE_MARKET_NAME)`
   - **DIM_MARKET** → Join: `mc.DIM_MARKET_KEY = m.DIM_MARKET_KEY`
   - **DIM_DATE (filtered)** → Join: `TO_NUMBER(REPLACE(main.MONTH_YEAR, '-', '')) = dt.CAL_MONTH` 
     - Filter: `CAL_DAY_IN_MONTH = 1` (first day of month only)
   - **DIM_PRODUCT_PLATFORM** → Join: `TRIM(main.PLATFORM_CATEGORY) = TRIM(pp.PRODUCT_PLATFORM_NAME)`
   - **DIM_CUSTOM_CHANNEL** → Join: `TRIM(main.SUB_CATEGORY) = TRIM(cc.CUSTOM_CHANNEL_NAME)`
   - **DIM_WEBSITE_DOMAIN** → Join: `TRIM(wb.WEBSITE_DOMAIN_NAME) = TRIM(main.DEVICE_WEB_INFO_HOSTNAME)`
   - **DIM_TRAFFIC_CHANNEL** → Join: `TRIM(main.SESSION_CUSTOM_CHANNEL_GROUP) = TRIM(tc.TRAFFIC_CHANNEL_NAME)`
   - **DIM_DIGITAL_DEVICE** → Join: `TRIM(main.DEVICE_CATEGORY) = TRIM(dd.DIGITAL_DEVICE_NAME)`

3. **NULL Key Handler**
   - Applies `COALESCE` to replace NULL dimension keys with `-1`
   - Ensures referential integrity:
     ```sql
     COALESCE(DIM_MARKET_KEY, '-1') AS DIM_MARKET_KEY
     COALESCE(DIM_PRODUCT_PLATFORM_KEY, '-1') AS DIM_PRODUCT_PLATFORM_KEY
     COALESCE(DIM_CUSTOM_CHANNEL_KEY, '-1') AS DIM_CUSTOM_CHANNEL_KEY
     COALESCE(DIM_TRAFFIC_CHANNEL_KEY, '-1') AS DIM_TRAFFIC_CHANNEL_KEY
     COALESCE(DIM_WEBSITE_DOMAIN_KEY, '-1') AS DIM_WEBSITE_DOMAIN_KEY
     COALESCE(DIM_DIGITAL_DEVICE_KEY, '-1') AS DIM_DIGITAL_DEVICE_KEY
     ```

4. **Remove Duplicates**
   - Apply DISTINCT on all output columns

5. **Data Type Casting**
   - **Dimension Keys:** Cast to `TEXT(255)`
   - **Date Indicators:** Cast to `DATE`
   - **Numeric Measures:** Cast to `NUMBER` or `NUMBER(38,5)` for rates
   - **Timestamps:** Cast to `TIMESTAMP_NTZ`
   
   Example casting grid:
   ```
   DIM_MARKET_KEY → TEXT(255)
   DIM_DATE_KEY → TEXT(255)
   YEAR_TO_DATE_INDICATOR → DATE
   TOTAL_SESSIONS_MONTHLY → NUMBER
   USER_PURCHASE_RATIO_MONTHLY → NUMBER(38,5)
   ENGAGEMENT_RATE_MONTHLY → NUMBER(38,5)
   LAST_UPDATED_DATETIME → TIMESTAMP_NTZ
   ```

6. **Select Final Columns**
   - Select only cast columns (exclude raw columns)

7. **Create Integration View**
   - Final view: `V_INT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE`

#### Output Schema (FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE)

| Column | Type | Description |
|--------|------|-------------|
| `DIM_MARKET_KEY` | TEXT(255) | Foreign key to DIM_MARKET |
| `DIM_DATE_KEY` | TEXT(255) | Foreign key to DIM_DATE |
| `YEAR_TO_DATE_INDICATOR` | DATE | YTD flag indicator |
| `DIM_PRODUCT_PLATFORM_KEY` | TEXT(255) | Foreign key to DIM_PRODUCT_PLATFORM |
| `DIM_CUSTOM_CHANNEL_KEY` | TEXT(255) | Foreign key to DIM_CUSTOM_CHANNEL |
| `DIM_TRAFFIC_CHANNEL_KEY` | TEXT(255) | Foreign key to DIM_TRAFFIC_CHANNEL |
| `DIM_WEBSITE_DOMAIN_KEY` | TEXT(255) | Foreign key to DIM_WEBSITE_DOMAIN |
| `DIM_DIGITAL_DEVICE_KEY` | TEXT(255) | Foreign key to DIM_DIGITAL_DEVICE |
| `GOOGLE_ANALYTICS_MONTHLY_MARKET_PERFORMANCE_BK` | TEXT(255) | Business key from source |
| `TOTAL_SESSIONS_MONTHLY` | NUMBER | Total sessions in the month |
| `ENGAGED_SESSIONS_MONTHLY` | NUMBER | Engaged sessions in the month |
| `USERS_VISIT_MONTHLY` | NUMBER | Unique users in the month |
| `USER_PURCHASE_RATIO_MONTHLY` | NUMBER(38,5) | Purchase rate for the month |
| `ENGAGEMENT_RATE_MONTHLY` | NUMBER(38,5) | Engagement rate for the month |
| `CART_CONVERSION_RATE_MONTHLY` | NUMBER(38,5) | Cart conversion rate |
| `CART_ABANDONMENT_RATE_MONTHLY` | NUMBER(38,5) | Cart abandonment rate |
| `TOTAL_SESSIONS_YTD` | NUMBER | Year-to-date total sessions |
| `ENGAGED_SESSIONS_YTD` | NUMBER | Year-to-date engaged sessions |
| `USERS_VISIT_YTD` | NUMBER(38,5) | Year-to-date unique users |
| `USER_PURCHASE_RATIO_YTD` | NUMBER(38,5) | Year-to-date purchase rate |
| `ENGAGEMENT_RATE_YTD` | NUMBER(38,5) | Year-to-date engagement rate |
| `CART_CONVERSION_RATE_YTD` | NUMBER(38,5) | Year-to-date cart conversion |
| `CART_ABANDONMENT_RATE_YTD` | NUMBER(38,5) | Year-to-date cart abandonment |
| `LAST_UPDATED_DATETIME` | TIMESTAMP_NTZ | Source update timestamp |

---

### 2. FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION

**Transformation File:** `trn_v_int_fact_google_analytics_monthly_performance_region.TRANSFORMATION`

**Grain:** One row per Region + Month + Platform + Channel + Domain + Device

#### Source
- **Transient Table:** `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION_DELTA`
- **Sourced From:** `STG_GOOGLE_ANALYTICS.T_GOOGLE_ANALYTICS_HACK_MONTHLY_REGION`

#### Transformation Steps

1. **Load Transient Delta Table**
   - Reads from `TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION_DELTA`
   - Contains raw columns from BigQuery:
     - REGION, MONTH_YEAR, PLATFORM_CATEGORY, SUB_CATEGORY
     - DEVICE_WEB_INFO_HOSTNAME, SESSION_CUSTOM_CHANNEL_GROUP, DEVICE_CATEGORY
     - YEAR_TO_DATE, TABLE_KEY
     - Monthly and YTD metrics (same as market fact)
     - UPDATED_AT

2. **Lookup Dimensions (Left Joins)**
   - **DIM_GA_MAPPING_REGION** → Join: `TRIM(main.REGION) = TRIM(mr.SOURCE_REGION_NAME)`
   - **DIM_REGION** → Join: `mr.DIM_REGION_KEY = r.DIM_REGION_KEY`
   - **DIM_DATE (filtered)** → Join: `TO_NUMBER(REPLACE(main.MONTH_YEAR, '-', '')) = dt.CAL_MONTH` 
     - Filter: `CAL_DAY_IN_MONTH = 1`
   - **DIM_PRODUCT_PLATFORM** → Join: `TRIM(main.PLATFORM_CATEGORY) = TRIM(pp.PRODUCT_PLATFORM_NAME)`
   - **DIM_CUSTOM_CHANNEL** → Join: `TRIM(main.SUB_CATEGORY) = TRIM(cc.CUSTOM_CHANNEL_NAME)`
   - **DIM_WEBSITE_DOMAIN** → Join: `TRIM(wb.WEBSITE_DOMAIN_NAME) = TRIM(main.DEVICE_WEB_INFO_HOSTNAME)`
   - **DIM_TRAFFIC_CHANNEL** → Join: `TRIM(main.SESSION_CUSTOM_CHANNEL_GROUP) = TRIM(tc.TRAFFIC_CHANNEL_NAME)`
   - **DIM_DIGITAL_DEVICE** → Join: `TRIM(main.DEVICE_CATEGORY) = TRIM(dd.DIGITAL_DEVICE_NAME)`

3. **NULL Key Handler**
   - Applies `COALESCE` to replace NULL dimension keys with `-1`:
     ```sql
     COALESCE(DIM_REGION_KEY, '-1') AS DIM_REGION_KEY
     COALESCE(DIM_PRODUCT_PLATFORM_KEY, '-1') AS DIM_PRODUCT_PLATFORM_KEY
     COALESCE(DIM_CUSTOM_CHANNEL_KEY, '-1') AS DIM_CUSTOM_CHANNEL_KEY
     COALESCE(DIM_TRAFFIC_CHANNEL_KEY, '-1') AS DIM_TRAFFIC_CHANNEL_KEY
     COALESCE(DIM_WEBSITE_DOMAIN_KEY, '-1') AS DIM_WEBSITE_DOMAIN_KEY
     COALESCE(DIM_DIGITAL_DEVICE_KEY, '-1') AS DIM_DIGITAL_DEVICE_KEY
     ```

4. **Remove Duplicates**
   - Apply DISTINCT on all output columns

5. **Data Type Casting**
   - Same casting rules as market fact table
   - **Dimension Keys:** Cast to `TEXT(255)`
   - **Numeric Measures:** Cast to `NUMBER` or `NUMBER(38,5)`
   - **Timestamps:** Cast to `TIMESTAMP_NTZ`

6. **Select Final Columns**
   - Select only cast columns

7. **Create Integration View**
   - Final view: `V_INT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION`

#### Output Schema (FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION)

| Column | Type | Description |
|--------|------|-------------|
| `DIM_REGION_KEY` | TEXT(255) | Foreign key to DIM_REGION |
| `DIM_DATE_KEY` | TEXT(255) | Foreign key to DIM_DATE |
| `YEAR_TO_DATE_INDICATOR` | DATE | YTD flag indicator |
| `DIM_PRODUCT_PLATFORM_KEY` | TEXT(255) | Foreign key to DIM_PRODUCT_PLATFORM |
| `DIM_CUSTOM_CHANNEL_KEY` | TEXT(255) | Foreign key to DIM_CUSTOM_CHANNEL |
| `DIM_TRAFFIC_CHANNEL_KEY` | TEXT(255) | Foreign key to DIM_TRAFFIC_CHANNEL |
| `DIM_WEBSITE_DOMAIN_KEY` | TEXT(255) | Foreign key to DIM_WEBSITE_DOMAIN |
| `DIM_DIGITAL_DEVICE_KEY` | TEXT(255) | Foreign key to DIM_DIGITAL_DEVICE |
| `GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION_BK` | TEXT(255) | Business key from source |
| `TOTAL_SESSIONS_MONTHLY` | NUMBER | Total sessions in the month |
| `ENGAGED_SESSIONS_MONTHLY` | NUMBER | Engaged sessions in the month |
| `USERS_VISIT_MONTHLY` | NUMBER | Unique users in the month |
| `USER_PURCHASE_RATIO_MONTHLY` | NUMBER(38,5) | Purchase rate for the month |
| `ENGAGEMENT_RATE_MONTHLY` | NUMBER(38,5) | Engagement rate for the month |
| `CART_CONVERSION_RATE_MONTHLY` | NUMBER(38,5) | Cart conversion rate |
| `CART_ABANDONMENT_RATE_MONTHLY` | NUMBER(38,5) | Cart abandonment rate |
| `TOTAL_SESSIONS_YTD` | NUMBER | Year-to-date total sessions |
| `ENGAGED_SESSIONS_YTD` | NUMBER | Year-to-date engaged sessions |
| `USERS_VISIT_YTD` | NUMBER(38,5) | Year-to-date unique users |
| `USER_PURCHASE_RATIO_YTD` | NUMBER(38,5) | Year-to-date purchase rate |
| `ENGAGEMENT_RATE_YTD` | NUMBER(38,5) | Year-to-date engagement rate |
| `CART_CONVERSION_RATE_YTD` | NUMBER(38,5) | Year-to-date cart conversion |
| `CART_ABANDONMENT_RATE_YTD` | NUMBER(38,5) | Year-to-date cart abandonment |
| `LAST_UPDATED_DATETIME` | TIMESTAMP_NTZ | Source update timestamp |

---

## Presentation Layer (PL)

### File Location
```
ROOT/02_DATA_WAREHOUSE/03_PRESENTATION/GOOGLE_ANALYTICS/
├── Fact/
│   ├── orc_harmonization_fact_google_analytics_monthly_performance.ORCHESTRATION
│   └── orc_harmonization_fact_google_analytics_monthly_performance_region.ORCHESTRATION
└── Unit Test/
    ├── orc_unit_test_fact_google_analytics_monthly_performance.ORCHESTRATION
    └── orc_unit_test_fact_google_analytics_monthly_performance_region.ORCHESTRATION
```

### Presentation Layer Tables

#### 1. FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE
**Schema:** `PL_SOCIALMEDIA.FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE`

Business-ready fact table for monthly performance analysis by market.

**Grain:** One row per market, month, platform, channel, domain, and device combination.

#### 2. FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION
**Schema:** `PL_SOCIALMEDIA.FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION`

Business-ready fact table for monthly performance analysis by region.

**Grain:** One row per region, month, platform, channel, domain, and device combination.

### Unit Tests

Automated validation pipelines ensure data quality:
- `orc_unit_test_fact_google_analytics_monthly_performance`
- `orc_unit_test_fact_google_analytics_monthly_performance_region`

---

## Data Flow

### Complete End-to-End Flow

```
┌──────────────────────────────────────────────────────────────────┐
│ SOURCE: Google BigQuery                                           │
│ Project: pmi-rrp-bi-glob-prod-001                                │
│ Dataset: dashboard_hack                                           │
│ Tables: ga4_hack_monthly_market, ga4_hack_monthly_region         │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ [Ingestion Pipeline]
                     │ • Service Account Auth
                     │ • PEM File Generation
                     │ • Incremental Load (based on updated_at)
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ STAGING LAYER                                                     │
│ Database: ${ev_database_10_staging}                              │
│ Schema: STG_GOOGLE_ANALYTICS                                     │
│ Tables:                                                           │
│   • T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET                       │
│   • T_GOOGLE_ANALYTICS_HACK_MONTHLY_REGION                       │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ [Harmonization Pipeline]
                     │ • Create transient delta tables
                     │ • Dimension lookups
                     │ • Data type transformations
                     │ • NULL key handling
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ INTEGRATION LAYER                                                 │
│ Database: ${ev_database_20_integration}                          │
│ Schema: ${ev_data_foundation_schema_20_integration}              │
│                                                                   │
│ DIMENSIONS:                                                       │
│   ├─ DIM_GA_MAPPING_MARKET_COUNTRY                               │
│   ├─ DIM_GA_MAPPING_REGION                                       │
│   ├─ DIM_DIGITAL_DEVICE                                          │
│   ├─ DIM_WEBSITE_DOMAIN                                          │
│   ├─ DIM_TRAFFIC_CHANNEL                                         │
│   └─ DIM_CUSTOM_CHANNEL                                          │
│                                                                   │
│ VIEWS:                                                            │
│   ├─ V_INT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE            │
│   └─ V_INT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION     │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     │ [Load to Presentation]
                     │ • Merge/Upsert logic
                     │ • Final data quality checks
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ PRESENTATION LAYER                                                │
│ Database: ${ev_database_30_presentation}                         │
│ Schema: PL_SOCIALMEDIA                                           │
│                                                                   │
│ FACT TABLES:                                                      │
│   ├─ FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE                   │
│   └─ FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION            │
│                                                                   │
│ DIMENSIONS (Shared):                                              │
│   ├─ DIM_MARKET (from PL_COMMON_LAYER)                           │
│   ├─ DIM_DATE (from PL_COMMON_LAYER)                             │
│   ├─ DIM_PRODUCT_PLATFORM (from PL_COMMON_LAYER)                 │
│   ├─ DIM_CUSTOM_CHANNEL                                          │
│   ├─ DIM_TRAFFIC_CHANNEL                                         │
│   ├─ DIM_WEBSITE_DOMAIN                                          │
│   └─ DIM_DIGITAL_DEVICE                                          │
└──────────────────────────────────────────────────────────────────┘
                     │
                     ▼
          [ BI Tools / Analytics ]
```

---

## Configuration

### Environment Variables

| Variable | Description | Usage |
|----------|-------------|-------|
| `ev_warehouse_10_default` | Default Snowflake warehouse for staging operations | Ingestion layer |
| `ev_database_10_staging` | Staging database name | Ingestion layer |
| `ev_database_20_integration` | Integration database name | Harmonization layer |
| `ev_database_30_presentation` | Presentation database name | Final output layer |
| `ev_data_foundation_schema_20_integration` | Integration schema name | Transformation views |
| `ev_default_system_env` | Current environment (dev/qas/prd) | All layers |
| `ev_harmonization_email_recipient` | Email for failure notifications | Error handling |

### AWS Secrets Manager Configuration

**Secret ARNs per Environment:**
- **Dev:** `arn:aws:secretsmanager:eu-west-1:737367661636:secret:dev/matillion/s-cons-matillion/elmacons-gcp-web-analytics-9vo9hv`
- **QAS:** `arn:aws:secretsmanager:eu-west-1:171145916340:secret:qa/matillion/s-cons-matillion/elmacons-gcp-web-analytics-XiutKy`
- **PRD:** `arn:aws:secretsmanager:eu-west-1:884166386585:secret:prd/matillion/s-cons-matillion/elmacons-gcp-web-analytics-qRWCb1`

**Secret Contents:**
```json
{
  "client_email": "matillion@pmi-rrp-bi-glob-prod-001.iam.gserviceaccount.com",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
}
```

---

## Error Handling

### Transaction Management

The harmonization pipeline uses **database transactions** to ensure atomicity:

```
Begin Transaction
  ├─ Create transient delta tables
  ├─ Process dimensions
  ├─ Process facts
  └─ Commit (or Rollback on failure)
```

### Failure Scenarios

#### 1. Transient Table Creation Failure
**Pipeline:** Harmonization Master

**Action:**
1. Send email notification to `${ev_harmonization_email_recipient}`
2. Email subject: "Harmonization Pipeline Check has failed for table [TABLE_NAME] in INTEGRATION layer!"
3. Delete transient table (if exists)
4. End with failure status

**Email Content Includes:**
- Pipeline name
- Table/View name
- Layer (INTEGRATION)
- Run history ID
- Environment

#### 2. Dimension Processing Failure
**Pipeline:** Harmonization Master

**Action:**
1. Rollback transaction
2. Truncate transient delta tables
3. End with failure status

#### 3. Fact Processing Failure
**Pipeline:** Harmonization Master

**Action:**
1. Rollback transaction
2. Truncate transient delta tables
3. End with failure status

### Logging and Monitoring

- **Query Tagging:** `ALTER SESSION SET query_tag = '{job_name}-{run_history_id}'`
- **ETL Task History:** Loaded at the end of successful pipeline execution
- **Run History ID:** Available as `${run_history_id}` for tracking

---

## Tables and Views

### Summary

| Layer | Type | Count | Examples |
|-------|------|-------|----------|
| **Staging** | Tables | 2 | T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET |
| **Integration** | Views | 2 | V_INT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE |
| **Integration** | Dimensions | 6 | DIM_DIGITAL_DEVICE, DIM_TRAFFIC_CHANNEL |
| **Integration** | Transient | 2 | TRANSIENT_FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_DELTA |
| **Presentation** | Fact Tables | 2 | FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE |
| **Presentation** | Dimensions | 7 | Shared dimensions from PL_COMMON_LAYER + GA-specific |

### Naming Conventions

- **Staging Tables:** `T_GOOGLE_ANALYTICS_[TABLE_NAME]`
- **Integration Views:** `V_INT_FACT_GOOGLE_ANALYTICS_[TABLE_NAME]`
- **Presentation Tables:** `FACT_GOOGLE_ANALYTICS_[TABLE_NAME]`
- **Dimensions:** `DIM_[DIMENSION_NAME]`
- **Transient Tables:** `TRANSIENT_FACT_GOOGLE_ANALYTICS_[TABLE_NAME]_DELTA`

---

## Key Metrics

### Monthly Metrics
- **TOTAL_SESSIONS_MONTHLY:** Total website sessions in the month
- **ENGAGED_SESSIONS_MONTHLY:** Sessions with engagement (>10 seconds or conversion)
- **USERS_VISIT_MONTHLY:** Unique users visiting in the month
- **USER_PURCHASE_RATIO_MONTHLY:** Percentage of users making a purchase
- **ENGAGEMENT_RATE_MONTHLY:** Percentage of engaged sessions
- **CART_CONVERSION_RATE_MONTHLY:** Cart-to-purchase conversion rate
- **CART_ABANDONMENT_RATE_MONTHLY:** Cart abandonment rate

### Year-to-Date Metrics
All monthly metrics have corresponding YTD aggregations:
- TOTAL_SESSIONS_YTD
- ENGAGED_SESSIONS_YTD
- USERS_VISIT_YTD
- USER_PURCHASE_RATIO_YTD
- ENGAGEMENT_RATE_YTD
- CART_CONVERSION_RATE_YTD
- CART_ABANDONMENT_RATE_YTD

---

## Business Use Cases

### 1. Market Performance Analysis
Track website engagement and conversion metrics across different markets using:
- `FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE` joined with `DIM_MARKET`

### 2. Regional Trends
Analyze regional performance patterns using:
- `FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE_REGION` joined with `DIM_GA_MAPPING_REGION`

### 3. Channel Attribution
Understand which marketing channels drive the most engagement:
- Join with `DIM_TRAFFIC_CHANNEL` and `DIM_CUSTOM_CHANNEL`

### 4. Device Analysis
Compare performance across device types (mobile, desktop, tablet):
- Join with `DIM_DIGITAL_DEVICE`

### 5. Platform Comparison
Analyze performance by product platform:
- Join with `DIM_PRODUCT_PLATFORM`

### 6. Time-Series Analysis
Track trends over time with monthly and YTD metrics:
- Join with `DIM_DATE` for calendar attributes

---

## Dependencies

### External Systems
- **Google BigQuery:** Source system for GA4 data
- **AWS Secrets Manager:** Credential management
- **Snowflake:** Target data warehouse

### Internal Dependencies
- **Common Dimensions:**
  - `PL_COMMON_LAYER.DIM_MARKET`
  - `PL_COMMON_LAYER.DIM_DATE`
  - `PL_COMMON_LAYER.DIM_PRODUCT_PLATFORM`

---

## Maintenance and Operations

### Incremental Loading
The pipeline uses `updated_at` timestamp for incremental processing:
- **BigQuery Indicator:** `DATE(updated_at)`
- **Snowflake Indicator:** `DATE(UPDATED_AT)`

### Performance Optimization
- **Transient Delta Tables:** Temporary tables for intermediate processing
- **Parallel Execution:** Dimensions and facts processed in parallel where possible
- **Transaction Boundaries:** Minimize transaction scope for better concurrency

### Data Refresh Schedule
The pipeline can be scheduled based on business requirements. Typical patterns:
- **Daily:** For near real-time reporting
- **Weekly:** For standard business reporting
- **On-Demand:** Triggered by upstream data availability

---

## Contact and Support

For issues or questions regarding this pipeline:
- **Email Notifications:** Configured via `${ev_harmonization_email_recipient}`
- **Pipeline Owner:** Data Engineering Team
- **Source System:** Google Analytics / BigQuery Team
- **Target System:** Snowflake DBA Team

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-02  
**Pipeline Version:** Based on current production configuration
