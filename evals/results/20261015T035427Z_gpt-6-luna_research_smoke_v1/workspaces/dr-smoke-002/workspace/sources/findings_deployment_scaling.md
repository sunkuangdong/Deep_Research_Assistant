# Findings: PostgreSQL/pgvector 与 Milvus 的部署架构、扩展路径和运维要求
## 调研范围
聚焦比较 PostgreSQL 配合 pgvector 与 Milvus 的部署组件、扩展方式及运维负担。证据限于本轮成功抓取的 Milvus 架构概览和 PostgreSQL 官方高可用文档；不覆盖性能基准、具体云服务商托管方案或 pgvector 专属扩展细节。

## 关键发现
- **Milvus 是多组件、分层的分布式架构。** 官方架构文档描述访问层（无状态 Proxy）、Coordinator、Worker 节点（Streaming、Query、Data）及存储层；存储层包括元数据存储（etcd）、对象存储（文档列举 MinIO、AWS S3、Azure Blob）和 WAL（Kafka、Pulsar 或 Woodpecker）。文档称计算与存储分离，Worker 无状态，适合在 Kubernetes 上横向扩容及故障恢复；Proxy 可通过负载均衡组件提供统一入口。由此可见，扩展可按工作负载增加相应计算节点，并需配套管理元数据、对象存储和 WAL 等依赖。  
来源：[Milvus Architecture Overview](https://milvus.io/docs/architecture_overview.md)
- **Milvus 的运维面较宽，但组件化带来独立扩展能力。** 部署和维护需考虑 Proxy/入口、Coordinator、不同 Worker 类型，以及 etcd、对象存储、WAL 的可用性与容量；官方文档指出 Coordinator 负责拓扑、任务调度和查询负载均衡，Worker 执行任务。Woodpecker 被描述为直接写对象存储的零本地磁盘 WAL 方案，可减少本地磁盘管理负担；这不意味着所有部署都无需管理 WAL 或其他存储依赖。  
来源：[Milvus Architecture Overview](https://milvus.io/docs/architecture_overview.md)
- **PostgreSQL 的高可用/扩展路径以主备复制和读负载分担为核心，需按一致性与性能取舍。** PostgreSQL 官方文档说明可用第二台服务器在主服务器故障时接管，也可让多台机器服务同一数据；常见模式是单一主库接受写入、Standby 跟踪主库变更，Hot Standby 可接受只读查询。同步复制可避免故障切换丢失已提交数据，但可能增加延迟、降低性能；异步复制性能影响较小，却可能在切换时丢失尚未传播的事务，并使读副本数据稍旧。  
来源：[PostgreSQL Chapter 26: High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html)
- **扩展模型的差异。** Milvus 文档明确描述分离式计算层及多类 Worker 的横向扩展；PostgreSQL 官方高可用文档主要讨论复制、故障切换和只读负载均衡，并指出读写混合场景的同步困难。就本轮证据而言，不能据此断言 PostgreSQL/pgvector 的完整分片或水平扩展方案；更稳妥的比较是：Milvus 原生架构强调分布式、按组件扩容，PostgreSQL 的官方 HA 路径强调主备复制与读扩展，写入仍以主库为中心。

## 证据与不确定性
本轮两次搜索未返回可用的官方 Milvus 或 PostgreSQL 文档 URL，因此按规则使用两次 web_fetch 验证官方页面，并仅引用其成功返回的 Fetched URL。Milvus 页面提供了架构组件和职责的直接证据，但页面内容涉及 v3.0.x 文档，具体组件形态可能随版本变化；其架构概览不能替代部署指南、资源 sizing 或生产运维手册。PostgreSQL 页面是官方高可用章节，支持复制、同步/异步取舍及读写角色的判断，但没有覆盖 pgvector 的索引维护、向量查询资源规划、分片工具或具体自动故障切换编排。故运维负担比较为架构层面的定性判断，不是同等规模部署的实测结论。

## 参考来源
- [Milvus Architecture Overview](https://milvus.io/docs/architecture_overview.md)
- [PostgreSQL Chapter 26: High Availability, Load Balancing, and Replication](https://www.postgresql.org/docs/current/high-availability.html)
