
# QMC Agent - Multi-Agent Entry Point (V3.0 Unified)
# Executes the Unified LangGraph Workflow with QMC + NPrinting

import sys
import os
import asyncio
import logging
import json
from datetime import datetime

# Fix path to allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.graph import compile_unified_graph, compile_graph
from src.state import create_initial_state
from src.config import Config

# Logger setup
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
logger = logging.getLogger("QMC_Agent")


async def run_unified_graph():
    """
    Executes the Unified Multi-Agent Graph (QMC + NPrinting).
    """
    logger.info("🚀 Starting Unified Multi-Agent Workflow (QMC + NPrinting)")
    logger.info(f"📅 Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate configuration
    qmc_missing = Config.validate()
    nprinting_missing = Config.validate_nprinting()
    
    if qmc_missing:
        logger.error(f"❌ Missing QMC configuration: {qmc_missing}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    if nprinting_missing:
        logger.warning(f"⚠️ Missing NPrinting config: {nprinting_missing} - NPrinting flow will be skipped")
    
    # 1. Compile the Unified Graph
    logger.info("⚙️ Compiling Unified Agent Graph...")
    app = compile_unified_graph()
    
    # 2. Initialize State
    initial_state = create_initial_state()
    
    # Config for LangGraph (thread_id allows persistence/memory)
    config = {"configurable": {"thread_id": f"unified-{datetime.now().strftime('%Y%m%d-%H%M%S')}"}}
    
    # 3. Invoke Graph
    logger.info("▶️ Invoking Unified Graph (QMC + NPrinting in parallel)...")
    final_state = await app.ainvoke(initial_state, config)
    
    # 4. Final Summary
    logger.info("=" * 60)
    logger.info("🏁 Unified Workflow Completed")
    logger.info("=" * 60)
    
    if final_state.get("current_step") == "error":
        logger.error(f"❌ Workflow failed: {final_state.get('error_message')}")
        return final_state
    
    # Display results
    logger.info("✅ Workflow finished successfully")
    
    # QMC Summary
    qmc_reports = final_state.get("process_reports", {})
    if qmc_reports:
        logger.info("\n📊 QMC Reports:")
        for process, report in qmc_reports.items():
            status = report.get("status", "Unknown")
            logger.info(f"   {process}: {status}")
    
    # NPrinting Summary
    nprinting_reports = final_state.get("nprinting_reports", {})
    if nprinting_reports:
        logger.info("\n📊 NPrinting Reports:")
        for process, report in nprinting_reports.items():
            status = report.get("status", "Unknown")
            logger.info(f"   {process}: {status}")
    
    # Combined Summary
    combined = final_state.get("combined_report", {})
    if combined:
        overall = combined.get("overall_status", "Unknown")
        logger.info(f"\n🎯 Overall Status: {overall}")
    
    # Report Image
    report_path = final_state.get("report_image_path")
    if report_path:
        logger.info(f"\n🖼️ Report Image: {report_path}")
    
    return final_state


async def run_qmc_only():
    """
    Legacy: Executes QMC-only workflow (backwards compatibility).
    """
    logger.info("🚀 Starting QMC-Only Workflow (Legacy Mode)")
    
    app = compile_graph()
    initial_state = create_initial_state()
    config = {"configurable": {"thread_id": "qmc-only-1"}}
    
    final_state = await app.ainvoke(initial_state, config)
    
    if final_state.get("current_step") == "error":
        logger.error(f"❌ Workflow failed: {final_state.get('error_message')}")
    else:
        logger.info("✅ QMC-Only Workflow completed")
        print(json.dumps(final_state.get("process_reports", {}), indent=2, ensure_ascii=False))
    
    return final_state


if __name__ == "__main__":
    # Check for command line args
    if len(sys.argv) > 1 and sys.argv[1] == "--qmc-only":
        asyncio.run(run_qmc_only())
    else:
        asyncio.run(run_unified_graph())

