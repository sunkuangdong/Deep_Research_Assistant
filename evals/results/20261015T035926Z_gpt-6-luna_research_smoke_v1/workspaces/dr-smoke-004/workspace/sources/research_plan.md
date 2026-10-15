# 调研计划

## 目标
比较两种适合构建 AI Agent 的公开可用模型方案，并按官方公开价格估算指定负载的日成本与月成本。运行日期按用户指定为 2026-10-14；需区分该日期与实际可验证的价格生效日期，不能把运行日期误称为价格发布日期。

## 负载与计算口径
- 每日请求数：10,000
- 每次请求输入：6,000 Token；输出：1,000 Token
- 日输入量：60,000,000 Token；日输出量：10,000,000 Token
- 月成本按 30 天估算，并明确这是标准化月份假设
- 公式：输入 Token 数 / 1,000,000 × 官方输入单价（美元/百万 Token）+ 输出 Token 数 / 1,000,000 × 官方输出单价（美元/百万 Token）
- 仅计算模型 Token 费用；不假设缓存折扣、批处理折扣、工具调用费、税费、汇率、重试或其他平台费用，除非官方价格页明确要求纳入。

## 子主题与精确产出路径
1. OpenAI 公开模型方案：核实适合 Agent 的模型定位、官方输入/输出价格及价格页说明。目标来源页面：OpenAI API Pricing 官方价格页、OpenAI Models 官方模型目录（两个不同页面）。产出：`/workspace/sources/findings_openai.md`。
2. Anthropic 公开模型方案：核实适合 Agent 的模型定位、官方输入/输出价格及价格页说明。目标来源页面：Anthropic API Pricing 官方价格页、Anthropic Models 官方模型目录（两个不同页面）。产出：`/workspace/sources/findings_anthropic.md`。

每次 researcher 委派只负责上述一个厂商子主题，使用各自独立 findings 路径；不得重复委派或覆盖文件。至少需要四个不同的、由本轮搜索返回或成功抓取验证的来源页面 URL（不同主机/路径；锚点不另计）。若两份 findings 合计不足四个有效页面，须在剩余 researcher 预算内以新的聚焦子主题、新 findings 路径和新的可靠来源页面补充后，方可进入分析。

## 分析与报告
- 核对两种方案的官方价格证据、模型适用性、成本差异、适用场景和价格变化风险。
- 委派 analyst 一次，使用 structured_calculator 复核日/月成本；输出 `/workspace/sources/analysis_agent_model_costs.md`。
- 主 Agent 起草 `/workspace/reports/draft_agent_model_costs.md`，严格使用指定的五个 Markdown 二级标题。
- 委派 editor 一次审阅；主 Agent 合并意见后一次性修订，并保存最终报告 `/workspace/reports/report_agent_model_costs_2026-10-14.md`。

## 来源与不确定性
优先使用厂商官方价格页和官方模型目录。记录每个可引用 URL 的本轮搜索/抓取验证情况；若官方页面未明确价格生效日期，报告中说明“页面可见价格按本次调研访问时记录，未检索到独立生效日期”，并标注价格可能变化。