# Restart Placeholders Reference

## 目标

这组占位符主要用于任务重启。

当 AI 会话中断、切换上下文、或多次接力时，可以通过固定占位符快速定位当前分支状态，而不必重新阅读全部文档。

如果是当前流程中新建的临时状态占位符文档，默认放在 `DEVELOP_TEMP/<timestamp>/`。

## 使用原则

- 占位符应固定命名
- 占位符应尽量少，但必须够定位
- 每次完成一个 commit 后应更新
- 每次出现阻塞或待确认事项时应更新

## 必备占位符

建议至少保留下面这些：

```text
[BRANCH_GOAL]
[BRANCH_NAME]
[WORKING_CARRIER]
[BRANCH_SCOPE]
[CONFIRMED_DOCS]
[COMMIT_PLAN_PATH]
[CURRENT_COMMIT_ID]
[CURRENT_COMMIT_GOAL]
[CURRENT_COMMIT_STATUS]
[LAST_COMPLETED_COMMIT]
[BRANCH_READINESS_STATUS]
[PR_REVIEW_STATUS]
[NEXT_ACTION]
[BLOCKERS]
[PENDING_USER_CONFIRMATIONS]
```

## 含义说明

| 占位符 | 说明 |
|---|---|
| `[BRANCH_GOAL]` | 本次分支一句话目标 |
| `[BRANCH_NAME]` | 当前分支名 |
| `[WORKING_CARRIER]` | 当前工作载体，如 `branch` / `worktree` |
| `[BRANCH_SCOPE]` | 本分支边界与不做范围 |
| `[CONFIRMED_DOCS]` | 已被用户确认的文档列表 |
| `[COMMIT_PLAN_PATH]` | commit 计划表位置 |
| `[CURRENT_COMMIT_ID]` | 当前正在执行的 commit |
| `[CURRENT_COMMIT_GOAL]` | 当前 commit 目标 |
| `[CURRENT_COMMIT_STATUS]` | 当前 commit 状态，如 `planning` / `doing` / `quick-reviewing` / `committed` / `blocked` |
| `[LAST_COMPLETED_COMMIT]` | 上一个已完成并提交的 commit |
| `[BRANCH_READINESS_STATUS]` | 当前分支 readiness 状态，如 `not-ready` / `checking` / `ready` |
| `[PR_REVIEW_STATUS]` | 当前 PR review 状态，如 `not-opened` / `waiting-review` / `changes-requested` / `approved` / `not-applicable` |
| `[NEXT_ACTION]` | 当前最直接的下一步动作 |
| `[BLOCKERS]` | 当前阻塞点 |
| `[PENDING_USER_CONFIRMATIONS]` | 当前仍需用户确认的事项 |

## 推荐写法

可以在分支主文档、commit plan 顶部、或状态记录区域保留一段固定块：

```text
[BRANCH_GOAL]: <一句话目标>
[BRANCH_NAME]: <branch-name>
[WORKING_CARRIER]: <branch-or-worktree>
[BRANCH_SCOPE]: <本次边界与不做内容>
[CONFIRMED_DOCS]: <doc-a>, <doc-b>, <doc-c>
[COMMIT_PLAN_PATH]: <path-or-link>
[CURRENT_COMMIT_ID]: C2
[CURRENT_COMMIT_GOAL]: 为 <capability> 补单元测试
[CURRENT_COMMIT_STATUS]: quick-reviewing
[LAST_COMPLETED_COMMIT]: C1
[BRANCH_READINESS_STATUS]: not-ready
[PR_REVIEW_STATUS]: not-opened
[NEXT_ACTION]: 完成 quick review 后提交 C2
[BLOCKERS]: 无
[PENDING_USER_CONFIRMATIONS]: 是否允许直接复用 application dto
```

## 更新时机

建议在这些时机更新：

1. 工作载体创建完成后
2. 用户确认相关文档后
3. commit plan 确认后
4. 当前 commit 切换时
5. quick review 完成后
6. 某次提交完成后
7. branch readiness 状态变化时
8. 进入或推进 PR review 阶段时
9. 出现新的阻塞点或待确认事项时

## 最小重启恢复流程

任务重启时优先读取这组占位符，然后按下面顺序恢复：

1. 读取 `[BRANCH_GOAL]`
2. 读取 `[WORKING_CARRIER]`
3. 读取 `[CURRENT_COMMIT_ID]` 与 `[CURRENT_COMMIT_STATUS]`
4. 读取 `[BRANCH_READINESS_STATUS]` 与 `[PR_REVIEW_STATUS]`
5. 读取 `[NEXT_ACTION]`
6. 检查 `[BLOCKERS]`
7. 检查 `[PENDING_USER_CONFIRMATIONS]`
8. 再决定是否需要回读完整文档

## 常见错误

- 只记录目标，不记录当前 commit
- 只记录当前 commit，不记录 next action
- commit 已提交但未更新 `CURRENT_COMMIT_STATUS`
- 用户已确认文档但未更新 `CONFIRMED_DOCS`
- 已阻塞但 `BLOCKERS` 仍写“无”
- 已进入 PR 阶段但未更新 `PR_REVIEW_STATUS`
