# Findings: 浏览器 LLM 助手相关的 WebSocket 协议与运行时行为

## 调研范围

仅覆盖浏览器端 LLM 助手使用 WebSocket 时相关的协议语义、HTTP 握手/升级、浏览器 WebSocket API 限制、生命周期与重连、安全/Origin 考量及运行影响。优先依据 RFC 6455 与 WHATWG WebSockets 标准。未涉及具体供应商、框架或其他实时传输协议。

## 关键发现

- **全双工语义（标准事实）**：WebSocket 在建立连接后提供双向通信；客户端与服务器可独立发送数据帧，不要求请求—响应交替。RFC 6455 将其描述为在单个 TCP 连接上提供全双工通信，并定义文本、二进制及控制帧。浏览器 API 通过 `send()` 发送、`message` 事件接收。来源：[RFC 6455 §1.1、§5](https://datatracker.ietf.org/doc/html/rfc6455#section-1.1)、[WHATWG WebSockets](https://websockets.spec.whatwg.org/)

- **握手与 HTTP Upgrade（标准事实）**：经典 WebSocket 建连从 HTTP 请求开始，包含 `Upgrade: websocket`、`Connection: Upgrade`、版本及随机 `Sec-WebSocket-Key` 等字段；服务器以 `101 Switching Protocols` 和校验后的 `Sec-WebSocket-Accept` 接受升级。握手还可协商子协议和扩展。浏览器脚本不能自行构造任意握手头；WHATWG 构造器接受 URL 与可选子协议列表，而非通用 headers 参数。来源：[RFC 6455 §4](https://datatracker.ietf.org/doc/html/rfc6455#section-4)、[WHATWG WebSockets—The WebSocket interface](https://websockets.spec.whatwg.org/#the-websocket-interface)

- **浏览器 API 与背压（标准事实）**：浏览器 `WebSocket` API 提供 `readyState`、`bufferedAmount`、`send()`、`close()` 及事件接口。`send()` 将数据排入发送队列；`bufferedAmount` 表示已排队但尚未发送到网络的数据字节数。经典 API 没有由接收端消费速度驱动的流式背压机制；WHATWG 明确指出，应用若消息到达速度超过处理能力，可能耗尽内存或 CPU。来源：[WHATWG WebSockets—The WebSocket interface](https://websockets.spec.whatwg.org/#the-websocket-interface)、[MDN WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

- **生命周期与重连（标准事实及边界）**：连接状态包括 CONNECTING、OPEN、CLOSING、CLOSED；连接建立、收到消息、错误及关闭分别通过事件暴露。标准 API 不提供自动重连语义，重连策略由应用实现。关闭握手可携带状态码和原因；网络中断等异常情况下，应用不能假定双方都能观察到正常关闭握手。来源：[WHATWG WebSockets](https://websockets.spec.whatwg.org/)、[RFC 6455 §7](https://datatracker.ietf.org/doc/html/rfc6455#section-7)

- **安全与 Origin（标准事实）**：浏览器握手会发送 `Origin`，服务器可据此限制哪些网页来源可建立连接；RFC 6455 将 Origin 校验作为防止未授权跨源网页使用服务的重要机制。WebSocket 不等同于同源策略下的普通 Fetch 请求，服务端必须自行验证 Origin、认证身份并授权每条连接/操作。使用 `wss:` 可在传输层启用 TLS。来源：[RFC 6455 §4.1、§10.2](https://datatracker.ietf.org/doc/html/rfc6455#section-4.1)、[RFC 6455 §10](https://datatracker.ietf.org/doc/html/rfc6455#section-10)、[WHATWG WebSockets](https://websockets.spec.whatwg.org/)

- **面向浏览器 LLM 助手的运行影响（推论，非协议保证）**：全双工连接适合在同一会话中上行发送用户输入、下行接收增量生成内容或状态事件；但 WebSocket 本身不定义 LLM token、会话恢复、消息确认、幂等性或重放。断线重连后若要避免丢失/重复输出，应用需设计会话标识、序号/游标、确认与恢复逻辑。由于经典 API 缺少接收端背压，客户端应限制并发处理、控制发送速率并监测 `bufferedAmount`；服务端也应实施队列与消息大小限制。代理、负载均衡器、空闲超时及移动网络切换可能中断长连接，因此需有心跳/超时检测和有界退避重连策略。以上为基于标准行为的工程推论，具体效果取决于部署环境。

## 证据与不确定性

主要依据 RFC 6455 与 WHATWG WebSockets 标准；搜索工具两次均返回 403（配额不足），因此未能通过联网搜索核验页面当前版本。引用为标准文档的精确 URL。MDN 仅作为 API 说明的次级参考。标准规定协议/API 行为，但不保证代理、浏览器进程调度、网络切换或服务端部署的具体表现；重连、会话恢复、流控策略属于应用设计。关于浏览器不能设置任意握手头，结论针对标准 WebSocket 构造器接口，不涵盖非标准扩展或代理方案。

## 参考来源

- [RFC 6455: The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [RFC 6455 §4: Opening Handshake](https://datatracker.ietf.org/doc/html/rfc6455#section-4)
- [RFC 6455 §7: Closing the Connection](https://datatracker.ietf.org/doc/html/rfc6455#section-7)
- [RFC 6455 §10: Security Considerations](https://datatracker.ietf.org/doc/html/rfc6455#section-10)
- [WHATWG WebSockets Standard](https://websockets.spec.whatwg.org/)
- [MDN: WebSocket](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
