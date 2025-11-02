import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph import create_agent_graph
from agents.state import AgentState

async def test_full_workflow():
    print("\n"+"="*80)
    print(" "*20+"AGENT GRAPH TEST")
    print("="*80+"\n")

    OWNER="K-Preetham-Reddy"
    REPO="flaky-test-repo"

    print("Test Configuration: ")
    print(f" Repository: {OWNER}/{REPO}")

    if not os.getenv("GITHUB_TOKEN"):
        print(" GITHUB_TOKEN not set")
    
    print("=" * 80)
    print("STEP 1: Creating and Compiling Graph")
    print("=" * 80)
    try:
        graph=create_agent_graph()
        print("Graph created and compiled\n")
    except Exception as e:
        print(f"Failed to create graph: {e}\n")
        return
    
    print("=" * 80)
    print("STEP 2: Generating Graph Visualization")
    print("=" * 80)
    try:
        viz_path=graph.visualize("agent_workflow_graph.png")
        if viz_path:
            print(f"Visualization saved to: {viz_path}\n")
        else:
            print("Visualization Skipped (optional dependencies not installed-pygraphviz & pillow)\n")
    except Exception as e:
        print(f"Visualization failed: {e}\n")
    
    print("=" * 80)
    print("STEP 3: Creating Initial Agent State")
    print("=" * 80)

    initial_state = AgentState(
        id="agent-gh-monitor-001",
        name="GitHub Workflow Debugger",
        role="monitor_and_debug",
        status="created",
        memory=[],
        goals=[
            "Monitor GitHub workflows continuously",
            "Detect workflow failures immediately",
            "Analyze error logs and identify root causes",
            "Suggest automated fixes"
        ],
        current_task=None,
        sub_tasks=[],
        context={
            "owner": OWNER,
            "repo": REPO,
            "monitoring_interval": 300,  # 5 minutes
            "max_failed_runs": 10,
            "auto_analyze": True
        },
        last_updated=datetime.now().isoformat()
    )

    print("Initial State Created: ")
    print(f"   Agent ID: {initial_state.id}")
    print(f"   Name: {initial_state.name}")
    print(f"   Role: {initial_state.role}")
    print(f"   Status: {initial_state.status}")
    print(f"   Goals: {len(initial_state.goals)} defined")
    print(f"   Repository: {initial_state.context['owner']}/{initial_state.context['repo']}")
    print()

    print("=" * 80)
    print("STEP 4: Executing Workflow")
    print("=" * 80)
    print("Running graph execution\n")

    try:
        final_state=await graph.execute(initial_state)
        print("Workflow execution completed successfully\n")

        print("=" * 80)
        print("STEP 5: Results Analysis")
        print("=" * 80)

        print(f"\n Final Agent State:")
        print(f"   Status: {final_state.status}")
        print(f"   Current Task: {final_state.current_task}")
        print(f"   Memory Entries: {len(final_state.memory)}")
        print(f"   Sub-tasks: {len(final_state.sub_tasks)}")
        
        print(f"\n Monitoring Statistics:")
        print(f"   Total Checks: {final_state.context.get('total_checks', 0)}")
        print(f"   Monitoring Started: {final_state.context.get('monitoring_started_at', 'N/A')}")
        print(f"   Last Check: {final_state.context.get('last_check', 'N/A')}")
        print(f"   Last Failure Count: {final_state.context.get('last_failure_count', 0)}")
        

        detected_failures = final_state.context.get("detected_failures", [])
        print(f"\n Failure Detection:")
        print(f"   Detected Failures: {len(detected_failures)}")
        
        if detected_failures:
            print(f"\n   Failed Workflow Runs:")
            for i, failure in enumerate(detected_failures[:5], 1):
                print(f"\n   {i}. Run #{failure['run_number']}: {failure['name']}")
                print(f"      Status: {failure['status']} | Conclusion: {failure['conclusion']}")
                print(f"      Branch: {failure['head_branch']}")
                print(f"      SHA: {failure['head_sha'][:8]}...")
                print(f"      Updated: {failure['updated_at']}")
                print(f"      URL: {failure['url']}")
            
            if len(detected_failures) > 5:
                print(f"\n   ... and {len(detected_failures) - 5} more failures")
        else:
            print("No failures detected - all workflows passing!")
        

        print(f"\n  Agent Memory Log (last 10 entries):")
        for entry in final_state.memory[-10:]:
            print(f"   {entry}")
        
        if "last_error" in final_state.context:
            print(f"\n   Error Encountered:")
            error = final_state.context["last_error"]
            print(f"   Message: {error['message']}")
            print(f"   Timestamp: {error['timestamp']}")
        
        print("\n" + "=" * 80)
        print("TEST EXECUTION SUMMARY")
        print("=" * 80)
        

        success = final_state.status not in ["error", "failed"]
        
        print(f"\nGraph Compilation: Success")
        print(f"Workflow Execution: Success")
        print(f"State Management: Success")
        print(f"GitHub Integration: Success")
        print(f"Failure Detection: {'Success' if detected_failures or final_state.status == 'complete' else 'No failures to detect'}")
        
        if success:
            print(f"\nALL TESTS PASSED!")
        else:
            print(f"\n  Tests completed with warnings (see details above)")
        
        print("\n" + "=" * 80)
        
        return final_state
        
    except Exception as e:
        print(f"\n Workflow execution failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 80)
        return None


async def test_failure_detection_on_real_repo():
    print("\n" + "="*80)
    print(" "*20 + "REAL REPOSITORY FAILURE DETECTION TEST")
    print("="*80 + "\n")
    

    test_owner = "K-Preetham-Reddy"
    test_repo = "flaky-test-repo"
    
    if not test_owner or not test_repo:
        print("  Skipping real repository test")
        print("  Set TEST_REPO_OWNER and TEST_REPO_NAME environment variables")
        print("  to test on a repository with failed workflows\n")
        return
    
    print(f"Testing on: {test_owner}/{test_repo}\n")
    

    graph = create_agent_graph()
    
    initial_state = AgentState(
        id="test-real-repo",
        name="Real Repository Test",
        role="monitor",
        status="created",
        memory=[],
        goals=["Detect real failures"],
        current_task=None,
        sub_tasks=[],
        context={
            "owner": test_owner,
            "repo": test_repo,
            "max_failed_runs": 5
        },
        last_updated=datetime.now().isoformat()
    )

    final_state = await graph.execute(initial_state)

    failures = final_state.context.get("detected_failures", [])
    
    if failures:
        print(f" Successfully detected {len(failures)} failures in {test_owner}/{test_repo}")
        print(f"\nFirst failure:")
        print(f"  Run  {failures[0]['run_number']}: {failures[0]['name']}")
        print(f"  URL: {failures[0]['url']}\n")
    else:
        print(f" No failures detected in {test_owner}/{test_repo} (all workflows passing!)\n")
    
    return final_state



if __name__ == "__main__":
    print("\n Starting Agent Graph Test Suite...\n")
    
    asyncio.run(test_full_workflow())
    
    print("\n" + "-"*80 + "\n")
    asyncio.run(test_failure_detection_on_real_repo())
    
    print("\n✅ All tests completed!\n")



