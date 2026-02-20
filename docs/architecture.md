# QMC Agent - Arquitectura del Sistema

## Diagrama de Flujo Principal

```mermaid
flowchart TB
    subgraph INICIO["🚀 INICIO"]
        START([START])
    end

    subgraph PARALLEL["⚡ EJECUCIÓN PARALELA"]
        direction TB
        
        subgraph QMC_FLOW["📊 Flujo QMC"]
            QMC_LOGIN["🔐 QMC Login"]
            QMC_EXTRACT["📥 QMC Extractor"]
            QMC_ANALYST["🤖 QMC Analyst LLM"]
            
            QMC_LOGIN -->|session_cookies| QMC_EXTRACT
            QMC_EXTRACT -->|raw_data| QMC_ANALYST
        end
        
        subgraph NP_FLOW["📈 Flujo NPrinting"]
            NP_LOGIN["🔐 NPrinting Login"]
            NP_EXTRACT["📥 NPrinting Extractor"]
            NP_ANALYST["🤖 NPrinting Analyst LLM"]
            
            NP_LOGIN -->|nprinting_cookies| NP_EXTRACT
            NP_EXTRACT -->|nprinting_data| NP_ANALYST
        end
    end

    subgraph SYNC["🔄 SINCRONIZACIÓN"]
        SYNC_NODE["Sync Node"]
    end

    subgraph ANALYSIS["🧠 ANÁLISIS COMBINADO"]
        COMBINED["Combined Analyst"]
    end

    subgraph OUTPUT["📋 REPORTE"]
        REPORTER["Reporter Node"]
        REPORT_IMG["📊 Imagen PNG"]
    end

    subgraph FIN["🏁 FIN"]
        END_NODE([END])
    end

    subgraph ERROR_FLOW["❌ MANEJO DE ERRORES"]
        ERROR["Error Node"]
    end

    START --> QMC_LOGIN
    START --> NP_LOGIN
    
    QMC_ANALYST --> SYNC_NODE
    NP_ANALYST --> SYNC_NODE
    
    SYNC_NODE --> COMBINED
    COMBINED --> REPORTER
    REPORTER --> REPORT_IMG
    REPORTER --> END_NODE
    
    QMC_LOGIN -.->|retry/error| ERROR
    NP_LOGIN -.->|retry/error| ERROR
    QMC_EXTRACT -.->|error| ERROR
    NP_EXTRACT -.->|error| ERROR
    ERROR --> END_NODE
```

## Diagrama de Componentes

```mermaid
flowchart LR
    subgraph SCRIPTS["📁 Scripts Playwright"]
        QMC_LOGIN_SCRIPT["qmc/login_script.py"]
        QMC_EXTRACT_SCRIPT["qmc/extract_script.py"]
        NP_LOGIN_SCRIPT["nprinting/login_script.py"]
        NP_EXTRACT_SCRIPT["nprinting/extract_script.py"]
    end

    subgraph NODES["📁 Nodes LangGraph"]
        QMC_LOGIN_NODE["qmc/login_node_sync.py"]
        QMC_EXTRACTOR_NODE["qmc/extractor.py"]
        QMC_ANALYST_NODE["qmc/analyst_llm.py"]
        NP_LOGIN_NODE["nprinting/login_node.py"]
        NP_EXTRACTOR_NODE["nprinting/extractor.py"]
        NP_ANALYST_NODE["nprinting/analyst.py"]
        COMBINED_NODE["combined_analyst.py"]
        REPORTER_NODE["reporter.py"]
    end

    subgraph CORE["📁 Core"]
        GRAPH["graph.py"]
        STATE["state.py"]
        CONFIG["config.py"]
        RUNNER["playwright_runner.py"]
    end

    subgraph EXTERNAL["🌐 Servicios Externos"]
        QMC_WEB["QMC Web Console"]
        NP_WEB["NPrinting Web"]
        GROQ["Groq LLM API"]
    end

    GRAPH --> STATE
    GRAPH --> NODES
    NODES --> RUNNER
    RUNNER --> SCRIPTS
    SCRIPTS --> QMC_WEB
    SCRIPTS --> NP_WEB
    QMC_ANALYST_NODE --> GROQ
    NP_ANALYST_NODE --> GROQ
```

