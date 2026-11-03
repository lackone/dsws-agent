from langgraph.runtime import Runtime

from app.agent.agent_context import DataAgentContext
from app.agent.agent_state import DataAgentState
import jieba.analyse

from app.core.log import logger


async def extract_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    writer = runtime.stream_writer
    writer("提取关键词")

    query = state["query"]

    # 只保留更可能承载业务含义的词性，减少“的、帮我、一下”这类无检索价值的噪声
    allow_pos = (
        "n",  # 名词: 商品、订单、销售额
        "nr",  # 人名: 张三、李四
        "ns",  # 地名: 华北、北京、上海
        "nt",  # 机构团体名: 门店、品牌、渠道
        "nz",  # 其他专有名词: SKU、GMV、AOV
        "v",  # 动词: 统计、对比、查询
        "vn",  # 名动词: 销售、成交、退款
        "a",  # 形容词: 新增、有效、活跃
        "an",  # 名形词: 可用、有效、异常
        "eng",  # 英文: GMV、SKU、ROI
        "i",  # 成语或习用语，避免遗漏整体表达
        "l",  # 常用固定短语，例如“销售总额”
    )

    # extract_tags 会基于 TF-IDF 抽取关键词，并按 allowPOS 做词性过滤
    keywords = jieba.analyse.extract_tags(query, allowPOS=allow_pos)

    # 保留原始问题作为兜底检索入口，避免关键词切分不准时丢掉完整语义
    keywords = list(set(keywords + [query]))
    logger.info(f"抽取关键词: {keywords}")
    return {"keywords": keywords}
