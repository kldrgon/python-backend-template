# Testing Reference

这里的 `smoke_tests/` 通常指专项联通性或环境验证测试目录，不等同于完整分层测试。
这里的 `wait_until` 指轮询等待工具，用于替代固定 `sleep`。

## Generic Test Structure

```text
tests/
├── unit_tests/
│   └── app/<context>/
├── integration_tests/
│   └── app/<context>/
├── system_tests/
│   └── app/<context>/
├── smoke_tests/
├── support/
└── conftest.py
```

## Test Scope Examples

- `unit`：聚合行为、值对象、领域服务、命令校验
- `integration`：Repository、QueryService、事务与 outbox、外部适配器局部集成
- `system`：HTTP 接口、鉴权链路、异常映射、异步事件链路
- `smoke`：手工验证脚本、环境联通性、一次性检查

## Test Level Decision Example

如果这次改动同时涉及聚合规则、仓储实现和 HTTP 接口：

```text
- 聚合规则：`tests/unit_tests/app/<context>/`
- Repository / outbox：`tests/integration_tests/app/<context>/`
- API / 鉴权 / 异常映射：`tests/system_tests/app/<context>/`
```

## Real Test Example

项目里的单元测试真实形态如下：

```python
import pytest

from app.qa.adapter.output.port import LLMPortAdapter
from app.qa.application.port import LLMMessage
from app.qa.domain.vo import MessageRole


@pytest.mark.asyncio
async def test_llm_port_adapter_requests_openai_compatible_stream(monkeypatch):
    adapter = LLMPortAdapter()
    chunks = []

    async for chunk in adapter.chat_completion_stream(
        messages=[LLMMessage(role=MessageRole.USER, content="你好")],
        system_prompt="你是助手",
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "你好"
```

这个例子说明：

- 适配器单测放 `tests/unit_tests/app/<context>/adapter/output/port/`
- 测试名直接体现行为
- 用 `pytest.mark.asyncio` 跑异步能力
- 断言聚焦最终可观察结果

## Execution Examples

```bash
uv run pytest tests/unit_tests/app/<context>/ -v
uv run pytest tests/integration_tests/app/<context>/ -v
uv run pytest tests/system_tests/app/<context>/ -v
```

## Async And Flaky Example

若系统存在异步传播或最终一致性延迟，优先使用轮询等待：

```text
wait_until(
    condition=<callable>,
    timeout=<seconds>,
    interval=<seconds>,
)
```

## Fixture Placement Guide

- 全局共享 fixture：根 `tests/conftest.py`
- 分层专属 fixture：对应层级目录下的 `conftest.py`
- 辅助工具：`tests/support/`
