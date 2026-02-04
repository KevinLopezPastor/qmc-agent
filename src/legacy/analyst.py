"""
QMC Agent - Analyst Module
Analyzes process status from extracted task data.
"""

import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from src.state import QMCState


# ============ Pydantic Schemas ============

class QMCTask(BaseModel):
    """Schema for a single QMC task."""
    Name: str = Field(description="Task name")
    Status: str = Field(description="Execution status")
    Last_execution: Optional[str] = Field(default=None)
    Next_execution: Optional[str] = Field(default=None)
    Tags: List[str] = Field(default=[])


class ProcessStatusSummary(BaseModel):
    """Summary of task statuses."""
    total_tareas: int
    completadas: int  # Success
    saltadas: int  # Skipped (no afecta estado final)
    en_ejecucion: int  # Running
    pendientes: int  # Started, Queued, Waiting
    fallidas: int  # Failed, Aborted


class ProcessStatus(BaseModel):
    """Overall process status report."""
    proceso: str
    estado: str  # Completado, En proceso, Fallido, Pendiente
    fecha: str
    hora_observacion: str
    resumen: ProcessStatusSummary
    tarea_inicio: Optional[str]
    tareas: List[dict]


# ============ Analysis Functions ============

def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parse datetime string to datetime object."""
    if not dt_str:
        return None
    
    # Handle various formats
    formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None


def order_tasks_by_execution(tasks: List[dict]) -> List[dict]:
    """Order tasks by Last_execution (earliest first)."""
    def get_exec_time(task):
        dt = parse_datetime(task.get("Last_execution") or task.get("Last execution"))
        return dt if dt else datetime.max
    
    return sorted(tasks, key=get_exec_time)


def find_start_task(tasks: List[dict]) -> Optional[str]:
    """Find the task that initiates the process (contains 'INICIO')."""
    for task in tasks:
        name = task.get("Name", "")
        if "INICIO" in name.upper():
            return name
    return None


def classify_status(status: str) -> str:
    """Classify status into categories."""
    status_upper = status.upper() if status else ""
    
    if status_upper in ["SUCCESS", "SUCCEEDED", "COMPLETED"]:
        return "completadas"
    elif status_upper in ["SKIPPED"]:
        return "saltadas"
    elif status_upper in ["RUNNING", "EXECUTING"]:
        return "en_ejecucion"
    elif status_upper in ["STARTED", "QUEUED", "WAITING", "PENDING"]:
        return "pendientes"
    elif status_upper in ["FAILED", "ERROR", "ABORTED", "CANCELLED"]:
        return "fallidas"
    else:
        return "otro"


def count_statuses(tasks: List[dict]) -> ProcessStatusSummary:
    """Count tasks by status category."""
    counts = {"completadas": 0, "saltadas": 0, "en_ejecucion": 0, "pendientes": 0, "fallidas": 0}
    
    for task in tasks:
        status = task.get("Status", "")
        category = classify_status(status)
        if category in counts:
            counts[category] += 1
    
    return ProcessStatusSummary(
        total_tareas=len(tasks),
        completadas=counts["completadas"],
        saltadas=counts["saltadas"],
        en_ejecucion=counts["en_ejecucion"],
        pendientes=counts["pendientes"],
        fallidas=counts["fallidas"]
    )


def determine_overall_status(summary: ProcessStatusSummary) -> str:
    """Determine overall process status. Skipped tasks don't affect the result."""
    # Tareas activas = total - saltadas
    tareas_activas = summary.total_tareas - summary.saltadas
    
    if summary.fallidas > 0:
        return "Fallido"
    elif tareas_activas == summary.completadas:
        return "Completado"
    elif summary.en_ejecucion > 0 or (summary.completadas > 0 and summary.pendientes > 0):
        return "En proceso"
    elif summary.pendientes == tareas_activas:
        return "Pendiente"
    else:
        return "En proceso"