## Diagrama de Secuencia

```mermaid
sequenceDiagram
    autonumber
    participant Main as main_agent.py
    participant Graph as LangGraph
    participant QMC as QMC Flow
    participant NP as NPrinting Flow
    participant LLM as Groq LLM
    participant Reporter

    Main->>Graph: ainvoke(initial_state)
    
    par Ejecución Paralela
        Graph->>QMC: qmc_login()
        QMC->>QMC: Playwright Login
        QMC-->>Graph: session_cookies
        Graph->>QMC: qmc_extractor()
        QMC->>QMC: Extraer tareas
        QMC-->>Graph: raw_data (tasks)
        Graph->>LLM: Analizar QMC tasks
        LLM-->>Graph: process_reports
    and
        Graph->>NP: nprinting_login()
        NP->>NP: Playwright Login
        NP-->>Graph: nprinting_cookies
        Graph->>NP: nprinting_extractor()
        NP->>NP: Filtrar Today + Paginar
        NP-->>Graph: nprinting_data
        Graph->>LLM: Analizar NPrinting tasks
        LLM-->>Graph: nprinting_reports
    end

    Graph->>Graph: sync_node()
    Graph->>Graph: combined_analyst()
    Graph->>Reporter: reporter_node()
    Reporter->>Reporter: Generar PNG
    Reporter-->>Main: final_state
```

## Diagrama de Estado

```mermaid
stateDiagram-v2
    [*] --> QMC_Login
    [*] --> NPrinting_Login

    state "QMC Flow" as qmc {
        QMC_Login --> QMC_Extractor: success
        QMC_Login --> QMC_Login: retry
        QMC_Extractor --> QMC_Analyst: data extracted
    }

    state "NPrinting Flow" as np {
        NPrinting_Login --> NPrinting_Extractor: success
        NPrinting_Login --> NPrinting_Login: retry
        NPrinting_Extractor --> NPrinting_Analyst: data extracted
    }

    QMC_Analyst --> Sync
    NPrinting_Analyst --> Sync

    Sync --> Combined_Analyst
    Combined_Analyst --> Reporter
    Reporter --> [*]

    QMC_Login --> Error: max retries
    NPrinting_Login --> Error: max retries
    QMC_Extractor --> Error: extraction failed
    NPrinting_Extractor --> Error: extraction failed
    Error --> [*]
```

## Estructura de Datos (State)

```mermaid
classDiagram
    class QMCState {
        +str current_step
        +str target_url
        +str nprinting_url
        +dict session_cookies
        +dict nprinting_cookies
        +str raw_data
        +list nprinting_data
        +dict process_reports
        +dict nprinting_reports
        +str overall_status
        +list screenshots
        +list logs
        +str qmc_error
        +str nprinting_error
        +int retry_count
        +int max_retries
    }

    class ProcessReport {
        +str status
        +str summary
        +list failed_tasks
        +str prefix
        +int task_count
    }

    class NPrintingReport {
        +str status
        +str summary
        +list failed_tasks
        +list running_tasks
        +int total_tasks
        +int completed_tasks
    }

    QMCState "1" --> "*" ProcessReport : process_reports
    QMCState "1" --> "*" NPrintingReport : nprinting_reports
```

## Procesos Monitoreados

```mermaid
mindmap
    root((QMC Agent))
        QMC Console
            FE_HITOS_DIARIO
            FE_COBRANZAS_DIARIA
            FE_PASIVOS
            FE_PRODUCCION
            FE_CALIDADCARTERA_DIARIO
        NPrinting
            Hitos
                prefix: h.
            Calidad de Cartera
                prefix: q1.
            Reporte de Producción
                prefix: k.
            Cobranzas
                prefix: x.
```
