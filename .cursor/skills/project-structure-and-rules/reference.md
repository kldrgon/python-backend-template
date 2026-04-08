# Project Structure And Rules Reference

## Recommended Coverage

这个总 skill 适合集中收这些规则：

- 目录结构
- 分层边界
- 界限上下文与领域模型关系
- 临时工作文档目录约定
- API 放置规则
- 命名规则
- 测试分层与测试命令
- 提交边界与不可提交内容

## Reference Layout

推荐把细节拆成多个 reference：

- `architecture-reference.md`
- `api-reference.md`
- `naming-reference.md`
- `testing-reference.md`
- `commit-reference.md`

## Reading Strategy

建议先读主 `SKILL.md`，只在命中下面情况时再回读对应 reference：

- 代码放置和分层问题：读 `architecture-reference.md`
- 上下文是否采用领域模型、是否允许轻量实现：读 `architecture-reference.md`
- 临时设计稿、计划稿、重启占位符放哪里：先看主 `SKILL.md`
- HTTP 接口问题：读 `api-reference.md`
- 命名问题：读 `naming-reference.md`
- 测试问题：读 `testing-reference.md`
- 提交边界问题：读 `commit-reference.md`

## Suggested Split

如果项目准备收敛 skill 体系，推荐这样分：

- `project-structure-and-rules`：集中放静态项目规则
- `task-design`：处理前置分流和任务设计
- `branch-workflow`：处理长流程执行

如果后续需要文档型 skill，可再单独补 `design-doc`。
