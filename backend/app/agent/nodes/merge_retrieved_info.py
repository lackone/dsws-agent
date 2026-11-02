from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_state import DataAgentState


async def merge_retrieved_info(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("合并召回信息")
