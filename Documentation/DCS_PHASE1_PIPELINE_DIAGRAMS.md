# DCS Phase 1 Pipeline Architecture Diagrams

## Master Pipeline Flow

```mermaid
graph TB
Start([Start]) --> QueryTag[Set Query Tag<br/>job_name-run_history_id]
QueryTag --> Ingestion[Ingestion Dispatch<br/>DISP Ingestion - CONS 1]

Ingestion --> SetVars[Set Variables<br/>- jv_source_name = dcs<br/>- jv_output_tenant_name = edp_consumer<br/>- jv_process_table]

SetVars --> DCSHarm[DCS Harmonization<br/>orc_harmonization_rde_bridge_consumer_rls 0]
DCSHarm --> LoadHistory[Task History Load]
LoadHistory --> End([End])

style Start fill:#90EE90
style End fill:#90EE90
style Ingestion fill:#87CEEB
style DCSHarm fill:#FFB6C1
style LoadHistory fill:#FFD700
```

## Multi-Market Ingestion and Staging Detail

```mermaid
graph LR
subgraph "DCS Source / Landing"
SRC[DCS Consumer Identity Domain<br/>14 Markets]
end

subgraph "Ingestion Control"
DISP[DISP Ingestion - CONS 1<br/>source = dcs<br/>tenant = edp_consumer]
TRIG[gv_trigger_harmonization<br/>downstream orchestration mappings]
end

subgraph "Staging Layer - STG_DCS"
STG[STG_DCS]
STG_T1[T_DCS_*_USERS<br/>14 markets]
STG_T2[T_DCS_*_USERSEXTRA<br/>14 markets]
STG_T3[T_DCS_CA_GUESTS<br/>1 market - CA only]
STG_T4[T_DCS_*_PROFILEFIELDS<br/>13 markets - no RO]
end

SRC --> DISP
DISP --> TRIG
DISP --> STG
STG --> STG_T1
STG --> STG_T2
STG --> STG_T3
STG --> STG_T4

style SRC fill:#4285F4
style DISP fill:#87CEEB
style TRIG fill:#FFD700
style STG fill:#87CEEB
```

## Integration Transformation Pattern

```mermaid
graph TB
subgraph "Staging Inputs"
S1[T_DCS_*_USERS<br/>14 market tables]
S2[T_DCS_*_USERSEXTRA<br/>14 market tables]
S3[T_DCS_CA_GUESTS<br/>1 market table]
S4[T_DCS_*_PROFILEFIELDS<br/>13 market tables]
end

subgraph "Shared Transformation Logic"
Union[UNION ALL<br/>Combine per-market tables]
Filter[Filter Bad Data Quality<br/>TRY_TO_TIMESTAMP_NTZ check]
Dedup[Deduplicate<br/>COUNT OVER + ROW_NUMBER OVER]
Country[Derive COUNTRY_CODE<br/>from market table name]
Hist[Add Historization Logic<br/>derive VALID_FROM]
Calc[Calculator / Column Mapping]
Select[Select Final Columns]
end

subgraph "Integration Views"
V1[V_INT_MDE_DCS_USER]
V2[V_INT_MDE_DCS_USER_EXTRA]
V3[V_INT_MDE_DCS_GUEST_USER]
V4[V_INT_RDE_DCS_PROFILE_FIELD]
end

S1 --> Union
S2 --> Union
S4 --> Union
S3 --> Filter
Union --> Filter

Filter --> Dedup
Dedup --> Country
Country --> Hist
Hist --> Calc
Calc --> Select

Select --> V1
Select --> V2
Select --> V3
Select --> V4

style Union fill:#DDA0DD
style Filter fill:#FFD700
style Dedup fill:#FFA07A
style Country fill:#FFA07A
style Hist fill:#FFA07A
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

## MDE and RDE Publication Map

```mermaid
graph LR
subgraph "Integration Layer"
I1[V_INT_MDE_DCS_USER]
I2[V_INT_MDE_DCS_USER_EXTRA]
I3[V_INT_MDE_DCS_GUEST_USER]
I4[V_INT_RDE_DCS_PROFILE_FIELD]
end

subgraph "Presentation Layer"
P1[MDE_DCS_USER]
P2[MDE_DCS_USER_EXTRA]
P3[MDE_DCS_GUEST_USER]
P4[RDE_DCS_PROFILE_FIELD]
end

subgraph "Unit Tests"
U1[orc_unit_test_mde_dcs_user]
U2[orc_unit_test_mde_dcs_user_extra]
U3[orc_unit_test_mde_dcs_guest_user]
U4[orc_unit_test_rde_dcs_profile_field]
end

I1 --> P1 --> U1
I2 --> P2 --> U2
I3 --> P3 --> U3
I4 --> P4 --> U4

