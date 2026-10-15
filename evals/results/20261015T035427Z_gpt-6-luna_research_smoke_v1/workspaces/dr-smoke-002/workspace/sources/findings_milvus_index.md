# Findings: Milvus 向量索引能力、过滤搜索与查询特性
## 调研范围
聚焦 Milvus 向量索引选择、过滤搜索机制及查询特性。搜索结果未能提供官方向量索引概览页面；尝试抓取的候选地址返回 404，因此索引类型与选择建议无法从本轮可验证来源确认。过滤搜索依据成功抓取的 Milvus 官方文档页面整理。

## 关键发现
- 过滤搜索支持在 ANN 搜索请求中附带元数据过滤条件。标准过滤先筛选符合条件的实体，再在筛选后的实体集合中执行 ANN 搜索并返回 Top-K；适合过滤表达式可有效缩小候选范围的场景。
来源：[Filtered Search | Milvus Documentation](https://milvus.io/docs/filtered-search.md)
- 文档区分标准过滤与迭代过滤。迭代过滤在向量搜索过程中逐个处理候选实体并执行标量过滤，直到达到指定 Top-K；对于复杂过滤表达式，可减少接受标量过滤的实体数量，但逐项处理可能导致较长耗时或性能问题，尤其候选实体较多时。
来源：[Filtered Search | Milvus Documentation](https://milvus.io/docs/filtered-search.md)
- 查询请求可指定过滤表达式、Top-K/limit 和输出字段；文档示例使用 `color like "red%" and likes > 50`，并展示 Python、Java、Go、Node.js 与 REST/cURL 调用形式。迭代过滤示例通过搜索参数 `hints: iterative_filter` 启用。
来源：[Filtered Search | Milvus Documentation](https://milvus.io/docs/filtered-search.md)
- 索引选择方面，本轮未取得可验证的官方索引概览证据，不能据此列举索引类型、参数或按数据规模/召回率/延迟给出选择建议。应以目标 Milvus 版本的索引文档及具体工作负载基准测试补足。
来源：本轮官方索引概览候选抓取失败（HTTP 404），无可引用 URL。

## 证据与不确定性
过滤搜索结论来自成功抓取的官方文档，但页面导航同时显示多个 Milvus 文档版本，抓取内容呈现 v3.0.x 页面，不能保证所有行为和 SDK 参数在其他版本完全一致。索引能力与索引选择缺少可验证来源：搜索未返回目标官方页面，且候选抓取失败；因此不对索引类型、索引构建限制或性能特征作事实性断言。过滤机制的性能描述是文档给出的定性说明，未提供量化阈值或跨场景基准。

## 参考来源
- [Filtered Search | Milvus Documentation](https://milvus.io/docs/filtered-search.md)
