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
    REPO="ExpressionTracker-Sentiment-Analysis-for-Dyslexic-Kids-During-Gameplay"

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
    
if __name__=="__main__":
    asyncio.run(test_github_mcp())