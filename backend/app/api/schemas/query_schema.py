from pydantic import BaseModel


class QuerySchema(BaseModel):
    # 前端请求体中的 query 字段，用来承载用户输入的自然语言问题
    query: str