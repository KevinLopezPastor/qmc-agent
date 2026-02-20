"""
Combined Analyst Node
Combines QMC and NPrinting analysis reports into a unified view.
"""

from typing import Dict
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from src.config import Config
from src.state import QMCState


def determine_overall_status(qmc_reports: Dict, nprinting_reports: Dict) -> str:
    """
    Determine overall status based on both QMC and NPrinting reports.
    Uses the same hierarchy: Failed > Running > Pending > Success
    """
    all_statuses = []
    
    # Collect all statuses from QMC
    for process, report in qmc_reports.items():
        status = report.get("status", "").lower()
        if status and status not in ["no data", "no run", "error"]:
            all_statuses.append(status)
    
    # Collect all statuses from NPrinting
    for process, report in nprinting_reports.items():
        status = report.get("status", "").lower()
        if status and status not in ["no data", "no run", "error"]:
            all_statuses.append(status)
    
    if not all_statuses:
        return "No Data"
    
    # Apply hierarchy
    if any(s == "failed" for s in all_statuses):
        return "Failed"
    if any(s == "running" for s in all_statuses):
        return "Running"
    if any(s == "pending" for s in all_statuses):
        return "Pending"
    if all(s == "success" for s in all_statuses):
        return "Success"
    
    return "Mixed"


def count_by_status(reports: Dict) -> Dict[str, int]:
    """Count processes by status."""
    counts = {"Success": 0, "Running": 0, "Failed": 0, "Pending": 0, "No Run": 0}
    for process, report in reports.items():
        status = report.get("status", "No Run")
        if status in counts:
            counts[status] += 1
        else:
            counts["No Run"] += 1
    return counts


async def combined_analyst_node(state: QMCState) -> dict:
    """
    Combined Analyst Node:
    - Receives QMC analysis (process_reports) and NPrinting analysis (nprinting_reports).
    - Correlates and generates unified executive summary.
    """
    print("   [Combined Analyst] Creating unified analysis...")
    
    qmc_reports = state.get("process_reports") or {}
    nprinting_reports = state.get("nprinting_reports") or {}
    
    # ==================== DEBUG LOGS ====================
    print("\n" + "="*60)
    print("   📥 DATOS RECIBIDOS PARA ANÁLISIS COMBINADO")
    print("="*60)
    
    print("\n   📊 QMC REPORTS:")
    if qmc_reports:
        for process, report in qmc_reports.items():
            status = report.get("status", "N/A")
            summary = report.get("summary", "N/A")[:80]
            print(f"      - {process}: [{status}] {summary}")
    else:
        print("      (vacío - sin datos)")
    
    print("\n   📈 NPRINTING REPORTS:")
    if nprinting_reports:
        for process, report in nprinting_reports.items():
            status = report.get("status", "N/A")
            summary = report.get("summary", "N/A")[:80]
            task_count = report.get("task_count", "N/A")
            print(f"      - {process}: [{status}] (tasks: {task_count}) {summary}")
    else:
        print("      (vacío - sin datos)")
    
    print("="*60 + "\n")
    # ==================== END DEBUG ====================
    
    # Handle empty cases
    if not qmc_reports and not nprinting_reports:
        return {
            "combined_report": {
                "overall_status": "No Data",
                "summary": "No data available from either QMC or NPrinting."
            },
            "logs": ["Combined: No data from either source"]
        }
    
    # Count statuses
    qmc_counts = count_by_status(qmc_reports)
    nprinting_counts = count_by_status(nprinting_reports)
    
    # Determine overall status
    overall_status = determine_overall_status(qmc_reports, nprinting_reports)
    
    # Build combined report
    combined_report = {
        "overall_status": overall_status,
        "qmc": {
            "total_processes": len(qmc_reports),
            "status_counts": qmc_counts,
            "processes": qmc_reports
        },
        "nprinting": {
            "total_processes": len(nprinting_reports),
            "status_counts": nprinting_counts,
            "processes": nprinting_reports
        },
        "summary": generate_summary(overall_status, qmc_reports, nprinting_reports)
    }
    
    print(f"   [Combined Analyst] Overall Status: {overall_status}")
    
    return {
        "combined_report": combined_report,
        "logs": [f"Combined: QMC({len(qmc_reports)}) + NPrinting({len(nprinting_reports)}) = {overall_status}"]
    }


def generate_summary(overall_status: str, qmc: Dict, nprinting: Dict) -> str:
    """Generate a brief executive summary."""
    total_qmc = len(qmc)
    total_nprinting = len(nprinting)
    
    qmc_failed = [p for p, r in qmc.items() if r.get("status", "").lower() == "failed"]
    nprinting_failed = [p for p, r in nprinting.items() if r.get("status", "").lower() == "failed"]
    
    if overall_status == "Success":
        return f"All {total_qmc + total_nprinting} processes completed successfully."
    elif overall_status == "Failed":
        failed_list = qmc_failed + nprinting_failed
        return f"CRITICAL: {len(failed_list)} process(es) failed: {', '.join(failed_list[:3])}{'...' if len(failed_list) > 3 else ''}"
    elif overall_status == "Running":
        return f"Processes are still running. QMC: {total_qmc}, NPrinting: {total_nprinting}."
    else:
        return f"Status: {overall_status}. QMC: {total_qmc} processes, NPrinting: {total_nprinting} processes."


# For testing
if __name__ == "__main__":
    import asyncio
    from src.state import create_initial_state
    
    state = create_initial_state()
    state["process_reports"] = {
        "Hitos": {"status": "Success", "summary": "All tasks completed"},
        "Cobranzas": {"status": "Failed", "summary": "1 task failed"}
    }
    state["nprinting_reports"] = {
        "Hitos": {"status": "Success", "summary": "All reports generated"},
        "Calidad de Cartera": {"status": "Running", "summary": "2 reports in progress"}
    }
    
    result = asyncio.run(combined_analyst_node(state))
    print("Result:", json.dumps(result, indent=2))
