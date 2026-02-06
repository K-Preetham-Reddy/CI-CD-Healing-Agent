import logging
from typing import Dict, Any, List
from .state import AgentState

logger=logging.getLogger("Routing")

def should_heal_or_notify(state: AgentState) -> str:
    """
    Returns:
    "heal" - Attemp automatic healing (retry workflows) - if the problem is solvable
    "notify" - Sending Notficication to the team - if the problem is comple or critical
    "end" - No action needed - If no failures or analysis failed 
    """
    logger.info("Decision making")
    
    analyzed_failures=state.context.get("analyzed_failures",[])
    analysis_summary=state.context.get("analysis_summary",{})

    if not analyzed_failures:
        logger.info("No failures to process")
        return "end"
    
    healable_count=0
    critical_count=0
    flaky_count=0

    healable_categories={
        "timeout_error",
        "network_error",
        "infrastructure_error",
        "environment_error"
    }

    critical_categories={
        "build_error",
        "dependency_error",
        "configuration_error"
    }
    
    for failure in analyzed_failures:
        analysis=failure.get("analysis",{})
        category=analysis.get("error_category","unknown")
        severity=analysis.get("severity","medium")
        is_flaky=analysis.get("is_falky",False)
        confidence=analysis.get("confidence_score",0.0)

        if is_flaky and confidence>=0.5:
            flaky_count+=1
            healable_count+=1
            continue

        if severity=="critical":
            critical_count+=1
            continue

        if category in healable_categories and confidence>=0.5:
            healable_count+=1
        elif category in critical_categories:
            critical_count+=1

    state.context["routing_decision"]={
        "total_failures":len(analyzed_failures),
        "healable_count":healable_count,
        "flaky_count":flaky_count,
        "critical_count":critical_count,
        "successful_analyses":analysis_summary.get("successful",0)
    }

    if critical_count>0:
        logger.info("Decision: NOTIFY"
                    f"Critical Failures Count: {critical_count}")
        state.memory.append(
            f"[{state.last_updated}] Routing: NOTIFY - {critical_count} critical failures"
        )
        return "notify"
    
    elif healable_count>0:
        logger.info("Decision: HEAL"
                    f"Healable Failures Count: {healable_count}"
                    f"(including {flaky_count} falky tests)")
        state.memory.append(
            f"[{state.last_updated}] Routing: HEAL - {healable_count} healable failures"
        )
        return "heal"
    else:
        logger.info(
            f"Decision: NOTIFY - {len(analyzed_failures)} failures need review"
        )
        state.memory.append(
            f"[{state.last_updated}] Routing: NOTIFY - Manual review needed"
        )
        return "notify"
    
def get_routing_summary(state: AgentState) -> Dict[str,Any]:
    """ Summary of Routing Decision"""
    decision_metrics=state.context.get("routing_decision",{})

    return {
        "decision":"heal" if decision_metrics.get("healable_count",0)>0 else "notify",
        "total_failures":decision_metrics.get("total_failures",0),
        "healable":decision_metrics.get("healable_count",0),
        "flaky":decision_metrics.get("flaky_count",0),
        "critical":decision_metrics.get("critical_count",0),
        "reasoning":_get_decision_reasoning(decision_metrics)
    }

def _get_decision_reasoning(metrics: Dict[str,Any])->str:
    """Reasoning for the decision"""
    healable=metrics.get("healable_count",0)
    flaky=metrics.get("flaky_count",0)
    critical=metrics.get("critical_count",0)

    if critical>0:
        return f"Found {critical} critical failures requiring human intervention"
    elif flaky>0:
        return f"Found {flaky} flaky tests that can be retried"
    elif healable>0:
        return f"Found {healable} healable failures (timeouts, network issues)"
    else:
        return "No clear automatic fix available, manual review needed"

if __name__ == "__main__":
    from datetime import datetime

    print("TESTING ROUTING LOGIC")

    print("Test 1: Flaky Test Detection")

    state1=AgentState(
        id="test-1",
        name="Routing Test",
        role="router",
        status="analysis_complete",
        memory=[],
        goals=["Test routing"],
        current_task=None,
        sub_tasks=[],
        context={
            "analyzed_failures": [
                {
                    "id": 1,
                    "run_number": 1,
                    "analysis": {
                        "error_category": "timeout_error",
                        "severity": "medium",
                        "is_flaky": True,
                        "confidence_score": 0.8
                    }
                }
            ],
            "analysis_summary": {"successful": 1}
        },
        last_updated=datetime.now().isoformat()
    )

    decision1=should_heal_or_notify(state1)
    summary1=get_routing_summary(state1)

    print(f"Decision: {decision1}")
    print(f"Reasoning: {summary1['reasoning']}")
    print(f"Expected: heal, Got: {decision1}\n")

    print("Test 2: Critical Failure Detection")

    state2=AgentState(
        id="test-2",
        name="Routing Test",
        role="router",
        status="analysis_complete",
        memory=[],
        goals=["Test routing"],
        current_task=None,
        sub_tasks=[],
        context={
            "analyzed_failures": [
                {
                    "id": 2,
                    "run_number": 2,
                    "analysis": {
                        "error_category": "build_error",
                        "severity": "critical",
                        "is_flaky": False,
                        "confidence_score": 0.9
                    }
                }
            ],
            "analysis_summary": {"successful": 1}
        },
        last_updated=datetime.now().isoformat()
    )

    decision2=should_heal_or_notify(state2)
    summary2=get_routing_summary(state2)

    print(f"Decision: {decision2}")
    print(f"Reasoning: {summary2['reasoning']}")
    print(f"Expected: heal, Got: {decision2}\n")

    print("Test 3: Mixed Failures (Healable + Critical)")
    
    state3=AgentState(
        id="test-3",
        name="Routing Test",
        role="router",
        status="analysis_complete",
        memory=[],
        goals=["Test routing"],
        current_task=None,
        sub_tasks=[],
        context={
            "analyzed_failures": [
                {
                    "id": 3,
                    "run_number": 3,
                    "analysis": {
                        "error_category": "timeout_error",
                        "severity": "medium",
                        "is_flaky": True,
                        "confidence_score": 0.7
                    }
                },
                {
                    "id": 4,
                    "run_number": 4,
                    "analysis": {
                        "error_category": "dependency_error",
                        "severity": "critical",
                        "is_flaky": False,
                        "confidence_score": 0.9
                    }
                }
            ],
            "analysis_summary": {"successful": 2}
        },
        last_updated=datetime.now().isoformat()
    )

    decision3=should_heal_or_notify(state3)
    summary3=get_routing_summary(state3)

    print(f"Decision: {decision3}")
    print(f"Reasoning: {summary3['reasoning']}")
    print(f"Expected: notify (critical takes priority), Got: {decision3}\n")

    print("Routing Tests Complete")
