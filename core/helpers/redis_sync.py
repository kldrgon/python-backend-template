"""线程安全的同步 Redis 客户端

用于心跳线程等多线程场景，使用同步 redis-py 而非异步客户端。
"""
import threading
from typing import Optional

import redis
import structlog

from core.config import config

logger: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

_sync_redis_client: Optional[redis.Redis] = None
_client_lock = threading.Lock()


def get_sync_redis_client() -> redis.Redis:
    """获取线程安全的同步 Redis 客户端（用于心跳线程）
    
    单例模式，线程安全。redis.Redis 客户端本身是线程安全的。
    
    Returns:
        redis.Redis: 同步 Redis 客户端实例
    """
    global _sync_redis_client
    
    if _sync_redis_client is None:
        with _client_lock:
            # 双重检查锁定
            if _sync_redis_client is None:
                try:
                    _sync_redis_client = redis.Redis(
                        host=config.redis.host,
                        port=config.redis.port,
                        db=config.redis.db,
                        password=config.redis.password,
                        decode_responses=True,  # 自动解码为字符串
                        socket_connect_timeout=5,
                        socket_keepalive=True,
                        health_check_interval=30,  # 健康检查
                    )
                    
                    # 测试连接
                    _sync_redis_client.ping()
                    
                    logger.info(
                        "sync_redis_client_initialized",
                        host=config.redis.host,
                        port=config.redis.port,
                        db=config.redis.db,
                    )
                except Exception as e:
                    logger.exception("sync_redis_client_init_failed")
                    raise RuntimeError(f"Failed to connect to Redis ({type(e).__name__})") from e
    
    return _sync_redis_client


def close_sync_redis_client() -> None:
    """关闭同步 Redis 客户端（优雅关闭时使用）"""
    global _sync_redis_client
    
    if _sync_redis_client is not None:
        with _client_lock:
            if _sync_redis_client is not None:
                try:
                    _sync_redis_client.close()
                    logger.info("sync_redis_client_closed")
                except Exception:
                    logger.exception("sync_redis_client_close_error")
                finally:
                    _sync_redis_client = None


