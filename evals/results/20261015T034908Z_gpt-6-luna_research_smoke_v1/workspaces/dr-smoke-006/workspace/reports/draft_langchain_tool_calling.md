# LangChain 结构化 Tool Calling 入门调研报告

## 背景

结构化 Tool Calling 是模型与应用中可执行能力之间的接口：开发者定义工具及其输入结构，将工具描述绑定给模型；模型在需要时返回结构化的调用请求；应用执行对应工具，再把结果作为消息交回模型或对话流程。它不是“模型直接运行任意代码”，而是由模型提出调用意图、应用负责执行与控制。

本报告依据 LangChain 官方 Python 文档，聚焦工具定义、参数 Schema、模型绑定和工具结果返回，并将这些组成转化为初学者实施清单。主要依据为官方 [Tools](https://docs.langchain.com/oss/python/langchain/tools)、[Models](https://docs.langchain.com/oss/python/langchain/models) 与 [Messages](https://docs.langchain.com/oss/python/langchain/messages) 文档；三者是不同页面来源。

## 关键发现

### 1. 工具定义：让用途和输入对模型可理解

LangChain 官方文档将工具视为具有明确输入和输出的可调用函数。Python 中可用 `@tool` 装饰器定义工具；默认情况下，函数名成为工具名，函数 docstring 成为工具描述。可通过装饰器参数自定义名称和描述。工具名建议采用 `snake_case`，并避免空格或特殊字符，以提高不同模型提供方之间的兼容性。

工具描述不仅是代码注释，也是模型判断何时调用工具的重要上下文。应准确说明工具能做什么、适用边界及参数含义，避免含糊或夸大能力。来源：[LangChain Tools 文档](https://docs.langchain.com/oss/python/langchain/tools)。

### 2. 参数 Schema：用类型和约束表达输入契约

函数参数的类型注解用于定义工具输入 Schema；默认值可表达可选参数及其默认行为。简单工具可直接使用类型注解，复杂输入可通过 Pydantic `BaseModel` 或 JSON Schema 声明，并通过 `args_schema` 指定。Pydantic 字段描述、默认值及 `Literal` 等约束可进一步明确允许的输入。

对初学者而言，Schema 应尽量窄而明确：只暴露工具真正需要的参数，为参数提供清晰类型和描述，对有限选项使用约束，并在工具实现中继续进行必要的校验。Schema 帮助模型生成结构化参数，但不应被视为安全边界或业务校验的替代品。来源：[LangChain Tools 文档](https://docs.langchain.com/oss/python/langchain/tools)。

### 3. 模型绑定：模型提出调用请求，应用负责执行

LangChain 模型接口支持通过 `bind_tools` 将可用工具信息提供给模型。模型响应可能包含工具调用请求及其参数；这表示模型希望调用某个工具，并不意味着工具已经执行。实际执行发生在应用或 agent 流程中：应用读取请求、选择并调用相应工具，再处理执行结果。需要说明的是，本轮抓取的模型文档内容被截断，未能完整核对 `bind_tools` 及具体调用流程细节；这里是基于 findings 中可见接口说明与流程概述的总结，不代表所有模型集成的行为完全一致。

因此，实施时要明确区分“绑定工具”“模型生成调用请求”和“应用执行工具”三个动作。不能仅因模型响应中出现 tool call 就假定外部操作已完成。来源：[LangChain Models 文档](https://docs.langchain.com/oss/python/langchain/models)。

### 4. 工具结果返回：用 ToolMessage 关联调用并续接消息流

工具执行后，结果可作为 `ToolMessage` 加入对话历史。`content` 承载供模型读取的结果；`tool_call_id` 将结果关联到先前 AI 消息中的具体工具调用，`name` 可标识产生结果的工具。官方消息示例展示了“带工具调用的 AI 消息 → 工具执行 → ToolMessage → 将更新后的消息历史交回模型”的流程。工具结果之后，模型可以继续回答，也可能提出后续工具调用。

这意味着结果返回不是孤立的字符串传递，而是带有调用关联信息的消息流转。若工具还产生不必直接提供给模型的附加数据，文档也展示了 `artifact` 用于承载这类信息；应区分模型可见内容与应用侧附加产物。来源：[LangChain Messages 文档](https://docs.langchain.com/oss/python/langchain/messages)。

## 实施清单

1. **先界定工具职责**：每个工具只做一件清晰的事，明确输入、输出、副作用和失败情形；对写入、支付、发送等有副作用的操作设置应用侧授权与确认机制。
2. **定义工具函数**：使用 `@tool` 暴露函数；选择清晰、稳定的工具名，优先 `snake_case`，避免空格和特殊字符。
3. **编写高质量描述**：用简洁 docstring 说明工具用途、适用条件、参数含义和限制；不要让描述暗示工具具备实际不支持的能力。
4. **声明参数 Schema**：为参数添加准确类型注解和必要默认值；复杂输入使用 Pydantic 或 JSON Schema，并通过 `args_schema` 指定；对枚举值、范围和必填项尽可能明确约束。
5. **在实现中校验输入**：Schema 之外仍需检查权限、业务规则、资源存在性、边界值和异常；不要把模型生成的参数当作可信输入。
6. **将工具绑定给模型**：通过模型接口的 `bind_tools` 提供工具集合；确认所用模型提供方及其集成支持相应的工具调用能力。
7. **处理模型响应**：检查响应是否包含 tool calls，读取工具名称和结构化参数；处理无调用、多个调用、未知工具、参数错误等情况，不要把调用请求误当成执行结果。
8. **由应用执行工具**：在受控的应用或 agent 流程中分派并执行工具；对超时、异常、重试和副作用进行显式处理。
9. **构造并追加结果消息**：将执行结果放入 `ToolMessage.content`，并用对应的 `tool_call_id` 关联原调用；需要时标明工具 `name`，并谨慎区分模型可见结果与 `artifact` 等附加数据。
10. **续接并测试完整消息流**：把包含工具结果的消息历史交回模型或流程，验证模型能正确总结结果或继续调用；测试正常、无调用、错误参数、工具失败及多步调用场景。
11. **检查可观测性与安全性**：记录必要的调用、结果状态和错误信息，避免泄露敏感数据；对高风险工具实施最小权限、审计和人工确认。

## 局限性

本报告以 LangChain 官方 Python 文档为依据，未覆盖 JavaScript/TypeScript API、特定模型提供方的工具调用差异、agent 执行器的完整配置，也未提供可直接运行的端到端代码。官方文档页面抓取内容存在截断，尤其模型绑定流程的具体细节未能在本轮可见文本中完整核对；因此报告只概括文档支持的接口与消息语义，不推断所有集成的行为完全一致。实际项目应结合所用 LangChain 版本、模型集成文档和运行测试验证。

本次按 --no-analysis 运行，未进行分析师阶段（analyst）。

参考资料均为本轮成功抓取并记录的 LangChain 官方页面：
- [Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- [Models - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/models)
- [Messages - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/messages)
