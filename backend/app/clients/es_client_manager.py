import asyncio
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.conf.config import ESConfig, app_config


# index	一组同类文档的逻辑容器
# document	index 中的一条 JSON 文档
# field	document 中的一个字段
# mapping	定义字段结构、字段类型以及索引行为

# MySQL	表 -> 行 -> 列
# Qdrant	collection -> point -> vector / payload
# Elasticsearch	index -> document -> field

# mapping 本质是 Elasticsearch 里的“表结构说明”。

# text 和 keyword 区别
# text 类型更偏全文检索。
# keyword 更偏精确匹配。

class ESClientManager:
    def __init__(self, es_config: ESConfig):
        # 保存 ES 配置对象，后面初始化客户端时会从这里读取 host 和 port
        self.es_config = es_config
        # 先把 client 声明出来，真正初始化放到 init() 中进行
        self.client: Optional[AsyncElasticsearch] = None

    def _get_url(self):
        # 根据配置文件拼出 ES 服务地址
        return f"http://{self.es_config.host}:{self.es_config.port}"

    def init(self):
        # 创建异步 ES 客户端
        # hosts 之所以是列表，是为了兼容 ES 常见的集群连接方式
        self.client = AsyncElasticsearch(hosts=[self._get_url()])

    async def close(self):
        # 在程序退出时统一关闭客户端连接
        await self.client.close()


# 创建一个全局可复用的 ES 客户端管理器对象
es_client_manager = ESClientManager(app_config.es)

if __name__ == "__main__":
    es_client_manager.init()


    async def test():
        client = es_client_manager.client

        # 创建测试索引
        await client.indices.create(
            index="test_index",
            mappings={
                "dynamic": False,  # 关闭动态映射，防止未知字段导致索引结构变化
                "properties": {
                    "name": {"type": "text"},
                    "author": {"type": "text"},
                    "release_date": {"type": "date", "format": "yyyy-MM-dd"},
                    "page_count": {"type": "integer"},
                }
            }
        )

        await client.bulk(
            operations=[
                {"index": {"_index": "test_index"}},
                {
                    "name": "Revelation Space",
                    "author": "Alastair Reynolds",
                    "release_date": "2000-03-15",
                    "page_count": 585,
                },
                {"index": {"_index": "test_index"}},
                {
                    "name": "1984",
                    "author": "George Orwell",
                    "release_date": "1985-06-01",
                    "page_count": 328,
                },
                {"index": {"_index": "test_index"}},
                {
                    "name": "Fahrenheit 451",
                    "author": "Ray Bradbury",
                    "release_date": "1953-10-15",
                    "page_count": 227,
                },
                {"index": {"_index": "test_index"}},
                {
                    "name": "Brave New World",
                    "author": "Aldous Huxley",
                    "release_date": "1932-06-01",
                    "page_count": 268,
                },
                {"index": {"_index": "test_index"}},
                {
                    "name": "The Handmaids Tale",
                    "author": "Margaret Atwood",
                    "release_date": "1985-06-01",
                    "page_count": 311,
                },
            ]
        )

        res = await client.search(
            index="test_index",
            query={"match": {"name": "brave"}}
        )

        print(res)

        # 关闭客户端连接

        await es_client_manager.close()


    # 运行测试
    asyncio.run(test())
