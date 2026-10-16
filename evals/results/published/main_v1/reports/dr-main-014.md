# 多租户向量数据库数据隔离方案：安全与运维权衡

## 背景

多租户向量数据库需要同时控制数据可见范围、身份授权、资源争用和运维复杂度。常见做法包括按租户拆分 collection、在共享 collection 内使用 partition、通过 metadata/payload filter 限定查询范围，以及为租户配置独立实例。它们并非同一层级的隔离：collection、partition 和 filter 多为数据库逻辑或数据组织边界；独立实例可能涉及更大的部署边界，但具体安全保证取决于产品架构和配置，不能仅凭名称推断。

本报告依据本轮检索到的 Milvus 与 Qdrant 官方文档 findings 比较机制。Pinecone 官方页面未在本轮搜索中检索到，独立实例也缺少直接产品级证据，因此相关结论明确保留不确定性。报告不把产品文档未证明的能力当作事实。

## 关键发现

1. **Milvus collection：隔离与授权证据相对明确，但资源对象更多。** 官方文档称 collection 之间物理隔离，支持 collection 级 RBAC、不同 schema，以及按租户 load/release。默认每集群最多 65,536 个 collection（可通过 `maxCollectionNum` 调整）；不支持跨租户查询。适合需要租户级授权、schema 差异或独立生命周期管理的场景。[Implement Multi-tenancy](https://milvus.io/docs/multi_tenancy.md)；[RBAC Explained](https://milvus.io/docs/rbac.md)

2. **Milvus partition：共享 schema、可跨租户查询，但没有 partition 级 RBAC。** 官方文档称 partition 内数据物理分隔，每个 collection 最多 1,024 个 partition，partition 需手动创建；可按 partition load/release，也可查询多个 partition。由于 RBAC 资源粒度不含 partition，租户路由和查询范围控制更依赖应用正确实现。[Implement Multi-tenancy](https://milvus.io/docs/multi_tenancy.md)；[RBAC Explained](https://milvus.io/docs/rbac.md)

3. **Qdrant payload/metadata filter：适合大量小型租户，但过滤器不是已证实的授权边界。** 官方建议在 point payload 中写入租户字段，并在查询中按该字段过滤；可为租户字段建立 keyword 索引，`is_tenant`（v1.11.0 起）可提示数据局部性。该模式减少大量 collection 的资源开销，但漏写/错写租户字段或查询漏过滤可能导致跨租户结果暴露，这是由机制推导的风险。租户 ID 应由可信服务端从认证身份推导，不能信任客户端任意指定过滤值。[Multitenancy - Qdrant](https://qdrant.tech/documentation/manage-data/multitenancy/)

4. **独立实例与 Pinecone namespace：本轮证据不足以作产品级安全排名。** 当前 findings 未检索到 Pinecone 官方原始页面，也没有独立实例的产品架构证据。独立部署可能减少部分共享资源或故障域耦合，但网络、凭据、控制面、备份和底层基础设施是否隔离必须逐项核实；不能直接断言其必然最安全或成本最高。

5. **没有可比的成本或性能基准。** 已检索到的数量限制计量对象不同：Milvus collection 默认集群上限、Milvus 单 collection partition 上限、Qdrant Cloud collection 默认集群上限不能直接构成跨方案容量排名。实际成本、延迟、吞吐和运维工时需在目标版本与负载下测量。

## 证据与分析

### 方案对比

| 方案 | 安全边界与主要风险 | 运维与扩展权衡 | 更适合的场景 |
|---|---|---|---|
| Collection | **官方事实：**Milvus 文档明确记载 collection 间物理隔离并支持 collection 级 RBAC。仍需正确配置身份、角色和资源权限；这不等于独立基础设施隔离。 | **官方事实：**租户对象随租户数增加；Milvus 默认集群上限 65,536，可调整。**推论：**权限和生命周期对象管理负担随之增加。跨租户查询不支持。 | 需要较强逻辑隔离、租户级授权、不同 schema 或独立冷热管理。 |
| Partition | **官方事实：**Milvus 文档记载数据按 partition 物理分隔，但 partition 级不支持 RBAC。**推论：**错误路由或查询范围控制可能扩大暴露面。 | **官方事实：**共享 schema；partition 需手动创建；每 collection 最多 1,024 个；可跨 partition 查询和管理冷热数据。 | 租户共享 schema、需要跨租户分析，且应用能可靠执行租户路由与范围校验。 |
| Metadata/payload filter | **官方事实：**Qdrant 通过租户字段过滤查询。过滤器本身不是身份认证。**推论：**漏过滤、错误租户字段或客户端可控租户值构成应用层风险。 | **官方事实：**官方建议大量小型租户共享 collection；`is_tenant` 可改善局部性，收益未量化。**推论：**减少 collection 对象压力，但需维护字段完整性、索引和所有查询路径的过滤覆盖。 | 大量小型、规模相近租户；可信服务端可统一注入租户条件并覆盖测试所有访问路径。 |
| 独立实例 | **证据缺口：**本轮没有目标产品的直接官方证据证明其网络、控制面、凭据、备份或底层基础设施隔离程度。 | **推论（未验证）：**可能增加部署、升级、监控、备份等对象；成本与自动化能力取决于产品和托管方式，当前无法量化。 | 仅在取得产品架构证据并验证隔离边界后，作为可能的资源/故障域隔离候选；不能视为已证实的安全优势。 |

### 综合判断

隔离强度不能只按“拆得越开越安全”排序。Milvus collection 是本轮材料中同时有物理分隔和 collection 级 RBAC 文档证据的方案；partition 虽有数据分隔描述，但缺少 partition 级授权；Qdrant filter 的安全性依赖应用在每次读写中正确执行租户约束。独立实例可能提供更大的资源边界，但本轮没有足够证据确认其实际安全边界，必须以目标产品的架构和配置为准。

运维负担主要在两类工作之间转移：collection/独立实例增加资源对象和生命周期管理；partition 需要维护分区与查询路由；payload filter 减少 collection 数量压力，却要求持续保证租户字段和过滤逻辑完整。以上是定性判断，不是量化工时或总拥有成本结论。

数量限制也不能混为一谈。Milvus 默认 65,536 个 collection 是集群级默认值，1,024 个 partition 是单 collection 上限，Qdrant Cloud 的 1,000 个 collection 是其集群默认限制。它们的计量对象、产品和部署语境不同，不能据此推导跨产品容量优劣。

### 来源数量核验与参考资料

本轮 findings 中可追溯的不同 HTTP(S) 页面共 4 个：Milvus 多租户文档、Milvus RBAC 文档、Qdrant 多租户文档、Qdrant 安全文档。Milvus 与 Qdrant 多租户文档分别在 findings 中重复出现，但按页面只计一次。用户要求至少 5 个不同来源链接；当前证据未达到该数量。Pinecone findings 明确记录本轮未检索到可引用官方页面，且搜索预算与 researcher 委派预算已耗尽，因此不能用未经本轮验证的 URL 或不相关链接凑数。此为交付限制，报告结论相应保持谨慎。

本轮可引用的官方来源如下：
- [Milvus: Implement Multi-tenancy](https://milvus.io/docs/multi_tenancy.md)
- [Milvus: RBAC Explained](https://milvus.io/docs/rbac.md)
- [Qdrant: Multitenancy](https://qdrant.tech/documentation/manage-data/multitenancy/)
- [Qdrant: Security documentation](https://qdrant.tech/documentation/security/)

## 建议

- **优先需要租户级授权和较强逻辑隔离：**评估 Milvus collection；在目标版本验证 RBAC 角色、collection 权限、租户身份映射及 collection 数量/资源容量。
- **需要跨租户分析且 schema 统一：**可评估 Milvus partition，但必须在可信服务端实施租户到 partition 的映射、查询范围校验和负向越权测试；不要把 partition 当作 RBAC 授权对象。
- **大量小型租户且希望共享资源：**可评估 Qdrant payload filter。租户 ID 应从已认证主体服务端生成；统一封装所有读写接口，确保过滤条件不可被客户端移除或替换，并测试漏过滤、错误字段和批量查询路径。`is_tenant` 是数据布局提示，不应替代授权控制。
- **考虑独立实例：**先要求供应商提供网络、身份凭据、控制面/数据面、备份恢复、故障域和资源配额的隔离说明，再结合实际报价、自动化能力和运维工时评估。当前没有产品级证据支持其隔离强度、成本或运维排名；“更强资源/故障域隔离”只能作为待验证假设。
- **考虑 Pinecone：**本轮未检索到官方原始页面，暂不对 namespace、独立 index/project/实例的隔离强度作判断；取得并核验官方文档后再纳入选型结论。
- **上线前验证：**以目标版本和真实租户规模进行越权测试、故障/恢复演练、性能与成本压测，并记录租户创建、迁移、删除、密钥轮换和审计流程。

## 局限性

- 用户要求至少 5 个不同 HTTP(S) 来源链接；本轮 findings 仅有 4 个不同页面，未达到要求。由于搜索与 researcher 预算已耗尽，不能补充未经本轮验证的链接。报告保留这一缺口，不以无关或低质量来源凑数。
- Pinecone 官方页面未检索到，namespace 与独立资源的安全语义、授权边界、配额和运维成本均无法核实；独立实例也缺少产品级原始证据。
- Qdrant 安全文档正文未在 findings 中得到核验，API key 权限粒度及服务端是否能强制租户过滤仍不确定。过滤遗漏风险是基于机制的推论，不是已确认漏洞。
- 官方文档未提供统一的成本、吞吐、延迟、资源消耗或运维工时基准；不能给出四种方案的数值评分或总成本排名。产品版本、部署形态和配置可能改变限制与行为。
