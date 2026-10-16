# LangGraph vs. Microsoft AutoGen for a Production Multi-Agent Research Assistant

## Background

A production research assistant must coordinate multiple agents and tools while preserving work across long-running sessions, pausing for human review, exposing enough operational telemetry to diagnose failures, and fitting the organization’s deployment and data-control requirements. LangGraph and Microsoft AutoGen both support multi-agent applications, but the evidence reviewed here points to different documented strengths: LangGraph’s graph workflow, checkpointing, and interrupt/resume primitives versus AutoGen AgentChat’s team-oriented conversational patterns and explicit turn/termination controls.

This comparison is **provisional**: the findings contain four distinct verified URL pages, below the requested minimum of five. The supplemental research request was rejected because the three-researcher limit had already been reached. The report uses only the verified official documentation and does not treat the evidence as a complete feature inventory or benchmark. The source shortfall particularly limits conclusions about AutoGen state, native deployment, and observability; recommendations below should be validated with additional documentation and workload testing before a framework decision.

## Key Findings

- **LangGraph has the clearer documented path for durable workflow state and approval pauses.** Its checkpointers persist thread-scoped graph snapshots, while stores can hold application-defined information across threads. `interrupt()` pauses execution and resumes with input on the same `thread_id`; production use requires a persistent checkpointer rather than an in-memory saver. [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) · [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- **AutoGen AgentChat is documented around team interaction patterns and bounded runs.** `RoundRobinGroupChat` and `SelectorGroupChat` provide different ways to coordinate agents, while turn limits and termination conditions can return control to the application. Its `UserProxyAgent` blocking path is intended for short, immediate feedback, not long waits; the documented alternative is to stop, persist state, and resume after feedback. [Human-in-the-Loop — AutoGen](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html)
- **The available production operations evidence is asymmetric.** LangSmith documents managed, hybrid, self-hosted, and standalone deployment options, plus trace destinations in some configurations. AutoGen’s native deployment and observability capabilities were not verified in this research pass. [LangSmith Deployment](https://docs.langchain.com/langsmith/deployment)
- **Neither framework’s cited documentation supplies the whole production control plane.** Reviewer identity and authorization, approval audit policy, business-rule enforcement, and application-specific reliability guarantees remain the system builder’s responsibility.

## Evidence and Analysis

### Orchestration

LangGraph’s documented model is an explicit graph of nodes and transitions, with dynamic interrupts that can pause execution at a chosen point. This is a natural fit when the research process has defined stages—such as query decomposition, source collection, evidence validation, synthesis, and publication—and when the application needs to place review gates between stages. The cited pages establish the persistence and interrupt behavior, but do not prescribe a complete multi-agent research architecture or a particular state schema.

AutoGen AgentChat’s documented patterns emphasize teams of agents. `RoundRobinGroupChat` provides member-order control, while `SelectorGroupChat` uses a selector to choose the next participant. Turn limits and termination conditions can bound a run; `HandoffTermination` can return control when an agent emits a handoff, subject to the documented tool-call requirement. This is a good conceptual match for work that is naturally expressed as an agent conversation, but the application still needs to define how team outputs become validated research artifacts.

**Trade-off:** LangGraph’s evidence favors explicit workflow control and pause/resume boundaries; AutoGen’s favors team interaction patterns and conversational control. The reviewed sources do not establish which is more flexible or performant in a given workload.

### State and persistence

LangGraph distinguishes thread-scoped checkpoints from cross-thread stores. The persistence documentation says in-memory savers lose checkpoints on process restart and recommends a persistent checkpointer for production, naming PostgreSQL and SQLite implementations. It also warns that checkpoint growth can increase latency and storage costs, making retention or pruning a design concern. For a research assistant, this supports preserving an in-progress run and its pending review state, while keeping reusable user preferences or shared knowledge in a separate store.

AutoGen’s human-in-the-loop guide describes saving team state after a run stops and resuming when feedback arrives, with internal team state preserved. However, the findings do not verify detailed serialization APIs, exact state contents, storage choices, concurrency behavior, or compatibility guarantees. The guide explicitly warns that a team blocked inside the `UserProxyAgent` interaction cannot be saved or resumed in that blocked state.

**Trade-off:** LangGraph’s persistence primitives and caveats are more specifically documented in the evidence collected. AutoGen documents an application-managed stop/persist/resume pattern, but the implementation details are less established here. This is an evidence asymmetry, not proof that AutoGen lacks persistence capabilities.

### Human approval

LangGraph’s `interrupt()` can pause a node, persist state through the configured persistence layer, and resume with supplied input using the same `thread_id`. The documentation describes approval before consequential actions and review or editing of model outputs and tool calls. Typed response schemas can validate resume values and support typed client forms, subject to the documented version requirement. A key operational caveat is that the node restarts from its beginning on resume: work before the interrupt should be idempotent, and irreversible actions should remain behind the approval gate.

AutoGen supports human feedback through `UserProxyAgent`, but its blocking interaction is recommended only for short, immediate responses. For longer waits, the documented pattern is to stop the team, persist its state, and resume after feedback arrives. That makes the application responsible for the durable wait lifecycle and for associating feedback with the correct run. An `APPROVE` token or handoff is an interaction pattern, not an identity or authorization mechanism.

**Trade-off:** For approvals that may wait minutes or hours and must survive process restarts, LangGraph has the more explicit documented in-workflow pause/resume path. AutoGen can support longer waits through an application-owned stop/persist/resume loop, while its blocking path is unsuitable for durable queues. In either case, approval identity, authorization, audit records, and policy enforcement must be implemented outside the model’s conversational output.

### Observability and deployment

The LangSmith deployment overview documents managed Cloud, self-hosted with control plane, Hybrid, and standalone Agent Server options. Standalone can run with Docker, Compose, or Kubernetes and requires customer-provided PostgreSQL, Redis, and a LangSmith license; Hybrid places the Agent Servers/data plane in customer infrastructure while LangChain manages the control plane. The page also documents LangSmith trace integration for specified configurations, with standalone tracing optional. These options make infrastructure ownership and control-plane placement explicit, but the reviewed page does not establish comparative cost, reliability, scaling limits, trace schema, or OpenTelemetry compatibility.

The same deployment page lists AutoGen among frameworks that can be deployed through LangChain’s Functional API or `deployments-wrap-sdk`. That is evidence of a LangChain deployment product’s framework support, not evidence about AutoGen’s native deployment stack. The findings did not verify AutoGen-specific observability or deployment documentation. This is an information gap, not evidence that AutoGen lacks those capabilities.

**Trade-off:** LangGraph/LangSmith has concrete deployment choices in the reviewed evidence, ranging from managed hosting to customer-operated infrastructure. More customer control can also mean more operational responsibility. A direct deployment or observability superiority claim is not supportable because corresponding AutoGen evidence is missing.

### Overall fit

- **Consider LangGraph first** when the assistant needs explicit research stages, durable thread-level state, long-lived approval pauses, and documented choices for managed versus customer-operated deployment. Plan for persistent storage, stable thread identifiers, checkpoint retention, and idempotent work around interrupts.
- **Consider AutoGen** when the assistant is best modeled as a team conversation with explicit turn and termination control, especially when human feedback is immediate. For longer approval waits, design an application-owned persistence and resume lifecycle and validate feedback independently.
- **Do not choose solely on the evidence here** if the deciding factors are cost, throughput, latency, reliability, scaling, or native observability/deployment parity. Those dimensions were not established by the reviewed sources and should be tested against the intended workload and current framework versions.

## Recommendations

1. **For a production research workflow with durable human review, provisionally prototype LangGraph as the default candidate.** This is a conditional recommendation based on the stronger documentation available in this run, not a balanced finding of product superiority. Model research stages and approval gates explicitly; use a persistent checkpointer, stable `thread_id` values, and a separate store for cross-run knowledge where appropriate. Treat interrupt-resume behavior and idempotency as core design constraints.
2. **Prototype AutoGen when team-conversation semantics are central.** Use bounded turns or termination conditions to return control to the application. Avoid relying on a blocked `UserProxyAgent` for long-lived approvals; instead, stop at a run boundary, persist state, and resume after application-level validation of the reviewer’s response.
3. **Build approval controls outside the agent framework.** Authenticate reviewers, authorize the specific action and scope, record decisions in an auditable system, and ensure the agent cannot treat a model-generated approval string as sufficient authorization.
4. **Run a workload-specific production evaluation before committing.** Test restart recovery, concurrent sessions, checkpoint growth and retention, approval latency, failure recovery, trace completeness, data residency, and operational burden. Verify current version-specific documentation, especially for AutoGen state management and native deployment/observability, which were not established here.

## Limitations

- Only four distinct verified URL pages were preserved in findings, below the requested minimum of five. The supplemental researcher request was rejected due to the three-researcher cap; no additional sources were added, and no irrelevant links were used to pad the report. This shortfall lowers confidence in the comparative recommendation.
- AutoGen state-management details are incomplete. The attempted presumed state page returned 404, so this report does not assert detailed serialization APIs, storage semantics, concurrency behavior, or compatibility guarantees.
- AutoGen-specific native deployment and observability evidence was not verified. This absence must not be interpreted as absence of capabilities.
- LangGraph deployment and observability conclusions rely on one overview page. Detailed telemetry semantics, comparative reliability, cost, scaling limits, and workload benchmarks are not established.
- Neither framework’s cited evidence establishes reviewer authentication/authorization, approval audit policy, exactly-once side effects, or a complete production architecture.
- Documentation is version-sensitive. The AutoGen guide is under a `stable` documentation path, and the LangGraph typed interrupt response feature has a stated minimum version; verify current versions and APIs before implementation.

## References

1. [Persistence — Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/persistence) — official LangGraph persistence documentation.
2. [Interrupts — Docs by LangChain](https://docs.langchain.com/oss/python/langgraph/interrupts) — official LangGraph interrupt and human-approval documentation.
3. [Human-in-the-Loop — AutoGen](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html) — official Microsoft AutoGen AgentChat human-feedback documentation.
4. [LangSmith Deployment](https://docs.langchain.com/langsmith/deployment) — official LangSmith deployment overview, including documented framework support and trace destinations.
