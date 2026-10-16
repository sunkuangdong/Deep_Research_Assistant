# 多租户向量数据库数据隔离方案：调研报告

## 背景

多租户向量数据库需要在共享基础设施与租户数据边界之间取得平衡。常见做法包括为租户分配 collection 或 partition、在共享数据上施加 metadata filter，以及为租户部署独立实例。它们并非同一层级的隔离原语：collection/partition/namespace/shard 是产品内的数据组织方式，metadata filter 是查询条件，独立实例则是部署边界。产品文档中的“物理隔离”或“不可见”描述，应按其具体产品语境理解，不能自动等同于独立硬件、网络、凭据或故障域。

本报告依据本轮核验的五个不同官方文档页面，比较安全边界、授权与误配置风险、运维复杂度、扩展限制和适用场景。产品文档用于说明产品能力，不构成独立安全审计结论。

## 关键发现

1. **在 Milvus 文档所述语境中，collection 相较 partition 提供更清晰的集合级管理与授权能力，但仍可能共享集群。** Milvus 文档称每租户一个 collection 可实现 collection 间物理隔离，并支持不同 schema、RBAC 及按租户加载/释放；默认每集群最多 65,536 个 collection，可通过配置提高。[Milvus 多租户策略](https://milvus.io/docs/multi_tenancy.md)

2. **Partition 适合共享 schema 的租户，但不应被当作独立授权主体。** Milvus 将 partition 定义为 collection 的子集，继承父 collection schema；每个 collection 最多 1,024 个 partition。文档称 partition 级多租户不支持 RBAC，尽管数据按 partition 分隔，查询路由和授权仍需由可信服务端严格控制。[Milvus 分区管理](https://milvus.io/docs/manage-partitions.md) [Milvus 多租户策略](https://milvus.io/docs/multi_tenancy.md)

3. **Namespace 或 tenant shard 可提供产品内的租户级数据组织，但不等于独立实例。** Pinecone 官方指南推荐 serverless index 中每租户一个 namespace，读写操作针对单一 namespace，并称 namespace 分别存储；其计划配额从 Starter 的 100 到 Enterprise 的 1,000,000。Weaviate 文档称每个 tenant 存储在单独 shard，且一个 tenant 的数据对其他 tenant 不可见。两者均不能据此推断独立网络、凭据、计算资源或故障域。[Pinecone 多租户指南](https://docs.pinecone.io/guides/index-data/implement-multitenancy) [Weaviate 多租户](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy)

4. **Metadata filter 的关键安全风险在于过滤条件是否由可信授权链路强制执行。** Qdrant 文档描述了通过 tenant payload 字段过滤共享 collection，并建议为 tenant 字段建立索引；但本轮核验页面没有证明数据库会自动把认证身份绑定到过滤条件。若客户端可遗漏或篡改 tenant filter，可能造成跨租户访问，这是架构风险推论。应由可信服务端从认证身份推导 tenant ID，并覆盖查询、写入、删除、聚合等操作路径。[Qdrant 多租户](https://qdrant.tech/documentation/manage-data/multitenancy/)

5. **独立实例可能形成更清晰的部署边界，但会增加运维对象和成本。** 本轮未检索到独立实例方案的厂商级对照页面；因此，独立实例可分开管理数据、配置、凭据和资源，以及可能便于租户级备份恢复、升级或故障控制，均属于一般架构推论，实际效果取决于具体部署。实例独立本身也不自动保证网络、密钥、备份和管理面隔离。

## 证据与分析

### 方案对比

| 方案 | 安全边界与主要风险 | 运维与扩展权衡 | 较适合的场景 |
|---|---|---|---|
| Collection（Milvus 文档语境） | 集合级数据组织；Milvus 文档描述 collection 间物理隔离并支持 RBAC。仍不能等同于独立实例或故障域。 | 可支持不同 schema、租户级加载管理；需管理更多集合并规划产品上限。Milvus 默认每集群 65,536 个 collection。 | 需要不同 schema、集合级 RBAC 或租户级加载/释放的场景。 |
| Partition（Milvus 文档语境） | 共享 collection/schema；Milvus 文档明确 partition 级不支持 RBAC。漏配查询范围或路由错误可能越界（架构推论）。 | 每 collection 最多 1,024 个 partition；需管理分区生命周期，适合租户数受限且 schema 相同的情况。 | 同 schema、可信服务端可强制路由、无需 partition 级 RBAC 的场景。 |
| Metadata filter | 过滤是数据筛选条件，不应单独视为授权。客户端可控时，遗漏或篡改租户条件可能导致越权（架构推论）。 | 共享 collection 可减少逐租户对象管理；需在所有数据操作路径强制注入、验证并审计租户条件。Qdrant 文档建议 tenant 字段索引，并提供面向 tenant 的数据组织提示。 | 大量小租户共享数据、且服务端授权与过滤执行链路可靠的场景。 |
| Namespace / tenant shard | 产品内租户级组织。Pinecone 的物理隔离表述限于 serverless；Weaviate tenant shard 的不可见性不证明独立实例或网络边界。 | 可按租户组织读写和生命周期；需关注计划配额、命名治理及产品特定限制。Weaviate 自动创建 tenant 时需防止拼写/大小写差异产生重复租户。 | 希望使用数据库原生租户组织能力、并接受其共享部署边界的场景。 |
| 独立实例 | 可形成更清晰的部署分界，降低共享查询路径漏过滤的风险（架构推论）；仍需单独验证网络、身份、密钥、备份和管理面。 | 可能便于租户级变更、资源管理、备份恢复、升级或故障控制，但均为架构推论，实际效果取决于部署；实例数量增加会带来容量碎片、配置/版本漂移、监控、备份恢复、升级和成本管理负担。 | 高敏感租户、独立生命周期或更强故障控制要求，且运维能力与预算允许的场景；需按具体部署验证。 |

### 综合判断

隔离强度不能只按“物理隔离”字样排序。Milvus partition 虽被描述为数据分隔，但共享 collection/schema 且不支持 partition 级 RBAC；Pinecone namespace 的物理隔离陈述限定于 serverless；Weaviate tenant shard 的数据不可见性也不等于独立实例。应分别核验数据组织、授权执行、网络与凭据、资源配额、备份和故障域。

安全上，metadata filter 的核心控制点是可信服务端是否将认证身份绑定到 tenant ID，并在所有读写路径强制执行。collection、namespace 或 tenant shard 可减少部分应用层路由错误，但仍需验证产品权限配置和调用身份。独立实例可减少共享数据路径的耦合，却不能替代控制面、网络、密钥和备份隔离设计。

运维上，逻辑隔离通常减少实例数量，但增加租户对象、命名、配额和生命周期治理；filter 方案减少逐租户对象管理，却要求持续保证过滤器完整性；独立实例提高租户级变更与资源管理的独立性（架构推论），但扩大运维面。现有来源没有同口径性能、成本或安全强度数据，不能据此做数值排名。

### 结论

不存在对所有租户规模和风险等级都最优的单一方案。对大量同 schema、低至中等隔离要求的租户，可优先评估数据库原生 namespace/tenant shard，或在可信服务端强制 metadata filter；需要不同 schema、集合级 RBAC 或租户级加载管理时，可评估 collection；高敏感租户或需要独立生命周期/故障控制时，可评估独立实例，并把网络、凭据、密钥、备份和管理面隔离纳入验收条件。独立实例的实际隔离与运维收益需结合具体部署验证。

## 建议

- **先定义威胁模型和隔离目标**：明确是否要求防止应用漏过滤、租户间权限隔离、资源干扰控制、独立备份恢复，或独立网络/故障域；不要把这些目标混为一个“隔离等级”。
- **对 metadata filter 实施服务端强制授权**：tenant ID 应从已认证身份推导，不接受客户端自行指定作为授权依据；统一封装查询、写入、删除、聚合等接口，并通过负向测试验证缺失、篡改和跨租户条件均被拒绝。
- **按产品语义选择逻辑边界**：需要不同 schema 或集合级 RBAC 时优先评估 collection；partition 仅用于共享 schema 且不依赖 partition 级 RBAC 的场景；使用 namespace/shard 时核对其适用部署形态、配额、生命周期和权限配置。
- **对高敏感租户采用分层隔离**：可将独立实例作为候选，但需同时验证网络策略、身份凭据、密钥、备份、管理面权限、监控和升级流程，避免只分开数据面而控制面仍共享。
- **把运维约束纳入容量设计**：核对 collection、partition、namespace 等产品上限及计划差异；建立租户创建/删除、命名规范、配额、审计、备份恢复和配置漂移治理流程。
- **上线前做隔离验证**：以跨租户读取、写入、删除、聚合、批量导入、租户删除与恢复等场景进行自动化测试，并在权限或路由变更后回归验证。

## 局限性

- 本轮核验的五个来源均为厂商官方产品文档；它们说明产品能力，但不是独立安全审计或特定部署配置的安全保证。
- 未检索到官方原始页面对独立实例方案进行同口径比较；独立实例的安全与运维判断属于一般架构推论，需结合具体部署验证。
- 本轮未核验 Pinecone metadata filtering 与 Qdrant filtering 的独立官方页面；关于 metadata filter 的具体产品行为仅依据 Qdrant 多租户页面所述能力，未推断自动授权机制。
- 没有统一口径的性能、成本、资源消耗、故障域或安全强度数据，不能给出跨产品数值排名。Milvus 与 Pinecone 文档中的数量限制计数对象和适用范围不同，不宜直接横向等价。
- Pinecone namespace 的物理隔离描述限定于 serverless；Milvus collection/partition 与 Weaviate tenant shard 的文档描述也不能外推为独立硬件、网络、凭据或故障域保证。

### 参考资料

1. [Implement Multi-tenancy | Milvus Documentation](https://milvus.io/docs/multi_tenancy.md)（官方）
2. [Manage Partitions | Milvus Documentation](https://milvus.io/docs/manage-partitions.md)（官方）
3. [Implement multitenancy | Pinecone Docs](https://docs.pinecone.io/guides/index-data/implement-multitenancy)（官方）
4. [Multitenancy | Qdrant Documentation](https://qdrant.tech/documentation/manage-data/multitenancy/)（官方）
5. [Multi-tenancy | Weaviate Documentation](https://docs.weaviate.io/weaviate/manage-collections/multi-tenancy)（官方）