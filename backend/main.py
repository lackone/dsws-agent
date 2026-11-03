import uuid

from fastapi import FastAPI, Request

from app.api.lifespan import lifespan
from app.api.routers.query_router import query_router
from app.core.context import request_id_ctx_var

# 创建 FastAPI 应用对象，后续所有路由、中间件、生命周期事件都会注册到 app 上
app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    # 返回普通 dict 时，FastAPI 会自动把它序列化成 JSON 响应
    return {"status": "ok"}


app.include_router(query_router)

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    # 请求被处理之前，先为当前请求生成一个唯一 ID
    request_id = uuid.uuid4()

    # 写入当前异步上下文，后续业务日志会从这里取 request_id
    request_id_ctx_var.set(request_id)

    # 继续执行后续路由处理逻辑
    response = await call_next(request)

    # 请求被处理之后，返回响应
    return response