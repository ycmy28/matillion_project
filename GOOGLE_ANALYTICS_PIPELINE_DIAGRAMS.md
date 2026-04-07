# Google Analytics Pipeline Architecture Diagrams

## Master Pipeline Flow

```mermaid
graph TB
    Start([Start]) --> QueryTag[Set Query Tag<br/>job_name-run_history_id]
    QueryTag --> Ingestion[Ingestion Pipeline<br/>orc_ingestion_bigquery_main]
    
    Ingestion --> SetVars[Set Variables<br/>- jv_secrets_manager_arn_dict<br/>- jv_source = GOOGLE_ANALYTICS<br/>- jv_snowflake_warehouse]
    
    SetVars --> Harmonization[Harmonization Pipeline<br/>orc_harmonization_master_google_analytics]
    
    Harmonization --> |Success| LoadHistory[Load ETL Task History]
    Harmonization --> |Failure| LoadHistory
    
    LoadHistory --> End([End])
    
    style Start fill:#90EE90
    style End fill:#90EE90
    style Ingestion fill:#87CEEB
    style Harmonization fill:#FFB6C1
```

## Ingestion Layer Detail

```mermaid
graph LR
    subgraph "BigQuery Source"
        BQ1[pmi-rrp-bi-glob-prod-001<br/>dashboard_hack<br/>ga4_hack_monthly_market]
        BQ2[pmi-rrp-bi-glob-prod-001<br/>dashboard_hack<br/>ga4_hack_monthly_region]
    end
    
    subgraph "Authentication"
        AWS[AWS Secrets Manager] --> PEM[Generate PEM File<br/>/tmp/private_key_CONS_GOOGLE_ANALYTICS.pem]
        PEM --> SA[Service Account<br/>matillion@pmi-rrp-bi-glob-prod-001.iam.gserviceaccount.com]
    end
    
    subgraph "Staging Layer"
        STG1[STG_GOOGLE_ANALYTICS<br/>T_GOOGLE_ANALYTICS_HACK_MONTHLY_MARKET]
        STG2[STG_GOOGLE_ANALYTICS<br/>T_GOOGLE_ANALYTICS_HACK_MONTHLY_REGION]
    end
    
    BQ1 --> |Grid Iterator| SA
    BQ2 --> |Grid Iterator| SA
    SA --> STG1
    SA --> STG2
    
    style BQ1 fill:#4285F4
    style BQ2 fill:#4285F4
    style AWS fill:#FF9900
    style STG1 fill:#87CEEB
    style STG2 fill:#87CEEB
```

## Harmonization Layer Flow

