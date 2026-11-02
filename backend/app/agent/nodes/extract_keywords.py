from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_state import DataAgentState


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("提取关键词")

