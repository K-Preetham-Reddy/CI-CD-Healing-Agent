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

        for run in failed_runs:
            if run.id not in processed_runs:
                failure_data={
                    "id":run.id,
                    "run_number":run.run_number,
                    "name":run.name,
                    "status":run.status,
                    "conclusion":run.conclusion,
                    "head_branch":run.head_branch,
                    "head_sha":run.head_sha,
                    "created_at":run.created_at,
                    "updated_at":run.updated_at,
                    "url":run.url
                }
                new_failures.append(failure_data)
                processed_runs.add(run.id)

                logger.info(
                    f"New failure: Run #{run.run_number} - {run.name} "
                    f"(Branch: {run.head_branch})"
                )
        if new_failures:
            logger.info(f"Detected {len(new_failures)} new failures")

            current_failures=state.context.get("detected_failures",[])
            current_failures.extend(new_failures)
            state.context["detected_failures"]=current_failures
            state.context["processed_runs"]=processed_runs

            state.memory.append(f"[{timestamp}] Check #{check_num}: Detected {len(new_failures)} new failed runs")

            state.current_task=f"Processing {len(new_failures)} newly detected failures"
        else:
            logger.info("No new failures detected")
            state.memory.append(f"[{timestamp}] Check #{check_num}: No new failures detected")
            
        if total_failures==0:
            state.status="complete"
            state.current_task="No failures detected - monitoring complete"
            logger.info("No failures in repository - monitoring complete")

        state.context["last_check"]=timestamp
        state.context["last_failure_count"]=total_failures
        state.last_updated=timestamp

        logger.info(
            f"Monitoring cycle #{check_num} complete -"
            f"New:{len(new_failures)}, Total:{len(state.context.get('detected_failures',[]))}"
        )
    
    except Exception as e:
        logger.error(f"Error during GitHub monitoring: {e}",exc_info=True)
        
        state.status="error"
        state.current_task=f"Error occurred: {str(e)}"
        state.memory.append(f"[{timestamp}] ERROR: {str(e)}")

        state.context["last_error"]={
            "message":str(e),
            "timestamp":timestamp,
            "check_number":check_num
        }
    return state
        
        

            
        

