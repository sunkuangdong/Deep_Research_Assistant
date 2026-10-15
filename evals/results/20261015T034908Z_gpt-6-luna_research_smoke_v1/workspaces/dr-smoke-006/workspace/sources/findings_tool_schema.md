# Findings: LangChain 官方 Python 工具定义与参数 Schema

## 调研范围
仅覆盖 LangChain 官方 Python 文档中工具的定义方式及输入参数 Schema，包括 `@tool`、函数类型注解、docstring、工具名称/描述自定义，以及通过 Pydantic 或 JSON Schema 声明复杂输入。未涉及模型绑定、工具调用流程或结果消息。

## 关键发现
- 官方文档将工具描述为具有明确输入和输出的可调用函数；最简单的定义方式是使用 `langchain.tools` 中的 `@tool` 装饰器。默认情况下，函数名作为工具名，函数 docstring 作为工具描述。
  来源：[Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- 类型注解是必需的，因为它们用于定义工具的输入 Schema。文档示例以 `query: str` 和带默认值的 `limit: int = 10` 展示参数类型与默认值；docstring 应简洁且信息充分，以帮助模型理解工具用途，并可用 `Args` 说明参数。
  来源：[Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- 可通过 `@tool("自定义名称")` 覆盖默认工具名，也可通过 `@tool(..., description="...")` 显式覆盖自动生成的工具描述。
  来源：[Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- 复杂输入可用 Pydantic 模型或 JSON Schema 定义，并通过 `@tool(args_schema=...)` 指定参数 Schema。文档展示 Pydantic `BaseModel`、`Field` 描述、默认值及 `Literal` 约束等写法。
  来源：[Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
- 官方建议工具名优先使用 `snake_case`；为提高不同模型提供方的兼容性，名称宜限于字母数字、下划线和连字符，避免空格或特殊字符。
  来源：[Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)

## 证据与不确定性
已成功读取用户指定的 LangChain 官方工具文档，页面内容明确覆盖上述定义与 Schema 要点。页面抓取内容被截断，因此未据此扩展到未完整呈现的细节；本文件仅记录可见内容。搜索结果未提供该官方页面，但通过 `web_fetch` 成功核验。所有引用均指向本轮成功返回的 `Fetched URL:`，且仅使用一个官方页面来源。

## 参考来源
- [Tools - Docs by LangChain](https://docs.langchain.com/oss/python/langchain/tools)