def analyze_process_status(tasks: List[dict], process_name: str = "FE_HITOS_DIARIO") -> ProcessStatus:
    """
    Analyze the status of a process based on its tasks.
    
    Args:
        tasks: List of task dictionaries
        process_name: Name of the process being analyzed
        
    Returns:
        ProcessStatus object with analysis results
    """
    now = datetime.now()
    
    # Order tasks by execution time
    ordered_tasks = order_tasks_by_execution(tasks)
    
    # Find start task
    start_task = find_start_task(ordered_tasks)
    
    # Count statuses
    summary = count_statuses(ordered_tasks)
    
    # Determine overall status
    overall_status = determine_overall_status(summary)
    
    return ProcessStatus(
        proceso=process_name,
        estado=overall_status,
        fecha=now.strftime("%Y-%m-%d"),
        hora_observacion=now.strftime("%H:%M:%S"),
        resumen=summary,
        tarea_inicio=start_task,
        tareas=ordered_tasks
    )


# ============ Analyst Node ============

def analyst_node_sync(state: QMCState) -> dict:
    """
    Analyst node: Analyzes process status from extracted data.
    
    Args:
        state: Current workflow state with raw_table_data
        
    Returns:
        Updated state dict with process_status
    """
    log_entry = f"[{datetime.now().isoformat()}] ANALYST: Analyzing process status"
    
    raw_data = state.get("raw_table_data", "")
    
    if not raw_data:
        log_entry += "\n  No data to analyze"
        return {
            "current_step": "error",
            "error_message": "No table data available for analysis",
            "logs": [log_entry]
        }
    
    try:
        # Parse raw data
        if isinstance(raw_data, str):
            data = json.loads(raw_data)
        else:
            data = raw_data
        
        tasks = data.get("rows", []) if isinstance(data, dict) else data
        log_entry += f"\n  Processing {len(tasks)} tasks"
        
        # Debug: Show sample task and unique status values
        if tasks:
            sample = tasks[0]
            log_entry += f"\n  Sample task keys: {list(sample.keys())}"
            statuses = set(t.get("Status", t.get("status", "UNKNOWN")) for t in tasks)
            log_entry += f"\n  Unique statuses found: {statuses}"
        
        # Detect process name from tags
        process_name = "FE_HITOS_DIARIO"  # Default
        for task in tasks:
            tags = task.get("Tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            for tag in tags:
                if "FE_HITOS" in tag.upper():
                    process_name = tag
                    break
        
        # Analyze process status
        status = analyze_process_status(tasks, process_name)
        r = status.resumen
        log_entry += f"\n  Process: {status.proceso}"
        log_entry += f"\n  Counts: {r.completadas} completadas, {r.saltadas} saltadas, {r.en_ejecucion} ejecutando, {r.pendientes} pendientes, {r.fallidas} fallidas"
        log_entry += f"\n  Estado final: {status.estado}"
        
        return {
            "current_step": "done",
            "process_status": status.model_dump(),
            "structured_data": status.tareas,
            "error_message": None,
            "logs": [log_entry]
        }
        
    except json.JSONDecodeError as e:
        log_entry += f"\n  JSON error: {str(e)}"
        return {
            "current_step": "error",
            "error_message": f"Failed to parse data: {str(e)}",
            "logs": [log_entry]
        }
        
    except Exception as e:
        log_entry += f"\n  Error: {str(e)}"
        return {
            "current_step": "error",
            "error_message": f"Analysis failed: {str(e)}",
            "logs": [log_entry]
        }


# Async version for compatibility
async def analyst_node(state: QMCState) -> dict:
    """Async wrapper for analyst_node_sync."""
    return analyst_node_sync(state)


def format_output(process_status: dict) -> str:
    """Format process status as pretty JSON."""
    return json.dumps(process_status, indent=2, ensure_ascii=False)


# For testing
if __name__ == "__main__":
    test_tasks = [
        {"Name": "INICIO_MALLA_NZ_HITOS_BT", "Status": "Success", "Last_execution": "2026-01-27T06:15:00", "Tags": ["FE_HITOS_DIARIO"]},
        {"Name": "CARGA_FACT_HITOS_BT_EXTRACCION", "Status": "Success", "Last_execution": "2026-01-27T06:33:00", "Tags": ["FE_HITOS_DIARIO"]},
        {"Name": "CARGA_FACT_HITOS_BT_TRANSFORM", "Status": "Running", "Last_execution": "2026-01-27T06:49:00", "Tags": ["FE_HITOS_DIARIO"]},
        {"Name": "PUBLISH_NP_EFICIENCIA", "Status": "Started", "Last_execution": None, "Tags": ["FE_HITOS_DIARIO"]},
    ]
    
    result = analyze_process_status(test_tasks)
    print(format_output(result.model_dump()))