```mermaid
graph TB
    Start([Start Harmonization]) --> BeginTx[Begin Transaction]
    
    BeginTx --> CreateTransient1[Create Transient Delta Table<br/>TRANSIENT_FACT_GA_MONTHLY_PERFORMANCE_DELTA]
    BeginTx --> CreateTransient2[Create Transient Delta Table<br/>TRANSIENT_FACT_GA_MONTHLY_PERFORMANCE_REGION_DELTA]
    
    CreateTransient1 --> |Success| DimProc[Process Dimensions<br/>Parallel Execution]
    CreateTransient2 --> |Success| DimProc
    
    CreateTransient1 --> |Failure| EmailFail1[Send Email Notification]
    CreateTransient2 --> |Failure| EmailFail2[Send Email Notification]
    
    EmailFail1 --> DeleteTrans1[Delete Transient Table]
    EmailFail2 --> DeleteTrans2[Delete Transient Table]
    DeleteTrans1 --> EndFail1([End Failure])
    DeleteTrans2 --> EndFail2([End Failure])
    
    DimProc --> Dim1[dim_ga_mapping_region]
    DimProc --> Dim2[dim_digital_device]
    DimProc --> Dim3[dim_website_domain]
    DimProc --> Dim4[dim_traffic_channel]
    DimProc --> Dim5[dim_custom_channel]
    DimProc --> Dim6[dim_ga_mapping_market_country]
    
    Dim1 --> |Success| FactProc[Process Facts<br/>Parallel Execution]
    Dim2 --> |Success| FactProc
    Dim3 --> |Success| FactProc
    Dim4 --> |Success| FactProc
    Dim5 --> |Success| FactProc
    Dim6 --> |Success| FactProc
    
    Dim1 --> |Failure| Rollback
    Dim2 --> |Failure| Rollback
    Dim3 --> |Failure| Rollback
    Dim4 --> |Failure| Rollback
    Dim5 --> |Failure| Rollback
    Dim6 --> |Failure| Rollback
    
    FactProc --> Fact1[fact_ga_monthly_performance]
    FactProc --> Fact2[fact_ga_monthly_performance_region]
    
    Fact1 --> |Success| Commit[Commit Transaction]
    Fact2 --> |Success| Commit
    
    Fact1 --> |Failure| Rollback[Rollback Transaction]
    Fact2 --> |Failure| Rollback
    
    Commit --> Truncate1[Truncate Transient Tables]
    Truncate1 --> EndSuccess([End Success])
    
    Rollback --> Truncate2[Truncate Transient Tables]
    Truncate2 --> EndFailProc([End Failure])
    
    style Start fill:#90EE90
    style EndSuccess fill:#90EE90
    style EndFail1 fill:#FFB6C1
    style EndFail2 fill:#FFB6C1
    style EndFailProc fill:#FFB6C1
    style BeginTx fill:#FFD700
    style Commit fill:#90EE90
    style Rollback fill:#FF6B6B
```

## Integration Layer Transformation Detail

```mermaid
graph TB
    subgraph "Source"
        TransDelta[TRANSIENT_FACT_GOOGLE_ANALYTICS<br/>MONTHLY_PERFORMANCE_DELTA]
    end
    
    subgraph "Dimension Lookups"
        DimMarketMap[DIM_GA_MAPPING_MARKET_COUNTRY<br/>Join: TRIM MARKET = SOURCE_MARKET_NAME]
        DimMarket[DIM_MARKET<br/>Join: DIM_MARKET_KEY]
        DimDate[DIM_DATE filtered CAL_DAY_IN_MONTH=1<br/>Join: MONTH_YEAR = CAL_MONTH]
        DimPlatform[DIM_PRODUCT_PLATFORM<br/>Join: TRIM PLATFORM_CATEGORY = PRODUCT_PLATFORM_NAME]
        DimCustom[DIM_CUSTOM_CHANNEL<br/>Join: TRIM SUB_CATEGORY = CUSTOM_CHANNEL_NAME]
        DimDomain[DIM_WEBSITE_DOMAIN<br/>Join: TRIM HOSTNAME = WEBSITE_DOMAIN_NAME]
        DimTraffic[DIM_TRAFFIC_CHANNEL<br/>Join: TRIM CHANNEL_GROUP = TRAFFIC_CHANNEL_NAME]
        DimDevice[DIM_DIGITAL_DEVICE<br/>Join: TRIM DEVICE_CATEGORY = DIGITAL_DEVICE_NAME]
    end
    
    subgraph "Transformation Steps"
        Join[Left Join All Dimensions]
        NullHandler[NULL Key Handler<br/>COALESCE key, -1]
        TypeCast[Data Type Casting<br/>- Keys → TEXT 255<br/>- Measures → NUMBER<br/>- Timestamps → TIMESTAMP_NTZ]
        Distinct[Remove Duplicates]
        SelectCols[Select Final Columns]
    end
    
    subgraph "Output"
        IntView[V_INT_FACT_GOOGLE_ANALYTICS<br/>MONTHLY_PERFORMANCE]
    end
    
    TransDelta --> Join
    DimMarketMap --> Join
    DimMarket --> Join
    DimDate --> Join
    DimPlatform --> Join
    DimCustom --> Join
    DimDomain --> Join
    DimTraffic --> Join
    DimDevice --> Join
    
    Join --> NullHandler
    NullHandler --> TypeCast
    TypeCast --> Distinct
    Distinct --> SelectCols
    SelectCols --> IntView
    
    style TransDelta fill:#87CEEB
    style IntView fill:#90EE90
    style Join fill:#FFD700
    style NullHandler fill:#FFA07A
    style TypeCast fill:#FFA07A
```

