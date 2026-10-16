# LLM 服务弹性设计：限流、超时与提供商故障

## 背景

LLM API 调用可能因速率限制、服务端过载、网络中断、超时或提供商故障而失败。弹性设计的关键不是“遇错就重试”，而是先判断故障是否暂时、请求是否可能已被处理，再选择等待重试、停止调用、切换路径或返回受控降级结果。生成式请求还涉及较高的延迟与费用，以及流式响应中断后处理状态不确定等问题。

本报告依据本轮检索到的标准、云服务文档和提供商文档，区分来源明确支持的事实与架构层建议。findings 记录了 5 个不同来源页面 URL：其中 RFC 6585、Google Cloud Storage、Anthropic 与 AWS EC2 页面有成功抓取或明确的搜索/抓取记录；AWS Builders’ Library URL 由本轮搜索结果返回，但 findings 未抓取全文，因此仅用于有限的工程实践背景，不据此归因具体参数。部分目标官方页面未能检索到，相关结论不作外推。

## 关键发现

1. **限流应遵循协议提示并限制重试。** IETF RFC 6585 将 HTTP 429 定义为限流响应，并允许服务端通过 `Retry-After` 指示再次请求前的等待时间；它不要求服务端必须返回该头，也没有规定客户端统一重试算法。[RFC 6585](https://www.rfc-editor.org/info/rfc6585/)
2. **重试只适用于可恢复且可安全重复的操作。** Google Cloud Storage 的重试指南将 408、429、5xx、socket timeout 和 TCP disconnect 等列为通常可重试信号，同时强调操作幂等性会影响重试安全性。[Google Cloud Storage：Retry strategy](https://docs.cloud.google.com/storage/docs/retry-strategy)
3. **提供商错误语义不能只看状态码。** Anthropic 文档指出，500 建议指数退避，529 表示暂时过载；429 可能是速率限制，也可能是支出上限。支出上限类 429 没有 `retry-after`，在额度恢复前会持续失败。其 SDK 对部分暂时性错误默认最多重试两次，并在存在时遵循 `retry-after`。[Claude API errors](https://platform.claude.com/docs/en/api/errors)
4. **超时或流式中断不等于服务端未处理。** Anthropic 文档说明 SSE 请求可能在 HTTP 200 后才发生错误。客户端可能只收到部分结果，无法据此断定服务端未执行；盲目重发可能造成重复生成或下游副作用。
5. **熔断、降级和幂等性需要应用架构补足。** 本轮证据支持有限重试与错误分类，但未取得 Resilience4j 熔断器官方页面，也没有提供商对跨提供商故障转移的统一承诺。AWS EC2 的一个具体 API 通过可选 `ClientToken` 支持幂等，这只能证明该 API 的契约，不能推断所有 LLM API 都支持幂等键。[AWS EC2：CreateIpamExternalResourceVerificationToken](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateIpamExternalResourceVerificationToken.html)

## 证据与分析

### 故障分类与动作映射

| 故障类别 | 典型信号（需按提供商验证） | 建议动作 | 主要风险 |
|---|---|---|---|
| 限流/暂时过载 | 429、提供商特定过载码（Anthropic 文档中的 529） | 优先遵循有效 `Retry-After`；否则有限退避并加入抖动；持续过载时考虑熔断或备用路径 | 重试加剧拥塞；429 可能代表额度/支出上限而非短暂速率限制 |
| 瞬态网络或服务错误 | 连接失败、socket timeout、TCP disconnect、部分 5xx | 仅在请求可安全重复且预算未耗尽时重试 | 超时后处理状态可能未知；重复计费或副作用 |
| 非瞬态请求/配置或额度问题 | 参数无效、认证/授权失败，或提供商明确说明需修正配置/额度的错误（具体语义依 API） | 停止自动重试，返回可诊断错误并修正请求、权限或额度状态 | 盲目重试浪费配额、延迟和费用；同一状态码在不同提供商可能含义不同 |
| 持续性提供商故障 | 连续失败、过载持续或健康探测失败 | 架构建议：熔断隔离故障域；按业务策略切换备用模型/提供商或返回受控降级 | 阈值不当导致误熔断；备用路径容量、质量、价格和数据条件不同 |
| 结果不确定的中断 | 请求超时、连接断开、SSE 中途错误 | 架构建议：查询/记录业务操作状态；使用经验证的幂等键或应用层去重；将生成与副作用提交分离 | 无法保证端到端“恰好一次”；跨提供商幂等语义可能不同 |

### 机制比较

- **退避重试**适合短暂、可恢复的故障。指数退避与随机抖动可避免大量客户端同步重试；应设置最大尝试次数、总截止时间和请求/资源预算，并协调 SDK、应用层与网关的重试，避免层层叠加。AWS Builders’ Library 提供超时、重试和带抖动退避的工程实践框架，但本轮未抓取全文，因此不引用其具体参数或公式。[AWS Builders’ Library：Timeouts, retries and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- **熔断**适合持续失败而非单次瞬态错误：达到本地失败阈值后暂时停止向故障提供商发送请求，并通过受控恢复探测决定是否恢复。它能减少故障扩散，但阈值、统计窗口和恢复策略必须结合流量与延迟分布验证。本轮未检索到 Resilience4j 官方页面，故状态机细节和参数不作为已核实事实。上述熔断行为属于架构建议，而非本轮来源所确认的特定库实现。
- **降级/故障转移**可在主路径不可用时保留部分业务能力，例如切换备用模型/提供商、使用允许陈旧结果的缓存，或返回明确的非生成式安全响应。这些是架构建议，不是所引提供商文档的保证。应明确备用路径的质量、延迟、成本、容量、数据处理和安全边界；若采用缓存，缓存键覆盖影响输出的输入与配置维度也属于需按系统验证的设计选择。
- **幂等性**是安全重试与故障切换的前提之一，但必须由目标 API 契约或应用层实现。AWS EC2 示例中的 `ClientToken` 仅适用于该 API 的定义；不能假定 LLM 生成端点支持相同键、作用域或保留期限。对有副作用的工作流，建议以稳定业务操作 ID 去重，并把模型生成与后续写入/支付等副作用分离。

### 证据边界

本轮可追溯的 5 个不同页面分别是 IETF RFC 6585、AWS Builders’ Library、Google Cloud Storage Retry strategy、Anthropic API errors 和 AWS EC2 API 参考。它们覆盖协议语义、工程实践、单一云产品重试指南、单一 LLM 提供商错误语义及一个具体幂等 API 示例，但并非对所有 LLM 提供商或 SDK 的全面比较。未检索到 Microsoft Azure transient fault handling、Resilience4j CircuitBreaker 和 OpenAI 官方错误/速率限制页面；因此不对这些来源的具体行为作事实断言。

## 建议

1. **建立统一故障分类表。** 按提供商、端点和请求阶段解析状态码、错误体、响应头及连接状态；至少区分可重试瞬态错误、非瞬态错误、限流/额度错误和结果不确定的中断。不要把所有 429 或 5xx 视为同一类。
2. **实施有界重试。** 有效 `Retry-After` 优先；否则采用带抖动的退避。设置最大尝试次数、总截止时间和资源预算，预算耗尽即停止。具体数值应由服务商契约、延迟目标、费用上限和线上观测确定，本报告不提供无数据支撑的统一阈值。
3. **贯穿调用链管理超时预算。** 架构建议：为单次尝试和整个业务请求设置截止时间，确保重试不会突破上游请求期限；可按所用 SDK/网关能力区分连接、响应等待和流式读取阶段的超时，并验证其配置语义。现有来源不足以支持通用的阶段划分或预算数值。
4. **将重试与熔断分工。** 短暂故障用有限重试；持续故障由按提供商/故障域隔离的熔断保护；恢复时采用受控探测。通过演练和指标校准阈值，避免熔断器本身成为误拒绝来源。此为架构建议，具体状态机与阈值需另行验证。
5. **设计明确的降级契约。** 仅在业务允许时切换模型或提供商；对缓存标注新鲜度，对非生成式回退提供安全、可理解的结果，并监控备用路径容量、质量和成本。避免无上限的跨提供商重试链。
6. **保护重复提交与副作用。** 核实每个 API 的幂等键支持、作用域和有效期；不支持时在应用层以稳定业务 ID 去重。对超时、SSE 中断等不确定结果，先检查操作状态或进入可恢复工作流，不要假定失败即未执行。
7. **观测并演练。** 按提供商记录错误类别、重试次数、退避等待、熔断状态、降级比例、超时阶段、重复请求和最终业务结果；通过限流、延迟、断连和提供商不可用演练验证策略。该建议属于工程实践推导，需用本系统数据评估。

## 局限性

- 本轮未检索到官方 OpenAI 错误/速率限制页面、Microsoft Azure 瞬态故障指导或 Resilience4j 熔断器文档；相关产品行为与配置细节未核实。对这些目标页面，**未检索到官方原始页面**。
- AWS Builders’ Library 页面 URL 来自本轮搜索结果，但 findings 未抓取全文；因此仅将其作为工程实践来源，不归因具体算法参数。
- Anthropic、Google Cloud Storage 与 AWS EC2 文档分别限定于各自产品/API，不能直接外推为所有 LLM 提供商的统一行为。
- 缺少各提供商故障率、延迟分布、重试成功率、费用、备用容量、缓存命中率和业务损失数据，无法量化策略收益或给出最优阈值。
- 熔断、跨提供商切换、缓存策略、超时预算和应用层去重的具体实现属于架构建议，仍需结合目标 API 契约、合规要求和生产演练验证。

### 参考资料

1. 标准：[RFC 6585: Additional HTTP Status Codes](https://www.rfc-editor.org/info/rfc6585/)
2. 官方工程实践：[Timeouts, retries and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
3. 官方云产品文档：[Google Cloud Storage：Retry strategy](https://docs.cloud.google.com/storage/docs/retry-strategy)
4. 官方 LLM 提供商文档：[Claude API errors](https://platform.claude.com/docs/en/api/errors)
5. 官方 API 参考：[CreateIpamExternalResourceVerificationToken](https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_CreateIpamExternalResourceVerificationToken.html)
