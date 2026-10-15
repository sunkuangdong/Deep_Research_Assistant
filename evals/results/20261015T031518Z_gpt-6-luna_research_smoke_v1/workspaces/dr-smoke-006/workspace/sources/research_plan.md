# 调研计划

## 主调研问题
基于 LangChain 官方文档，梳理结构化 Tool Calling 的基本组成：工具定义、参数 Schema、模型绑定、工具结果返回，并形成适合初学者执行的实施清单。

## 子主题与预期产出
1. **工具定义与参数 Schema**：核实官方文档中工具声明、函数签名/类型注解、参数描述及 schema 生成方式。产出：`/workspace/sources/findings_tool_schema.md`。目标来源：LangChain Python 官方文档的 Tools 页面、Structured output/工具相关官方参考页面。
2. **模型绑定与调用流程**：核实模型如何绑定工具、模型返回的 tool call 结构及调用控制方式。产出：`/workspace/sources/findings_model_binding.md`。目标来源：LangChain 官方 Models/Tool calling 页面及 API 参考。
3. **工具执行与结果返回**：核实工具调用执行、ToolMessage/工具结果回传模型的基本循环及结果格式。产出：`/workspace/sources/findings_tool_results.md`。目标来源：LangChain 官方 Tool calling 页面、消息/ToolMessage 官方参考。

## 来源目标与质量要求
至少覆盖 3 个不同的 HTTP(S) 来源链接，优先使用 `python.langchain.com`、`docs.langchain.com` 等 LangChain 官方文档域名；每个 URL 必须来自本轮 web_search 明确返回的 `URL:` 字段，逐字保留。若官方原始页面未检索到，明确标注“未检索到官方原始页面”，不以第三方来源冒充官方资料。

## 综合策略
按“定义工具与 schema → 将工具绑定到模型 → 执行工具并回传结果”的顺序组织证据，区分模型生成 tool call 与应用实际执行工具的职责。最终报告严格使用二级标题 `背景`、`关键发现`、`实施清单`、`局限性`，并在局限性中说明本次按 `--no-analysis` 运行、未进行分析师阶段。