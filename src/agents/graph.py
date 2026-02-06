from langgraph.graph import StateGraph, END
from typing import Dict, Any
import logging
from datetime import datetime

from src.agents.state import AgentState
from src.agents.nodes.start_node import start_node
from src.agents.nodes.github_monitor_node import github_monitor_node
from src.agents.nodes.analysis_node import failure_analysis_node

logging.basicConfig(level=logging.INFO)
logger=logging.getLogger("AgentGraph")

class AgentWorkflowGraph:
    def __init__(self):
        self.graph=StateGraph(AgentState)
        self._build_graph()
        self.app=None
        logger.info("AgentWorkflowGraph initialized")

    def _build_graph(self):
        self.graph.add_node("start",start_node)
        self.graph.add_node("github_monitor",github_monitor_node)
        self.graph.add_node("analysis",failure_analysis_node)

        self.graph.set_entry_point("start")
        self.graph.add_edge("start","github_monitor")

        self.graph.add_conditional_edges(
            "github_monitor",
            self._route_after_monitor,
            {
                "continue":"github_monitor",
                "end":END
            }
        )
        logger.info("Graph structure built successfully")
    
    def _route_after_monitor(self,state:AgentState)->str:
        failures=state.context.get("detected_failures",[])

        if failures:
            logger.info(f"Detected {len(failures)} failures - ending workflow")
        else:
            logger.info("No failures detected - ending workflow")
        return "end"

    def compile(self):
        if self.app is None:
            self.app=self.graph.compile()
            logger.info("Graph compiled successully")
        return self.app
    
    def visualize(self,output_path:str = "agent_graph.png"):
        try:
            from IPython.display import Image

            graph_image=self.app.get_graph().draw_mermaid_png()

            with open(output_path,"wb") as f:
                f.write(graph_image)
            
            logger.info(f"Graph visualization saved to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to generate visualization: {e}")
            logger.info(f"Install requrired packages")
            return None
    
    async def execute(self, initial_state: Dict[str,Any])->AgentState:
        if self.app is None:
            self.compile()
        
        logger.info("Starting graph execution")

        if not isinstance(initial_state,AgentState):
            state=AgentState(**initial_state)
        else:
            state=initial_state

        result=await self.app.ainvoke(state)

        logger.info("Graph execution completed")

        if isinstance(result,dict):
            return AgentState(**result)
        return result
    
    def execute_sync(self,initial_state:Dict[str,Any])->AgentState:
        if self.app is None:
            self.compile()
        logger.info("Sync graph exec")
        if not isinstance(initial_state,AgentState):
            state=AgentState(**initial_state)
        else:
            state=initial_state
        
        result=self.app.invoke(state)

        logger.info("Graph execution completed")
        if isinstance(result,dict):
            return AgentState(**result)
        return result

def create_agent_graph()->AgentWorkflowGraph:
    graph=AgentWorkflowGraph()
    graph.compile()
    return graph

if __name__=="main":
    print("AgentWorkflowGraph module")
    print("Run test_graph.py for test")
    
    