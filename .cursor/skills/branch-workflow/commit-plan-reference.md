# Commit Plan Reference

## 目标

`commit plan` 是分支长流程里的核心文档。

它的作用不是简单列待办，而是把一个分支拆成可连续执行、可快速 `quick review`、可立即提交的最小 commit 单元。

如果是本次流程中新建的临时 `commit plan`，默认放在 `DEVELOP_TEMP/<timestamp>/`。

## 使用原则

- 一个 commit 只做一件事
- 一个 commit 应该能独立 quick review
- 一个 commit 应该能独立提交
- 一个 commit 不应混入下一步内容
- 每个 commit 都要带 quick review 检查点
- 正式 review 默认属于 PR 阶段，不属于单个 commit 计划项

## 建议字段

主表建议至少包含这些字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 本次 commit 的序号或标识(并不是实际的commit id) |
| `type` | 是 | `feat` / `test` / `fix` / `refactor` / `docs` |
| `goal` | 是 | 本次 commit 只做什么 |
| `scope` | 是 | 预期涉及哪些目录、模块或文件类型 |
| `exclude` | 是 | 明确不应混入什么 |
| `docs` | 是 | 本次依赖的已确认文档 |
| `implementation` | 是 | 主要实现点 |
| `test` | 是 | 需要补哪些测试，或说明为何不补 |
| `quick-review` | 是 | 提交前要检查的重点 |
| `status` | 是 | `pending` / `doing` / `quick-reviewing` / `committed` |

## 主表模板

```markdown
| id | type | goal | scope | exclude | docs | implementation | test | quick-review | status |
|---|---|---|---|---|---|---|---|---|---|
| C1 | feat | [只做一件事] | [目录/模块范围] | [禁止混入项] | [已确认文档] | [本次实现点] | [本次测试安排] | [提交前检查点] | pending |
```

## 拆分规则

优先按下面方式拆 commit：

1. 先按能力边界拆
2. 再按功能代码与测试代码拆
3. 再按是否需要单独 quick review 拆

如果一个 commit 同时满足下面任一条件，应继续拆小：

- 同时改了多个不强相关模块
- 同时包含功能代码和大量测试代码
- 单次提交无法一句话说清目标
- quick review 时很难判断是否越界

## Quick Review 内嵌规则

`quick-review` 字段不是装饰，它是提交前的硬检查。

每个 commit 至少检查：

- 是否偏离 `goal`
- 是否超出 `scope`
- 是否混入 `exclude`
- 是否缺最小必要测试
- 是否违反项目已有规则
- 是否还能继续拆小

## 推荐节奏

推荐按下面节奏循环：

1. 读取当前 commit 行
2. 执行本次改动
3. 更新 `status=quick-reviewing`
4. 做 quick review
5. 通过后提交
6. 更新 `status=committed`
7. 进入下一行

## 与 Branch / PR 的边界

- `commit plan` 只负责 commit 级执行与 `quick review`
- 分支级检查应放在 `branch readiness check`
- 正式 review 应放在 `PR review` 阶段
- 不要把 branch readiness 或 PR review 混写进单个 commit 行

## 示例

```markdown
| id | type | goal | scope | exclude | docs | implementation | test | quick-review | status |
|---|---|---|---|---|---|---|---|---|---|
| C1 | feat | 新增 <capability> 命令与应用服务 | `app/<context>/domain/` `app/<context>/application/` | `tests/`、后续 API 改动 | `<design-doc>` | 补聚合行为、命令对象、use case、command service | 暂不补，在 C2 补 unit test | 检查是否越界、是否缺最小校验 | pending |
| C2 | test | 为 <capability> 补单元测试 | `tests/unit_tests/app/<context>/` | 功能代码 | `<design-doc>` `<commit-plan>` | 无 | 补聚合与 command service 的 unit test | 检查是否只含测试改动 | pending |
| C3 | feat | 新增 <capability> API 接口 | `app/<context>/adapter/input/api/` | `tests/`、后续异常映射调整 | `<design-doc>` `<api-doc>` | 补 request/response、route、service 调用 | 暂不补，在 C4 补 system test | 检查是否只含 API 相关改动 | pending |
| C4 | test | 为 <capability> 补 system test | `tests/system_tests/app/<context>/` | 功能代码 | `<design-doc>` `<commit-plan>` | 无 | 补 API 成功与异常路径 system test | 检查是否只含测试改动 | pending |
```

## 子计划何时出现

当某一行 commit 仍然过大时，再额外写一个子计划。

子计划只服务于当前 commit，不取代主表。

例如：

- `C3-sub-1` 先补 request/response
- `C3-sub-2` 再补 route
- `C3-sub-3` 最后补异常映射

## 常见错误

- 把整个分支写成一个 commit
- `feat` 和 `test` 混在同一行
- `goal` 写得过大，无法一句话说清
- `scope` 不写，导致后面不断越界
- `status` 不更新，任务重启后无法定位
