# 调研计划

## 主调研问题
基于 LangChain 官方文档，梳理结构化 Tool Calling 的基本组成：工具定义、参数 Schema、模型绑定、工具结果返回，并形成适合初学者的实施清单。

## 子主题与来源页面目标
1. **工具定义与参数 Schema**：核实 `@tool` / `StructuredTool` 的定义方式、类型注解与参数 Schema 约束。目标官方页面：LangChain Python 工具概念文档（`https://docs.langchain.com/oss/python/langchain/tools`）。产出：`/workspace/sources/findings_tool_schema.md`。
2. **模型绑定与调用流程**：核实模型如何绑定工具、模型输出的 tool call 结构及执行流程。目标官方页面：LangChain Python 模型工具调用文档（`https://docs.langchain.com/oss/python/langchain/models`）。产出：`/workspace/sources/findings_model_binding.md`。
3. **工具结果返回与消息语义**：核实工具执行结果如何作为 ToolMessage 返回、工具调用 ID/名称等关联信息。目标官方页面：LangChain Python 消息文档（`https://docs.langchain.com/oss/python/langchain/messages`）。产出：`/workspace/sources/findings_tool_results.md`。

## 综合策略
优先使用 LangChain 官方文档原始页面，分别由不同 researcher 调研不同子主题和页面，避免重复页面。综合时区分模型生成调用请求与应用执行工具两个阶段，提炼初学者可操作的步骤，并标注文档版本/提供商差异及证据边界。按本次 no-analysis 运行约束，不委派 analyst、不创建 analysis 文件；起草前核对 findings 中至少 3 个不同且本轮验证的 URL 页面。最终报告使用指定的四个二级标题，并包含至少 3 个不同 HTTP(S) 来源链接。