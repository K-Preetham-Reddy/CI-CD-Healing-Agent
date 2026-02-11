import logging
from datetime import datetime
from typing import Dict, Any, List
from ..state import AgentState

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent.parent))
from mcp_servers.github_mcp import GitHubMCP

logger = logging.getLogger("HealingNode")

async def retry_node(state: AgentState) -> AgentState:
    """
    Identifies healable failures from analysis
    Retries failed workflow runs
    Tracks retry attempts and success/failure
    Updates state with healing results
    """

    logger.info("Healing Node: start - Workflow retry")

    state.status="healing"
    state.current_task="Attempting to heal failures via workflow retry"

    timestamp=datetime.now().isoformat()

    routing_decision=state.context.get("routing_decision",{})
    healable_count=routing_decision.get("healable_count",0)

    if healable_count==0:
        logger.warning("No healable failures identified, skipping retry")
        state.memory.append(f"[{timestamp}] No healable failures to retry")
        state.status="healing_skipped"
        return state
    
    logger.info(f"Attempting to heal {healable_count} failures")
    state.memory.append(f"[{timestamp}] Starting healing for {healable_count} failures")

    owner=state.context.get("owner")
    repo=state.context.get("repo")

    try:
        github=GitHubMCP()
    except Exception as e:
        error_msg=f"Failed to initialize GitHub client: {e}"
        logger.error(error_msg)
        state.status="error"
        state.memory.append(f"[{timestamp}] ERROR: {error_msg}")
        state.context["last_error"]={
            "message":error_msg,
            "timestamp":timestamp
        }
        return state
    
    analyzed_failures=state.context.get("analyzed_failures",[])

    healable_categories={
        "timeout_error",
        "network_error",
        "infrastructure_error",
        "environment_error"
    }
    retry_results={
        "total_retried":0,
        "successful_retries":0,
        "failed_retries":0,
        "skipped":0,
        "details":[]
    }

    for failure in analyzed_failures:
        analysis=failure.get("analysis",{})
        category=analysis.get("error_category","unknown")
        is_flaky=analysis.get("is_flaky",False)
        confidence=analysis.get("confidence_score",0.0)
        run_id=failure.get("id")
        run_number=failure.get("run_number")
    
        should_retry=False
        retry_reason=""

        if is_flaky and confidence>=0.5:
            should_retry=True
            retry_reason="Flaky test detected"
        elif category in healable_categories and confidence>=0.5:
            should_retry=True
            retry_reason=f"Healable {category}"
    
        if not should_retry:
            retry_results["skipped"]+=1
            logger.info(f"Skipping retry for Run #{run_number} - not healable")
            continue

        
