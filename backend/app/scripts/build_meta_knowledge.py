import asyncio
from argparse import ArgumentParser
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.models.base import Base
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


async def initDB(engine: AsyncEngine):
    from app.models.column_info import ColumnInfoMySQL
    from app.models.table_info import TableInfoMySQL
    from app.models.metric_info import MetricInfoMySQL
    from app.models.column_metric import ColumnMetricMySQL

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def build(config_path: Path):
    # 1、初始化 MySQL 客户端管理器
    meta_mysql_client_manager.init()
    dw_mysql_client_manager.init()

    qdrant_client_manager.init()
    embedding_client_manager.init()
    es_client_manager.init()

    await initDB(meta_mysql_client_manager.engine)

    # 2、创建数据库会话
    async with(
        meta_mysql_client_manager.session_factory() as meta_session,
        dw_mysql_client_manager.session_factory() as dw_session,
    ):
        # 3. 创建 repository 对象
        meta_mysql_repository = MetaMySQLRepository(meta_session)
        dw_mysql_repository = DWMySQLRepository(dw_session)

        # 字段语义召回写入 Qdrant
        column_qdrant_repository = ColumnQdrantRepository(qdrant_client_manager.client)

        # 字段真实值匹配写入 ES
        value_es_repository = ValueESRepository(es_client_manager.client)

        # 指标语义召回写入独立的 Qdrant collection
        metric_qdrant_repository = MetricQdrantRepository(qdrant_client_manager.client)

        embedding_client = embedding_client_manager.client

        # 4. 创建 service 对象，并把 repository 注入进去
        meta_knowledge_service = MetaKnowledgeService(
            meta_mysql_repository=meta_mysql_repository,
            dw_mysql_repository=dw_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            embedding_client=embedding_client,
            value_es_repository=value_es_repository,
            metric_qdrant_repository=metric_qdrant_repository,
        )

        # 5. 真正进入服务层的构建逻辑
        await meta_knowledge_service.build(config_path)

    # 关闭数据库会话
    await meta_mysql_client_manager.close()
    await dw_mysql_client_manager.close()


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-c", "--conf", help="meta配置文件路径")
    args = parser.parse_args()

    asyncio.run(build(config_path=Path(args.conf)))
