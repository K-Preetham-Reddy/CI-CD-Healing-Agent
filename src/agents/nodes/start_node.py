import logging
from datetime import datetime
from ..state import AgentState

logger=logging.getLogger("StartNode")

def start_node(state:AgentState)->AgentState:
    logger.info(f"Intializing agent: {state.name} (ID: {state.id})")

    state.status="initialized"
    state.current_task="Preparing to monitor GitHub workflows"

    timestamp=datetime.now().isoformat()
    state.memory.append(f"[{timestamp}] Agent initialized - Role: {state.role}")
    required_keys=["owner","repo"]
    missing_keys=[key for key in required_keys if key not in state.context]

    if missing_keys:
        error_msg=f"Missing required context keys: {missing_keys}"
        logger.error(error_msg)
        state.status="error"
        state.memory.append(f"[{timestamp}] ERROR: {error_msg}")
        return state

    if "monitoring_interval" not in state.context:
        state.context["monitoring_interval"]=300
        logger.info("Set default monitoring_interval: 300s")

    if "max_failed_runs" not in state.context:
        state.context["max_failed_runs"]=10
        logger.info("Set default max_failed_runs: 10")
    
    state.context["monitoring_started_at"]=timestamp
    state.context["total_checks"]=0
    state.context["detected_failures"]=[]
    state.context["processed_runs"]=set()

    state.sub_tasks=[
        "Connect to GitHub API",
        "Fetch workflow runs",
        "Detect failures",
        "Analyze error logs"
    ]
    repo_full_name=f"{state.context['owner']}/{state.context['repo']}"
    logger.info(f"Montoring repository: {repo_full_name}")
    logger.info(f"Monitoring interval: {state.context['monitoring_interval']}s")
    logger.info(f"Max failed runs to check: {state.context['max_failed_runs']}")

    state.last_updated=timestamp
    state.memory.append(
        f"[{timestamp}] Configuration validated - Ready to monitor {repo_full_name}"
    )
    logger.info("Initialization complete")
    return state
