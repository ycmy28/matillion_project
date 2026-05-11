# DCS Phase 1 (Users) Pipeline Architecture Diagrams

## Master Pipeline Flow

```mermaid
graph TB
    Start([Start]) --> QueryTag[Set Query Tag<br>job_name-run_history_id]
    QueryTag --> Ingestion[Ingestion Dispatch<br>DISP Ingestion - CONS 1]
    Ingestion --> SetVars[Set Variables<br>- jv_source_name = dcs<br>- jv_output_tenant_name = edp_consumer<br>- jv_process_table]
    SetVars --> DCSHarm[DCS Harmonization<br>MDE + RDE Objects]
    DCSHarm --> LoadHistory[Task History Load]
    LoadHistory --> End([End])

    style Start fill:#90EE90
    style End fill:#90EE90
    style Ingestion fill:#87CEEB
    style DCSHarm fill:#FFB6C1
    style LoadHistory fill:#FFD700