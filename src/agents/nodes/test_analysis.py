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
        return True

    except ConnectionError as e:
        print(f"Connection failed: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}\n")
        return False

        


