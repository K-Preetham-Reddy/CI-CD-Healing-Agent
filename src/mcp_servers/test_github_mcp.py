import asyncio
import os
from dotenv import load_dotenv
from github_mcp import GitHubMCP

load_dotenv()

async def test_github_mcp():
    print("\n" + "="*60)
    print("GITHUB MCP SERVER - SIMPLE TESTS")
    print("="*60+"\n")
    OWNER="K-Preetham-Reddy"
    REPO="flaky-test-repo"

    try:
        github=GitHubMCP()
        print("Working\n")
    except ValueError as e:
        print(f"Error: {e}")
        print("Set GITHUB_TOKEN \n")
        return
    
    print("get_repo() test")
    try:
        repo=await github.get_repo(OWNER,REPO)
        print(f"{repo.full_name}")
        print(f"Stars: {repo.stars}, Forks: {repo.forks}\n")
    except Exception as e:
        print(f"Error:{e}\n")
    
    print("get_workflow_runs() test")
    try:
        runs=await github.get_workflow_runs(OWNER,REPO,per_page=3)
        print(f"Found {runs.total_count} total runs")
        if runs.workflow_runs:
            print(f"Latest: {runs.workflow_runs[0].name}\n")
        else:
            print("No workflow runs found\n")
    except Exception as e:
        print(f"Error:{e}\n")
    
    print("get_failed_runs() test")
    try:
        failed=await github.get_failed_runs(OWNER,REPO,limit=3)
        print(f"Found {failed.total_count} failed runs")
        if failed.failed_runs:
            print(f"First failed: {failed.failed_runs[0].name}\n")
        else:
            print("No failed runs\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    run_id=None
    try:
        runs=await github.get_workflows_runs(OWNER,REPO,per_page=1)
        if runs.workflow_runs:
            run_id=runs.workflow_runs[0].id
    except:
        pass

    print("get_run_status() test")
    if run_id:
        try:
            status=await github.get_run_status(OWNER,REPO,run_id)
            print(f"Run #{status.run_number}: {status.status}\n")
        except Exception as e:
            print(f"Error: {e}\n")
    else:
        print(" Skipped (No runs available)\n")
    
    print("get_run_logs() test")
    if run_id:
        try:
            logs=await github.get_run_logs(OWNER,REPO,run_id)
            print(f"{logs.message}")
            if logs.download_url:
                print(f"URL available\n")
            elif logs.error:
                print(f"{logs.error}\n")
        except Exception as e:
            print(f"Error: {e}\n")
    else:
        print(" Skipped (No runs available)\n")
    
    print("get_rate_limit() test")
    try:
        rate=await github.get_rate_limit()
        print(f"Rate limit: {rate.remaining}/{rate.limit} remaing\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    print("rerun_workflow() test")
    print("Won't be triggered for testing, will be implemented later on\n")


    print("="*60)
    print("TESTS COMPLETE")
    print("="*60+"\n")
    
if __name__=="__main__":
    asyncio.run(test_github_mcp())