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

        logger.info(f"Retrying Run {run_number} - Reason: {retry_reason}")
        state.current_task=f"Retrying workflow run {run_number}"

        try:
            result = await github.rerun_workflow(
                owner=owner,
                repo=repo,
                run_id=run_id,
                failed_jobs_only=True
            )

            if result.success:
                retry_results["successful_retries"]+=1
                retry_results["total_retried"]+=1

                retry_info={
                    "run_id":run_id,
                    "run_number":run_number,
                    "status":"success",
                    "reason":retry_reason,
                    "message":result.message,
                    "timestamp":timestamp
                }
                retry_results["details"].append(retry_info)

                logger.info(f"Sucessfully retried Run #{run_number}")
                state.memory.append(f"[{timestamp}] Successful - Retried Run #{run_number}: {retry_reason}")
            else:
                retry_results["failed_retries"]+=1
                retry_results["total_retries"]+=1

                retry_info={
                    "run_id":run_id,
                    "run_number":run_number,
                    "status":"success",
                    "reason":retry_reason,
                    "message":result.message,
                    "timestamp":timestamp
                }

                retry_results["details"].append(retry_info)

                logger.warning(f" Failed to retry Run #{run_number}: {result.message}")
                state.memory.append(f"[{timestamp}] Failed - Retry failed for Run #{run_number}:{result.message}")
            
        except Exception as e:
            retry_results["failed_retries"]+=1
            retry_results["total_Retried"]+=1

            error_msg=str(e)
            retry_info={
                "run_id":run_id,
                "run_number":run_number,
                "status":"error",
                "reason":retry_reason,
                "message":error_msg,
                "timestamp":timestamp
            }
            retry_results["details"].append(retry_info)

            logger.error(f"Error retrying Run #{run_number}: {e}")
            state.memory.append(f"[{timestamp}] ERROR retrying Run #{run_number}: {error_msg}")

        state.context["retry_results"]=retry_results
        state.context["last_healing_attempt"]=timestamp

        if retry_results["successful_retries"]>0:
            state.status="healing_complete"
            state.current_task=(
                f"Healing complete: {retry_results['successful_retries']} workflows retried"
            )
        elif retry_results["total_retried"]==0:
            state.status="healing_skipped"
            state.current_task="No failures required retry"
        else:
            state.status="healing_partial"
            state.current_task=(f"Healing partially complete: "
                f"{retry_results['failed_retries']} retries failed")
            
        state.memory.append(
            f"[{timestamp}] Healing summary: "
            f"{retry_results['successful_retries']} successful, "
            f"{retry_results['failed_retries']} failed,"
            f"{retry_results['skipped']} skipped" 
        )
        
        logger.info(
            f"Healing complete: {retry_results['successful_retries']}/{retry_results['total_retried']} successful retries"
        )

        state.last_updated=timestamp

        return state
    
def get_healing_summary(state: AgentState) -> Dict[str,Any]:
    retry_results=state.context.get("retry_results",{})

    return {
        "total_retried":retry_results.get("total_retried",0),
        "successful":retry_results.get("successful_retries",0),
        "failed":retry_results.get("failed_retries",0),
        "skipped":retry_results.get("skipped",0),
        "success_rate":(
            retry_results.get("successful_retries",0)/max(retry_results.get("total_retried",1),1)*100
        ),
        "details":retry_results.get("details",[])
    }

if __name__=="__main__":
    import asyncio

    async def test_retry_node():
        print("Testing Retry Node")

        test_state=AgentState(
            id="test_healing",
            name="Healing Test",
            role="healer",
            status="analysis_complete",
            memory=["[timestamp] Analysis complete"]
            goals=["Test healing"],
            current_task=None,
            sub_tasks=[],
            context={
                "owner":"test_owner",
                "repo":"test-repo",
                "routing_decision":{
                    "healable_count":2,
                    "flaky_count":1,
                    "critical_count":0
                },
                "analyzed_failures":[
                    {
                        "id":123,
                        "run_number":1,
                        "name":"Test CI",
                        "analysis":{
                            "error_category":"timeout_error",
                            "severity":"medium",
                            "is_flaky":True,
                            "confidence_score":0.8
                        }
                    },
                    {
                        
                    }
                ]
            }
        )