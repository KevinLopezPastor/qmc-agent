
# QMC Agent - CLI Entry Point
from datetime import datetime
import asyncio
import argparse
from typing import List, Dict
import sys
import os

# Fix path to allow imports from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from logging.handlers import RotatingFileHandler

from src.config import Config
from src.state import create_initial_state
from src.nodes.login_node_sync import login_node_sync
from src.nodes.extractor import extractor_node
from src.nodes.analyst_llm import analyst_llm_node
from src.nodes.reporter import reporter_node

# Configuration for Logging
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logging():
    """Configure logging to file and console."""
    logger = logging.getLogger("QMC_Agent")
    logger.setLevel(logging.DEBUG)
    
    # Formatters
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
    
    # File Handler (Rotating)
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Add Handlers
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
    return logger

logger = setup_logging()

async def run_agent(tags: List[str] = None):
    """
    Main Async Entry Point for QMC Agent.
    """
    logger.info("🚀 Starting QMC Agent")
    logger.info(f"📋 Target Tags: {tags if tags else 'ALL'}")
    logger.debug(f"⚙️  Config: Headless={Config.HEADLESS}, Timeout={Config.TIMEOUT_MS}ms")
    
    # 1. Initialize State
    state = create_initial_state()
    
    # 2. Login (Sync Node via Subprocess)
    logger.info("🔑 Authenticating...")
    try:
        login_result = login_node_sync(state)
        state.update(login_result)
        
        if not login_result.get("success"):
            logger.error(f"❌ Login Failed: {login_result.get('error_message')}")
            return
        
        logger.info("✅ Login Success")
        
    except Exception as e:
        logger.critical(f"❌ Login Critical Error: {str(e)}", exc_info=True)
        return
    
    # 3. Extraction (Global Filter)
    logger.info("🕷️ Extracting Data (Last execution = Today)...")
    try:
        extract_result = extractor_node(state)
        state.update(extract_result)
        
        if state.get("current_step") == "error":
             logger.error(f"❌ Extraction Failed: {state.get('error_message')}")
             return
             
    except Exception as e:
        logger.error(f"❌ Extraction Exception: {str(e)}", exc_info=True)
        return

    # 4. Partition & Analyze (LLM)
    logger.info("🤖 Analyzing Data with LLM...")
    try:
        # Filter config if specific tags requested (logic handled by Analyst usually, but skipping for now)
        analyst_result = await analyst_llm_node(state)
        state.update(analyst_result)
        
    except Exception as e:
        logger.error(f"❌ Analysis Exception: {str(e)}", exc_info=True)
        return
    
    # 5. Visual Report (Image)
    logger.info("🖼️ Generating Visual Report...")
    try:
        report_result = reporter_node(state)
        state.update(report_result)
        
        if report_result.get("report_image_path"):
            logger.info(f"✅ Report Image: {report_result.get('report_image_path')}")
        else:
            logger.warning("⚠️ Report generated but path missing?")
            
    except Exception as e:
         logger.error(f"❌ Reporting Exception: {str(e)}", exc_info=True)

    # 6. Final Console Summary
    reports = state.get("process_reports", {})
    print(f"\n📊 === FINAL REPORT SUMMARY ===")
    
    # Filter output if tags specified
    keys_to_show = tags if tags else reports.keys()
    
    for tag in keys_to_show:
        if tag in reports:
            rep = reports[tag]
            status = rep.get("status")
            status_emoji = "✅" if status == "Success" else "⚠️" if status == "Running" else "❌" if status == "Failed" else "⚪"
            
            print(f"\n{status_emoji} Process: {tag}")
            print(f"   Status: {status}")
            print(f"   Summary: {rep.get('summary')}")
            if rep.get("failed_tasks"):
                print(f"   🔴 Failed Tasks: {', '.join(rep.get('failed_tasks'))}")
            if rep.get("running_tasks"):
                print(f"   🔵 Running Tasks: {', '.join(rep.get('running_tasks'))}")
        else:
             if tags: print(f"\n❓ Process: {tag} - No data found")

    logger.info("🏁 Agent Finished")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QMC Agent CLI")
    parser.add_argument("--tags", type=str, help="Comma-separated list of tags to monitor (e.g., FE_HITOS,FE_COBRANZAS)")
    parser.add_argument("--all", action="store_true", help="Monitor all configured processes")
    
    args = parser.parse_args()
    
    # Parse tags
    target_tags = []
    if args.tags:
        target_tags = [t.strip() for t in args.tags.split(",")]
    elif args.all:
        target_tags = list(Config.MONITORED_PROCESSES.keys())
        
    asyncio.run(run_agent(target_tags))
