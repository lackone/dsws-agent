import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_llm import llm
from app.agent.agent_state import DataAgentState, MetricInfoState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    step = "过滤指标信息"
    writer({"type": "progress", "step": step, "status": "running"})

    try:
        query = state["query"]
        metric_infos: list[MetricInfoState] = state["metric_infos"]

        # metric_infos 转成 YAML 后作为候选项交给模型，模型只需要返回被选中的指标名称
        prompt = PromptTemplate(
            template=load_prompt("filter_metric_info"),
            input_variables=["query", "metric_infos"],
        )

        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {
                "query": query,
                "metric_infos": yaml.dump(
                    metric_infos, allow_unicode=True, sort_keys=False
                ),
            }
        )

        # 用模型返回的指标名称过滤原始结构，保留描述 依赖字段 别名等完整上下文
        filtered_metric_infos = [
            metric_info for metric_info in metric_infos if metric_info["name"] in result
        ]

        logger.info(
            f"过滤后的指标信息：{[filtered_metric_info['name'] for filtered_metric_info in filtered_metric_infos]}"
        )

        writer({"type": "progress", "step": step, "status": "success"})

        return {"metric_infos": filtered_metric_infos}

    except Exception as e:
        logger.error(f"{step} failed: {e}")
        writer({"type": "progress", "step": step, "status": "error"})
        raise