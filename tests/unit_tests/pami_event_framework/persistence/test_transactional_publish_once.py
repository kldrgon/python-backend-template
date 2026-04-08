import asyncio
import pytest

from pami_event_framework.persistence import transactional


@pytest.mark.asyncio
async def test_safe_publish_once_uses_captured_publisher_not_global():
    class Publisher:
        def __init__(self):
            self.called = False

        async def publish_once(self):
            self.called = True

    publisher = Publisher()
    transactional.set_event_publisher(publisher)

    # 模拟任务创建后全局 publisher 被 shutdown 清空
    task = asyncio.get_running_loop().create_task(
        transactional._safe_publish_once(publisher)
    )
    transactional.set_event_publisher(None)
    await task

    assert publisher.called is True
