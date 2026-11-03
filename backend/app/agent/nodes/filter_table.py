import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_llm import llm
from app.agent.agent_state import DataAgentState, TableInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "过滤表信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        table_infos: list[TableInfoState] = state["table_infos"]

        # table_infos 是嵌套结构，转成 YAML 后更适合放进提示词，也保留中文字段说明
        prompt = PromptTemplate(
            template=load_prompt("filter_table_info"),
            input_variables=["query", "table_infos"],
        )

        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "table_infos": yaml.dump(
                    table_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )

        # 模型只负责选择，程序根据选择结果从原始 TableInfoState 中裁剪，避免模型重写复杂结构出错

        filtered_table_infos: list[TableInfoState] = []
        for table_info in table_infos:
            if table_info["name"] in result:
                table_info["columns"] = [
                    column_info
                    for column_info in table_info["columns"]
                    if column_info["name"] in result[table_info["name"]]
                ]
                filtered_table_infos.append(table_info)

        logger.info(
            f"过滤后的表信息：{[filtered_table_info['name'] for filtered_table_info in filtered_table_infos]}"
        )

        writer({"type": "progress", "step": step, "status": "success"})

        return {"table_infos": filtered_table_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise