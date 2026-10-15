# Findings: pgvector 的索引能力与查询特性

## 调研范围
聚焦 pgvector 的向量索引类型、索引构建与查询行为、过滤条件下的检索特性及适用边界；不覆盖部署、性能基准或其他向量数据库比较。

## 关键发现
- pgvector 提供两类近似最近邻索引：HNSW 与 IVFFlat。HNSW 通常以更高的构建时间和内存开销换取较好的查询召回/速度；IVFFlat 构建较快、内存占用较低，但需要训练聚类列表，查询质量与速度受列表数及探测列表数影响。两者均可按距离算子类建立索引，常见距离包括 L2、内积、余弦距离及 L1；索引查询需使用与索引算子类匹配的排序表达式，并以距离升序取近邻。
  来源：https://github.com/pgvector/pgvector
- 不建立 ANN 索引时，向量距离排序可执行精确最近邻搜索；ANN 索引通过减少候选搜索换取近似结果。HNSW 的构建参数包括 `m`、`ef_construction`，查询时可调 `ef_search`；IVFFlat 的构建参数包括 `lists`，查询时可调 `probes`。提高搜索宽度/探测量通常增加召回率与计算成本。HNSW 可在数据为空时建索引；IVFFlat 应在已有数据后建索引，以便聚类训练。
  来源：https://github.com/pgvector/pgvector
- 过滤条件与 ANN 检索组合时，过滤通常在索引候选检索后应用，因此选择性过滤可能导致返回行数少于 `LIMIT`。可通过提高 `ef_search`/`probes`、启用 iterative scans（支持版本中）继续扫描候选，或采用分区、部分索引等方式改善；过滤条件很严格时，精确扫描可能更合适。迭代扫描可设置扫描上限/排序模式，仍需结合数据分布验证召回与成本。
  来源：https://github.com/pgvector/pgvector
- PostgreSQL 官方索引文档指出，索引能加速行定位，但会给数据库整体带来额外开销；PostgreSQL 提供 B-tree、Hash、GiST、SP-GiST、GIN、BRIN 等通用索引类型。pgvector 的 HNSW/IVFFlat 是扩展提供的向量 ANN 索引，不应与 PostgreSQL 内建索引类型混为一谈。索引是否被采用取决于查询表达式、算子类、规划器估算及成本，需用 `EXPLAIN` 检查实际计划。
  来源：https://www.postgresql.org/docs/current/indexes.html
- 适用边界：ANN 结果并非保证精确最近邻；需要严格精确结果时应使用无 ANN 索引的精确排序或对候选结果做精确重排。HNSW 更适合重视查询质量、可承担较高内存/建索引成本的场景；IVFFlat 更适合希望降低资源成本且能合理训练/调参的场景。过滤选择性、数据规模、更新负载、向量维度和召回目标都会影响选型，不能仅凭索引名称断定性能优劣。
  来源：https://github.com/pgvector/pgvector

## 证据与不确定性
pgvector 官方仓库 README 与 PostgreSQL 官方索引章节均已成功抓取，来源可靠。搜索结果未直接返回目标官方页面，因此通过 `web_fetch` 验证并引用其明确返回的 Fetched URL。GitHub 页面抓取内容被截断，以上 pgvector 细节依据官方 README 页面可见内容及其项目文档主题整理；具体参数默认值、版本差异和 iterative scans 的行为应以部署版本 README 为准。本次 PostgreSQL 官方页面是通用索引章节，并不专门说明 pgvector 扩展。未进行实测，性能结论属于定性适用边界，不构成特定工作负载的性能保证。

## 参考来源
- [pgvector 官方 GitHub 仓库](https://github.com/pgvector/pgvector)
- [PostgreSQL 18 官方索引文档](https://www.postgresql.org/docs/current/indexes.html)
