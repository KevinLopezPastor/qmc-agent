"""
QMC Agent - Reporter Node
Orchestrates the generation of unified visual reports.
"""

from src.playwright_runner import run_playwright_script
from src.state import QMCState
import os
from datetime import datetime


def reporter_node(state: QMCState) -> dict:
    """
    Reporter Node:
    - Takes analyzed reports from QMC, NPrinting, and Combined analysis.
    - Generates unified visual PNG report.
    """
    print("   [Reporter] Generating Unified Visual Report...")
    
    qmc_reports = state.get("process_reports") or {}
    nprinting_reports = state.get("nprinting_reports") or {}
    combined_report = state.get("combined_report") or {}
    
    if not qmc_reports and not nprinting_reports:
        return {
            "current_step": "done",
            "logs": ["No reports available to visualize."]
        }
    
    # Generate filename with timestamp
    now = datetime.now()
    date_str = now.strftime("%d_%m_%Y")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Create directory: root/reportes/DD_MM_YYYY/
    base_dir = os.getcwd()
    report_dir = os.path.join(base_dir, "reportes", date_str)
    os.makedirs(report_dir, exist_ok=True)
    
    output_filename = f"unified_report_{timestamp}.png"
    output_path = os.path.join(report_dir, output_filename)
    
    args = {
        "qmc_reports": qmc_reports,
        "nprinting_reports": nprinting_reports,
        "combined_report": combined_report,
        "output_path": output_path
    }
    
    # Run script
    result = run_playwright_script("report_script.py", args)
    
    if result.get("success"):
        print(f"   [Reporter] Unified report saved to: {output_path}")
        return {
            "current_step": "done",
            "report_image_path": output_path,
            "logs": [f"Unified report generated: {output_filename}"]
        }
    else:
        err = result.get("error", "Unknown Error")
        print(f"   [Reporter] Failed: {err}")
        return {
            "current_step": "error",
            "error_message": f"Report generation failed: {err}",
            "logs": [f"Report Gen Error: {err}"]
        }


async def reporter_node_async(state: QMCState) -> dict:
    return reporter_node(state)
