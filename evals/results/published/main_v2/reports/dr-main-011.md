# Security Controls for Tool-Calling Agents: Authorization and Auditability

## Background

**Executive summary.** The strongest general design pattern is to enforce authorization outside the model, grant narrowly scoped capabilities, separate read/prepare from write/send/execute, and require risk-based approval for consequential actions. Application-level audit records should make each tool action attributable and reconstructable while minimizing sensitive payload retention. These are design implications drawn from general NIST and OWASP guidance, not a complete agent-specific standard.

Tool-calling agents can cross important security boundaries when they query databases, send email, search the web, or create scheduled jobs. The central risk is not simply that a model may produce an incorrect answer: a tool invocation can expose sensitive data, change records, communicate externally, or create persistent activity. Security therefore depends on controls outside the model itself—identity, authorization, constrained tool interfaces, approval gates, and reliable audit records.

The evidence reviewed here consists of general risk-management and security-control frameworks, OWASP application-security/logging guidance, and NIST log-management guidance. NIST describes the AI Risk Management Framework as voluntary guidance for incorporating trustworthiness considerations across AI design, development, use, and evaluation. NIST SP 800-53 is a flexible security and privacy control catalog, including access-control and audit-related families. These sources provide a foundation, but they do not prescribe a complete agent-specific implementation. [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework); [NIST SP 800-53 Rev. 5](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)

## Key Findings

1. **Authorization should be enforced at the tool boundary, not inferred from model intent.** Bind each invocation to an authenticated user or service principal and an explicit policy decision. Scope permissions to the minimum required operation, resource, data, and time window. Separate read and prepare capabilities from write, send, execute, and administrative capabilities. This is a design application of NIST's risk-management and control-catalog approach, rather than a verbatim agent-specific rule.

2. **Risk should be tiered by impact and persistence.** A bounded, reversible, non-sensitive read is generally lower impact than a bulk database mutation, external email send, or recurring job. Stronger checks and human confirmation are appropriate when actions are irreversible, externally visible, broad in scope, or persistent. Approval should be risk-based rather than imposed identically on every tool call.

