# Commit Reference

## Generic Commit Rhythm Examples

如果项目要求功能与测试分离，可采用：

```text
feat -> test -> feat -> test
```

如果项目不要求严格配对，也可改成：

```text
feat -> feat -> test
refactor -> test
fix -> test
```

## Staging Boundary Example

```text
feat commit:
- app/
- core/
- migrations/

test commit:
- tests/
```

## Commit Split Examples

```text
feat: add <aggregate> command workflow
test: add unit tests for <aggregate> command workflow

feat: add <capability> api endpoint
test: add system tests for <capability> api endpoint
```

## Exclusion Examples

通常不应进入正式提交的内容：

- 临时文档
- 临时脚本
- 本地调试输出
- 缓存文件
- 私有配置文件
