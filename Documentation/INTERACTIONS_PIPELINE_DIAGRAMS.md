# Interactions Pipeline Architecture Diagrams

## Master Pipeline Flow

```mermaid
graph TB
    Start([Start]) --> QueryTag[Set Query Tag<br/>job_name-run_history_id]
    QueryTag --> Ingestion[Ingestion Dispatch<br/>DISP Ingestion - CONS 1]

    Ingestion --> SetVars[Set Variables<br/>- jv_source_name = dce2<br/>- jv_output_tenant_name = edp_consumer<br/>- jv_process_table]

    SetVars --> BridgeRLS[Bridge / RLS Step<br/>orc_harmonization_rde_bridge_consumer_rls 0]
    BridgeRLS --> LoadHistory[Task History Load]
    LoadHistory --> End([End])

    style Start fill:#90EE90
    style End fill:#90EE90
    style Ingestion fill:#87CEEB
    style BridgeRLS fill:#FFB6C1
    style LoadHistory fill:#FFD700
```

## Ingestion and Staging Detail

```mermaid
graph LR
    subgraph "DCE2 Source / Landing"
        SRC[DCE2 Consumer Interaction Domain]
    end

    subgraph "Ingestion Control"
        DISP[DISP Ingestion - CONS 1<br/>source = dce2<br/>tenant = edp_consumer]
        TRIG[gv_trigger_harmonization<br/>downstream orchestration mappings]
    end

    subgraph "Staging Layer"
        STG[STG_DCE2]
        STG_T1[T_DCE2_INTERACTION]
        STG_T2[T_DCE2_INTERACTION_DEVICE]
        STG_T3[T_DCE2_INTERACTION_FLAVOUR]
        STG_T4[T_DCE2_INTERACTION_PRODUCT]
        STG_T5[T_DCE2_INTERACTION_VOUCHER]
    end

    SRC --> DISP
    DISP --> TRIG
    DISP --> STG
    STG --> STG_T1
    STG --> STG_T2
    STG --> STG_T3
    STG --> STG_T4
    STG --> STG_T5

    style SRC fill:#4285F4
    style DISP fill:#87CEEB
    style TRIG fill:#FFD700
    style STG fill:#87CEEB
```

## Integration Transformation Pattern

```mermaid
graph TB
    subgraph "Staging Inputs"
        S1[T_DCE2_INTERACTION]
        S2[T_DCE2_INTERACTION_DEVICE]
        S3[T_DCE2_INTERACTION_FLAVOUR]
        S4[T_DCE2_INTERACTION_PRODUCT]
        S5[T_DCE2_INTERACTION_VOUCHER]
    end

    subgraph "Shared Transformation Logic"
        Filter[Filter Bad Data Quality<br/>TRY_TO_TIMESTAMP_NTZ(date_time) <= __LOAD_TS<br/>or date_time is NULL]
        Hist[Add Historization Logic<br/>derive VALID_FROM]
        Dedup[Deduplicate<br/>COUNT OVER + ROW_NUMBER OVER]
        Calc[Calculator / Column Mapping]
        Select[Select Final Columns]
    end

    subgraph "Integration Views"
        V1[V_INT_TDE_CONSUMER_INTERACTION]
        V2[V_INT_MDE_CONSUMER_INTERACTION_DEVICE]
        V3[V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR]
        V4[V_INT_MDE_CONSUMER_INTERACTION_PRODUCT]
        V5[V_INT_MDE_CONSUMER_INTERACTION_VOUCHER]
    end

    S1 --> Filter
    S2 --> Filter
    S3 --> Filter
    S4 --> Filter
    S5 --> Filter

    Filter --> Hist
    Hist --> Dedup
    Dedup --> Calc
    Calc --> Select

    Select --> V1
    Select --> V2
    Select --> V3
    Select --> V4
    Select --> V5

    style Filter fill:#FFD700
    style Hist fill:#FFA07A
    style Dedup fill:#FFA07A
    style Calc fill:#87CEEB
    style Select fill:#90EE90
```

## Presentation Harmonization Flow

```mermaid
graph TB
    Start([Start Harmonization]) --> Cols[Get Staging Column List]
    Cols --> Retry[Retry - Initial]
    Retry --> Create[Create Table<br/>Loading Type = SCD2_DELTA_V3]
    Create --> Transform[Run Integration Transformation]
    Transform --> Truncate[Truncate Table]
    Truncate --> Cleanup1[Delete Transient Table]
    Cleanup1 --> Cleanup2[Delete Tables]
    Cleanup2 --> EndSuccess([End Success])

    Create -->|Failure| Email[Send Email Notification]
    Transform -->|Failure| Email
    Email --> EndFail([End Failure])

    style Start fill:#90EE90
    style EndSuccess fill:#90EE90
    style EndFail fill:#FFB6C1
    style Create fill:#FFD700
    style Transform fill:#87CEEB
    style Email fill:#FF6B6B
```

## MDE and TDE Publication Map

