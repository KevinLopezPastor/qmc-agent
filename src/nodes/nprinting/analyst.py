"""
NPrinting Analyst Node
Analyzes NPrinting tasks using LLM, filtering by prefix patterns.
"""

from typing import List, Dict
import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from src.config import Config
from src.state import QMCState


def filter_tasks_by_prefix(tasks: List[Dict], prefix: str) -> List[Dict]:
    """Filter tasks whose 'Task name' starts with the given prefix."""
    return [
        t for t in tasks 
        if t.get("Task name", "").startswith(prefix)
    ]


def analyze_nprinting_group(process_name: str, tasks: List[Dict], llm) -> Dict:
    """
    Analyzes a single group of NPrinting tasks using LLM.
    """
    if not tasks:
        return {
            "status": "No Data",
            "summary": "No tasks found for this process today."
        }
    
    # Prepare simplified task list for LLM
    simplified_tasks = [
        {
            "Task name": t.get("Task name"),
            "Status": t.get("Status"),
            "Progress": t.get("Progress"),
            "Created": t.get("Created")
        }
        for t in tasks
    ]
    
    prompt = ChatPromptTemplate.from_template(
        """
        Act as an NPrinting Report Analyst. Analyze the following tasks for '{process_name}'.
        
        Context:
        - These are NPrinting report generation tasks.
        - Status can be: Completed, Running, Failed, Queued, Aborted, etc.
        - Progress is a percentage (0-100%).
        
        STRICT Status Hierarchy (Top priority wins):
        1. "Failed": If ANY task has 'Failed', 'Error', 'Aborted' status.
        2. "Running": If NO failures, but ANY task is 'Running' or progress < 100%.
        3. "Pending": If NO failures and NO running, but tasks are 'Queued' or 'Waiting'.
        4. "Success": If and ONLY IF ALL tasks are 'Completed' with 100% progress.
        
        Tasks:
        {tasks_json}
        
        Output format (JSON only):
        {{
            "status": "Success" | "Running" | "Failed" | "Pending",
            "summary": "Brief explanation (max 1 sentence)",
            "failed_tasks": ["List of failed task names"],
            "running_tasks": ["List of running task names"],
            "total_tasks": <number>,
            "completed_tasks": <number>
        }}
        """
    )
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "process_name": process_name,
            "tasks_json": json.dumps(simplified_tasks, indent=2)
        })
        
        # Parse JSON from content
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        
        result = json.loads(content.strip())
        
        # Ensure result is a dict, not a list
        if isinstance(result, list):
            # If it's a list, wrap it or take first element
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                result = {
                    "status": "Error",
                    "summary": "LLM returned unexpected format (list instead of dict)"
                }
        
        return result
        
    except Exception as e:
        return {
            "status": "Error",
            "summary": f"LLM Analysis failed: {str(e)}"
        }


async def nprinting_analyst_node(state: QMCState) -> dict:
    """
    NPrinting Analyst Node:
    - Partitions data by prefix patterns (h.*, q1.*, k.*, x.*).
    - Calls LLM for each monitored process.
    - Aggregates results.
    """
    print("   [NPrinting Analyst] Starting LLM Analysis...")
    
    # Initialize LLM
    llm = ChatGroq(
        temperature=0,
        model_name=Config.GROQ_MODEL,
        api_key=Config.GROQ_API_KEY
    )
    
    all_tasks = state.get("nprinting_data") or []
    if not all_tasks:
        return {
            "nprinting_reports": {},
            "logs": ["NPrinting: No data to analyze"]
        }
    
    # Partition by prefix patterns
    monitored_prefixes = Config.NPRINTING_MONITORED
    final_report = {}
    
    for prefix, alias in monitored_prefixes.items():
        # Filter tasks by prefix
        prefix_tasks = filter_tasks_by_prefix(all_tasks, prefix)
        print(f"     > Analyzing {alias} ({len(prefix_tasks)} tasks with prefix '{prefix}')...")
        
        if not prefix_tasks:
            final_report[alias] = {
                "status": "No Run",
                "summary": "No tasks found for today.",
                "prefix": prefix
            }
            continue
        
        analysis = analyze_nprinting_group(alias, prefix_tasks, llm)
        analysis["prefix"] = prefix
        analysis["task_count"] = len(prefix_tasks)
        final_report[alias] = analysis
        print(f"       Result: {analysis.get('status')} - {analysis.get('summary')}")
    
    return {
        "nprinting_reports": final_report,
        "logs": [f"NPrinting: Analyzed {len(monitored_prefixes)} process groups"]
    }


# For testing
if __name__ == "__main__":
    import asyncio
    from src.state import create_initial_state
    
    state = create_initial_state()
    state["nprinting_data"] = [
        {"Task name": "h. Tablero Eficiencia", "Status": "Completed", "Progress": "100%", "Created": "2026-02-04"},
        {"Task name": "h. Reporte Gerencial", "Status": "Running", "Progress": "50%", "Created": "2026-02-04"},
        {"Task name": "x.Cobranza Diaria", "Status": "Completed", "Progress": "100%", "Created": "2026-02-04"},
    ]
    
    result = asyncio.run(nprinting_analyst_node(state))
    print("Result:", json.dumps(result, indent=2))
