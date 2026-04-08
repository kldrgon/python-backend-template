---
name: project-structure-and-rules
description: Checks structure, API, naming, testing, and commit boundaries before implementation. Use when you need to decide where code should live or which project convention applies.
---

# Project Structure And Rules

## Use When

- 需要判断代码、测试或文档应放在哪里
- 需要判断分层、API、命名、测试、提交边界
- 需要在实现前先确认本次应遵守哪些项目规范
- 用户要求“按项目规范实现”

## Core Goal

开始实现前，先确认这次改动真正相关的结构、API、命名、测试和提交边界。

不要一次性展开全部规范，只处理当前任务需要的部分。

## What To Check

优先判断下面几类问题：

1. 事前分流：
   - 这次是可以直接做，还是需要先澄清、先写设计稿、或进入长流程

2. 代码落点：
   - 这是领域规则、应用编排、输入适配、输出适配、查询、测试还是文档

3. API 边界：
   - 这次是否涉及路由、请求模型、响应模型、异常映射

4. 命名边界：
   - 这次新建的是接口、实现、查询服务、仓储还是应用服务

5. 测试边界：
   - 这次应补哪一层测试
   - 验证方式应放在哪一层

6. 提交边界：
   - 本次改动是否混入了不属于当前目标的文件

7. 设计稿边界：
   - 这次是否需要显式写清目标、范围、上下文边界、假设与待确认项

8. 长流程边界：
   - 这次是否需要先确认文档、commit 计划、quick review 与分支级检查

## When To Read References

只有在下面情况时，再查看对应 reference：

- 结构或分层判断不清：看 `architecture-reference.md`
- API 落点不清：看 `api-reference.md`
- 命名拿不准：看 `naming-reference.md`
- 测试层级不清：看 `testing-reference.md`
- 提交边界不清：看 `commit-reference.md`

## Required Behavior

- 先判断这次任务真正相关的规范点，再进入实现。
- 只补看必要的细节，不把所有规则一次性展开。
- 如果规则冲突，先指出冲突点。
- 如果需要先澄清需求，转入 `task-design`。
- 如果进入长流程执行，转入 `branch-workflow`。

## Output Pattern

在开始实现前，优先用这种短说明：

```text
我先确认这次改动的代码落点、API/命名边界、测试层级和提交边界。
如果哪条规范还不清楚，我会先指出并补看对应说明。
```

## Additional Resources

- 总览见 [reference.md](./reference.md)
- 分层与结构细节见 [architecture-reference.md](./architecture-reference.md)
- API 细节见 [api-reference.md](./api-reference.md)
- 命名细节见 [naming-reference.md](./naming-reference.md)
- 测试细节见 [testing-reference.md](./testing-reference.md)
- 提交细节见 [commit-reference.md](./commit-reference.md)
