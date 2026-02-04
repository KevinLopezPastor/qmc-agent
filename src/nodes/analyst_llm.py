"""
QMC Agent - Analyst LLM Node
Uses Groq (LLaMA 3) to analyze process groups dynamically.
"""

from typing import List, Dict
import json
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from src.config import Config
from src.state import QMCState

def analyze_group(process_name: str, tasks: List[Dict], llm) -> Dict:
    """
    Analyzes a single group of tasks using LLM.
    """
    if not tasks:
        return {
            "status": "No Data",
            "summary": "No tasks found for this process today."
        }

    # Prepare simplified task list for LLM to save tokens
    # CRITICAL: Filter out Disabled tasks as they do not affect process status.
    simplified_tasks = []
    for t in tasks:
        # Check Enabled status (Default to Yes if missing to be safe, or check data source)
        # In QMC, it's typically "Yes" or "No".
        if t.get("Enabled") != "Yes":
           continue
           
        simplified_tasks.append({
            "Name": t.get("Name"),
            "Status": t.get("Status"),
            "Last execution": t.get("Last execution")
            # We don't need to send "Enabled" since we pre-filtered
        })
        
    if not simplified_tasks:
        return {
            "status": "No Run",
            "summary": "No ENABLED tasks found for this process today."
        }
        
    prompt = ChatPromptTemplate.from_template(
        """
        Act as a Qlik Process Analyst. Analyze the following list of tasks for the process '{process_name}'.
        
        Context:
        - These tasks ran TODAY.
        - ALL provided tasks are ENABLED (Critical for the process).
        STRICT Status Hierarchy (Top priority wins):
        1. "Failed": If ANY task is 'Failed', 'Error', 'Aborted', 'Skipped', 'Never started', or 'Reset'. (CRITICAL: Even if others are running/success, this overrides).
        2. "Running": If NO failures, but ANY task is 'Started', 'Triggered', 'Retrying', 'Aborting' (Active execution).
        3. "Pending": If NO failures and NO active execution, but tasks are 'Queued' (Waiting) or only dependencies are checking.
        4. "Success": If and ONLY IF ALL tasks are 'Success'.
        
        Tasks:
        {tasks_json}
        
        Output format (JSON only):
        {{
            "status": "Success" | "Running" | "Failed" | "Pending",
            "summary": "Brief explanation (max 1 sentence)",
            "failed_tasks": ["List of task names that failed or were skipped"],
            "running_tasks": ["List of task names still running"]
        }}
        """
    )
    
    chain = prompt | llm
    
    try:
        response = chain.invoke({
            "process_name": process_name,
            "tasks_json": json.dumps(simplified_tasks, indent=2)
        })
        
        # Parse JSON from content (handle potential markdown fences)
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return json.loads(content.strip())
        
    except Exception as e:
        return {
            "status": "Error",
            "summary": f"LLM Analysis failed: {str(e)}"
        }

async def analyst_llm_node(state: QMCState) -> dict:
    """
    Analyst Node:
    - Partitions data by TAGS/Process.
    - Calls LLM for each monitored process.
    - Aggregates results.
    """
    print("   [Analyst] Starting LLM Analysis...")
    
    # 1. Initialize LLM
    llm = ChatGroq(
        temperature=0, 
        model_name=Config.GROQ_MODEL, 
        api_key=Config.GROQ_API_KEY
    )
    
    all_tasks = state.get("structured_data", [])
    if not all_tasks:
        return {"current_step": "done", "logs": ["No data to analyze"]}
    
    # 2. Partition Data
    # Config.MONITORED_PROCESSES = {"FE_HITOS": "Hitos", ...}
    monitored_tags = Config.MONITORED_PROCESSES
    partitions = {tag: [] for tag in monitored_tags}
    
    # Also keep track of 'Unknown' if needed, but for now focus on targets
    for task in all_tasks:
        task_tags_str = task.get("Tags", "")
        # Handle if tags is list or str
        # task_tags_str might be "FE_HITOS_DIARIO" or ["FE_HITOS_DIARIO"]
        
        # Normalize to string for searching
        found = False
        for mon_key in monitored_tags:
            if mon_key in str(task_tags_str):
                partitions[mon_key].append(task)
                found = True
                # A task might belong to multiple? Usually one primary process.
                # We stop at first match for simplicity or allow multiple?
                # Let's allow multiple just in case.
                
    # 3. Analyze Each Partition
    final_report = {}
    
    for tag, p_tasks in partitions.items():
        print(f"     > Analyzing {tag} ({len(p_tasks)} tasks)...")
        if not p_tasks:
            final_report[tag] = {
                "status": "No Run",
                "summary": "No execution records found for today."
            }
            continue
            
        analysis = analyze_group(tag, p_tasks, llm)
        final_report[tag] = analysis
        print(f"       Result: {analysis.get('status')} - {analysis.get('summary')}")
        
    # 4. Save Final Report to State
    # We might want to save this as a JSON file too
    
    return {
        "current_step": "report",
        "process_reports": final_report,
        "logs": [f"Analyzed {len(partitions)} process groups"]
    }
