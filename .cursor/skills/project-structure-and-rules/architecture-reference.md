# Architecture Reference

## Generic Context Structure

其中 `adapter/input/api/v1/` 里的 `v1/` 表示 API version 目录。
下面这个目录骨架表示“采用领域模型时的常见完整形态”，不是每个界限上下文都必须完整拥有这些目录。

```text
app/<context>/
├── adapter/
│   ├── input/
│   │   └── api/
│   │       ├── v1/
│   │       │   ├── request/
│   │       │   ├── response/
│   │       │   ├── <classification>.py
│   │       │   └── __init__.py
│   │       └── exception_handler.py
│   └── output/
│       ├── repository/
│       ├── query/
│       ├── port/
│       └── mapper/
├── application/
│   ├── port/
│   └── service/
├── domain/
│   ├── aggregate/
│   ├── entity/
│   ├── vo/
│   ├── command/
│   ├── event/
│   ├── repository/
│   ├── usecase/
│   ├── domain_service/
│   └── exception/
├── query/
├── event_handler/
├── container.py
└── __init__.py
```

## Placement Decision Guide

这里的 Port 指面向外部能力或跨上下文能力的抽象接口。

- 是否采用领域模型，应以界限上下文为单位决定。
- 一个界限上下文内部可以包含多个领域模型。
- 如果某个上下文采用轻量实现，则可按需省略 `domain/`、`repository/`、`mapper/` 等目录。

- 纯业务规则：放 `domain/`
- 用例编排：放 `application/service/`
- 跨上下文能力接口：放 `application/port/`
- Port 实现：放 `adapter/output/port/`
- DB 写侧实现：放 `adapter/output/repository/`
- 读侧查询实现：放 `adapter/output/query/` 或 `query/`
- 事件处理：放 `event_handler/`

## Placement Example

如果任务是“新增用户认证资源绑定用例”，可先这样放置：

```text
app/auth/
├── domain/
│   └── ...                # 认证资源绑定规则、不变量
├── application/service/
│   └── ...                # 绑定用例编排
├── adapter/output/repository/
│   └── ...                # 持久化写侧实现
└── adapter/input/api/v1/
    └── ...                # HTTP 路由、请求、响应
```

## Real Code Example: Port And Adapter

下面是项目里真实存在的 `Port` 与 `Adapter` 形态：

```python
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel, ConfigDict, field_validator

from app.qa.domain.vo import MessageRole


class LLMMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        return MessageRole.normalize(value)


class LLMPort(ABC):
    @abstractmethod
    async def chat_completion_stream(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str,
    ) -> AsyncIterator[str]:
        ...
```

```python
from collections.abc import AsyncIterator

import httpx

from app.qa.application.port import LLMMessage, LLMPort


class LLMPortAdapter(LLMPort):
    async def chat_completion_stream(
        self,
        *,
        messages: list[LLMMessage],
        system_prompt: str,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                endpoint,
                headers=headers,
                json=payload,
            ) as response:
                async for line in response.aiter_lines():
                    ...
```

上面这个模式对应：

- 抽象能力定义在 `application/port/`
- 外部依赖接入写在 `adapter/output/port/`
- 应用层依赖抽象，不直接依赖外部 SDK 细节

## Cross-Context Example

同一界限上下文内部，领域服务可以被本上下文内其他领域对象或应用服务直接调用。

跨界限上下文时，必须走 `Port + Adaptor`。

如果上下文不分开部署，Adaptor 可以依赖邻域服务实现 Port，但语义上仍然是跨上下文适配。

```text
如果 <context-a> 需要调用 <context-b> 的能力：
1. 在 <context-a>/application/port/ 定义接口
2. 在 <context-a>/adapter/output/port/ 实现适配器
3. 不直接依赖 <context-b> 的内部实现细节
```

```text
例如 `learning` 需要调用 `user` 上下文能力：
1. 在 `app/learning/application/port/` 定义用户能力接口
2. 在 `app/learning/adapter/output/port/` 写对 `user` 的适配器
3. 不直接导入 `app/user/domain/` 内部对象
```

## Real Code Example: Application Service

应用服务负责编排用例，真实代码通常像这样：

```python
class MiniappAuthCommandService(MiniappAuthUseCase):
    def __init__(self, *, user_account_port: UserAccountPort):
        self.user_account_port = user_account_port

    @Transactional()
    async def bind_and_login(self, *, command: MiniappBindCommand) -> MiniappBindResponseDTO:
        user_by_unionid, user_by_openid = await self._find_user_by_wechat_identity(
            openid=str(command.openid),
            unionid=str(command.unionid) if command.unionid else None,
        )
        user = user_by_unionid or user_by_openid
        if user is None:
            user = await self.user_account_port.create_user(
                email=email, password=password, nickname=nickname, role="student"
            )
        return self._build_response(user)
```

这个例子体现：

- 应用服务放在 `application/service/`
- 应用服务依赖 `Port`
- 事务、编排、异常控制在应用层完成

## Lightweight Context Example

如果某个界限上下文不采用领域模型，而采用轻量实现：

- 允许在 `application/service` 中直接导入 `model` 写 SQL
- 不引入 `repository`
- `mapper` 只有在转换收益明显时再引入

如果某个界限上下文采用领域模型：

- 应明确核心领域对象、边界和不变量
- `repository` 只属于领域模型路线

## Event Chain Example

这里的 outbox 指事务内先写入事件记录、再由异步链路投递的暂存机制。
这里的 workflow 指由消息、任务或编排引擎驱动的异步流程。

如果上下文采用领域模型：

- 领域事件应由聚合根或其他领域模型发起

如果上下文采用轻量实现：

- 不应把应用层事件命名为领域事件
- 应由应用层显式产生应用事件
- 若需要异步投递，也由应用层写入 outbox

```text
<aggregate> raises <domain-event>
-> transaction persists aggregate and outbox
-> message bus publishes event
-> workflow or activity handles asynchronous process
```
