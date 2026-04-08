"""
异步测试工具函数
"""

import asyncio


async def wait_until(
    condition_fn,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> None:
    """
    轮询等待异步条件成立，超时后抛出 TimeoutError。

    用法：
        await wait_until(lambda: check_thumbnail_exists(blob_id))
        await wait_until(some_async_fn, timeout=20)
    """
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        result = condition_fn()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return
        if loop.time() >= deadline:
            raise TimeoutError(f"条件在 {timeout}s 内未成立")
        await asyncio.sleep(interval)
