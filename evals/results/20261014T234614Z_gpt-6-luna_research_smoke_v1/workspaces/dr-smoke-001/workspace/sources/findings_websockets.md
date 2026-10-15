# Findings: WebSocket 标准与浏览器行为（面向 LLM 流式响应）

## 调研范围

仅覆盖 WebSocket 标准及浏览器端行为对流式 LLM 响应的相关含义：双向消息、浏览器 API、协议分帧与连接生命周期、安全/Origin，以及有一手技术来源支持的运行影响。不比较其他传输方式。联网搜索服务本次返回配额错误，因此以下依据可直接引用的标准与浏览器文档链接整理；未能在本次运行中逐页核验具体版本或实现差异。

## 关键发现

- WebSocket 在单条连接上支持双向通信：RFC 6455 定义客户端与服务器之间的双向通信通道；浏览器 `WebSocket` API 提供 `send()` 发送数据，并通过 `message` 事件接收服务器消息。对 LLM 流式响应而言，服务器可连续发送多个应用层消息，客户端也可在同一连接发送提示、取消或控制消息；具体消息格式和流式语义由应用协议定义，而非 WebSocket 标准规定。
  来源：[RFC 6455 §1.1](https://www.rfc-editor.org/rfc/rfc6455#section-1.1)、[MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- 浏览器 API 的核心生命周期事件包括 `open`、`message`、`error`、`close`；`readyState` 表示连接状态。`send()` 可发送字符串、`Blob`、`ArrayBuffer` 或 typed array 等数据；接收消息通过 `MessageEvent.data` 暴露，文本帧通常为字符串，二进制数据的呈现受 `binaryType` 影响。应用应在连接打开后发送，并处理关闭/错误及重连策略；重连并非协议自动提供的应用级保证。
  来源：[MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)、[MDN WebSocket message event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/message_event)、[MDN WebSocket.readyState](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/readyState)

- WebSocket 帧是协议传输单位，应用消息可由一个或多个帧组成；RFC 6455 支持消息分片，并规定控制帧（如 Ping、Pong、Close）不能分片且长度受限。浏览器应用通常接收重组后的消息事件，而不是逐帧处理。因此，LLM token/chunk 的边界应由应用层消息约定决定，不能假设一个 WebSocket 帧等于一个 token 或一个完整响应片段。
  来源：[RFC 6455 §5.2](https://www.rfc-editor.org/rfc/rfc6455#section-5.2)、[RFC 6455 §5.4](https://www.rfc-editor.org/rfc/rfc6455#section-5.4)、[RFC 6455 §5.5](https://www.rfc-editor.org/rfc/rfc6455#section-5.5)、[MDN WebSocket message event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/message_event)

- 握手通过 HTTP Upgrade 建立连接；RFC 6455 定义 `Origin` 请求头，服务器可据此判断浏览器脚本来源并拒绝不被授权的跨源连接。浏览器 WebSocket API 不提供任意设置握手请求头的通用参数，因此认证设计需考虑浏览器 API 限制（例如依赖适当的 Cookie/会话或应用层认证机制）；具体方案及其风险需结合部署环境验证。使用 `wss:` 可在传输层启用 TLS。
  来源：[RFC 6455 §4.1](https://www.rfc-editor.org/rfc/rfc6455#section-4.1)、[RFC 6455 §10.2](https://www.rfc-editor.org/rfc/rfc6455#section-10.2)、[MDN WebSocket() constructor](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/WebSocket)

- 浏览器标准 WebSocket API 没有接收端背压接口；MDN 明确指出，若消息到达速度超过应用处理速度，可能导致内存增长或 CPU 饱和。发送侧 `bufferedAmount` 可观察已排队但尚未发送的数据字节数，但它不是接收侧流控机制。对流式 LLM 客户端，需在应用层控制发送速率/队列、限制缓冲并及时处理消息；服务端分块大小、速率和取消协议也属于应用设计事项。
  来源：[MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)、[MDN WebSocket.bufferedAmount](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/bufferedAmount)

- 关闭握手是协议生命周期的一部分：端点可发送 Close 控制帧，另一端响应后连接关闭；浏览器 `close()` 发起关闭，`close` 事件提供关闭信息。应用应区分正常结束、异常断开与服务端/网络关闭，并定义未完成生成的处理方式。协议本身不保证应用层响应完成或断线后的续传。
  来源：[RFC 6455 §7.1](https://www.rfc-editor.org/rfc/rfc6455#section-7.1)、[MDN WebSocket.close()](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close)、[MDN close event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close_event)

## 证据与不确定性

核心协议事实来自 RFC 6455，浏览器 API 行为来自 MDN 文档，适用于解释标准 WebSocket 与浏览器接口的基本能力。搜索工具本次均返回 403 配额错误，未能执行网页检索或核对文档更新时间；链接内容未在本次运行中逐页读取。浏览器实现细节、代理/负载均衡器超时、最大消息尺寸、认证部署方式及具体 LLM 服务的分块语义均依实现和配置而异，不能仅由 RFC/通用 MDN 文档推断。RFC 的帧分片不等同于应用层流式分块；背压结论针对传统浏览器 `WebSocket` API，不应外推到其他 API 或非浏览器实现。

## 参考来源

- [RFC 6455: The WebSocket Protocol](https://www.rfc-editor.org/rfc/rfc6455)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN: WebSocket() constructor](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/WebSocket)
- [MDN: WebSocket message event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/message_event)
- [MDN: WebSocket.readyState](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/readyState)
- [MDN: WebSocket.bufferedAmount](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/bufferedAmount)
- [MDN: WebSocket.close()](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close)
- [MDN: WebSocket close event](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/close_event)
