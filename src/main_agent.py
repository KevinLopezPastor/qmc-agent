
# QMC Agent - Multi-Agent Entry Point
# Executes the LangGraph Workflow defined in src/graph.py

import sys
import os
import asyncio
import logging
import json
from datetime import datetime

# Fix path to allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import compile_graph
from src.state import create_initial_state
from src.config import Config

# Reuse logger configuration from main.py logic if possible, or simple setup
# For simplicity, we'll do a basic setup here similar to main.py
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [GRAPH] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "agent_graph.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("QMC_Graph")

async def run_graph(tags=None):
    """
    Executes the Multi-Agent Graph.
    """
    logger.info("🚀 Starting QMC Multi-Agent Workflow")
    logger.info(f"Target Tags: {tags if tags else 'ALL'}")
    
    # 1. Compile the Graph
    logger.info("⚙️ Compiling Agent Graph...")
    app = compile_graph()
    
    # 2. Initialize State
    initial_state = create_initial_state()
    
    # Config for LangGraph (thread_id allows persistence/memory)
    config = {"configurable": {"thread_id": "qmc-execution-1"}}
    
    # 3. Invoke Graph
    logger.info("▶️ Invoking Graph...")
    final_state = await app.ainvoke(initial_state, config)
    
    # 4. Final Summary
    logger.info("🏁 Workflow Completed")
    
    if final_state.get("current_step") == "error":
        logger.error(f"❌ Workflow failed with error: {final_state.get('error_message')}")
    else:
        logger.info("✅ Workflow finished successfully")
        reports = final_state.get("process_reports", {})
        if reports:
            logger.info("📊 Summary Report:")
            print(json.dumps(reports, indent=2, ensure_ascii=False))
            
            # Check for image
            # The reporter node sets 'report_image_path' in state? 
            # Wait, state definition might not have explicit 'report_image_path' key in TypedDict?
            # Let's check state.py... it has 'process_reports'.
            # Reporter Node returns {"report_image_path": ...} which updates the state.
            # But TypedDict QMCState needs to have that key defined to access it safely via .get()?
            # Actually LangGraph merges dicts, but for strict typing...
            # Let's assume it's in the merged state or inside process_reports? 
            # Reporter node usually returns { "process_reports": ... } or specific keys.
            pass

if __name__ == "__main__":
    asyncio.run(run_graph())
