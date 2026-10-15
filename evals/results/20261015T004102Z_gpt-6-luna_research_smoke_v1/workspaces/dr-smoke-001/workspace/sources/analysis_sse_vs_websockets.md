# Analysis: SSE 与 WebSocket 在浏览器 LLM 流式响应中的取舍

## 数据来源

仅使用用户指定的三份 findings：
- `/workspace/sources/findings_sse.md`
- `/workspace/sources/findings_websockets.md`
- `/workspace/sources/findings_llm_patterns.md`

未联网搜索，未修改 findings。以下将“标准/API 明确规定的事实”与“基于事实的工程推论/建议”分开。本文不作性能数字比较，也无须数值计算。

## 计算任务

无数值计算任务。比较维度为：方向性、浏览器 API 易用性、认证与请求形态、取消、重连与恢复、背压、基础设施/部署、适用场景。

## 计算过程

不适用：未进行数值计算。

## 分析结论

### 1. 方向性

**标准事实**
- SSE/EventSource 是服务器到浏览器的单向事件流；客户端不能在同一 EventSource 连接上发送应用数据。
- WebSocket 建立后是全双工连接，客户端和服务器可独立发送消息。

**工程推论**
- 对“提交一次提示词，逐步接收模型输出”的交互，双向连接并非必需：可用独立 HTTP 请求提交输入，再用 SSE/Fetch 流接收输出。
- 若同一会话需要持续上行控制消息（例如实时打断、频繁交互状态或多路消息）并同时下行输出，WebSocket 的连接模型更贴合；但协议本身不定义 LLM 会话或消息语义。

### 2. 浏览器 API 易用性

**标准/API 事实**
- 原生 EventSource 接口简洁，接收 `message` 或具名事件，并支持 `close()`；但构造器没有任意请求头、方法或请求体参数，适合 GET 型订阅。
- Fetch + ReadableStream 可用于逐块读取响应体；应用负责解码、缓冲和事件解析。AbortController 可取消 Fetch 请求。
- 浏览器 WebSocket 提供 `send()`、`message`、`close()`、连接状态及 `bufferedAmount`；浏览器脚本不能通过标准构造器设置任意握手头。

**工程推论**
- 若需要 POST body、Authorization 头、AbortSignal 或自定义解析，Fetch 流通常比原生 EventSource 更灵活。这里的比较是 API 形态，不代表性能优劣。
- EventSource 的简洁性以请求控制能力受限为代价；WebSocket 的双向能力也意味着应用需自行定义消息类型、状态和错误处理。

### 3. 认证与请求形态

**标准/API 事实**
- EventSource 可配置 `withCredentials`，但不能设置任意 Authorization 头或请求体。跨源凭据请求受 CORS、Cookie SameSite/第三方 Cookie 等规则约束；带凭据的 CORS 响应不能使用通配 `Access-Control-Allow-Origin: *`。
- 浏览器 WebSocket 握手会发送 Origin，服务端可据此校验来源；标准浏览器构造器不提供通用自定义握手头参数。服务端仍须认证身份并授权连接及操作。
- Fetch 可设置请求头和请求体，且可配合 AbortSignal；跨源时仍受 CORS 约束。

**工程推论**
- 需要 Bearer Authorization 或 POST 提示词时，优先考虑 Fetch 流，或由受信任后端代理；不要把长期服务端密钥放入浏览器代码。
- WebSocket 的认证需按浏览器可用机制和服务端设计落实，不能假设可像 Fetch 一样任意添加握手头。Origin 校验不是身份认证的替代品。
- 具体供应商是否支持短期凭据、流式 POST 或特定恢复方式，须按其当前 API 文档确认。

### 4. 取消

**标准/API 事实**
- EventSource 可通过 `close()` 关闭连接；WebSocket 可通过 `close()` 发起关闭。
- Fetch 请求可通过 AbortController 中止。

**工程推论**
- 对单次生成，Fetch + AbortSignal 提供直接的请求取消控制；EventSource/ WebSocket 也能关闭传输，但关闭客户端连接不等于保证服务端推理或副作用立即停止。
- 若产品要求“停止生成”具有服务端语义，应另定义取消操作/任务状态，并验证服务端是否真正终止计算，而不能只依赖断开连接。

### 5. 重连与恢复

**标准/API 事实**
- SSE 规范定义自动重连、`retry` 和 `id`/`Last-Event-ID` 游标机制；这不保证恰好一次处理，也不自动保证服务端可重放事件。
- 标准浏览器 WebSocket API 不提供自动重连；应用需自行实现。