style I1 fill:#FFB6C1
style I2 fill:#FFB6C1
style I3 fill:#FFB6C1
style I4 fill:#FFB6C1
style P1 fill:#90EE90
style P2 fill:#90EE90
style P3 fill:#90EE90
style P4 fill:#90EE90
style U1 fill:#87CEEB
style U2 fill:#87CEEB
style U3 fill:#87CEEB
style U4 fill:#87CEEB
```

## Complete Data Warehouse Architecture

```mermaid
graph TB
subgraph "Source Domain"
SRC[DCS Consumer Identity Events<br/>14 Markets]
end

subgraph "Staging Layer"
STG[ev_database_10_staging<br/>STG_DCS]
STG1[T_DCS_*_USERS<br/>14 market tables]
STG2[T_DCS_*_USERSEXTRA<br/>14 market tables]
STG3[T_DCS_CA_GUESTS<br/>1 market table]
STG4[T_DCS_*_PROFILEFIELDS<br/>13 market tables]

STG --> STG1
STG --> STG2
STG --> STG3
STG --> STG4
end

subgraph "Integration Layer"
INT[ev_database_20_integration<br/>ev_data_foundation_schema_20_integration]
INT1[V_INT_MDE_DCS_USER]
INT2[V_INT_MDE_DCS_USER_EXTRA]
INT3[V_INT_MDE_DCS_GUEST_USER]
INT4[V_INT_RDE_DCS_PROFILE_FIELD]
INT5[V_INT_HELPER_COUNTRY_MAPPING]

INT --> INT1
INT --> INT2
INT --> INT3
INT --> INT4
INT --> INT5
end

subgraph "Presentation Layer"
PL[ev_database_30_presentation<br/>PL_IDENTITY]
PL1[MDE_DCS_USER]
PL2[MDE_DCS_USER_EXTRA]
PL3[MDE_DCS_GUEST_USER]
PL4[RDE_DCS_PROFILE_FIELD]

DQ[PL_COMMON_LAYER_DQ<br/>DQ companion tables]

PL --> PL1
PL --> PL2
PL --> PL3
PL --> PL4
end

subgraph "Analytics and Sharing"
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
NewRow[Incoming Staging Rows<br/>per market] --> Union[UNION ALL Markets]
Union --> ParseTS[Parse Timestamps]
ParseTS --> Quality[Validate Timestamp vs __LOAD_TS]
Quality --> Dedup[Deduplicate by Business Key + Timestamp]
Dedup --> Country[Derive COUNTRY_CODE]
Country --> ValidFrom[Set VALID_FROM]
ValidFrom --> Merge[SCD2 Delta Load]
Merge --> Active[ACTIVE_FLAG = TRUE current row]
Merge --> Closed[Prior row closed with VALID_TO]

style NewRow fill:#87CEEB
style Union fill:#DDA0DD
style Merge fill:#FFD700
style Active fill:#90EE90
style Closed fill:#FFB6C1
```

## Market Coverage Matrix

```mermaid
graph LR
subgraph "Markets"
AU[AU]
CA[CA]
DK[DK]
GR[GR]
IL[IL]
IT[IT]
KZ[KZ]
LT[LT]
NL[NL]
NZ[NZ]
PT[PT]
RO[RO]
SE[SE]
UA[UA]
end

subgraph "Staging Tables"
USERS[T_DCS_*_USERS<br/>All 14 markets]
EXTRA[T_DCS_*_USERSEXTRA<br/>All 14 markets]
GUEST[T_DCS_CA_GUESTS<br/>CA only]
PROFILE[T_DCS_*_PROFILEFIELDS<br/>13 markets - no RO]
end

AU --> USERS
AU --> EXTRA
AU --> PROFILE
CA --> USERS
CA --> EXTRA
CA --> GUEST
CA --> PROFILE
DK --> USERS
DK --> EXTRA
DK --> PROFILE
GR --> USERS
GR --> EXTRA
GR --> PROFILE
IL --> USERS
IL --> EXTRA
IL --> PROFILE
IT --> USERS
IT --> EXTRA
IT --> PROFILE
KZ --> USERS
KZ --> EXTRA
KZ --> PROFILE
LT --> USERS
LT --> EXTRA
LT --> PROFILE
NL --> USERS
NL --> EXTRA
NL --> PROFILE
NZ --> USERS
NZ --> EXTRA
NZ --> PROFILE
PT --> USERS
PT --> EXTRA
PT --> PROFILE
RO --> USERS
RO --> EXTRA
SE --> USERS
SE --> EXTRA
SE --> PROFILE
UA --> USERS
UA --> EXTRA
UA --> PROFILE

style USERS fill:#87CEEB
style EXTRA fill:#87CEEB
style GUEST fill:#FFD700
style PROFILE fill:#90EE90
```
