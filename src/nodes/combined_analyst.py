"""
Combined Analyst Node (V2 Optimized)
Combines QMC and NPrinting analysis reports into a unified view.

Optimizations:
- Logging instead of print/debug blocks
- Handles "Error" and "Mixed" statuses properly
- Generates executive summary with proper edge cases
"""

import logging
from typing import Dict
import json

from src.state import QMCState

logger = logging.getLogger("Combined.Analyst")


def determine_overall_status(qmc_reports: Dict, nprinting_reports: Dict) -> str:
    """
    Determine overall status based on both QMC and NPrinting reports.
    Hierarchy: Failed > Error > Running > Pending > Success
    """
    all_statuses = []
    
    for report in list(qmc_reports.values()) + list(nprinting_reports.values()):
        status = report.get("status", "").lower()
        if status and status not in ["no data", "no run"]:
            all_statuses.append(status)
    
    if not all_statuses:
        return "No Data"
    
    # Apply hierarchy (including Error)
    if any(s == "failed" for s in all_statuses):
        return "Failed"
    if any(s == "error" for s in all_statuses):
        return "Failed"  # Map Error → Failed for reporting
    if any(s == "running" for s in all_statuses):
        return "Running"
    if any(s == "pending" for s in all_statuses):
        return "Pending"
    if all(s == "success" for s in all_statuses):
        return "Success"
    
    return "Pending"  # Fallback to Pending instead of "Mixed"


def count_by_status(reports: Dict) -> Dict[str, int]:
    """Count processes by status."""
    counts = {"Success": 0, "Running": 0, "Failed": 0, "Pending": 0, "No Run": 0, "Error": 0}
    for report in reports.values():
        status = report.get("status", "No Run")
        if status in counts:
            counts[status] += 1
        else:
            counts["No Run"] += 1
    return counts


async def generate_summary_llm(overall_status: str, qmc: Dict, nprinting: Dict) -> str:
    """Generate executive summary using LLM for natural language, with Python fallback."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_groq import ChatGroq
        from src.config import Config
        
        # Build context
        qmc_items = []
        for p, r in qmc.items():
            qmc_items.append(f"  - {p}: {r.get('status', 'N/A')} — {r.get('summary', '')[:60]}")
        
        nprinting_items = []
        for p, r in nprinting.items():
            nprinting_items.append(f"  - {p}: {r.get('status', 'N/A')} — {r.get('summary', '')[:60]}")
        
        context = f"""Overall Status: {overall_status}

QMC Processes ({len(qmc)}):
{chr(10).join(qmc_items) if qmc_items else '  (none)'}

NPrinting Processes ({len(nprinting)}):
{chr(10).join(nprinting_items) if nprinting_items else '  (none)'}"""
        
        prompt = ChatPromptTemplate.from_template(
            """Eres un redactor de reportes ejecutivos. Escribe un resumen ejecutivo de 1-2 oraciones EN ESPAÑOL
para los siguientes resultados de monitoreo QMC + NPrinting. Sé directo y accionable.
Si hay fallos, menciona los nombres de los procesos. Si todo está bien, dilo brevemente.

{context}

Responde SOLO con el texto del resumen, sin JSON, sin formato."""
        )
        
        llm = ChatGroq(temperature=0.3, model_name=Config.GROQ_MODEL, api_key=Config.GROQ_API_KEY)
        chain = prompt | llm
        response = chain.invoke({"context": context})
        return response.content.strip()
        
    except Exception as e:
        logger.warning(f"LLM summary failed, using fallback: {e}")
        return _generate_summary_fallback(overall_status, qmc, nprinting)


def _generate_summary_fallback(overall_status: str, qmc: Dict, nprinting: Dict) -> str:
    """Deterministic fallback summary (no LLM needed)."""
    total_qmc = len(qmc)
    total_nprinting = len(nprinting)
    
    qmc_failed = [p for p, r in qmc.items() if r.get("status", "").lower() in ["failed", "error"]]
    nprinting_failed = [p for p, r in nprinting.items() if r.get("status", "").lower() in ["failed", "error"]]
    
    if overall_status == "Success":
        return f"All {total_qmc + total_nprinting} processes completed successfully."
    elif overall_status == "Failed":
        failed_list = qmc_failed + nprinting_failed
        return f"CRITICAL: {len(failed_list)} process(es) failed: {', '.join(failed_list[:3])}{'...' if len(failed_list) > 3 else ''}"
    elif overall_status == "Running":
        return f"Processes are still running. QMC: {total_qmc}, NPrinting: {total_nprinting}."
    else:
        return f"Status: {overall_status}. QMC: {total_qmc} processes, NPrinting: {total_nprinting} processes."


async def combined_analyst_node(state: QMCState) -> dict:
    """
    Combined Analyst Node:
    - Receives QMC analysis and NPrinting analysis.
    - Correlates and generates unified executive summary.
    """
    logger.info("Creating unified analysis...")
    
    qmc_reports = state.get("process_reports") or {}
    nprinting_reports = state.get("nprinting_reports") or {}
    
    # Structured logging
    logger.debug(f"QMC Reports received: {len(qmc_reports)}")
    for process, report in qmc_reports.items():
        logger.debug(f"  QMC | {process}: [{report.get('status', 'N/A')}]")
    
    logger.debug(f"NPrinting Reports received: {len(nprinting_reports)}")
    for process, report in nprinting_reports.items():
        logger.debug(f"  NPrinting | {process}: [{report.get('status', 'N/A')}] (tasks: {report.get('task_count', 'N/A')})")
    
    # Handle empty cases — no data means tasks haven't run yet → Pending
    if not qmc_reports and not nprinting_reports:
        logger.warning("No data from either source — marking as Pending")
        return {
            "combined_report": {
                "overall_status": "Pending",
                "summary": "Tasks have not been executed yet. All processes are pending."
            },
            "logs": ["Combined: No data from either source — Pending"]
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
        "summary": await generate_summary_llm(overall_status, qmc_reports, nprinting_reports)
    }
    
    logger.info(f"Overall Status: {overall_status} | QMC({len(qmc_reports)}) + NPrinting({len(nprinting_reports)})")
    
    return {
        "combined_report": combined_report,
        "logs": [f"Combined: QMC({len(qmc_reports)}) + NPrinting({len(nprinting_reports)}) = {overall_status}"]
    }
