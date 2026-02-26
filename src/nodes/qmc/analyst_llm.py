"""
QMC Agent - Analyst LLM Node (V2 Optimized)
Uses Groq (LLaMA 3) to analyze QMC process groups dynamically.

Optimizations:
- Pydantic structured output (guaranteed format)
- Retry with exponential backoff (tenacity)
- Parallel LLM calls per process group (asyncio.gather)
- Logging instead of print
"""

import asyncio
import logging
from typing import List, Dict, Literal
import json

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import Config
from src.state import QMCState

logger = logging.getLogger("QMC.Analyst")


# ============ Pydantic Output Schema ============

class AnalysisResult(BaseModel):
    """Structured output for LLM analysis — guarantees valid format."""
    status: Literal["Success", "Running", "Failed", "Pending"]
    summary: str = Field(description="Brief explanation, max 1 sentence")
    failed_tasks: List[str] = Field(default_factory=list)
    running_tasks: List[str] = Field(default_factory=list)


# ============ LLM Call with Retry ============

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=lambda rs: logger.warning(f"LLM call failed, retrying ({rs.attempt_number}/3)...")
)
def _invoke_llm(chain, params: dict) -> str:
    """Invoke LLM with automatic retry on failure."""
    response = chain.invoke(params)
    return response.content


def _parse_llm_response(content: str) -> dict:
    """Parse and validate LLM JSON response using Pydantic."""
    # Strip markdown fences
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    raw = json.loads(content.strip())
    
    # Handle list responses — only accept items that look like analysis
    if isinstance(raw, list):
        analysis_item = None
        for item in raw:
            if isinstance(item, dict) and "status" in item and "summary" in item:
                analysis_item = item
                break
        if analysis_item:
            raw = analysis_item
        else:
            raise ValueError(f"LLM returned a list of raw tasks instead of analysis. Got {len(raw)} items.")
    
    # Validate expected fields exist
    if not isinstance(raw, dict) or "status" not in raw:
        raise ValueError(f"LLM returned unexpected format. Keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
    
    # Validate with Pydantic
    result = AnalysisResult(**raw)
    return result.model_dump()


# ============ Core Analysis ============

def analyze_group(process_name: str, tasks: List[Dict], llm) -> Dict:
    """Analyzes a single group of tasks using LLM."""
    if not tasks:
        return {"status": "No Data", "summary": "No tasks found for this process today."}

    # Filter out disabled tasks
    simplified_tasks = [
        {
            "Name": t.get("Name"),
            "Status": t.get("Status"),
            "Last execution": t.get("Last execution")
        }
        for t in tasks if t.get("Enabled") == "Yes"
    ]
    
    if not simplified_tasks:
        return {"status": "No Run", "summary": "No ENABLED tasks found for this process today."}
        
    prompt = ChatPromptTemplate.from_template(
        """
        Act as a Qlik Process Analyst. Analyze the following list of tasks for the process '{process_name}'.
        
        Context:
        - These tasks ran TODAY.
        - ALL provided tasks are ENABLED (Critical for the process).
        STRICT Status Hierarchy (Top priority wins):
        1. "Failed": If ANY task is 'Failed', 'Error', 'Aborted', 'Skipped', 'Never started', or 'Reset'.
        2. "Running": If NO failures, but ANY task is 'Started', 'Triggered', 'Retrying', 'Aborting'.
        3. "Pending": If NO failures and NO active execution, but tasks are 'Queued'.
        4. "Success": If and ONLY IF ALL tasks are 'Success'.
        
        === FEW-SHOT EXAMPLES ===
        
        Example 1 (All Success):
        Input: [{{"Name": "FE_HITOS_DIARIO", "Status": "Success"}}, {{"Name": "FE_COBRANZAS_DIARIA", "Status": "Success"}}]
        Output: {{"status": "Success", "summary": "All 2 tasks completed successfully.", "failed_tasks": [], "running_tasks": []}}
        
        Example 2 (One Failed):
        Input: [{{"Name": "FE_HITOS_DIARIO", "Status": "Success"}}, {{"Name": "FE_COBRANZAS_DIARIA", "Status": "Failed"}}]
        Output: {{"status": "Failed", "summary": "1 of 2 tasks failed: FE_COBRANZAS_DIARIA.", "failed_tasks": ["FE_COBRANZAS_DIARIA"], "running_tasks": []}}
        
        Example 3 (Mixed with Running):
        Input: [{{"Name": "FE_HITOS_DIARIO", "Status": "Success"}}, {{"Name": "FE_COBRANZAS_DIARIA", "Status": "Started"}}]
        Output: {{"status": "Running", "summary": "1 task still running: FE_COBRANZAS_DIARIA.", "failed_tasks": [], "running_tasks": ["FE_COBRANZAS_DIARIA"]}}
        
        === END EXAMPLES ===
        
        Tasks to analyze:
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
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=lambda rs: logger.warning(f"Analysis failed for {process_name}, retrying ({rs.attempt_number}/3)...")
    )
    def _analyze_with_retry():
        content = chain.invoke({
            "process_name": process_name,
            "tasks_json": json.dumps(simplified_tasks, indent=2)
        }).content
        return _parse_llm_response(content)
    
    try:
        return _analyze_with_retry()
    except Exception as e:
        logger.error(f"LLM Analysis failed for {process_name} after retries: {e}")
        return {"status": "Error", "summary": f"LLM Analysis failed: {str(e)}"}


# ============ Main Node (Parallel) ============

async def analyst_llm_node(state: QMCState) -> dict:
    """
    QMC Analyst Node:
    - Partitions data by TAGS/Process.
    - Calls LLM in PARALLEL for each monitored process.
    - Aggregates results.
    """
    logger.info("Starting QMC LLM Analysis...")
    
    llm = ChatGroq(
        temperature=0, 
        model_name=Config.GROQ_MODEL, 
        api_key=Config.GROQ_API_KEY
    )
    
    all_tasks = state.get("structured_data") or []
    if not all_tasks:
        return {"process_reports": {}, "logs": ["QMC: No data to analyze"]}
    
    # Partition Data by Tags
    monitored_tags = Config.MONITORED_PROCESSES
    partitions = {tag: [] for tag in monitored_tags}
    
    for task in all_tasks:
        task_tags_str = str(task.get("Tags", ""))
        for mon_key in monitored_tags:
            if mon_key in task_tags_str:
                partitions[mon_key].append(task)
    
    # Parallel LLM calls using asyncio (staggered to avoid rate limits)
    async def _analyze_one(tag, p_tasks, delay):
        await asyncio.sleep(delay)  # Stagger calls to avoid 429s
        logger.info(f"  Analyzing {tag} ({len(p_tasks)} tasks)...")
        if not p_tasks:
            return tag, {"status": "Pending", "summary": "No execution records found for today."}
        
        # Run sync LLM call in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_group, tag, p_tasks, llm)
        logger.info(f"  {tag}: {result.get('status')} - {result.get('summary')}")
        return tag, result
    
    # Launch analyses with 0.5s stagger between each
    tasks = [_analyze_one(tag, p_tasks, i * 0.5) for i, (tag, p_tasks) in enumerate(partitions.items())]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    final_report = {}
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Parallel analysis failed: {r}")
            continue
        tag, analysis = r
        final_report[tag] = analysis
    
    return {
        "process_reports": final_report,
        "logs": [f"QMC: Analyzed {len(final_report)} process groups (parallel)"]
    }
