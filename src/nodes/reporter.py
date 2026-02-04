"""
QMC Agent - Reporter Node
Orchestrates the generation of visual reports.
"""

from src.playwright_runner import run_playwright_script
from src.state import QMCState
import os
from datetime import datetime

def reporter_node(state: QMCState) -> dict:
    """
    Reporter Node:
    - Takes analyzed reports from state.
    - Generates visual PNG using report_script.py.
    """
    print("   [Reporter] Generating Visual Report...")
    
    process_reports = state.get("process_reports", {})
    if not process_reports:
        return {
            "logs": ["No reports available to visualize."]
        }
        
    # Generate filename with timestamp
    now = datetime.now()
    date_str = now.strftime("%d_%m_%Y")
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    
    # Create directory: root/reportes/29_01_2026/
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__))) # Adjust relative to src/nodes/
    # Better: just use CWD which is project root usually
    base_dir = os.getcwd() 
    
    report_dir = os.path.join(base_dir, "reportes", date_str)
    os.makedirs(report_dir, exist_ok=True)
    
    output_filename = f"qmc_report_{timestamp}.png"
    output_path = os.path.join(report_dir, output_filename)
    
    args = {
        "reports": process_reports,
        "output_path": output_path
    }
    
    # Run script
    result = run_playwright_script("report_script.py", args)
    
    if result.get("success"):
        print(f"   [Reporter] Report saved to: {output_path}")
        return {
            "current_step": "done",
            "report_image_path": output_path,
            "logs": [f"Visual report generated: {output_filename}"]
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
