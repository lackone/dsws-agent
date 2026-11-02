from typing import TypedDict


class DataAgentState(TypedDict):
    query: str # 用户查询
    error: str # 错误信息
