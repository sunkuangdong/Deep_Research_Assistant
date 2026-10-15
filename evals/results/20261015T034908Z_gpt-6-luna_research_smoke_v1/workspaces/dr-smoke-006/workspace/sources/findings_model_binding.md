# Findings: LangChain 官方 Python 模型绑定与工具调用流程

## 调研范围

仅覆盖 LangChain 官方 Python 模型文档中模型如何绑定工具、模型如何返回工具调用请求，以及模型调用与应用执行工具之间的边界。不涉及工具定义细节，也不讨论 `ToolMessage` 的结果语义。

## 关键发现

- LangChain 的模型接口支持工具调用；模型可通过 `bind_tools` 接收可用工具集合。绑定的作用是将工具信息提供给模型，使模型能够在响应中提出工具调用请求；这一步本身不等同于应用执行工具。
  来源：[Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)
- 模型响应可能包含工具调用请求（tool calls），其中表达模型希望调用的工具及相应参数。该响应是模型输出的一部分，应用需要读取并处理这些请求。
  来源：[Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)
- 工具执行边界在应用侧：模型负责决定是否请求调用工具，实际执行由应用或 agent 流程负责；执行结果之后可再交由模型继续处理。单独调用模型并不会自动意味着工具已被执行。
  来源：[Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)
- 官方文档将模型描述为 agent 的推理引擎，并区分直接独立调用模型与在 agent 中使用模型；agent 流程可围绕模型决策和工具调用组织后续步骤。
  来源：[Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)

## 证据与不确定性

已成功抓取用户指定的官方 Python 模型文档，确认其页面涵盖模型接口、工具调用及独立模型与 agent 使用方式。抓取内容被截断，未能在返回文本中完整核对 `bind_tools` 及工具调用流程的具体段落，因此上述流程性概括应视为官方页面主题与接口说明层面的摘要；未引用非官方来源补足细节。搜索结果未返回可用的官方页面 URL，故仅引用成功抓取并明确返回的官方页面 URL。

## 参考来源

- [Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)
