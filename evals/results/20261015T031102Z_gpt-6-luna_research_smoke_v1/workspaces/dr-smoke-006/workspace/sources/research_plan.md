# 调研计划

## 目标
基于 LangChain 官方文档，说明结构化 Tool Calling 的基本组成：工具定义、参数 Schema、模型绑定、工具结果返回，并形成适合初学者的实施清单。优先使用 LangChain 官方文档原始页面；所有引用 URL 必须来自本轮 web_search 返回的完整 URL。

## 来源目标（至少 3 个不同来源）
1. 工具定义与参数 Schema：检索 LangChain 官方工具文档，重点核实 `@tool`、类型注解、docstring、Pydantic/JSON Schema 等定义方式。产出路径：`/workspace/sources/findings_tool_schema.md`。
2. 模型绑定与调用流程：检索 LangChain 官方模型/工具调用文档，核实 `bind_tools`、模型返回的 tool call 结构及调用执行边界。产出路径：`/workspace/sources/findings_model_binding.md`。
3. 工具结果返回与消息语义：检索 LangChain 官方消息/工具文档，核实 ToolMessage、tool_call_id、结果回传模型的流程及相关选项。产出路径：`/workspace/sources/findings_tool_results.md`。

## 方法与约束
- 每个 researcher 只负责一个聚焦子主题，使用不同 findings 路径，不覆盖已有文件。
- 进入分析或起草前，核对 findings 中不同且由本轮搜索返回的 URL 数量；至少 3 个，且优先官方来源。
- 本次运行禁止委派 analyst；最终报告需明确说明“本次按 --no-analysis 运行，未进行分析师阶段（analyst）。”
- 报告文件名日期固定为 `2026-10-14`。
- 最终报告二级标题必须严格为：`## 背景`、`## 关键发现`、`## 实施清单`、`## 局限性`。