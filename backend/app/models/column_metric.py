from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ColumnMetricMySQL(Base):
    """字段与指标关联关系表对应的 ORM 模型"""

    __tablename__ = "column_metric"

    # 这里采用联合主键
    # 表示同一对 字段 指标 关系只允许出现一次
    column_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="列编号"
    )
    metric_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, comment="指标编号"
    )