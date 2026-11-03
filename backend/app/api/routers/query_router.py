import asyncio

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from app.api.deps import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.services.query_service import QueryService

# 当前模块只负责查询相关接口，后续接口变多时可以继续拆分其他 router
query_router = APIRouter()


async def fake_streamer():
    # 先用 10 个 step 模拟智能体执行过程，方便验证流式响应是否可用
    for i in range(10):
        # 暂停 1 秒只是为了观察流式效果；真实项目中这里会被节点执行耗时代替
        await asyncio.sleep(1)

        # SSE 消息以 data: 开头，并以两个换行符结尾
        # 客户端会把每次 yield 的内容识别为一条独立事件
        yield f"data: step:{i}\n\n"


# @query_router.post("/api/query")
# async def query_handler(query: QuerySchema):
#     # query 参数会由 FastAPI 根据请求体自动解析成 QuerySchema 对象
#     # StreamingResponse 会把 fake_streamer() 每次 yield 的内容持续写给客户端
#     return StreamingResponse(fake_streamer(), media_type="text/event-stream")


@query_router.post("/api/query")
async def query_handler(
        # FastAPI 会把前端 JSON 请求体自动解析成 QuerySchema
        query: QuerySchema,
        # FastAPI 会调用 get_query_service，递归组装它依赖的仓储和客户端
        query_service: QueryService = Depends(get_query_service),
):
    return StreamingResponse(
        # query.query 是用户问题字符串；QueryService.query 返回异步生成器
        query_service.query(query.query),
        media_type="text/event-stream",
    )
