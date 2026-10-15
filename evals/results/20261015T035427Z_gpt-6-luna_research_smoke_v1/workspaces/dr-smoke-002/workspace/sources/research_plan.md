# 研究计划

## 研究问题
比较 PostgreSQL pgvector 与 Milvus 在中等规模企业 RAG 系统中的适用场景，重点评估部署复杂度、索引能力、扩展方式和运维成本，并形成有条件的选型建议。

## 研究范围与方法
优先使用 PostgreSQL/pgvector 与 Milvus 官方文档作为一手证据；对比功能时区分数据库扩展与专用向量数据库的架构差异，不把产品宣传性描述直接等同于企业实际成本。研究员分别负责单一聚焦子主题，使用不同 findings 文件和不同官方页面目标；分析师基于 findings 进行结构化比较并评估不确定性。

## 子主题、产出路径与来源页面目标
1. pgvector 的索引类型、过滤与查询能力；产出：`/workspace/sources/findings_pgvector_index.md`。目标页面：pgvector 官方 README（索引与查询章节）、PostgreSQL 官方索引文档（索引类型/并发构建）。
2. Milvus 的索引、查询与过滤能力；产出：`/workspace/sources/findings_milvus_index.md`。目标页面：Milvus 官方文档的向量索引概览、过滤搜索文档。
3. 两者部署架构、扩展路径与运维要求；产出：`/workspace/sources/findings_deployment_scaling.md`。目标页面：Milvus 官方部署架构/资源管理文档、PostgreSQL 官方高可用或扩展文档；与前两项页面目标不同。

## 最少来源核验
进入分析或起草前，核对 findings 中由本轮 web_search 明确返回或 web_fetch 成功验证的完整 URL。至少需要 5 个不同页面（不同主机/路径；同页锚点不重复计数），优先覆盖 pgvector 官方 README、PostgreSQL 官方文档、Milvus 官方索引文档、Milvus 官方过滤文档、Milvus 官方架构/部署文档。若不足，须在剩余 researcher 预算内以新的聚焦子主题、新 findings 路径和新页面目标补充。

## 交付物
- `/workspace/sources/question.txt`
- `/workspace/sources/findings_pgvector_index.md`
- `/workspace/sources/findings_milvus_index.md`
- `/workspace/sources/findings_deployment_scaling.md`
- `/workspace/sources/analysis_pgvector_vs_milvus.md`
- `/workspace/reports/draft_pgvector_vs_milvus.md`
- `/workspace/reports/report_pgvector_vs_milvus_2026-10-14.md`

最终报告使用二级标题：`背景`、`关键发现`、`证据与分析`、`建议`、`局限性`，并至少列出 5 个不同的 HTTP(S) 来源链接。