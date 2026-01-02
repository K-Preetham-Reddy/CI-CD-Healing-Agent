import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agents.state import AgentState
from agents.nodes.analysis_node import failure_analysis_node
from agents.config import get_ollama_client

TEST_CASES = [
    {
        "name": "Flaky timeout test",
        "logs": """
        test_api_connection FAIL
        
        Traceback (most recent call last):
          File "tests/test_integration.py", line 45, in test_api_connection
            response = requests.get(API_URL, timeout=5)
        requests.exceptions.Timeout: Read timed out (timeout=5)
        
        FAILED (failures=1)
        """,
        "expected": {
            "category": "timeout_error",
            "is_flaky": True
        }
    },
    {
        "name": "Import error - missing dependency",
        "logs": """
        Traceback (most recent call last):
          File "src/main.py", line 3, in <module>
            from flask_cors import CORS
        ModuleNotFoundError: No module named 'flask_cors'
        
        Error: Process completed with exit code 1.
        """,
        "expected": {
            "category": "dependency_error",
            "is_flaky": False
        }
    },
    {
        "name": "Test assertion failure",
        "logs": """
        test_user_login FAIL
        
        Traceback (most recent call last):
          File "tests/test_auth.py", line 23, in test_user_login
            self.assertEqual(response.status_code, 200)
        AssertionError: 401 != 200
        
        FAILED (failures=1)
        """,
        "expected": {
            "category": "test_failure",
            "is_flaky": False
        }
    },
    {
        "name": "Build error",
        "logs": """
        npm ERR! code ELIFECYCLE
        npm ERR! myapp@1.0.0 build: `webpack --config webpack.prod.js`
        
        ERROR in ./src/components/Dashboard.tsx
        Module not found: Error: Can't resolve './NotFoundComponent'
        
        webpack compiled with 1 error
        """,
        "expected": {
            "category": "build_error",
            "is_flaky": False
        }
    },
    {
        "name": "Permission denied",
        "logs": """
        Error: fatal: could not read Username for 'https://github.com'
        Error: The process '/usr/bin/git' failed with exit code 128
        fatal: Authentication failed for 'https://github.com/user/repo.git/'
        """,
        "expected": {
            "category": "permission_error",
            "is_flaky": False
        }
    }
]

async def test_ollama_connection():
    """Ollama Server"""
    print("\n"+"="*80)
    print("TEST 0: Ollama Connection")
    print("="*80+"\n")

    try:
        client=get_ollama_client()
        print("Server connected")

        response=client.generate("What model are you?",max_tokens=10)
        print(f"Test response: {response.strip()}")
        print("\nConnection test passed\n")
        return True

    except ConnectionError as e:
        print(f"Connection failed: {e}")
        print("\nSetup Issue")
        return False
    except Exception as e:
        print(f"Error: {e}\n")
        return False

async def test_single_failure_analysis():
    print("\nTEST 1: Single Failure Analysis\n")

    mock_failure={
        "id":123456,
        "run_number":42,
        "name":"CI Tests",
        "head_branch":"main",
        "conclusion":"failure",
        "url":"https://github.com/owner/repo/actions/runs/123456"
    }

    state=AgentState(
        id="test-analysis-1",
        name="Analysis Test",
        role="analyzer",
        status="monitoring",
        memory=[],
        goals=["Test analysis"],
        current_task=None,
        sub_tasks=[],
        context={
            "owner":"test-owner",
            "repo":"test-repo",
            "detected_failures":[mock_failure]
        },
        last_updated=datetime.now().isoformat()
    )

    print("Ollama Analysis...")
    result=await failure_analysis_node(state)

    print(f"\nStatus: {result.status}")
    print(f"Current Task: {result.current_task}")

    analyzed=result.context.get("analyzed_failures",[])
    if analyzed:
        analysis=analyzed[0].get("analysis",{})
        print(f"\nAnalysis Result:")
        print(f"- Category: {analysis.get('error_category','N/A')}")
        print(f"- Severity: {analysis.get('severity','N/A')}")
        print(f"- Is Flaky: {analysis.get("is_flaky",False)}")
        print(f"- Confidence: {analysis.get('confidence_score',0):.2f}")
        print(f"- Root Cause: {analysis.get('root_cause','N/A')[:80]}")
        print(f"- Suggested Fix: {analysis.get('suggested_fix','N/A')[:100]}...")

    summary=result.context.get("analysis_summary",{})
    print(f"\nSummary: ")
    print(f" Total:{summary.get('total_analyzed',0)}")
    print(f" Successful: {summary.get('successful',0)}")
    print(f" Failed: {summary.get('failed',0)}")

async def test_classification_accuracy():
    print("TEST 2: Classification Accuracy (Ollama)")

    try:
        client=get_ollama_client()
    except Exception as e:
        print(f" Can't Run Test: {e}")
        return None

    from agents.nodes.analysis_node import analyze_failure_with_ollama

    correct = 0
    total = len(TEST_CASES)
    results=[]

    for i, test_case in enumerate(TEST_CASES,1):
        print(f"\nTest Case {i}/{total}: {test_case['name']}")

        mock_failure={
            "id":i,
            "run_number":i,
            "name":test_case['name'],
            "head_branch":"main",
            "conclusion":"failure"
        }

        analysis = await analyze_failure_with_ollama(mock_failure, test_case['logs'],client)

        expected=test_case['expected']
        category_match=analysis.get('error_category')==expected['category']
        flaky_match=analysis.get('is_flaky')==expected.get('is_flaky',False)

        if category_match:
            correct+=1
            result="PASS"
        else:
            result="FAIL"

        results.append({
            "name":test_case['name'],
            "expected":expected['category'],
            "got":analysis.get('error_category'),
            "match":category_match
        })

        print(f"{result}")
        print(f" Expected: {expected['category']}")
        print(f" Got: {analysis.get('error_category')}")
        print(f" Root Cause: {analysis.get('root_cause','N/A')[:80]}")
        print(f" Confidence: {analysis.get('confidence_score',0):.2f}")

        


