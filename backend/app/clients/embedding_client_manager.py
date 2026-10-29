import asyncio
from typing import Optional

from app.conf.config import EmbeddingConfig, LocalEmbeddingConfig, app_config

from huggingface_hub import AsyncInferenceClient, InferenceClient
from langchain_core.embeddings import Embeddings
from langchain_huggingface import HuggingFaceEndpointEmbeddings


class LocalEmbeddings(Embeddings):
    """
    本地 Embedding 客户端：在进程内直接跑模型，不经过 HTTP 接口。
    """

    def __init__(self, model: str, device: str, cache_dir: str):
        # 延迟导入，未启用本地模式时不必安装该依赖
        from sentence_transformers import SentenceTransformer

        # 传入模型 ID 时框架会自动下载权重, cache_dir 指定权重缓存目录
        # 后续再次加载会直接命中缓存, 无需重复下载
        self.model = SentenceTransformer(model, device=device, cache_folder=cache_dir)

    def _encode(self, texts):
        # 归一化后输出为普通 list，便于写入向量库
        return self.model.encode(texts, normalize_embeddings=True).tolist()

    def embed_documents(self, texts):
        # 批量文本向量化
        return self._encode(list(texts))

    def embed_query(self, text):
        # 单条查询向量化
        return self._encode([text])[0]

    async def aembed_documents(self, texts):
        # 推理是阻塞操作，放到线程池执行
        return await asyncio.to_thread(self.embed_documents, texts)

    async def aembed_query(self, text):
        # 推理是阻塞操作，放到线程池执行
        return await asyncio.to_thread(self.embed_query, text)


class EmbeddingClientManager:
    def __init__(self, config: EmbeddingConfig, local_config: LocalEmbeddingConfig):
        # 客户端在模块导入阶段先不立即创建，避免启动时就发起外部依赖连接
        self.client: Optional[Embeddings] = None
        # 保存 Embedding 服务配置，供 init() 时组装服务访问地址使用
        self.config = config
        # 保存本地 Embedding 配置，决定是否切换到本地模型
        self.local_config = local_config

    def _get_url(self):
        # 当前项目通过 host + port 访问外部已启动的 Embedding 推理服务
        return f"http://{self.config.host}:{self.config.port}"

    def init(self):
        # 在应用启动阶段显式调用，完成真正的客户端初始化
        # 本地模式开启时，直接加载本地模型，完全不访问远程接口
        if self.local_config.enable:
            self.client = LocalEmbeddings(
                self.config.model,
                self.local_config.device,
                self.local_config.cache_dir,
            )
            return

        # LangChain 的 model 参数使用模型 ID，本地 TEI 地址交给底层推理客户端
        self.client = HuggingFaceEndpointEmbeddings(model=self.config.model)
        endpoint_url = f"{self._get_url()}/embed"
        self.client.client = InferenceClient(model=endpoint_url)
        self.client.async_client = AsyncInferenceClient(model=endpoint_url)


# 初始化 Embedding 客户端管理器
embedding_client_manager = EmbeddingClientManager(app_config.embedding, app_config.local_embedding)

if __name__ == "__main__":
    # 本地调试入口：初始化客户端后执行一次最小化向量化调用
    embedding_client_manager.init()

    client = embedding_client_manager.client


    async def test():
        # 使用示例文本验证 Embedding 服务是否可正常响应
        text = "你好，我是中国人的?"
        query_result = await client.aembed_query(text)
        # 只打印维度数与前 3 个数值，便于快速确认返回结果结构正确
        print(len(query_result), query_result[:3])


    # 运行调试测试
    asyncio.run(test())
