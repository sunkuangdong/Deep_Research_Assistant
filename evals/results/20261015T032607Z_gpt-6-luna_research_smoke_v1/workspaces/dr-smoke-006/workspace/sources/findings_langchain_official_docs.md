# Findings: LangChain 官方工具定义、Schema 与模型工具调用

## 调研范围
本文件聚焦 LangChain 官方 Python 文档中工具的定义方式、输入 Schema、模型绑定/工具调用及工具结果返回。仅记录本轮工具成功抓取并明确返回的官方 URL；不覆盖其他 LangChain 主题。

## 关键发现
- 工具是具有明确输入和输出的可调用函数，会传递给聊天模型；模型根据对话上下文决定是否调用工具以及提供哪些输入参数。官方文档将工具调用描述为模型与外部工具交互的能力。
  来源：[Tools](https://docs.langchain.com/oss/python/langchain/tools)；[Models（tool-calling 锚点）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- 最简工具定义可使用 `@tool` 装饰器。函数类型注解是必需的，用于定义输入 Schema；函数 docstring 默认作为工具描述，帮助模型判断何时使用工具。工具名默认取函数名，也可自定义名称和描述；文档建议使用 `snake_case`，并避免空格或特殊字符以提高不同模型提供方的兼容性。
  来源：[Tools](https://docs.langchain.com/oss/python/langchain/tools)
- 复杂输入可通过 Pydantic 模型或 JSON Schema 定义。官方示例展示字段类型、默认值、枚举约束及字段描述，并通过 `args_schema` 将 Pydantic 模型指定为工具参数 Schema。
  来源：[Tools](https://docs.langchain.com/oss/python/langchain/tools)
- 模型可通过标准模型接口初始化；文档说明模型既可在 agent 中使用，也可独立调用。模型工具调用能力用于调用外部工具（例如数据库查询或 API），并在响应中利用工具结果。模型在 agent 中承担决策角色，包括决定调用哪些工具、如何解释结果以及何时给出最终答复。
  来源：[Models（tool-calling 锚点）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
- 工具文档目录明确列出多种工具返回形式：字符串、对象、多模态内容、`Command`，以及工具直接返回和带 `return_direct` 的 `Command` 等路径。因此，工具结果不局限于纯文本；具体返回形式应按调用流程和所需状态/控制行为选择。
  来源：[Tools](https://docs.langchain.com/oss/python/langchain/tools)
- 本轮抓取的 Tools 页面内容被标记为截断，但返回文本明确包含工具定义、Schema 示例开头及结果返回章节目录；Models 页面抓取也被标记为截断，返回内容确认模型工具调用的总体作用，但未完整呈现该章节的全部细节。
  来源：[Tools](https://docs.langchain.com/oss/python/langchain/tools)；[Models（tool-calling 锚点）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)

## 证据与不确定性
证据来自 LangChain 官方文档页面的成功抓取，足以支持工具定义、类型注解与 Schema、模型工具调用的基本机制，以及工具结果存在多种返回形式等概括。由于抓取结果标记为截断，本轮未能核实工具结果各形式的完整语义、具体消息结构、模型绑定 API 的完整参数与调用示例，也未能确认不同模型提供方之间的行为差异；因此不对这些细节作进一步断言。搜索结果未提供可引用的官方页面 URL，故来源仅采用本轮 `web_fetch` 明确返回的 `Fetched URL`。

## 参考来源
- [Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- [Models - Docs by LangChain（tool-calling 锚点）](https://docs.langchain.com/oss/python/langchain/models#tool-calling)