3. **Retrieved content is data, not authority.** Web pages, search snippets, database records, email bodies, and job parameters may be untrusted or malicious. Preserve provenance, validate arguments, and prevent retrieved content from changing permissions or bypassing policy. The available OWASP LLM Top 10 project page identifies broad risks including prompt injection, data leakage, inadequate sandboxing, and unauthorized code execution; however, it did not expose the detailed 2025 Prompt Injection entry. It therefore supports broad risk framing only, not specific attack mechanics or mitigations. [OWASP LLM Top 10 project](https://owasp.org/projects/top-10-for-large-language-model-applications)

4. **Application-level audit events are a recommended design implication for reconstructing tool actions.** Infrastructure logs alone may not capture the user, authorization context, target, and outcome. A useful event design would record the initiating actor/session, tool and target, requested operation, authorization decision, approval identity where applicable, timestamp, result, and provenance needed for investigation. OWASP's Logging Cheat Sheet describes application logs as useful for audit trails, policy-violation monitoring, and reconstruction of attributable transactions. NIST SP 800-92 provides foundational enterprise log-management guidance, but is dated 2006 and is not agent-specific. [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html); [NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final)

5. **Auditability must be balanced with privacy and log integrity.** Protect logs with access controls and integrity safeguards; consider centralized collection and separation of security events from operational traces. Capture enough context to investigate, but avoid indiscriminate retention of credentials, full prompts, or sensitive tool payloads. OWASP cautions that data crossing trust zones may be missing, modified, forged, replayed, or malicious, and that logging should be proportionate to purpose.

## Evidence and Analysis

### Control design by tool

| Tool | Lower-risk boundary | Higher-risk boundary | Recommended controls |
|---|---|---|---|
| Database | Read-only access to approved, non-sensitive views | Sensitive-data extraction, writes, bulk changes, schema/admin operations | Use narrowly scoped identities and resource-level permissions; separate read from write/admin; minimize returned fields; validate/parameterize queries; require stronger authorization for mutations. |
| Email | Draft-only capability or internal, constrained recipients | External send, sensitive attachments, broad distribution, mailbox administration | Separate draft from send; constrain sender, recipients, attachments, and data classes; require confirmation or policy approval for material external impact; log approval and delivery outcome. |
| Web search | Search with non-sensitive queries and provenance tracking | Queries that disclose sensitive context or retrieved content that can trigger actions | Treat results as untrusted; preserve source provenance; prevent retrieved instructions from expanding authority; constrain what content can flow into other tools. |
| Scheduled jobs | Bounded, one-time, low-impact task | Persistent/recurring execution, broad resource access, externally visible effects | Separate job creation/editing from execution/cancellation; constrain schedule, duration, frequency, target, and execution identity; review high-impact recurring jobs; provide a disable path. |

These tool-specific controls are reasoned applications of the cited general guidance, not direct prescriptions from the source pages. Risk depends on data sensitivity, scope, reversibility, persistence, and exposure—not only on the tool category. For example, a database read can be high impact if it exposes regulated data, while a narrowly scoped one-time job may be low impact.

### Authorization and approval trade-offs

Least privilege reduces blast radius and limits the consequences of prompt injection, mistaken reasoning, or compromised credentials. It also increases integration complexity: teams must define resource scopes, operation classes, and policy checks for each tool. Human approval can reduce unintended high-impact actions, but adds latency and user friction. A practical design is to allow low-impact, reversible actions under policy while requiring explicit approval for actions that are irreversible, persistent, externally visible, or broad in scope. The approval decision should be enforced by a trusted policy layer, not by the model's own assertion that an action is safe.

### Auditability and untrusted inputs

A trace should connect the initiating principal and session to the tool call, target, authorization decision, any approval, and execution result. Provenance for retrieved content helps investigators understand whether untrusted material influenced a call. Logs should be protected against unauthorized access or alteration and retained according to defined operational, security, and privacy purposes. Excessive payload capture can itself create a sensitive-data repository; sparse logs, conversely, may make incident reconstruction impossible. The appropriate balance depends on the threat model and applicable retention requirements.

### Evidence strength and uncertainty

The five distinct eligible pages are official NIST and OWASP sources, as confirmed by the evidence inventory. They support general risk-management, control-catalog, LLM-risk, and logging principles. They do not establish measured effectiveness, universal approval thresholds, or a complete agent-specific control standard. The OWASP LLM page is a project landing page rather than the detailed 2025 Prompt Injection entry. NIST SP 800-92 is foundational and dated 2006. No deployment details were provided about data classification, user roles, tool APIs, approval workflows, or retention rules, so exact permission scopes and thresholds cannot be specified.

## Recommendations

1. **Create a tool authorization layer independent of the model.** Authenticate the initiating user/service, evaluate each call against policy, and bind the decision to the specific tool, operation, resource, and context. Do not treat natural-language intent or model-generated explanations as authorization.
2. **Use capability separation and least privilege.** Provide distinct read, draft/prepare, commit/send/execute, and administrative capabilities. Scope credentials to the minimum data and operations required; use short-lived or otherwise constrained credentials where supported.
3. **Apply risk-based approval.** Require explicit confirmation or policy approval for sensitive-data access, database mutations, external email, broad distribution, and persistent or recurring jobs when impact warrants it. Make approval specific to the proposed action and its target.
4. **Constrain and validate tool inputs.** Use allowlists and schema validation for arguments, enforce resource and schedule limits, and treat all retrieved or cross-trust-zone content as untrusted data. Preserve provenance and prevent content from changing permissions or policy.
5. **Build attributable, protected audit trails.** Record actor/session, tool, target, operation, authorization decision, approval, timestamp, outcome, and relevant provenance. Protect log access and integrity, define retention and review processes, and minimize sensitive payload collection.
6. **Test the complete control path.** Assess authorization bypass, prompt-injection influence, excessive permissions, replay or duplicate execution, approval handling, and audit completeness across each tool. Reassess controls as tools, models, data, and organizational baselines change.

## Limitations

The cited sources are general frameworks and application-security/log-management guidance, not agent-specific implementation standards. Tool-by-tool controls and risk tiers in this report are design implications that require validation against the deployment threat model and organizational policies. The detailed OWASP 2025 Prompt Injection page was not retrieved; the available OWASP project landing page supports only broad risk framing. NIST SP 800-92 is dated 2006 and should be treated as foundational log-management guidance rather than a current agent-specific specification. No quantitative evidence was available to compare control effectiveness, incident likelihood, or operational overhead. Exact permission scopes, approval thresholds, and retention periods remain context-dependent.

## References

1. [AI Risk Management Framework | NIST](https://www.nist.gov/itl/ai-risk-management-framework)
2. [SP 800-53 Rev. 5, Security and Privacy Controls for Information Systems and Organizations | NIST CSRC](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final)
3. [Top 10 for Large Language Model Applications | OWASP](https://owasp.org/projects/top-10-for-large-language-model-applications)
4. [Logging Cheat Sheet | OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)
5. [SP 800-92, Guide to Computer Security Log Management | NIST CSRC](https://csrc.nist.gov/pubs/sp/800/92/final)
