import uuid
from dataclasses import asdict
from pathlib import Path

from omegaconf import OmegaConf

from app.conf.meta import MetaConfig
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.entities.value_info import ValueInfo
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from langchain_core.embeddings import Embeddings

from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class MetaKnowledgeService:
    def __init__(self,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 column_qdrant_repository: ColumnQdrantRepository,
                 embedding_client: Embeddings,
                 value_es_repository: ValueESRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 ):
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.column_qdrant_repository = column_qdrant_repository
        self.embedding_client = embedding_client
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository

    async def build(self, config_path: Path):
        # 1、读取配置文件
        context = OmegaConf.load(config_path)
        schema = OmegaConf.structured(MetaConfig)
        meta_config: MetaConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
        logger.info("加载配置文件")

        if meta_config.tables:
            # 将表信息和字段信息保存到 Meta MySQL
            column_infos = await self._save_tables_to_meta_db(meta_config)
            logger.info("保存表信息和字段信息到 Meta MySQL")

            # 对字段信息建立向量索引
            await self._save_column_info_to_qdrant(column_infos)
            logger.info("为字段信息建立向量索引")

            # 对指定的维度字段取值建立全文索引
            await self._save_value_info_to_es(meta_config, column_infos)
            logger.info("为字段取值建立全文索引")

        if meta_config.metrics:
            # 将指标信息和字段依赖关系保存到 Meta MySQL
            metric_infos = await self._save_metrics_to_meta_db(meta_config)
            logger.info("保存指标信息到数据库成功")

            # 对指标信息建立向量索引
            await self._save_metrics_to_qdrant(metric_infos)
            logger.info("为指标信息建立向量索引成功")

    async def _save_column_info_to_qdrant(self, column_infos: list[ColumnInfo]):
        """把字段元数据继续推进成可语义检索的 Qdrant 向量点"""
        await self.column_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for column_info in column_infos:
            # 一个字段不会只生成一个向量点，而是把名字 描述 别名都拆开建立语义入口
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.name,
                    "payload": asdict(column_info),
                }
            )

            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": column_info.description,
                    "payload": asdict(column_info),
                }
            )

            for alia in column_info.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alia,
                        "payload": asdict(column_info),
                    }
                )

        # 先把待向量化文本抽出来，再分批调用 Embedding 服务
        # 这样更容易控制单次请求大小
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        embedding_batch_size = 20
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i: i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(
                batch_embedding_texts
            )
            embeddings.extend(batch_embeddings)

        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]

        await self.column_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_value_info_to_es(
            self, meta_config: MetaConfig, column_infos: list[ColumnInfo]
    ):
        """把允许同步的字段真实取值写入 Elasticsearch 全文索引"""
        await self.value_es_repository.ensure_index()

        # 不是所有字段都要同步真实值，是否同步由配置里的 sync 显式控制
        column2sync: dict[str, bool] = {}
        for table in meta_config.tables:
            for column in table.columns:
                column2sync[f"{table.name}.{column.name}"] = column.sync

        value_infos: list[ValueInfo] = []
        for column_info in column_infos:
            sync = column2sync[column_info.id]
            if sync:
                # 这里拿的是字段真实值全集，不再是第 8 章里的少量 examples
                current_column_values = (
                    await self.dw_mysql_repository.get_column_values(
                        column_info.table_id, column_info.name, 100000
                    )
                )
                current_values_infos = [
                    ValueInfo(
                        id=f"{column_info.id}.{current_column_value}",
                        value=current_column_value,
                        column_id=column_info.id,
                    )
                    for current_column_value in current_column_values
                ]
                value_infos.extend(current_values_infos)

        await self.value_es_repository.index(value_infos)

    async def _save_metrics_to_meta_db(
            self, meta_config: MetaConfig
    ) -> list[MetricInfo]:
        """把配置里的指标信息和字段依赖关系写入 Meta MySQL"""
        metric_infos: list[MetricInfo] = []
        column_metrics: list[ColumnMetric] = []

        for metric in meta_config.metrics:
            # MetricInfo 表达指标本身，当前直接用指标名作为稳定业务 id
            metric_info = MetricInfo(
                id=metric.name,
                name=metric.name,
                description=metric.description,
                relevant_columns=metric.relevant_columns,
                alias=metric.alias,
            )
            metric_infos.append(metric_info)
            for column in metric.relevant_columns:
                # ColumnMetric 单独表达“某个指标依赖某个字段”这层关系
                column_metric = ColumnMetric(column_id=column, metric_id=metric.name)
                column_metrics.append(column_metric)

        # 指标本身和字段关系要放在同一笔事务里，避免只写入其中一部分
        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_metric_infos(metric_infos)
            self.meta_mysql_repository.save_column_metrics(column_metrics)

        return metric_infos

    async def _save_metrics_to_qdrant(self, metric_infos: list[MetricInfo]):
        """把指标元数据继续推进成可语义检索的 Qdrant 向量点"""
        await self.metric_qdrant_repository.ensure_collection()

        points: list[dict] = []
        for metric_info in metric_infos:
            # 和字段一样，一个指标也会拆成名字 描述 别名这几类语义入口
            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.name,
                    "payload": asdict(metric_info),
                }
            )

            points.append(
                {
                    "id": uuid.uuid4(),
                    "embedding_text": metric_info.description,
                    "payload": asdict(metric_info),
                }
            )

            for alia in metric_info.alias:
                points.append(
                    {
                        "id": uuid.uuid4(),
                        "embedding_text": alia,
                        "payload": asdict(metric_info),
                    }
                )

        # 先把待向量化文本抽出来，再分批调用 Embedding 服务
        # 返回的 embeddings 要继续和前面的 id payload 按顺序对齐
        embeddings: list[list[float]] = []
        embedding_texts = [point["embedding_text"] for point in points]
        embedding_batch_size = 20
        for i in range(0, len(embedding_texts), embedding_batch_size):
            batch_embedding_texts = embedding_texts[i: i + embedding_batch_size]
            batch_embeddings = await self.embedding_client.aembed_documents(
                batch_embedding_texts
            )
            embeddings.extend(batch_embeddings)

        ids = [point["id"] for point in points]
        payloads = [point["payload"] for point in points]

        await self.metric_qdrant_repository.upsert(ids, embeddings, payloads)

    async def _save_tables_to_meta_db(self, meta_config: MetaConfig):
        table_infos: list[TableInfo] = []
        column_infos: list[ColumnInfo] = []

        for table in meta_config.tables:
            table_info = TableInfo(
                id=table.name,
                name=table.name,
                role=table.role,
                description=table.description,
            )
            table_infos.append(table_info)

            # 从 DW 中获取表的列类型
            column_types: dict[str, str] = await self.dw_mysql_repository.get_column_types(
                table.name
            )
            # 从 DW 中获取表的列值
            for column in table.columns:
                column_values: list = await self.dw_mysql_repository.get_column_values(
                    table.name, column.name, 10
                )
                column_info = ColumnInfo(
                    id=f"{table.name}.{column.name}",
                    name=column.name,
                    type=column_types[column.name],
                    role=column.role,
                    examples=column_values,
                    description=column.description,
                    alias=column.alias,
                    table_id=table.name,
                )
                column_infos.append(column_info)

        async with self.meta_mysql_repository.session.begin():
            self.meta_mysql_repository.save_table_infos(table_infos)
            self.meta_mysql_repository.save_column_infos(column_infos)

        return column_infos
