from pydantic import BaseModel
from typing import List,Dict,Any,Optional
class AgentState(BaseModel):
    id:str
    name:str
    role:str
    status:str
    memory:List[str]
    goals:List[str]
    current_task:Optional[str]=None
    sub_tasks:List[str]
    context:Dict[str,Any]
    last_updated:str


