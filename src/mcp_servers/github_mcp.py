from mcp.server.fastmcp import FastMCP
import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from dotenv import load_dotenv
import os
from datetime import datetime
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GitHubMCP")


class RepoInfo(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool
    stars: int = Field(alias="stargazers_count")
    forks: int = Field(alias="forks_count")
    open_issues: int = Field(alias="open_issues_count")
    default_branch: str
    language: Optional[str] = None
    created_at: str
    updated_at: str
    url: str = Field(alias="html_url")

    class Config:
        populate_by_name = True


class WorkflowRun(BaseModel):
    id: int
    run_number: int
    name: str
    head_branch: str
    head_sha: str
    status: str
    conclusion: Optional[str] = None
    created_at: str
    updated_at: str
    url: str = Field(alias="html_url")

    class Config:
        populate_by_name = True


class WorkflowRunsResponse(BaseModel):
    total_count: int
    workflow_runs: List[WorkflowRun]


class FailedRunsResponse(BaseModel):
    total_count: int
    failed_runs: List[WorkflowRun] 


class RunStatus(BaseModel):
    id: int
    name: str
    head_branch: str
    status: str
    conclusion: Optional[str] = None
    run_number: int
    event: str
    created_at: str
    updated_at: str
    run_started_at: Optional[str] = None
    url: str = Field(alias="html_url")
    jobs_url: str
    logs_url: str
    
    class Config:
        populate_by_name = True


class LogsResponse(BaseModel):
    download_url: Optional[str] = None
    message: str
    error: Optional[str] = None


class RerunResponse(BaseModel):
    success: bool
    message: str
    run_id: int
    failed_jobs_only: bool


class RateLimitStatus(BaseModel):
    limit: int
    remaining: int
    used: int
    reset: str
    reset_in_seconds: float


class RateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded"""
    pass


class GitHubMCP:
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("Provide proper GITHUB_TOKEN")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitHub-MCP-Server/1.0"
        }
        logger.info("GitHubMCP initialized successfully")

    def _check_rate_limit(self, response: httpx.Response) -> None:
        remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
        if remaining == 0:
            reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
            reset_time = datetime.fromtimestamp(reset_timestamp)
            raise RateLimitError(
                f"GitHub API rate limit exceeded. Resets at {reset_time}"
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30.0
            )
            self._check_rate_limit(response)
            
            if response.status_code == 404:
                raise ValueError(f"Resource not found: {endpoint}")
            elif response.status_code == 403:
                raise RateLimitError("Access forbidden or rate limit exceeded")
            
            response.raise_for_status()
            return response.json()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPStatusError),
        reraise=True
    )
    async def _post(self, endpoint: str, json_data: Optional[dict] = None) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=json_data,
                timeout=30.0
            )
            self._check_rate_limit(response)
            response.raise_for_status()
            
            if response.status_code == 204:
                return {}
            return response.json() if response.content else {}
        
    async def get_repo(self, owner: str, repo: str) -> RepoInfo:
        logger.info(f"Fetching repo: {owner}/{repo}")
        data = await self._get(f"repos/{owner}/{repo}")
        return RepoInfo(**data)

    async def get_workflow_runs(self,owner:str,repo:str,branch:str="main",status:Optional[str]=None,per_page:int=30,page:int=1)->WorkflowRunsResponse:
        logger.info(f"Fetching workflow runs: {owner}/{repo}")
        params={"per_page":min(per_page,100),"page":page}
        if branch:
            params["branch"]=branch
        if status:
            params["status"]=status
        
        data=await self._get(f"repos/{owner}/{repo}/actions/runs",params=params)
        return WorkflowRunsResponse(**data)

    async def get_failed_runs(self,owner:str,repo:str,branch: str="main",limit:Optional[int]=None)->FailedRunsResponse:
        logger.info(f"Fetching failed runs:{owner}/{repo}")
        failed_runs=[]
        page=1
        per_page=100

        while True:
            response=await self.get_workflow_runs(owner,repo,branch,status="completed",per_page=per_page,page=page)
            for run in response.workflow_runs:
                if run.conclusion=="failure":
                    failed_runs.append(run)
                    if limit and len(failed_runs)>=limit:
                        return FailedRunsResponse(
                            total_count=len(failed_runs),
                            failed_runs=failed_runs
                        )
            if len(response.workflow_runs)<per_page:
                break
            page+=1
        
        return FailedRunsResponse(total_count=len(failed_runs),failed_runs=failed_runs)
    
    async def get_run_logs(self,owner:str,repo:str,run_id:int)->LogsResponse:
        logger.info(f"Fetching logs for run {run_id}")
        endpoint=f"repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        url=f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response=await client.get(url,headers=self.headers,follow_redirects=False,timeout=30.0)
            if response.status_code==302:
                download_url=response.headers.get("Location")
                return LogsResponse(download_url=download_url,message="Use this URL to download the logs zp file")
            elif response.status_code==410:
                return LogsResponse(message="Logs unavailable",error="Logs have expired(logs are only kept for 90 days)")
            else:
                response.raise_for_status()
                return LogsResponse(message="Unexpected response")



mcp = FastMCP("github-mcp-server")
github = GitHubMCP(token=os.getenv("GITHUB_TOKEN"))


@mcp.tool()
async def get_repo(owner: str, repo: str) -> RepoInfo:
    """Get repository information"""
    return await github.get_repo(owner, repo)

@mcp.tool()
async def get_workflow_runs(owner:str,repo:str,branch:Optional[str]=None,status:Optional[str]=None,per_page:int=30,page:int=1)->WorkflowRunsResponse:
    return await github.get_workflow_runs(owner,repo,branch,status,per_page,page)

if __name__ == "__main__":
    logger.info("Starting GitHub MCP Server...")
    mcp.run()