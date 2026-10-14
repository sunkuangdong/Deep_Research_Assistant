# Findings: LangChain Python 工具定义与参数 Schema

## 调研范围

聚焦 LangChain 官方 Python 文档中工具的定义与输入参数 Schema：`@tool` 装饰器、类型注解、docstring、显式参数 Schema（包括 Pydantic 与 JSON Schema），以及初学者应留意的使用约束。不涉及其他 Agent 框架或工具调用实现。

## 关键发现

- **联网检索未能取得官方文档正文，以下具体规则无法作为已核实事实陈述。** 本次两次官方站点定向搜索均因搜索服务返回 HTTP 403（配额不足）失败；因此不能可靠确认当前文档对 `@tool` 的参数推断、docstring 格式、Schema 类型支持及版本差异的具体表述。为避免把记忆或非官方资料冒充官方证据，本文件不对这些细节作无来源断言。
  来源：搜索服务错误记录；官方文档入口（待核验）：[LangChain Python 工具文档](https://docs.langchain.com/oss/python/langchain/tools)

- **初学者应将类型注解、docstring 与显式 Schema 的具体要求视为待查证项。** 在无法读取官方原文的情况下，不能据此文件断定哪些字段必填、参数如何映射、何种 docstring 格式会被解析，或 Pydantic/JSON Schema 的兼容范围。实际使用前应以所安装 LangChain 版本对应的官方文档和 API 参考为准。
  来源：[LangChain Python 工具文档](https://docs.langchain.com/oss/python/langchain/tools)（本次未能访问核验）

## 证据与不确定性

本次最多两次联网搜索均失败，未获得可引用的官方页面内容或搜索结果；因此关于 `@tool`、类型注解、docstring、Pydantic、JSON Schema 的具体行为与约束均未完成证据核验。官方文档 URL 仅作为待核验入口列出，不应视为本次已成功检索或验证的证据。需要在搜索服务恢复后直接查阅官方工具指南及相关 API 参考，并按 LangChain 版本确认细节。

## 参考来源

- [LangChain Python 工具文档（官方入口，本文未能联网核验正文）](https://docs.langchain.com/oss/python/langchain/tools)
- 官方站点定向搜索尝试：`site:python.langchain.com/docs how to create tools @tool type hints docstring args_schema Pydantic JSON Schema`（HTTP 403，配额不足）
- 官方站点定向搜索尝试：`site:docs.langchain.com/oss/python/langchain/tools @tool args_schema docstring type hints`（HTTP 403，配额不足）