## Complete Data Warehouse Architecture

```mermaid
graph TB
    subgraph "Source: Google BigQuery"
        BQ[pmi-rrp-bi-glob-prod-001<br/>dashboard_hack]
    end
    
    subgraph "Staging Layer"
        STG[STG_GOOGLE_ANALYTICS<br/>ev_database_10_staging]
        STG_T1[T_GA_HACK_MONTHLY_MARKET]
        STG_T2[T_GA_HACK_MONTHLY_REGION]
        
        STG --> STG_T1
        STG --> STG_T2
    end
    
    subgraph "Integration Layer"
        INT[ev_database_20_integration<br/>ev_data_foundation_schema_20_integration]
        
        INT_DIM[Dimensions]
        INT_D1[DIM_GA_MAPPING_MARKET_COUNTRY]
        INT_D2[DIM_GA_MAPPING_REGION]
        INT_D3[DIM_DIGITAL_DEVICE]
        INT_D4[DIM_WEBSITE_DOMAIN]
        INT_D5[DIM_TRAFFIC_CHANNEL]
        INT_D6[DIM_CUSTOM_CHANNEL]
        
        INT_VIEW[Integration Views]
        INT_V1[V_INT_FACT_GA_MONTHLY_PERFORMANCE]
        INT_V2[V_INT_FACT_GA_MONTHLY_PERFORMANCE_REGION]
        
        INT --> INT_DIM
        INT --> INT_VIEW
        INT_DIM --> INT_D1
        INT_DIM --> INT_D2
        INT_DIM --> INT_D3
        INT_DIM --> INT_D4
        INT_DIM --> INT_D5
        INT_DIM --> INT_D6
        INT_VIEW --> INT_V1
        INT_VIEW --> INT_V2
    end
    
    subgraph "Presentation Layer"
        PL[ev_database_30_presentation<br/>PL_SOCIALMEDIA]
        
        PL_FACT[Fact Tables]
        PL_F1[FACT_GA_MONTHLY_PERFORMANCE]
        PL_F2[FACT_GA_MONTHLY_PERFORMANCE_REGION]
        
        PL_DIM[Dimensions Available]
        PL_D1[DIM_MARKET from PL_COMMON_LAYER]
        PL_D2[DIM_DATE from PL_COMMON_LAYER]
        PL_D3[DIM_PRODUCT_PLATFORM from PL_COMMON_LAYER]
        PL_D4[+ GA-specific dimensions]
        
        PL --> PL_FACT
        PL --> PL_DIM
        PL_FACT --> PL_F1
        PL_FACT --> PL_F2
        PL_DIM --> PL_D1
        PL_DIM --> PL_D2
        PL_DIM --> PL_D3
        PL_DIM --> PL_D4
    end
    
    subgraph "Analytics & BI"
        BI[Tableau / PowerBI / SQL Clients]
    end
    
    BQ --> |Ingestion Pipeline| STG
    STG --> |Harmonization Pipeline| INT
    INT --> |Load to Presentation| PL
    PL --> |Queries| BI
    
    style BQ fill:#4285F4
    style STG fill:#87CEEB
    style INT fill:#FFB6C1
    style PL fill:#90EE90
    style BI fill:#9370DB
```

## Fact Table Schema

