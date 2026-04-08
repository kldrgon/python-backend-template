---
name: project-structure-and-rules
description: Defines project structure, layering boundaries, API conventions, naming expectations, testing rules, commit rules, and related references. Use when starting implementation, placing code, naming new symbols, adding endpoints or tests, checking commit boundaries, or applying project-wide conventions.
---

# Project Structure And Rules

## Use When

- 需要判断代码、测试、文档应放在哪里
- 需要确认项目分层和边界
- 需要新增或修改 HTTP 接口
- 需要新建类、接口、文件并确认命名
- 需要确认测试层级、测试命令或测试放置位置
- 需要确认提交边界、提交节奏或哪些文件不应提交
- 用户要求“按项目规范实现”

## Core Goal

本 skill 负责集中提供项目级静态规则。

它不是长流程 skill，也不替代任务设计或分支执行。

## Structure Rules

先确认下面几类结构信息：

- 业务代码目录
- API 目录
- 领域层、应用层、适配器层边界
- 测试目录分层
- 设计文档目录
- 临时工作文档目录

如果某项结构规则在项目里还未定，保留占位并要求用户确认。

本项目默认存在一个临时工作目录：`DEVELOP_TEMP`。

- `DEVELOP_TEMP` 是工作目录，不是正式文档目录
- 设计草稿、commit plan、sub plan、任务重启占位符、临时分析记录默认放这里
- `DEVELOP_TEMP` 下的二级目录默认使用时间戳命名，如 `DEVELOP_TEMP/20260407_153000/`

默认按下面顺序判断落点：

1. 这是领域规则还是编排逻辑
2. 是否依赖外部能力或跨上下文能力
3. 是否属于 API 输入输出适配
4. 是否属于读侧查询
5. 是否属于测试或文档

## Architecture Rules

常见分层可理解为：

- 以 `app/<context>/` 或等价目录作为业务边界
- 是否采用领域模型，应以界限上下文为单位决定
- 一个界限上下文内部可以包含多个领域模型
- `domain` 放领域概念，不依赖 `application`
- `application/service` 放用例编排
- `application/port` 放本上下文缺少的能力接口。这里的 Port 指面向外部能力的抽象接口
- `adapter/input` 负责接收输入
- `adapter/output` 负责仓储、外部系统、Port 实现
- `query/` 属于读侧。这里的 QueryService 指面向读取场景的查询服务

同一界限上下文内，领域服务可以被本上下文内部其他领域对象或应用服务直接使用。

跨上下文默认通过 `Port + Adaptor` 解耦，不直接依赖对方内部实现。

如果上下文不分开部署，Adaptor 可以依赖邻域服务来实现 Port，但语义上仍然是跨上下文适配。

涉及事件、outbox、workflow 时：

- 采用领域模型的上下文，领域事件由聚合根或实体产生
- 不采用领域模型的轻量实现上下文，不应把应用层事件命名为领域事件
- 轻量实现上下文若需要事件，应由应用层显式产生应用事件
- 应用层负责事务内持久化与 outbox。这里的 outbox 指事务内先落库、再异步投递的事件暂存机制
- API 层不直接发消息总线或工作流引擎
- 这里的 workflow 指由消息或任务引擎驱动的跨步骤异步流程

如果某个界限上下文不采用领域模型，而采用轻量实现：

- 可以在 `application/service` 中直接导入 `model` 写 SQL
- 不引入 `repository`
- `mapper` 仅在转换收益明显时再引入

如果某个界限上下文采用领域模型：

- 应明确核心领域对象、边界和不变量
- `repository` 只属于领域模型路线

## API Rules

API 规则也收敛到本 skill：

- 路由通常放 `app/<context>/adapter/input/api/v1/`
- 这里的 `v1/` 表示 API version 目录
- 请求模型通常放 `request/`
- 响应模型通常放 `response/`
- 路由只负责接参、调用应用服务或 UseCase、返回响应、映射异常。这里的 UseCase 指单个业务用例的应用层入口
- 路由不负责领域规则、仓储操作、消息发送
- API DTO 与领域命令对象分开。这里的 DTO 指用于输入输出传递的数据对象
- 异常统一映射为稳定的 HTTP 响应

## Naming Rules

命名规则统一收敛到这里：

下面这些 `Repository` 命名规则，只适用于采用领域模型的界限上下文。
如果某个上下文采用轻量实现，则不强制创建 `repository`。

- 仓储接口：`XxxRepository`
- 仓储实现：`SQLAlchemyXxxRepository`
- 查询服务接口：`XxxQueryService`
- 查询服务实现：`SQLAlchemyXxxQueryService`
- 用例接口：`XxxUseCase`
- 应用服务实现：`XxxCommandService`
- `QueryService` 作为整体词，不拆开
- 不使用 `XxxSQLAlchemyRepository`、`SqlalchemyXxx...`、`SAXxx...`

命名前先确认：

- 它是接口还是实现
- 它属于哪一层
- 项目里是否已有同类先例
- 是否会和 DTO、实体、聚合重名

## Testing Rules

测试规则作为项目总规则的一部分统一定义：

- 先判断本次应补 `unit`、`integration` 还是 `system`
- 优先按测试目录分层，不混跑不同层级
- 优先沿用项目既有 `pytest`、`asyncio`、`wait_until` 等约定
- 新测试先放到最小可复用层级，不随意提升到全局

需要细化时，回读测试 reference 和 `tests/` 目录。

## Commit Rules

提交规则也作为项目总规则的一部分统一定义：

- 先确认本次 commit 目标与文件范围
- 只提交当前目标范围内的文件
- 功能、测试、文档、重构应按项目约定拆分
- 临时文件、本地文件、无关文件不应混入正式提交

需要细化时，回读提交 reference 和 `branch-workflow` 的计划参考。

## Related Files To Re-read

遇到下面情况时，应优先回读对应文件，而不是只靠当前记忆：

- 结构边界不清：回读 [architecture-reference.md](./architecture-reference.md)
- API 落点不清：回读 [api-reference.md](./api-reference.md)
- 命名不清：回读 [naming-reference.md](./naming-reference.md)
- 测试落点不清：回读 [testing-reference.md](./testing-reference.md) 和 `tests/` 目录
- 提交边界不清：回读 [commit-reference.md](./commit-reference.md) 和 `branch-workflow` 的计划参考
- 分支长流程执行：回读 `branch-workflow` 相关文件

## Required Behavior

- 只给项目级规则，不把流程步骤塞进这里。
- 如果规则与当前任务冲突，先指出冲突点。
- 如果需要先澄清需求，转入 `task-design`。
- 如果进入长流程执行，转入 `branch-workflow`。

## Output Pattern

在开始实现前，优先用这种短说明：

```text
我先按项目结构与规则判断这次改动应落在哪一层、测试应放哪一层、提交应如何拆分。
如果某条规则还不明确，我会先指出并向你确认。
```

## Additional Resources

- 总览见 [reference.md](./reference.md)
- 分层与结构细节见 [architecture-reference.md](./architecture-reference.md)
- API 细节见 [api-reference.md](./api-reference.md)
- 命名细节见 [naming-reference.md](./naming-reference.md)
- 测试细节见 [testing-reference.md](./testing-reference.md)
- 提交细节见 [commit-reference.md](./commit-reference.md)
