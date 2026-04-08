# Project Structure And Rules Reference

## Recommended Coverage

当你需要展开查看细节时，重点看这些主题：

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

建议先参考适用的项目静态规则，只在下面情况时再查看对应 reference：

- 代码放置和分层问题：读 `architecture-reference.md`
- 上下文是否采用领域模型、是否允许轻量实现：读 `architecture-reference.md`
- 临时设计稿、计划稿、重启占位符放哪里：先看主 `SKILL.md`
- HTTP 接口问题：读 `api-reference.md`
- 命名问题：读 `naming-reference.md`
- 测试问题：读 `testing-reference.md`
- 提交边界问题：读 `commit-reference.md`

## Reading Examples

```text
如果你在想“这段逻辑该放 domain 还是 application”：
- 读 `architecture-reference.md`

如果你在想“这个路由、Request、Response 该怎么落”：
- 读 `api-reference.md`

如果你在想“仓储实现、查询服务、DTO 该怎么命名”：
- 读 `naming-reference.md`

如果你在想“这次该补 unit、integration 还是 system”：
- 读 `testing-reference.md`

如果你在想“这批改动能不能一起提交，是否混入无关文件”：
- 读 `commit-reference.md`
```