```mermaid
erDiagram
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE {
        TEXT_255 DIM_MARKET_KEY FK
        TEXT_255 DIM_DATE_KEY FK
        DATE YEAR_TO_DATE_INDICATOR
        TEXT_255 DIM_PRODUCT_PLATFORM_KEY FK
        TEXT_255 DIM_CUSTOM_CHANNEL_KEY FK
        TEXT_255 DIM_TRAFFIC_CHANNEL_KEY FK
        TEXT_255 DIM_WEBSITE_DOMAIN_KEY FK
        TEXT_255 DIM_DIGITAL_DEVICE_KEY FK
        TEXT_255 GOOGLE_ANALYTICS_MONTHLY_MARKET_PERFORMANCE_BK
        NUMBER TOTAL_SESSIONS_MONTHLY
        NUMBER ENGAGED_SESSIONS_MONTHLY
        NUMBER USERS_VISIT_MONTHLY
        NUMBER_38_5 USER_PURCHASE_RATIO_MONTHLY
        NUMBER_38_5 ENGAGEMENT_RATE_MONTHLY
        NUMBER_38_5 CART_CONVERSION_RATE_MONTHLY
        NUMBER_38_5 CART_ABANDONMENT_RATE_MONTHLY
        NUMBER TOTAL_SESSIONS_YTD
        NUMBER ENGAGED_SESSIONS_YTD
        NUMBER_38_5 USERS_VISIT_YTD
        NUMBER_38_5 USER_PURCHASE_RATIO_YTD
        NUMBER_38_5 ENGAGEMENT_RATE_YTD
        NUMBER_38_5 CART_CONVERSION_RATE_YTD
        NUMBER_38_5 CART_ABANDONMENT_RATE_YTD
        TIMESTAMP_NTZ LAST_UPDATED_DATETIME
    }
    
    DIM_MARKET {
        TEXT_255 DIM_MARKET_KEY PK
        TEXT MARKET_NAME
    }
    
    DIM_DATE {
        TEXT_255 DIM_DATE_KEY PK
        NUMBER CAL_MONTH
        NUMBER CAL_DAY_IN_MONTH
    }
    
    DIM_PRODUCT_PLATFORM {
        TEXT_255 DIM_PRODUCT_PLATFORM_KEY PK
        TEXT PRODUCT_PLATFORM_NAME
    }
    
    DIM_CUSTOM_CHANNEL {
        TEXT_255 DIM_CUSTOM_CHANNEL_KEY PK
        TEXT CUSTOM_CHANNEL_NAME
    }
    
    DIM_TRAFFIC_CHANNEL {
        TEXT_255 DIM_TRAFFIC_CHANNEL_KEY PK
        TEXT TRAFFIC_CHANNEL_NAME
    }
    
    DIM_WEBSITE_DOMAIN {
        TEXT_255 DIM_WEBSITE_DOMAIN_KEY PK
        TEXT WEBSITE_DOMAIN_NAME
    }
    
    DIM_DIGITAL_DEVICE {
        TEXT_255 DIM_DIGITAL_DEVICE_KEY PK
        TEXT DIGITAL_DEVICE_NAME
    }
    
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_MARKET : "has"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_DATE : "on"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_PRODUCT_PLATFORM : "for"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_CUSTOM_CHANNEL : "via"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_TRAFFIC_CHANNEL : "from"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_WEBSITE_DOMAIN : "at"
    FACT_GOOGLE_ANALYTICS_MONTHLY_PERFORMANCE ||--o{ DIM_DIGITAL_DEVICE : "using"
```

## Execution Timeline

```mermaid
gantt
    title Google Analytics Pipeline Execution Flow
    dateFormat HH:mm
    axisFormat %H:%M
    
    section Preparation
    Set Query Tag           :done, prep1, 00:00, 1m
    
    section Ingestion
    PEM File Generation     :active, ing1, 00:01, 2m
    Grid Iterator Setup     :ing2, after ing1, 1m
    Load Table 1 (Market)   :ing3, after ing2, 10m
    Load Table 2 (Region)   :ing4, after ing2, 10m
    
    section Harmonization
    Begin Transaction       :harm1, after ing3 ing4, 1m
    Create Transient Tables :harm2, after harm1, 3m
    Process Dimensions      :harm3, after harm2, 8m
    Process Facts           :harm4, after harm3, 12m
    Commit Transaction      :harm5, after harm4, 1m
    Truncate Transient      :harm6, after harm5, 2m
    
    section Finalization
    Load ETL History        :final1, after harm6, 2m
    End Pipeline            :milestone, final2, after final1, 0m
```

