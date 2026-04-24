# GCTS Strategy Implementation Diagram

```mermaid
flowchart TB
    A[Kantar files in S3<br/>Responses = Delta<br/>Options = Full<br/>Question Map = Full] --> B[Current ingestion path<br/>orc_ingestion_gcts]

    B --> C[Current risk area<br/>orc_load_stage_objects<br/>orc_run_group_calc<br/>orc_update_indicator]

    C --> D[Recommended historical layer in Snowflake<br/>HL_GCTS_RESPONSE<br/>HL_GCTS_OPTIONS<br/>HL_GCTS_QUESTION_MAP<br/>HL_GCTS_COUNTRY_CATEGORY]

    D --> E[Controlled current-facing layer<br/>Current stage views or current tables<br/>Expose active/latest slice]

    E --> F1[trn_v_int_dim_gcts_question<br/>Validate or adjust latest rule]
    E --> F2[trn_v_int_dim_gcts_option<br/>Add latest _ETL_LOAD_DATETIME logic]
    E --> F3[trn_v_int_fact_gcts_response<br/>Apply cutoff rule by YEAR MONTH COUNTRYCATEGORYID]

    F1 --> G[Stable downstream publishing]
    F2 --> G
    F3 --> G

    G --> H[Presentation Layer remains controlled<br/>while historical data is preserved]

    X[Disabled initial-load path<br/>trn_load_gcts_from_do<br/>Get the list of source files<br/>Load Stage Layer - Node] -.excluded from normal scheduled run.-> B
```

## Notes

- Recommended strategy: hybrid approach
- Preserve history in dedicated Snowflake history tables
- Keep a controlled current-facing layer for downstream consumption
- Adjust the 3 target transformations intentionally
- Exclude the disabled initial-load path from the normal scheduled-run design
