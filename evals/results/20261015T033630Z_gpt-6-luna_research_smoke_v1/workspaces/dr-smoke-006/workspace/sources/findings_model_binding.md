# Findings: LangChain 模型绑定与工具调用流程

## 调研范围
聚焦 LangChain Python Models 文档中 Tool calling 的说明：模型如何通过 `bind_tools` 接收工具定义、模型返回的 tool call 数据结构，以及模型提出调用与应用实际执行工具之间的责任边界。不涉及其他模型能力或其他研究员目标页面。

## 关键发现
- LangChain 的工具调用是模型接口的一种能力：应用将工具定义绑定到聊天模型，再调用模型；模型可在响应中提出工具调用请求。绑定工具是向模型提供可用工具的描述/模式，并不等于工具已经执行。
  来源：[LangChain Models 文档（Tool calling 章节）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- 模型返回的工具调用信息位于 `AIMessage` 的 `tool_calls` 字段中。每个调用包含工具名称、参数（通常为结构化参数对象）及调用标识等信息；它是模型生成的调用请求，而不是工具函数的返回值。
  来源：[LangChain Models 文档（Tool calling 章节）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- `bind_tools` 负责把工具定义绑定到模型，使模型能够按工具 schema 生成调用请求；模型本身只决定是否请求调用以及生成参数。实际执行工具、处理执行结果并将结果继续交给模型，属于应用/agent 执行循环的职责。若直接单独调用模型，调用方需自行处理返回的 tool call；使用 agent 时由 agent 循环协调工具执行与后续模型调用。
  来源：[LangChain Models 文档（Tool calling 章节）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)

## 证据与不确定性
本轮搜索未直接返回目标官方页面；随后成功抓取 LangChain 官方 Models 页面，并在页面内容中确认其包含 Tool calling 章节。抓取内容被截断，未完整呈现该章节的代码示例及字段细节，因此关于 `tool_calls` 字段组成的描述限于页面可核实的通用结构，未扩展到具体 provider 的差异。官方页面明确区分模型生成调用请求与实际工具执行；不同集成对调用参数、标识及返回消息的具体表示可能存在差异，应以对应 provider 文档为准。

## 参考来源
- [Models - Docs by LangChain（Tool calling 章节）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
