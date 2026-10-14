# Findings: LangChain 模型工具绑定与工具结果返回

## 调研范围
聚焦 LangChain 官方文档中模型的 `bind_tools`/工具调用、AI 消息中的工具调用结构、工具执行后以 `ToolMessage` 返回结果，以及文档对结果内容、状态和错误处理的说明。不覆盖具体供应商模型的完整差异或第三方工具实现。

## 关键发现
- LangChain 的工具调用流程由模型提出调用、应用执行工具、再将工具结果交回模型组成；模型本身通常不会直接执行工具。工具调用是结构化数据，而非仅靠模型文本输出表达。  
来源：[LangChain — Tool calling](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- `bind_tools` 用于将工具定义绑定到聊天模型，使模型能够按工具 schema 生成调用。工具可由 LangChain 工具、函数或兼容的工具定义提供；具体支持形式和参数因模型集成而异。  
来源：[LangChain — Tool calling](https://docs.langchain.com/oss/python/langchain/models#tool-calling)；[ChatOpenAI — Tool calling](https://python.langchain.com/docs/integrations/chat/openai/#tool-calling)
- 模型响应中的工具调用通常位于 `AIMessage.tool_calls`，每项包含工具名 `name`、参数对象 `args` 和调用标识 `id`；模型可在一次响应中提出一个或多个调用。`AIMessage` 还可能包含 `content`，因此工具调用与普通文本内容并非互斥。  
来源：[LangChain — Tool calling](https://docs.langchain.com/oss/python/langchain/models#tool-calling)；[Messages](https://docs.langchain.com/oss/python/langchain/messages)
- 工具执行后，结果以 `ToolMessage` 追加到对话中，并通过 `tool_call_id` 与对应的模型调用关联。随后可将包含工具结果的消息历史再次传给模型，以生成面向用户的后续答复。  
来源：[LangChain — Tool calling](https://docs.langchain.com/oss/python/langchain/models#tool-calling)；[Messages](https://docs.langchain.com/oss/python/langchain/messages)
- `ToolMessage.content` 承载工具结果；消息还可包含 `name`、`tool_call_id`、`status` 等字段。文档所述状态可用于区分成功与错误（例如 `success`/`error`）；工具结果也可通过 `artifact` 携带不必作为模型可见文本传递的附加数据。  
来源：[Messages](https://docs.langchain.com/oss/python/langchain/messages)
- 工具调用参数应按工具 schema 解析和校验；工具执行错误的具体捕获、重试或转成错误消息的策略取决于调用方式/Agent 配置。官方工具文档说明可通过 `ToolMessage` 表达错误状态，但并未规定所有模型绑定调用都自动采用统一错误处理策略。  
来源：[Messages](https://docs.langchain.com/oss/python/langchain/messages)；[LangChain — Tools](https://docs.langchain.com/oss/python/langchain/tools)

## 证据与不确定性
本次按要求尝试联网搜索官方原始文档两次，但搜索服务均返回 HTTP 403（额度/配额不足），无法通过搜索结果核验页面当前内容。以上引用为 LangChain 官方文档的规范页面 URL，结论依据其公开文档结构与 API 说明整理；不同模型集成对 `bind_tools` 参数、工具调用字段映射及多模态结果的支持可能不同。错误处理尤其依赖具体执行器或 Agent，不能据此推断所有调用路径会自动捕获异常或重试。

## 参考来源
- [LangChain — Tool calling](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- [LangChain — Messages](https://docs.langchain.com/oss/python/langchain/messages)
- [LangChain — Tools](https://docs.langchain.com/oss/python/langchain/tools)
- [ChatOpenAI — Tool calling](https://python.langchain.com/docs/integrations/chat/openai/#tool-calling)
