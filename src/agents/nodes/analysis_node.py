import logging
import json
from datetime import datetime
from typing import Optional,Any,Dict,List
from ..state import AgentState
from ..config import get_ollama_client,OLLAMA_MODEL,OLLAMA_MAX_TOKENS,OLLAMA_TEMPERATURE

import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent.parent))
from mcp_servers.github_mcp import GitHubMCP

logger=logging.getLogger("AnalysisNode")

FAILURE_ANALYSIS_PROMPT="""You are an expert DevOps engineer analyzing GitHub Actions workflow failures.

Analyze the following workflow failures and provide a structured classification.

## Workflow Information
- Run Number: {run_number}
- Workflow Name: {workflow_name}
- Branch: {branch}
- Conclusion: {conclusion}

## Error Logs
{logs}

## Task
Analyze this failure and respond with ONLY a valid JSON object (no markdown, no explanation):

{{
  "error_category":"<category>",
  "error_type":"<specific_type>",
  "severity":"<severity_level>",
  "root_cause":"<brief_description>",
  "affected_components":["<component1>","<component2>"],
  "is_flaky":<true or false>,
  "confidence_score":<0.0 to 1.0>,
  "suggested_fix":"<actionable_fix>",
  "reasoning":"<your_analysis>"
}}

### Categories (choose ONE):
- test_failure: Test case failing, assertion errors
- build_error: Compilation or build issue
- dependency_error: Missing or conflicting dependencies
- infrastructure_error: CI/CD infrastructure issues
- timeout_error: Process or test timeouts
- configuration_error: Misconfiguration in workflow or code
- network_error: Network connectivity issues
- permission_error: Access or permission denied
- environment_error: Environment setup issues
- unknown: Cannot determine from logs

### Severity Level (choose ONE):
- critical: Blocks all workflows, immediate action required
- high: Major feature broken, affects multiple areas
- medium: Single feature/test broken, workaround possible
- low: Minor issue, cosmetic or non-blocking

### Flaky Detection:
Set "is_flaky" to true ONLY if:
- Random timeouts without code changes
- Race conditions evident
- Timing-dependent failures
- Environmental inconsistencies visible

### Confidence:
Rate 0.0 (very uncertain) to 1.0 (very certain).

IMPORTANT: Return ONLY the JSON object. No markdown code blocks, no extra text.
"""

async def fetch_failure_logs(github: GitHubMCP,owner: str, repo: str, run_id:int)->str:
    try:
        logs_response=await github.get_run_logs(owner,repo,run_id)
        
        if logs_response.error:
            return f"[ERROR] {logs_response.error}"
        
        if logs_response.download_url:
            return f"[LOGS_AVAILABLE] Currently not going to be implemented.\n\nLogs are available on GitHub."
        
        return "[NO_LOGS] No logs available for this run"
    
    except Exception as e:
        logger.error(f"Error fetching logs:{e}")
        return f"[ERROR] Failed to fetch logs: {str(e)}"

def parse_ollama_response(response_text:str)->Dict[str,Any]:
    try:
        text=response_text.strip()

        if "```json" in text:
            s=text.find("``json")+7
            e=text.find("```",s)
            text=text[s:e].strip()
        elif "```" in text:
            s=text.find("```")+3
            e=text.find("```",s)
            text=text[s:e].strip()

        if "{" in text and "}" in text:
            s=text.find("{")
            e=text.find("}")
            text=text[s:e]
        
        parsed=json.loads(text)

        required_fields=[
            "error_category","error_type","severity",
            "root_cause","is_flaky","confidence_score"
        ]
        for field in required_fields:
            if field not in parsed:
                logger.warning(f"Missing field: {field}")
                parsed[field]="unknown" if field !="is_flaky" else False
                if field=="confidence_score":
                    parsed[field]=0.5
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.debug(f"Response text: {response_text}")

        return{
            "error_category":"unknown",
            "error_type":"parse_error",
            "severity":"medium",
            "root_cause":"Failed to parse LLM response",
            "affected_components":[],
            "is_flaky":False,
            "confidence_score":0.0,
            "suggested_fix":"Manual review required",
            "reasoning":f"Parse error: {str(e)}",
            "parse_error":True
        }  

