# 调研计划

## 主调研问题
基于 LangChain 官方文档，梳理结构化 Tool Calling 的基本组成：工具定义、参数 Schema、模型绑定、工具结果返回，并形成适合初学者的实施清单。

## 子主题与来源页面目标
1. **工具定义与参数 Schema**：核实 `@tool` / `StructuredTool` 的定义方式、类型注解与参数 Schema 约束。目标官方页面：LangChain Python 文档的 Tools 页面（工具定义与 schema 说明）。产出：`/workspace/sources/findings_tool_schema.md`。
2. **模型绑定与调用流程**：核实模型如何绑定工具、工具调用如何由模型返回，以及调用参数/结构化调用的基本流程。目标官方页面：LangChain Python 文档的 Models 页面（Tool calling 章节）。产出：`/workspace/sources/findings_model_binding.md`。
3. **工具结果返回与消息语义**：核实工具执行结果如何回传给模型、工具消息与调用 ID 的关联，以及结果内容的约定。目标官方页面：LangChain Python 文档的 Messages 页面（Tool messages / tool calls 章节）。产出：`/workspace/sources/findings_tool_results.md`。

以上目标为三个不同官方文档页面，不能以同一页面的不同锚点充当多个来源。研究员需分别聚焦各自子主题，记录本轮搜索/抓取成功返回的完整 URL。

## 综合策略
以 LangChain 官方文档为主证据，按“定义工具与输入契约 → 绑定模型并发起调用 → 执行工具并回传结果”的生命周期组织结论。区分模型提出工具调用与应用实际执行工具的责任边界；将初学者清单写成可操作步骤，并标注版本/集成差异及文档未明确处的不确定性。起草前核验至少三个不同的成功检索来源页面。