```mermaid
graph LR
    subgraph "Integration Layer"
        I1[V_INT_TDE_CONSUMER_INTERACTION]
        I2[V_INT_MDE_CONSUMER_INTERACTION_DEVICE]
        I3[V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR]
        I4[V_INT_MDE_CONSUMER_INTERACTION_PRODUCT]
        I5[V_INT_MDE_CONSUMER_INTERACTION_VOUCHER]
    end

    subgraph "Presentation Layer"
        P1[TDE_CONSUMER_INTERACTION]
        P2[MDE_CONSUMER_INTERACTION_DEVICE]
        P3[MDE_CONSUMER_INTERACTION_FLAVOUR]
        P4[MDE_CONSUMER_INTERACTION_PRODUCT]
        P5[MDE_CONSUMER_INTERACTION_VOUCHER]
    end

    subgraph "Unit Tests"
        U1[orc_unit_test_tde_consumer_interaction]
        U2[orc_unit_test_mde_consumer_interaction_device]
        U3[orc_unit_test_mde_consumer_interaction_flavour]
        U4[orc_unit_test_mde_consumer_interaction_product]
        U5[orc_unit_test_mde_consumer_interaction_voucher]
    end

    I1 --> P1 --> U1
    I2 --> P2 --> U2
    I3 --> P3 --> U3
    I4 --> P4 --> U4
    I5 --> P5 --> U5

    style I1 fill:#FFB6C1
    style I2 fill:#FFB6C1
    style I3 fill:#FFB6C1
    style I4 fill:#FFB6C1
    style I5 fill:#FFB6C1
    style P1 fill:#90EE90
    style P2 fill:#90EE90
    style P3 fill:#90EE90
    style P4 fill:#90EE90
    style P5 fill:#90EE90
    style U1 fill:#87CEEB
    style U2 fill:#87CEEB
    style U3 fill:#87CEEB
    style U4 fill:#87CEEB
    style U5 fill:#87CEEB
```

## Row-Level Security Pattern

```mermaid
graph LR
    subgraph "Presentation Objects"
        TDE[TDE_CONSUMER_INTERACTION]
        DEV[MDE_CONSUMER_INTERACTION_DEVICE]
        FLA[MDE_CONSUMER_INTERACTION_FLAVOUR]
        PRO[MDE_CONSUMER_INTERACTION_PRODUCT]
        VOU[MDE_CONSUMER_INTERACTION_VOUCHER]
    end

    subgraph "Consumer Security Alignment"
        GIGYA[MDE_GIGYA_CONSUMER]
        RLS[RLS Country Filter<br/>#RLS_LIST_OF_COUNTRIES]
    end

    TDE --> GIGYA
    DEV --> GIGYA
    FLA --> GIGYA
    PRO --> GIGYA
    VOU --> GIGYA
    GIGYA --> RLS

    style GIGYA fill:#FFD700
    style RLS fill:#FF6B6B
    style TDE fill:#90EE90
    style DEV fill:#90EE90
    style FLA fill:#90EE90
    style PRO fill:#90EE90
    style VOU fill:#90EE90
```

## Complete Data Warehouse Architecture

```mermaid
graph TB
    subgraph "Source Domain"
        SRC[DCE2 Interaction Events]
    end

    subgraph "Staging Layer"
        STG[ev_database_10_staging<br/>STG_DCE2]
        STG1[T_DCE2_INTERACTION]
        STG2[T_DCE2_INTERACTION_DEVICE]
        STG3[T_DCE2_INTERACTION_FLAVOUR]
        STG4[T_DCE2_INTERACTION_PRODUCT]
        STG5[T_DCE2_INTERACTION_VOUCHER]

        STG --> STG1
        STG --> STG2
        STG --> STG3
        STG --> STG4
        STG --> STG5
    end

    subgraph "Integration Layer"
        INT[ev_database_20_integration<br/>ev_data_foundation_schema_20_integration]
        INT1[V_INT_TDE_CONSUMER_INTERACTION]
        INT2[V_INT_MDE_CONSUMER_INTERACTION_DEVICE]
        INT3[V_INT_MDE_CONSUMER_INTERACTION_FLAVOUR]
        INT4[V_INT_MDE_CONSUMER_INTERACTION_PRODUCT]
        INT5[V_INT_MDE_CONSUMER_INTERACTION_VOUCHER]

        INT --> INT1
        INT --> INT2
        INT --> INT3
        INT --> INT4
        INT --> INT5
    end

    subgraph "Presentation Layer"
        PL[ev_database_30_presentation<br/>PL_INTERACTION]
        PL1[TDE_CONSUMER_INTERACTION]
        PL2[MDE_CONSUMER_INTERACTION_DEVICE]
        PL3[MDE_CONSUMER_INTERACTION_FLAVOUR]
        PL4[MDE_CONSUMER_INTERACTION_PRODUCT]
        PL5[MDE_CONSUMER_INTERACTION_VOUCHER]

        DQ[PL_COMMON_LAYER_DQ<br/>DQ companion tables]

        PL --> PL1
        PL --> PL2
        PL --> PL3
        PL --> PL4
        PL --> PL5
    end

    subgraph "Analytics & Sharing"
        BI[Power BI / SQL / Shared Data Products]
    end

    SRC --> |Ingestion| STG
    STG --> |Integration Transformations| INT
    INT --> |SCD2 Delta Harmonization| PL
    PL --> |Consumption| BI
    PL --> DQ

    style SRC fill:#4285F4
    style STG fill:#87CEEB
    style INT fill:#FFB6C1
    style PL fill:#90EE90
    style DQ fill:#FFD700
    style BI fill:#9370DB
```

## SCD2 Lifecycle Pattern

```mermaid
graph TB
    NewRow[Incoming Staging Row] --> ParseTS[Parse INTERACTION_DATETIME]
    ParseTS --> Quality[Validate Timestamp vs __LOAD_TS]
    Quality --> Dedup[Deduplicate by Business Key + Timestamp]
    Dedup --> ValidFrom[Set VALID_FROM]
    ValidFrom --> Merge[SCD2 Delta Load]
    Merge --> Active[ACTIVE_FLAG = TRUE current row]
    Merge --> Closed[Prior row closed with VALID_TO]

    style NewRow fill:#87CEEB
    style Merge fill:#FFD700
    style Active fill:#90EE90
    style Closed fill:#FFB6C1
```
