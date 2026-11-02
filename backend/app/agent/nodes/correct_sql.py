from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_state import DataAgentState


async def correct_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("修正SQL语句")
