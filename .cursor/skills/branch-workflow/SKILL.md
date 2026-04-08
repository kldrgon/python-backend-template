---
name: branch-workflow
description: Drives a full long-running delivery workflow from branch goal, working-carrier selection, document confirmation, commit planning, implementation, branch readiness check, and PR-stage review coordination. Use when a task should be executed as a multi-commit branch or worktree workflow rather than a one-shot coding step.
---

# Branch Workflow

## Use When

- 用户要开始一个完整分支任务
- 任务会持续多个 commit
- 任务可能需要用 `git worktree` 并行推进或隔离目录
- 需要先写文档、再按计划推进实现
- 需要每完成一个 commit 就 quick review 并提交
- 需要在分支完成后进入 PR 阶段

## Core Rules

- 先定分支目标，再决定使用 `branch` 还是 `git worktree`。
- 没有用户确认过的文档，不进入编码。
- 没有 commit 计划表，不进入连续开发。
- 每完成一个 commit，都先做 quick review，再提交。
- 一个 commit 只做一件事，不混入无关改动。
- `quick review` 是 commit 级自检，不等于正式 review。
- `branch readiness check` 是分支级检查，不等于正式 review。
- 正式 review 默认以 PR 为单位，可能由用户自己做，也可能由其他 reviewer 做。

## Stop Conditions

遇到下面情况时先停下并要求确认，不直接继续：

- 分支目标不清
- 分支边界不清
- 当前工作载体未确认
- 文档未确认
- commit 计划表未确认
- 当前 commit 过大但尚未拆分
- quick review 未通过
- branch readiness check 未通过

## Workflow

### 1. Confirm Branch Goal

先产出并确认：

- 一句话分支目标
- 本次分支边界
- 明确“不做什么”

如果分支目标不清，不进入下一步。

### 2. Choose Working Carrier

基于已确认的目标，先决定当前任务使用什么工作载体。

要求：

- 先确认项目的分支命名规范
- 分支命名规范是占位，由用户决定
- 先判断使用普通 `branch` 还是 `git worktree`
- 如果需要并行开发、隔离目录、减少来回切分支，优先考虑 `git worktree`
- 用户认可分支名和工作方式后再创建

### 3. Prepare Documents

进入实现前，至少准备并确认下面几类文档。

#### 3.1 Related Design Docs

这类文档用于描述本次分支直接相关的设计与上下文。

- 可以是外部已有文档
- 可以是本次新建文档
- 若是本次过程中新建的临时设计文档，默认放 `DEVELOP_TEMP/<timestamp>/`
- 内容必须用户确认

#### 3.2 Commit Plan

这是本流程的核心文档。

要求：

- 每一项都应能独立完成、独立 review、独立提交
- 每完成一项就提交一次
- 必须用户确认
- 默认放在 `DEVELOP_TEMP/<timestamp>/`
- 详细结构与示例见 `commit-plan-reference.md`

#### 3.3 Sub Plan

只在某一个 commit 过大时使用。

- 只服务于单个 commit
- 是 commit plan 的辅助文档
- 主要描述“这个 commit 具体要改什么”
- 必须用户确认
- 默认与当前 commit plan 放在同一个 `DEVELOP_TEMP/<timestamp>/` 目录

### 4. Execute One Commit

执行当前 commit 计划项时：

- 只做当前计划项
- 不提前做后续 commit 内容
- 不混入无关文件
- 需要时参考对应子计划

### 5. Quick Review Current Commit

这是快速 review，不是完整 code review。

每个 commit 在提交前都必须快速检查：

- 是否偏离当前 commit 目标
- 是否混入无关改动
- 是否缺必要测试
- 是否违反项目分层、命名、API、测试、提交规则
- 是否还能继续拆小

若 quick review 不通过，先修正，再提交。

### 6. Commit Current Step

当前计划项完成且 quick review 通过后立即提交。

要求：

- 不积压多个计划项后一起提交
- 提交时只包含当前计划项范围内的文件

### 7. Loop To Next Commit

对下一个 commit 重复执行：

- 读取计划项
- 必要时展开子计划
- 实现
- quick review
- 提交

直到本分支所有计划项完成。

### 8. Branch Readiness Check

