from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_llm import llm
from app.agent.agent_state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "召回字段信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        keywords = state["keywords"]
        query = state["query"]

        column_qdrant_repository = runtime.context["column_qdrant_repository"]
        embedding_client = runtime.context["embedding_client"]

        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )

        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        # 原始关键词和 LLM 扩展词一起参与召回；set 去重，避免重复请求同一关键词
        keywords = set(keywords + result)

        column_info_map: dict[str, ColumnInfo] = {}

        for keyword in keywords:
            # 查询词必须先转成向量，才能和第 9 章写入 Qdrant 的字段向量做相似度检索
            embedding = await embedding_client.aembed_query(keyword)

            current_column_infos: list[ColumnInfo] = await column_qdrant_repository.search(embedding)

            for column_info in current_column_infos:
                if column_info.id not in column_info_map:
                    column_info_map[column_info.id] = column_info

        # 写回 state 的是去重后的 ColumnInfo 列表，不暴露 Qdrant 原始 point 结构
        retrieved_column_infos: list[ColumnInfo] = list(column_info_map.values())

        logger.info(f"检索到字段信息：{list(column_info_map.keys())}")

        writer({"type": "progress", "step": step, "status": "success"})

        return {"retrieved_column_infos": retrieved_column_infos}
    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise
