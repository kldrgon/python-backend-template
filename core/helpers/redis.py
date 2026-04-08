import asyncio
from redis.asyncio.client import Redis


from contextvars import ContextVar, Token
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator
from redis import asyncio as redis

from core.config import config
_redis_url = None
if config.redis.password:
    _redis_url = f"redis://:{config.redis.password}@{config.redis.host}:{config.redis.port}/{config.redis.db}"
else:
    _redis_url = f"redis://{config.redis.host}:{config.redis.port}/{config.redis.db}"

# 为不同的进程上下文存储 Redis 客户端
# - FastAPI 主进程: 使用 _default_redis_client
# - Celery Worker 进程: 使用通过 init_redis_for_celery_worker() 创建的独立客户端
# 
# 为什么需要分离？
# 1. Celery 使用 prefork 模式时，worker 进程是从主进程 fork 出来的
# 2. Redis 连接池（socket 文件描述符、锁等）不能安全地在 fork 之间共享
# 3. 每个 worker 进程必须创建自己的客户端和连接池
_redis_client_context: ContextVar[redis.Redis | None] = ContextVar[redis.Redis | None]("_redis_client_context", default=None)

# 任务级别的 Redis 客户端（用于 Windows + asyncio.run 场景）
_task_redis_client: ContextVar[redis.Redis | None] = ContextVar[redis.Redis | None]("_task_redis_client", default=None)

# 默认全局客户端（FastAPI 使用）
_default_redis_client = redis.from_url(url=_redis_url, decode_responses=True)

# 二进制数据专用客户端（用于图片等二进制缓存，不自动解码）
_binary_redis_client = redis.from_url(url=_redis_url, decode_responses=False)

# 按事件循环隔离默认客户端，避免不同 loop 复用同一连接池
_loop_redis_clients: dict[int, redis.Redis] = {}


def get_redis_client_for_task() -> redis.Redis:
    """
    为 Celery 任务创建新的 Redis 客户端实例
    
    在 Windows + asyncio.run() 的环境下，每个任务都有新的事件循环，
    复用的 Redis 客户端会导致连接绑定到旧的（已关闭的）事件循环。
    
    解决方案：每个任务创建独立的 Redis 客户端，在任务结束时自动清理。
    虽然牺牲了连接池复用的性能优势，但保证了稳定性。
    
    Returns:
        新的 Redis 客户端实例（任务结束后会自动关闭）
    """
    # 创建独立的客户端实例，不复用连接池
    return redis.from_url(
        url=_redis_url, 
        decode_responses=True,
        health_check_interval=30,
    )


def get_redis_client() -> redis.Redis:
    """
    获取当前上下文的 Redis 客户端。
    
    优先级（从高到低）：
    1. 任务级别客户端（通过 task_redis_client_context() 设置）
    2. Worker 进程级别客户端（通过 init_redis_for_celery_worker() 设置）
    3. 默认全局客户端（FastAPI 主进程使用）
    """
    # 优先使用任务级别的客户端（用于 Windows + asyncio.run 场景）
    task_client = _task_redis_client.get()
    if task_client is not None:
        return task_client
    
    # 其次使用 worker 进程级别的客户端
    ctx_client = _redis_client_context.get()
    if ctx_client is not None:
        return ctx_client
    
    # 最后使用默认客户端（按事件循环隔离）
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        return _default_redis_client

    loop_client = _loop_redis_clients.get(loop_id)
    if loop_client is None:
        loop_client = redis.from_url(
            url=_redis_url,
            decode_responses=True,
            health_check_interval=30,
        )
        _loop_redis_clients[loop_id] = loop_client
    return loop_client


def init_redis_for_celery_worker() -> None:
    """
    为 Celery worker 进程初始化独立的 Redis 客户端。
    
    应该在 worker 进程启动时调用一次（通过 worker_process_init 信号），
    而不是在每个任务中调用。这样可以：
    1. 避免与父进程的连接池冲突
    2. 跨任务复用连接池，提升性能
    3. 减少连接建立/销毁的开销
    
    注意：这是一个同步函数，不需要在 async 环境中调用。
    
    关于事件循环：
    Redis 异步客户端会在每次操作时自动检测当前的事件循环，
    因此即使每个 Celery 任务使用新的事件循环（asyncio.run），
    Redis 客户端也能正常工作。
    """
    # 配置连接池参数以提高稳定性
    new_client = redis.from_url(
        url=_redis_url, 
        decode_responses=True,
        # 允许连接在不同事件循环中使用
        health_check_interval=30,  # 定期健康检查，自动重连
    )
    _redis_client_context.set(new_client)


# 保留向后兼容的别名（已废弃，但避免破坏现有代码）
def init_redis_for_celery_task() -> None:
    """
    @deprecated: 使用 init_redis_for_celery_worker() 代替
    
    此函数保留仅为向后兼容。应该在 worker 启动时调用一次，
    而不是在每个任务中调用。
    """
    init_redis_for_celery_worker()


async def cleanup_redis_for_celery_task() -> None:
    """
    @deprecated: 不再需要调用此函数
    
    Redis 客户端现在在 worker 进程级别管理，跨任务复用，
    不需要每个任务结束时清理。保留此函数仅为向后兼容。
    """
    # 空操作，保持向后兼容
    pass


# 向后兼容的全局客户端
redis_client = _default_redis_client

# 二进制数据客户端（用于存储图片等二进制内容）
binary_redis_client = _binary_redis_client


@asynccontextmanager
async def task_redis_client_context() -> AsyncGenerator[redis.Redis, None]:
    """
    为 Celery 任务提供独立的 Redis 客户端上下文
    
    在 Windows + asyncio.run() 环境下，每个任务都有新的事件循环，
    复用的 Redis 客户端会导致连接绑定到旧的（已关闭的）事件循环。
    
    此上下文管理器为每个任务创建独立的 Redis 客户端，并在任务结束时清理。
    
    用法：
        async with task_redis_client_context() as client:
            # 在此作用域内，get_redis_client() 会返回这个任务级别的客户端
            await client.set("key", "value")
            # 或使用 get_redis_client()
            redis_client = get_redis_client()
            await redis_client.get("key")
    """
    client = get_redis_client_for_task()
    token = _task_redis_client.set(client)
    try:
        yield client
    finally:
        # 清理：关闭客户端并重置上下文
        try:
            await client.aclose()
        except Exception:
            # 忽略关闭错误
            pass
        finally:
            _task_redis_client.reset(token)