这是分支级检查，但不是正式 review。

进入 PR 前检查：

- commit 计划表是否全部完成
- 文档是否已同步
- 测试、验证、构建是否达到当前分支要求
- 是否遗留未提交改动
- 是否存在无关临时文件
- 提交粒度是否仍然合理
- 是否还有需要交代的风险点

若 readiness check 未通过，先修正，再决定是否进入 PR 阶段。

### 9. Enter PR Review Stage

当分支已 ready 后，进入 PR 阶段。

要求：

- 正式 review 默认按 PR 组织，不按单个 commit 组织
- 代理不应默认假设“branch review 必须由自己完成”
- 应允许以下几种情况：
  - 用户自己 review
  - 外部 reviewer review
  - 用户要求代理协助 review 当前 PR
- 如果 PR review 给出反馈，后续修改应继续遵守 commit plan 和提交边界

### 10. Branch Closing Check

分支结束前检查：

- 当前工作载体是否可以安全收尾
- PR review 状态是否已交代清楚
- 是否还有未处理反馈或残留风险
- 是否还需要后续提交、合并或清理动作

## Required Behavior

- 如果缺少分支目标，先问。
- 如果缺少工作载体决策，先停。
- 如果缺少文档确认，先停。
- 如果缺少 commit 计划表，先补计划，不直接开始长流程编码。
- 如果任务适合并行目录隔离，主动建议 `git worktree`。
- 如果某个 commit 过大，主动建议拆子计划。
- 如果任务中断后恢复，先读取任务重启占位符，再决定是否回读完整文档。
- 如果分支已基本完成，先做 `branch readiness check`，不要直接把它当作正式 review。
- 如果进入正式 review，按 PR 阶段处理，并明确 review 由谁执行。

## Mandatory Re-read Points (Must Re-read) IMPORTANT

为了对抗上下文稀释，遇到下面情况时必须重新读取规则，不允许只靠当前记忆继续执行。

### 必须重读本流程的 `SKILL.md`

- 第一次进入这条长流程时
- 每次准备开始新的 commit 计划项时
- 用户临时改变分支目标或边界时
- 发现当前改动明显超出原计划时
- quick review 前
- branch readiness check 前
- 进入 PR 阶段前

### 必须重读本流程的 `commit-plan-reference.md`

- 第一次编写 commit 计划表时
- 修改 commit 计划表时
- 判断当前 commit 是否需要继续拆小时
- 准备进入下一个 commit 前
- 发现 `feat/test/fix/refactor/docs` 边界开始混乱时

### 必须重读本流程的 `restart-placeholders-reference.md`

- 任务中断后恢复时
- 需要判断“当前做到哪里”时
- 需要判断“下一步做什么”时
- 出现阻塞点或新增待确认事项时

### 回读后的动作

回读后至少要重新确认：

- 当前分支目标是否仍然成立
- 当前工作载体是否仍然合适
- 当前 commit 是否仍和计划一致
- 当前状态是否需要更新占位符
- 是否应继续执行、拆子计划、进入 PR 阶段、还是先停下等用户确认

## Restart Placeholders

为了方便任务中断后快速恢复，相关文档中应保留一组固定占位符。

至少包括：

- 当前分支目标
- 当前分支名
- 当前工作载体（`branch` / `worktree`）
- 当前已确认文档
- 当前执行到的 commit
- 当前 commit 状态
- 当前分支 readiness 状态
- 当前 PR / review 状态
- 下一个动作
- 当前阻塞点
- 需要用户确认的事项

如果这些占位符是为当前分支临时维护的，默认放在 `DEVELOP_TEMP/<timestamp>/` 下，与当前分支相关文档保持在同一批目录中。

## 何时必须重读其他技术、边界相关的 SKILL

- 每次准备开始新的 commit 计划项时
- quick review 前

## Additional Resources

- commit 计划表细则见 [commit-plan-reference.md](./commit-plan-reference.md)
- 任务重启占位符见 [restart-placeholders-reference.md](./restart-placeholders-reference.md)
- 本项目默认临时工作文档目录为 `DEVELOP_TEMP/<timestamp>/`
- 相关正式设计文档位置、分支命名规范位置仍属于项目占位，应由用户决定。 
