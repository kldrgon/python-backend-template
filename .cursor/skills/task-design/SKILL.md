---
name: task-design
description: Performs a lightweight preflight triage and designs implementation tasks before coding. Use when the user asks for approach first, requirements are still fuzzy, multiple approaches exist, changes span multiple files or layers, or you need to decide whether to clarify, document, or execute next.
---

# Task Design

## Use When

- 用户刚提出一个开发需求，需要先判断现在该澄清、写文档还是进入执行
- 用户要你先说思路、方案、拆分方式，再开始编码
- 需求还不够清楚
- 同一目标存在多种可选实现
- 改动会跨多个目录、多个层次或多个 commit
- 开始开发前需要先定边界、顺序、风险或验收标准

## Core Goal

本 skill 是编码前的总入口。

它先做轻量分流，再做任务设计，但不直接进入实现。

## Preflight Gate

开始设计前，先快速判断下面几件事：

1. 当前问题属于哪一类：
   - 需求澄清
   - 方案设计
   - 文档沉淀
   - 长流程执行前准备

2. 当前信息是否已经足够：
   - 目标是否明确
   - 范围是否明确
   - 约束是否明确
   - 验收是否明确

3. 当前更适合进入哪一步：
   - 继续在本 skill 内澄清和设计
   - 转入 `design-doc` 形成按界限上下文做设计选择的草案或正式文档
   - 转入 `branch-workflow` 进入长流程执行

4. 在真正编码前，至少确认：
   - 当前任务目标
   - 当前任务边界
   - 当前建议路线
   - 当前待确认项

Preflight 只做最小分流，不重复项目全部规则细节。

## Design Checklist

开始设计时，先完成下面几步：

1. 澄清目标：
   - 这次到底要解决什么问题
   - 预期结果是什么
   - 明确“不做什么”

2. 识别约束：
   - 现有架构边界
   - API、命名、测试、提交等项目规则
   - 必须保留的兼容性或存量约束

3. 划定范围：
   - 会影响哪些目录、模块、层次
   - 哪些改动属于本次任务
   - 哪些改动应延后处理

4. 给出方案：
   - 默认给出一个推荐方案
   - 如果确实存在关键分歧，再列备选方案
   - 说明为什么推荐当前方案

5. 拆分任务：
   - 拆成可以独立理解和执行的步骤
   - 标出先后顺序
   - 标出哪些步骤需要用户先确认

6. 定义验收：
   - 改完后应看到什么结果
   - 需要哪些验证方式

## Decision Outcomes

完成本 skill 后，结论通常只有三种：

1. 继续澄清：
   - 关键信息仍不足
   - 先停下并向用户确认

2. 形成文档：
   - 当前结论已经值得沉淀
   - 需要把各界限上下文是否采用领域模型的选择写成可确认设计稿
   - 转入 `design-doc`

3. 进入执行准备：
   - 目标、边界和路径已经足够清晰
   - 如果是长流程，转入 `branch-workflow`

## Required Behavior

- 先做最小 preflight，再输出简短思路。
- 如果关键信息不足，先问，不擅自假设。
- 如果需求还不稳定，不把未确认内容写成定稿结论。
- 如果需要留痕或评审，明确提示转入 `design-doc`。
- 如果需要把界限上下文级别的设计选择写清楚，优先转入 `design-doc`。
- 如果任务明显是长流程，设计完成后提示进入 `branch-workflow`。
- 如果任务已足够明确，避免过度设计。
- 方案比较只保留真正有价值的分歧，不堆无关选项。

## Output Pattern

优先按这个格式输出：

```text
分流判断：
- 当前更适合：<继续澄清 / 形成文档 / 进入执行准备>

目标：
- <一句话说明要解决什么>

边界：
- 做什么
- 不做什么

方案：
- 推荐做法：<一句话>
- 原因：<一句话>

任务拆分：
1. <步骤一>
2. <步骤二>
3. <步骤三>

待确认：
- <需要用户确认的点>

验收：
- <怎么判断完成>

下一步：
- <进入 design-doc / 进入 branch-workflow / 继续澄清>
```

## Handoff

设计完成后，按任务类型提示后续应参考的 skill：

- 需要按项目静态规则判断落点：`project-structure-and-rules`
- 进入长流程分支执行：`branch-workflow`
