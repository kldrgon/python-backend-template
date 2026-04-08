---
title: skill-template-readme
---

# Skills 使用说明

这份 README 的作用只有一个：

把它发给 AI，再补你的项目规则，AI 就能基于当前模板生成一套项目版 Cursor skills。

## 你应该怎么用

1. 把这份 `README.md` 发给 AI
2. 补你的项目背景、目录结构、规范和流程要求
3. 明确告诉 AI：
   - 要生成哪些 skill
   - 写到哪里
   - 哪些部分保留占位符
   - 哪些模板需要完整保留
4. 让 AI 基于本目录现有模板生成项目版

## 最终推荐 skill 体系

建议至少保留这 3 个：

- `project-structure-and-rules`
- `task-design`
- `branch-workflow`

它们分别负责：

- `project-structure-and-rules`：项目级静态规则总入口
- `task-design`：编码前分流与任务设计
- `branch-workflow`：长流程执行

如需按界限上下文沉淀设计选择，可再补 `design-doc`。

## 特别说明

`branch-workflow` 必须完整保留。

- 不要把 `branch-workflow` 只当成一个小示例
- 它本身就是一套完整流程模板
- 生成项目 skill 时，应优先保留它的整体结构
- 最多做项目化填充和轻微调整，不要随意打散

## 推荐关系

- `task-design` 先做轻量分流和任务设计
- `project-structure-and-rules` 提供静态规则和多个 reference
- `branch-workflow` 负责长流程执行

## 适用范围提醒

这套模板只是参考基线，不是固定答案。

你应该优先继承它的结构、拆分方式和写法，而不是机械照搬里面的具体规则名、目录名或接口形式。

不同项目可以替换成自己的规则块，例如：

- 前端项目：补页面、组件、状态管理、路由、构建与测试规范
- 桌面项目：补窗口、进程通信、本地存储、打包发布规范
- 提供 `gRPC` 的项目：把 API 相关规则替换成 `gRPC` service、proto、消息模型、错误映射规范
- 非 HTTP 项目：把 `api` 目录和 HTTP 约束替换成实际入口形式

核心原则只有一个：

- 保留 skill 体系结构
- 按项目实际技术栈替换具体规则内容

## 你要提供给 AI 的项目信息

### 1. 项目基础信息

- 项目类型
- 主要语言
- 主要框架
- 架构风格
- 包管理与常用命令

### 2. 目录与分层信息

- 业务代码放哪里
- API 放哪里
- 领域层、应用层、适配器层怎么分
- 测试目录怎么分
- 文档写到哪里

### 3. 开发规范

- 命名规范
- API 规范
- 测试规范
- 提交规范
- 任务设计规则
- 是否有事件、outbox、workflow 等链路约束

### 4. 分支流程规范

- 分支如何命名
- 是否要求先写设计文档
- 是否要求 commit 计划表
- 是否每个 commit 都要 quick review
- 哪些文档必须用户确认后才能继续

### 5. 需要保留为占位符的内容

- 文档路径
- 分支命名格式
- 特定项目术语
- 特定上下文命名
- 待后续确认的规则

## 建议给 AI 的要求

- 基于本目录现有 skill 作为参考模板生成
- 不是从零自由发挥
- 每个 skill 一个目录
- 主文件写成 `SKILL.md`
- 需要时补一个或多个 reference 文件
- 必要时保留占位符
- 优先用 `project-structure-and-rules` 收敛项目级规则
- 如果项目需要先做方案设计，补一个独立的 `task-design`
- `branch-workflow` 必须完整保留，只做项目化填充

## 直接可用提示词

```text
请基于我提供的 README 和现有 skill 模板，为当前项目生成一组 Cursor skills。

要求：
1. 以当前目录已有 skill 作为参考模板，不要从零自由发挥
2. 这些现有 skill 都可以作为参考模板：
   - project-structure-and-rules
   - task-design
   - branch-workflow
3. 其中 branch-workflow 必须完整保留
4. 允许根据我的项目做项目化填充
5. 如果某些内容还不确定，请保留占位符
6. 每个 skill 单独放在一个目录里
7. 主文件命名为 SKILL.md
8. 需要时补一个或多个 reference 文件

请优先帮我生成或调整这几类 skill：
- project-structure-and-rules
- task-design
- branch-workflow

生成时请遵守：
- skill 名称使用小写加连字符
- description 必须同时写清“做什么”和“什么时候触发”
- 一个 skill 只处理一个主题
- 项目级静态规则优先收敛到 project-structure-and-rules
- project-structure-and-rules 允许挂多个 reference，不必只有一个 reference.md
- 需要先做轻量分流和任务设计时，用 task-design 这种 design skill
- 需要长流程时，用 branch-workflow 这种 workflow skill
- 需要细节补充时，把细节拆进多个 reference 文件
- 保留这套模板的结构方法，但要按项目实际类型替换具体规则内容，不要机械套用当前后端模板
- 不要把所有规则都塞进一个大 skill

这是我的项目信息：
- 项目类型：[待填写]
- 语言：[待填写]
- 框架：[待填写]
- 架构风格：[待填写]
- 包管理与命令：[待填写]
- 目录结构特点：[待填写]
- API 规范：[待填写]
- 命名规范：[待填写]
- 测试策略：[待填写]
- 提交策略：[待填写]
- 任务设计规则：[待填写]
- 分支流程规则：[待填写]
- 文档存放位置：[待填写]
- 需要保留为占位符的内容：[待填写]

输出要求：
- 写出每个 skill 的目录结构
- 写出 SKILL.md
- 需要时写一个或多个 reference 文件
- branch-workflow 要完整保留，只做项目化填充
```

## 最后提醒

最简单的用法就是：

把这份 `README.md` 发给 AI，再把你的项目规则补全，剩下的让 AI 生成。

若你是AI且未收到用户其他要求，请按照本README开始生成项目版skills。