async def analyze_failure_with_ollama(failure: Dict[str,Any],logs:str,client)->Dict[str,Any]:
    prompt=FAILURE_ANALYSIS_PROMPT.format(
        run_number=failure.get("run_number","N/A"),
        workflow_name=failure.get("name","Unknown"),
        branch=failure.get("head_branch","N/A"),
        conclusion=failure.get("conclusion","failure"),
        logs=logs[:6000]
    )

    try:
        logger.info(f"Analyzing failure #{failure.get('run_number')} with Ollama ({OLLAMA_MODEL})")

        messages=[
            {
                "role":"system",
                "content":"You are an expert DevOps engineer. Always respond with valid JSON only, no markdown."
            },
            {
                "role":"user",
                "content":prompt
            }
        ]
        response_text=client.chat(messages=messages,temperature=OLLAMA_TEMPERATURE,max_token=OLLAMA_MAX_TOKENS)

        analysis=parse_ollama_response(response_text)

        analysis["analyzed_at"]=datetime.now().isoformat()
        analysis["model_used"]=OLLAMA_MODEL
        analysis["run_id"]=failure.get("id")
        analysis["run_number"]=failure.get("run_number")

        logger.info(
            f"Analysis complete: {analysis.get('error_category')}"
            f"(confidence: {analysis.get('confidence_score',0):.2f})"
        )

        return analysis
    
    except Exception as e:
        logger.error(f"Ollama analysis failed: {e}")

        return{
            "error_category":"unknown",
            "error_type":"analysis_failed",
            "severity":"medium",
            "root_cause":f"Failed to analyze: {str(e)}",
            "affected_components":[],
            "is_flaky":False,
            "confidence_score":0.0,
            "suggested_fix":"Manual investigation required",
            "reasoning":f"Automatic analysis failed: {str(e)}",
            "analyzed_at":datetime.now().isoformat(),
            "run_id":failure.get("id"),
            "run_number":failure.get("run_number"),
            "error":str(e)
        }

async def failure_analysis_node(state:AgentState)->AgentState:
    logger.info("Starting failure analysis with Ollama")

    state.status="analyzing"
    state.current_task="Analyzing workflow failures with local AI"

    timestamp=datetime.now().isoformat()

    detected_failures=state.context.get("detected_failures",[])

    if not detected_failures:
        logger.info("No failures to analyze")
        state.memory.append(f"[{timestamp}] No failures to analyze")
        state.status="complete"
        return state

    logger.info(f"Analyzing {len(detected_failures)} failures")
    state.memory.append(f"[{timestamp}] Starting analysis of {len(detected_failures)} failures with Ollama")

    owner=state.context.get("owner")
    repo=state.context.get("repo")

    try:
        ollama_client=get_ollama_client()
        github=GitHubMCP()
    except Exception as e:
        error_msg=f"Failed to initialize clients: {e}"
        logger.error(error_msg)
        state.status="error"
        state.memory.append(f"[{timestamp}] ERROR: {error_msg}")
        state.context["last_error"]={
            "message":error_msg,
            "timestamp":timestamp
        }
        return state

    analyzed_failures=[]
    analysis_summary={
        "total_analyzed":0,
        "successful":0,
        "failed":0,
        "categories":{},
        "high_confidence":0,
        "flaky_tests":0
    }
    for i,failure in enumerate(detected_failures,1):
        run_id=failure.get("id")
        run_number=failure.get("run_number")

        logger.info(f"Analyzing failure {i}/{len(detected_failures)}: Run #{run_number}")
        state.current_task=f"Analyzing failure {i}/{len(detected_failures)} with Ollama"

        try:
            logs=await fetch_failure_logs(github, owner, repo, run_id)

            analysis=await analyze_failure_with_ollama(failure,logs,ollama_client)

            failure_with_analysis={
                **failure,
                "analysis":analysis
            }
            analyzed_failures.append(failure_with_analysis)

            analysis_summary["total_analyzed"]+=1

            if "error" not in analysis and not analysis.get("parse_error"):
                analysis_summary["successful"]+=1

                category=analysis.get("error_category","unknown")
                analysis_summary["categories"][category] /= analysis_summary["category"].get(category,0)+1

                if analysis.get("confidence_score",0)>=0.7:
                    analysis_summary["high_confidence"]+=1
                
                if analysis.get("is_flaky",False):
                    analysis_summary["flaky_tests"]+=1
                
            else:
                analysis_summary["failed"]+=1
            
            state.memory.append(
                f"[{timestamp}] Run #{run_number}: {analysis.get('error_category','unknown')}"
                f"- {analysis.get('root_cause','N/A')[:60]}"
            )

        except Exception as e:
            logger.error(f"Failed to analyze run #{run_number}: {e}")
            analysis_summary["failed"]+=1

            analyzed_failures.append({
                **failure,
                "analysis":{
                    "error":str(e),
                    "analyzed_at":timestamp
                }
            })
    state.context["analyzed_failures"]=analyzed_failures
    state.context["analysis_summary"]=analysis_summary
    state.context["last_analysis"]=timestamp

    state.status="analysis_complete"
    state.current_task=f"Analyzed {analysis_summary['successful']}/{analysis_summary["total_analyzed"]} failures successfully"

    state.memory.append(
        f"[{timestamp}] Analysis complete: "
        f"{analysis_summary['successful']} successful, "
        f"{analysis_summary['failed']} failed, "
        f"{analysis_summary['high_confidence']} high confidence"
    )

    logger.info(f"Analysis complete: {analysis_summary['successful']}/{analysis_summary['total_analyzed']} successful")
    state.last_updated=timestamp
    
    return state
            
    

