import logging
import os
from datetime import datetime
from ..state import AgentState

import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent.parent.parent))
from mcp_servers.github_mcp import GitHubMCP

logger=logging.getLogger("GitHubMonitorNode")

async def github_monitor_node(state: AgentState)->AgentState:
    logger.info("Starting GitHub workflow monitoring")

    state.status="monitoring"
    state.current_task="Monitoring GitHub workflow for failures"

    owner=state.context.get("owner")
    repo=state.context.get("repo")
    max_failed_runs=state.context.get("max_failed_runs",10)

    state.context["total_checks"]=state.context.get("total_checks",0)
    check_num=state.context["total_checks"]

    timestamp=datetime.now().isoformat()
    try:
        logger.info(f"Connection to GitHub API for {owner}/{repo}")
        github=GitHubMCP()
        state.memory.append(f"[{timestamp}] Check #{check_num}: Connected to GitHub API")
        
        logger.info(f"Fetching failed runs (limit: {max_failed_runs})")
        failed_runs_response=await github.get_failed_runs(owner=owner,repo=repo,limit=max_failed_runs)

        failed_runs=failed_runs_response.failed_runs
        total_failures=failed_runs_response.total_count
        logger.info(f"Found {total_failures} total failed runs")

        processed_runs=state.context.get("processed_runs",set())
        new_failures=[]
        