**工程推论**
- SSE 的内建重连适合可恢复的事件订阅，但 LLM 生成能否续传取决于服务端是否保存事件、提供稳定 ID 和重放语义。重连不等于恢复同一次生成。
- WebSocket 断线后需自行实现退避、会话标识、序号/游标、确认及去重/恢复。若没有服务端恢复协议，重试可能重新触发生成、造成重复内容或成本。
- 两种方案都应区分“重新建立传输连接”与“恢复原任务”。

### 6. 背压

**标准/API 事实**
- 经典浏览器 WebSocket API 没有由接收端消费速度驱动的流式背压；`bufferedAmount` 反映尚未发送到网络的出站排队字节数，并非接收端消费队列的完整流控机制。
- Fetch ReadableStream 提供流式读取接口；SSE 事件流也按文本事件解析，网络读取块不等于事件边界。

**工程推论**
- WebSocket 应用需限制发送速率、消息大小和并发处理，并监控队列；服务端也应设置有界队列和流控策略。
- Fetch/Streams 的读取模型更适合由应用逐步消费响应，但端到端缓冲仍受浏览器、网络和中间层影响，不能据此假定完全无缓冲或自动解决所有背压问题。
- 对典型逐 token 输出，需避免把网络块直接当作 token 或完整事件；应按协议帧/应用事件解析。

### 7. 基础设施与部署

**标准事实**
- SSE 使用 HTTP `text/event-stream`；HTTP 传输分块边界不是 SSE 事件边界。WebSocket 经典握手从 HTTP Upgrade 开始，之后使用 WebSocket 帧。
- 协议标准规定传输语义，但不保证特定代理、CDN、负载均衡器或 serverless 平台的缓冲、空闲超时、连接时长和网络切换表现。

**工程推论**
- SSE/Fetch 可沿用 HTTP 请求链路，但必须验证代理缓冲、压缩、超时及增量交付；WebSocket 则要求部署链路支持 Upgrade/长连接，并处理心跳、空闲超时和连接生命周期。
- 不能仅凭协议名称断定哪种更易部署；应在目标环境端到端测试首事件延迟、持续增量、取消、断连和恢复。

### 8. 适用场景与决策框架

| 需求特征 | 优先评估 | 理由与注意事项 |
|---|---|---|
| 单次提示词请求，逐步显示响应；需要 POST、Authorization 或 AbortSignal | Fetch + ReadableStream | 请求控制和取消接口灵活；应用需解析流并处理错误/结束状态。 |
| GET 型、单向事件订阅；Cookie/CORS 形态匹配；希望使用原生事件接口 | EventSource / SSE | API 简洁且有标准重连游标机制；自定义头、请求体及任务恢复仍受限/需另行实现。 |
| 同一连接上持续双向消息、频繁上行控制与下行事件 | WebSocket | 全双工模型匹配；需自行实现认证策略、重连、恢复、流控和消息协议。 |
| 需要可靠恢复同一生成任务、去重或确认 | 先确定应用层恢复协议，再选传输 | SSE 的 Last-Event-ID 或 WebSocket 重连本身都不提供任务级恢复保证。 |
| 部署环境对长连接/Upgrade/缓冲限制未知 | 先做目标环境验证 | 代理和平台行为可能成为决定因素，标准无法替代部署验证。 |

**总体判断**：浏览器 AI 助手的常见“请求一次、流式返回”模式，优先评估 Fetch + ReadableStream；若接口天然是单向 GET 事件订阅且 EventSource 的请求限制可接受，可选 SSE/EventSource。只有在确有持续双向通信需求时，才因方向性选择 WebSocket；不要仅因响应是流式就默认需要 WebSocket。无论选择何者，认证、取消的服务端语义、任务恢复和部署链路都应作为独立设计项。

## 数据缺口与不确定性

- Findings 主要依据 WHATWG、RFC、Fetch/浏览器 API 文档及所列供应商/平台文档入口；原 findings 说明搜索服务未能核验页面当前版本。本文未联网补充核验，结论限于 findings 中记录的内容。
- 未提供具体供应商 API、浏览器支持矩阵、认证方案、代理/CDN/云平台配置或恢复协议，因此无法判断某一部署的实际可用性、延迟、吞吐或成本。
- SSE 的自动重连不等于 LLM 任务续传；WebSocket 的重连也不等于消息恢复。两者的任务级语义需由应用和服务端明确约定。
- 取消传输不保证服务端推理立即停止；需通过具体服务端行为验证。
- 背压与缓冲表现受浏览器实现、应用消费速度和中间层配置影响；本文不作定量性能结论。
