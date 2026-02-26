"""
NPrinting Analyst Node (V2 Optimized)
Analyzes NPrinting tasks using LLM, filtering by prefix patterns.

Optimizations:
- Pydantic structured output (guaranteed format)
- Retry with exponential backoff (tenacity)
- Parallel LLM calls per process group (asyncio.gather)
- Case-insensitive prefix matching
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

logger = logging.getLogger("NPrinting.Analyst")


# ============ Pydantic Output Schema ============

class NPrintingAnalysisResult(BaseModel):
    """Structured output for NPrinting LLM analysis."""
    status: Literal["Success", "Running", "Failed", "Pending"]
    summary: str = Field(description="Brief explanation, max 1 sentence")
    failed_tasks: List[str] = Field(default_factory=list)
    running_tasks: List[str] = Field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0


# ============ Prefix Matching (Robust) ============

def filter_tasks_by_prefix(tasks: List[Dict], prefix: str) -> List[Dict]:
    """Filter tasks whose 'Task name' starts with the given prefix (case-insensitive, trimmed)."""
    prefix_lower = prefix.strip().lower()
    return [
        t for t in tasks 
        if t.get("Task name", "").strip().lower().startswith(prefix_lower)
    ]


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
    # Log raw response for debugging
    logger.debug(f"Raw LLM response: {content[:500]}")
    
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
    
    try:
        raw = json.loads(content.strip())
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse failed. Content was: {content[:300]}")
        raise ValueError(f"LLM returned invalid JSON: {e}")
    
    # Handle list responses — but only if the first item looks like an analysis
    if isinstance(raw, list):
        analysis_item = None
        for item in raw:
            if isinstance(item, dict) and "status" in item and "summary" in item:
                analysis_item = item
                break
        if analysis_item:
            raw = analysis_item
        else:
            logger.error(f"LLM returned list without analysis. First item keys: {list(raw[0].keys()) if raw and isinstance(raw[0], dict) else 'N/A'}")
            raise ValueError(f"LLM returned a list of raw tasks instead of analysis. Got {len(raw)} items.")
    
    # Validate the parsed dict has expected fields
    if not isinstance(raw, dict) or "status" not in raw:
        logger.error(f"Unexpected format. Keys: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
        raise ValueError(f"LLM returned unexpected format. Keys found: {list(raw.keys()) if isinstance(raw, dict) else type(raw)}")
    
    result = NPrintingAnalysisResult(**raw)
    return result.model_dump()


# ============ Core Analysis ============

def analyze_nprinting_group(process_name: str, tasks: List[Dict], llm) -> Dict:
    """Analyzes a single group of NPrinting tasks using LLM."""
    if not tasks:
        return {"status": "No Data", "summary": "No tasks found for this process today."}
    
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
        
        === FEW-SHOT EXAMPLES ===
        
        Example 1 (All Completed):
        Input: [{{"Task name": "h. Tablero Eficiencia Comercial - Tiendas", "Status": "Completed", "Progress": "100%"}}, {{"Task name": "h. Tablero Eficiencia Comercial - Gerencial", "Status": "Completed", "Progress": "100%"}}]
        Output: {{"status": "Success", "summary": "All 2 reports generated successfully.", "failed_tasks": [], "running_tasks": [], "total_tasks": 2, "completed_tasks": 2}}
        
        Example 2 (One Failed):
        Input: [{{"Task name": "h. Tablero Eficiencia Comercial - Tiendas", "Status": "Completed", "Progress": "100%"}}, {{"Task name": "h. Tablero Eficiencia Comercial - Gerencial", "Status": "Failed", "Progress": "0%"}}]
        Output: {{"status": "Failed", "summary": "1 of 2 reports failed: h. Tablero Eficiencia Comercial - Gerencial.", "failed_tasks": ["h. Tablero Eficiencia Comercial - Gerencial"], "running_tasks": [], "total_tasks": 2, "completed_tasks": 1}}
        
        Example 3 (Still Running):
        Input: [{{"Task name": "h. Tablero Eficiencia Comercial - Tiendas", "Status": "Completed", "Progress": "100%"}}, {{"Task name": "h. Tablero Eficiencia Comercial - Gerencial", "Status": "Running", "Progress": "60%"}}]
        Output: {{"status": "Running", "summary": "1 report still generating: h. Tablero Eficiencia Comercial - Gerencial (60%).", "failed_tasks": [], "running_tasks": ["h. Tablero Eficiencia Comercial - Gerencial"], "total_tasks": 2, "completed_tasks": 1}}
        
        === END EXAMPLES ===
        
        Tasks to analyze:
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

async def nprinting_analyst_node(state: QMCState) -> dict:
    """
    NPrinting Analyst Node:
    - Partitions data by prefix patterns.
    - Calls LLM in PARALLEL for each monitored process.
    - Aggregates results.
    """
    logger.info("Starting NPrinting LLM Analysis...")
    
    llm = ChatGroq(
        temperature=0,
        model_name=Config.GROQ_MODEL,
        api_key=Config.GROQ_API_KEY
    )
    
    all_tasks = state.get("nprinting_data") or []
    if not all_tasks:
        return {"nprinting_reports": {}, "logs": ["NPrinting: No data to analyze"]}
    
    monitored_prefixes = Config.NPRINTING_MONITORED
    
    # Parallel LLM calls (staggered to avoid rate limits)
    async def _analyze_one(prefix, alias, delay):
        await asyncio.sleep(delay)  # Stagger calls to avoid 429s
        prefix_tasks = filter_tasks_by_prefix(all_tasks, prefix)
        logger.info(f"  Analyzing {alias} ({len(prefix_tasks)} tasks, prefix='{prefix}')...")
        
        if not prefix_tasks:
            return alias, {
                "status": "Pending",
                "summary": "Tasks have not been executed yet.",
                "prefix": prefix,
                "task_count": 0
            }
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, analyze_nprinting_group, alias, prefix_tasks, llm)
        result["prefix"] = prefix
        result["task_count"] = len(prefix_tasks)
        logger.info(f"  {alias}: {result.get('status')} - {result.get('summary')}")
        return alias, result
    
    # Launch analyses with 0.5s stagger between each
    tasks = [_analyze_one(prefix, alias, i * 0.5) for i, (prefix, alias) in enumerate(monitored_prefixes.items())]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Collect results
    final_report = {}
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Parallel analysis failed: {r}")
            continue
        alias, analysis = r
        final_report[alias] = analysis
    
    return {
        "nprinting_reports": final_report,
        "logs": [f"NPrinting: Analyzed {len(final_report)} process groups (parallel)"]
    }
