"""
QMC Agent - Subprocess-based Playwright Runner
Runs Playwright in a completely separate process to avoid asyncio conflicts in Jupyter.
"""

import json
import subprocess
import sys
import os
from pathlib import Path


def run_playwright_script(script_name: str, args: dict) -> dict:
    """
    Run a Playwright script in a separate Python process.
    This completely isolates Playwright from the Jupyter asyncio event loop.
    
    Args:
        script_name: Name of the script to run (without path)
        args: Dictionary of arguments to pass to the script
        
    Returns:
        Dictionary with results from the script
    """
    # Get the path to the scripts directory
    scripts_dir = Path(__file__).parent / "scripts"
    script_path = scripts_dir / script_name
    
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Script not found: {script_path}"
        }
    
    # Serialize arguments to JSON
    args_json = json.dumps(args)
    
    # Run the script in a separate process
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), args_json],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for NPrinting pagination
            cwd=str(Path(__file__).parent.parent)  # Run from project root
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"Process exited with code {result.returncode}",
                "stdout": result.stdout
            }
        
        # Parse JSON output from the script
        try:
            output = json.loads(result.stdout)
            return output
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Failed to parse script output as JSON",
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Script timed out after 120 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
