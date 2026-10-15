# Findings: LangChain 官方 Python 消息文档中的工具结果返回语义

## 调研范围
仅覆盖 LangChain 官方 Python 消息文档中工具执行结果如何以 `ToolMessage` 返回、如何通过 `tool_call_id` / `name` 等字段关联，以及工具调用与结果消息在对话消息流中的位置。不涉及工具定义、注册或模型绑定。

## 关键发现
- 官方文档将 `ToolMessage` 定义为表示工具调用输出的消息类型；工具执行结果作为消息加入对话历史，而不是替代模型发出的工具调用消息。
  来源：[Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
- `tool_call_id` 用于将工具结果与发起该工具调用的 AI 消息中的特定工具调用对应起来。文档示例的消息流是：模型返回带工具调用的 `AIMessage`，执行工具后追加含结果的 `ToolMessage`，再将更新后的消息历史交给模型继续生成。
  来源：[Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
- `ToolMessage` 的 `name` 字段可标识产生结果的工具；关联工具调用的关键字段是 `tool_call_id`。结果内容放在消息的 `content` 中。文档还展示了 `artifact` 可承载不必直接呈现给模型的附加工具输出；它与供模型读取的消息内容用途不同。
  来源：[Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
- 工具结果消息属于标准消息流的一部分：模型可在收到工具结果后继续响应，也可能继续发出后续工具调用。因此，工具调用、工具结果和后续模型响应按消息顺序共同构成多轮交互记录。
  来源：[Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)

## 证据与不确定性
已成功抓取用户指定的官方页面，页面内容明确包含消息类型、AI 工具调用、Tool message 及消息流转相关章节。搜索未返回该官方页面，因此依据成功抓取结果引用其 `Fetched URL`。抓取内容被标记为截断，当前可见文本未完整呈现所有字段示例；关于字段用途的摘要以页面可见的工具消息章节信息为依据，未扩展到工具定义或模型绑定。未发现与本主题相关的来源冲突。

## 参考来源
- [Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
