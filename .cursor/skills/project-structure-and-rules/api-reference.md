# API Reference

## Generic API Structure

这里的 `v1/` 表示 API version 目录，也就是版本号目录，不是普通业务分类目录。

```text
app/<context>/adapter/input/api/
├── v1/
│   ├── request/
│   │   ├── <classification>.py
│   │   └── __init__.py
│   ├── response/
│   │   ├── <classification>.py
│   │   └── __init__.py
│   ├── <classification>.py
│   └── __init__.py
└── exception_handler.py
```

## Classification Standard Options

`v1/` 下面再按项目选定的接口分类标准拆分。
这里的 UseCase 指单个业务用例的应用层入口。
这里的 DTO 指用于请求或响应传递的数据对象。

`<classification>` 可以按项目选择：

- `<aggregate>`
- `<capability>`
- `<use_case>`
- `<module>`

## Request And Response Example

```text
request/<classification>.py
- Create<Aggregate>Request
- Update<Aggregate>Request
- Query<Capability>Request

response/<classification>.py
- <Aggregate>DetailResponse
- <Aggregate>SummaryResponse
- <Capability>ResultResponse
```

## Route Responsibility Example

路由层通常只做：

- 接收参数
- 调用 UseCase 或应用服务
- 组装统一响应
- 映射异常

路由层通常不做：

- 直接操作 Repository
- 承载领域规则
- 直接发消息或调工作流引擎

## Exception Mapping Example

```text
<domain-exception> -> 4xx response
<application-exception> -> 4xx or 5xx response
unexpected exception -> unified internal error response
```
