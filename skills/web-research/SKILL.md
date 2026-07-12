---
name: web-research
description: 结构化多来源联网调研，支持并行委派调研员子 Agent
---

# 联网调研技能

当用户要求调研、调查、对比或深度分析某个主题时使用本技能。

> **注意**：本技能是主 Agent 的流程指南，不是子 Agent。联网搜索请委派 `researcher` 子 Agent，**不要**将 `web-research` 作为 subagent_type 调用。合法子 Agent 名称是 `researcher`、`analyst`、`editor`。

## 流程

### 1. 规划

1. 将用户问题写入 `/workspace/sources/question.txt`
2. 创建 `/workspace/sources/research_plan.md`，包含（**中文撰写**）：
   - 主调研问题
   - 2–4 个互不重叠的子主题
   - 每个子主题的预期产出
   - 综合策略

### 2. 委派（可并行）

对每个子主题，用 `task` 工具启动 **researcher（调研员）** 子 Agent：

```text
调研【具体子主题】。可用 write_todos 列出最多 3 条中文步骤（可选）。
使用 web_search 搜索（每个 researcher 最多 3 次；整次运行共享搜索预算，当前默认最多 6 次）。
将 findings 保存到 /workspace/sources/findings_[子主题slug].md（slug 必须全小写，例如 findings_langgraph.md），写入后结束。
禁止使用 CamelCase、*_research.md 或根路径。
```

子主题相互独立时，最多并行 3 个调研员。**总数不超过 3 个。**

### 3. 综合

1. 先 `ls /workspace/sources/`，再读取所有实际存在的 `/workspace/sources/findings_*.md`
2. 整合为连贯分析
3. 定稿前委派 **editor（编辑）** 子 Agent 审阅

## findings 文件要求

每个调研员必须把调研结果写入一个 findings 文件：

```text
/workspace/sources/findings_[子主题slug].md
```

`[子主题slug]` 规则：只允许小写字母、数字、下划线，例如 `langgraph`、`autogen`。
禁止：`findings_LangGraph.md`、`LangGraph_research.md`、`/findings_langgraph.md`。

文件内容必须包含：

```markdown
# Findings: [子主题]

## 调研范围

说明本文件覆盖的子主题边界。

## 关键发现

- 发现 1  
  来源：[URL 或来源名称]

- 发现 2  
  来源：[URL 或来源名称]

## 证据与不确定性

说明证据是否充分、是否存在冲突、是否有信息缺口。

## 参考来源

- [来源标题](URL)
```

## 最佳实践

- 委派前必须先写 `/workspace/sources/research_plan.md`
- 每个调研员只负责一个聚焦子主题
- Agent 之间通过文件传递信息，不要依赖对话历史
- 搜索关键词优先使用中文，专有名词可保留英文
- 不要重复搜索语义相同的关键词
- 关键事实必须保留来源 URL 或来源名称
- 不要编造来源、日期、数字、排名或引用
- 如果证据不足或来源冲突，必须明确说明不确定性
- findings 写入后立即停止，不要继续搜索或改写其他文件

## 来源质量约束

- 如果用户指定了官方来源、政府网站、机构网站或特定来源名称，必须优先检索该官方原始页面。
- 搜索关键词应明确包含官方来源名称，例如“国家统计局 2023 省级 GDP”。
- 如果未检索到官方原始页面，必须在 findings 中明确写出“未检索到官方原始页面”。
- 可以使用第三方来源作为补充证据，但必须标注为第三方来源。
- 禁止将第三方网站、转载页面、媒体文章或聚合平台冒充为官方数据来源。
- 当官方来源和第三方来源冲突时，以官方来源为准；若缺少官方来源，只能给出带不确定性的结论。