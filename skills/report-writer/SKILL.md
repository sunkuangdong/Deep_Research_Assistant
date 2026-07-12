---
name: report-writer
description: 将调研结果整理为结构清晰、专业的中文情报报告
---

# 报告撰写技能

将调研 findings、analysis 和 editor feedback 综合为最终交付物时使用本技能。

> **注意**：本技能是主 Agent 的写作指南，不是子 Agent。请主 Agent 亲自用 `write_file` / `edit_file` 撰写和修订报告，**不要**通过 `task` 工具委派 `report-writer`。

## 使用前提

使用本技能前，主 Agent 应先读取以下材料：

- `/workspace/sources/question.txt`
- `/workspace/sources/research_plan.md`
- `/workspace/sources/findings_*.md`
- `/workspace/sources/analysis_*.md`（如有）

## 报告结构

1. **标题** — `# [主题]：情报简报`
2. **执行摘要** — 3–5 条核心要点
3. **背景** — 主题背景与当前重要性
4. **核心发现** — 按主题组织，而非按来源堆砌
5. **分析** — 趋势、影响、风险、机遇、适用场景或取舍
6. **结论** — 直接回答原始问题
7. **局限性** — 说明信息缺口、证据不足或仍需验证的问题
8. **参考资料** — 编号列表，格式 `[标题](URL)`

## 写作规范

- **全文使用中文**（专有名词可保留英文）
- 第三人称专业表述，禁止「我调研了」「我发现」等自述
- 关键论断必须能追溯到 findings 或 analysis
- 重要事实尽量 inline 引用 `[标题](URL)`
- 不要编造来源、URL、数字、排名、日期或引用
- 每节内容充实（多段落），避免一句话带过
- 对比类报告：每项单独一节，再加综合对比节
- 如果证据不足，必须明确写出“不确定”或“仍需进一步验证”
- 如果用户指定官方来源，但 findings 中写明“未检索到官方原始页面”，报告中也必须保留这句话。
- 第三方来源只能标注为第三方来源，禁止冒充或包装成官方数据来源。
- 参考资料章节必须区分官方来源和第三方来源；没有官方来源时，必须明确说明没有检索到官方原始页面。

## 文件命名

- 草稿：`/workspace/reports/draft_[主题slug].md`
- 终稿：`/workspace/reports/report_[主题slug]_[运行日期].md`
- `[主题slug]` 必须全小写 ASCII（`[a-z0-9_]+`），例如 `langgraph_vs_autogen`
- `[运行日期]` 必须使用用户消息中提供的“运行日期”，禁止自行编造日期。
- 读取 findings/analysis 前先 `ls /workspace/sources/`，只使用真实文件名，禁止臆造或改写大小写。

## 工作流程

1. 读取用户原始问题、调研计划和所有 findings 文件。
2. 如存在 analysis 文件，也必须读取。
3. 用 `write_file` 写入草稿：`/workspace/reports/draft_[主题slug].md`。
4. 草稿完成后委派 **editor（编辑）** 审阅。
5. 根据 editor 反馈，用 `edit_file` 或 `write_file` 修订一次。
6. 保存终稿：`/workspace/reports/report_[主题slug]_[运行日期].md`。
7. 最终回复用户时，必须包含：
   - 终稿保存路径
   - 2–3 条核心发现
   - 主要局限性或信息缺口

## 禁止事项

- 禁止把 `report-writer` 当作 subagent_type 调用
- 禁止跳过 findings 直接写最终报告
- 禁止无来源地编造结论
- 禁止无限循环审阅和修订