## Error Handling Flow

```mermaid
graph TB
    Start([Pipeline Start]) --> Exec{Execution}
    
    Exec --> |Success Path| Normal[Normal Flow]
    Exec --> |Failure Path| Error{Error Type}
    
    Normal --> Commit[Commit Changes]
    Commit --> Cleanup[Cleanup Transient Tables]
    Cleanup --> History[Load ETL History]
    History --> Success([End Success])
    
    Error --> |Transient Creation Failed| Email1[Send Email Notification]
    Error --> |Dimension Processing Failed| Rollback[Rollback Transaction]
    Error --> |Fact Processing Failed| Rollback
    
    Email1 --> Delete[Delete Transient Table]
    Delete --> Fail1([End Failure])
    
    Rollback --> Truncate[Truncate Transient Tables]
    Truncate --> Fail2([End Failure])
    
    style Start fill:#90EE90
    style Success fill:#90EE90
    style Fail1 fill:#FF6B6B
    style Fail2 fill:#FF6B6B
    style Error fill:#FFD700
    style Rollback fill:#FFA500
    style Email1 fill:#FFA500
```

## Data Lineage

```mermaid
graph LR
    subgraph "BigQuery Source"
        BQ_M[ga4_hack_monthly_market]
        BQ_R[ga4_hack_monthly_region]
    end
    
    subgraph "Staging"
        STG_M[T_GA_HACK_MONTHLY_MARKET]
        STG_R[T_GA_HACK_MONTHLY_REGION]
    end
    
    subgraph "Integration Transient"
        TRANS_M[TRANSIENT_FACT_GA_MONTHLY_PERFORMANCE_DELTA]
        TRANS_R[TRANSIENT_FACT_GA_MONTHLY_PERFORMANCE_REGION_DELTA]
    end
    
    subgraph "Integration Views"
        VIEW_M[V_INT_FACT_GA_MONTHLY_PERFORMANCE]
        VIEW_R[V_INT_FACT_GA_MONTHLY_PERFORMANCE_REGION]
    end
    
    subgraph "Presentation"
        FACT_M[FACT_GA_MONTHLY_PERFORMANCE]
        FACT_R[FACT_GA_MONTHLY_PERFORMANCE_REGION]
    end
    
    BQ_M -->|Ingestion| STG_M
    BQ_R -->|Ingestion| STG_R
    
    STG_M -->|Create Delta| TRANS_M
    STG_R -->|Create Delta| TRANS_R
    
    TRANS_M -->|Transform & Join Dims| VIEW_M
    TRANS_R -->|Transform & Join Dims| VIEW_R
    
    VIEW_M -->|Load/Merge| FACT_M
    VIEW_R -->|Load/Merge| FACT_R
    
    style BQ_M fill:#4285F4
    style BQ_R fill:#4285F4
    style STG_M fill:#87CEEB
    style STG_R fill:#87CEEB
    style TRANS_M fill:#FFB6C1
    style TRANS_R fill:#FFB6C1
    style VIEW_M fill:#DDA0DD
    style VIEW_R fill:#DDA0DD
    style FACT_M fill:#90EE90
    style FACT_R fill:#90EE90
```

---

## Notes on Diagrams

These diagrams are rendered using Mermaid syntax and can be viewed in:
- GitHub README files
- GitLab markdown
- VS Code with Mermaid extension
- Mermaid Live Editor (https://mermaid.live)
- Confluence with Mermaid plugin
- Many documentation platforms

To view these diagrams, paste the code blocks into any Mermaid-compatible viewer or view this file in a platform that supports Mermaid rendering.
