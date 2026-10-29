import asyncio
import random
from typing import Optional

from qdrant_client import AsyncQdrantClient, models

from app.conf.config import QdrantConfig, app_config


# collection	一组向量点的集合，可以类比成“同类向量的一张表”
# point	集合中的一条记录
# vector	这条记录对应的向量
# payload	跟着向量一起保存的业务字段
# distance	用什么方式比较“像不像”

class QdRantClientManager:
    def __init__(self, qdrant_client: QdrantConfig):
        """ 保存配置对象，后面初始化客户端时要从这里读取 host 和 port """
        self.qdrant_client = qdrant_client
        self.client: Optional[AsyncQdrantClient] = None

    def _get_url(self):
        """ 根据配置文件拼出 Qdrant 服务地址 """
        return f"http://{self.qdrant_client.host}:{self.qdrant_client.port}"

    def init(self):
        """ 创建异步客户端 """
        self.client = AsyncQdrantClient(self._get_url())

    async def close(self):
        """ 关闭异步客户端连接 """
        await self.client.close()


# 创建一个全局的管理器对象
qdrant_client_manager = QdRantClientManager(app_config.qdrant)

if __name__ == '__main__':
    qdrant_client_manager.init()


    async def test():
        client = qdrant_client_manager.client

        # 创建测试集合
        if not await client.collection_exists("test_collection"):
            await client.create_collection(
                collection_name="test_collection",
                vectors_config=models.VectorParams(
                    size=10,
                    distance=models.Distance.COSINE
                )
            )

        # 插入测试数据
        await client.upsert(
            collection_name="test_collection",
            points=[
                models.PointStruct(
                    id=i,
                    vector=[random.random() for _ in range(10)],
                )
                for i in range(100)
            ]
        )

        # 查询测试数据
        res = await client.query_points(
            collection_name="test_collection",
            query=[random.random() for _ in range(10)],
            limit=10,
            score_threshold=0.6,  # 只返回相似度大于 0.6 的点
        )

        # 打印查询结果
        print(res)

        # 关闭客户端连接
        await qdrant_client_manager.close()


    # 运行测试
    asyncio.run(test())
