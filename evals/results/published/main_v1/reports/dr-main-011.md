# Security Controls for Tool-Calling Agents

## Background
Tool-calling agents can cross from language generation into consequential operations: querying databases, sending email, searching public or authenticated web resources, and creating or modifying scheduled jobs. Security therefore depends not only on model behavior, but on the identity and permissions behind each tool, how untrusted content is handled, how side effects are approved, and whether actions can later be reconstructed.

This report synthesizes general zero-trust architecture guidance, OWASP prompt-injection guidance, a tool-integrated-agent benchmark, and NIST log-management guidance. The evidence is not a complete agent-specific control standard; implementation recommendations are identified as applications of broader principles.

## Key Findings
- **Authorization should be the hard boundary on capability.** Authenticate the agent/runtime and the represented human or service principal, then authorize each operation against its specific resource. Do not infer trust from network location or grant broad credentials merely because the agent runs in a trusted environment. This applies the resource-centric principles in [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final).
- **Treat retrieved content as untrusted data.** Web pages, search results, and emails may contain instructions intended to redirect the agent. OWASP describes prompt injection as a route to unintended actions, data leakage, or unauthorized access; filtering and sanitization are useful but not complete guarantees ([OWASP LLM01:2023](https://owasp.github.io/www-project-top-10-for-large-language-model-applications/Archive/0_1_vulns/Prompt_Injection.html)).
- **Tool-integrated agents have demonstrated susceptibility in benchmark settings.** InjecAgent reports 1,054 test cases across 17 user tools and 62 attacker tools, and a 24% vulnerability rate for ReAct-prompted GPT-4 in its evaluation. These results are benchmark-specific, not a real-world prevalence estimate ([InjecAgent](https://arxiv.org/abs/2403.02691)).
- **Consequential actions need layered gates.** For sending email, changing database records, or scheduling jobs, combine narrow permissions with validation against the user's request and explicit confirmation where impact warrants it. Confirmation does not replace least privilege; logging does not itself prevent an action.
- **Auditability requires correlated, protected, privacy-conscious records.** Record the initiating run and each tool attempt/outcome with identity, action, target, status, and timestamps; protect logs from alteration and loss, monitor for gaps, and minimize sensitive payload capture. These are practical applications of NIST's enterprise log-management guidance, not an agent-specific schema ([NIST SP 800-92](https://csrc.nist.gov/pubs/sp/800/92/final)).

## Evidence and Analysis
### Authorization and tool boundaries
NIST SP 800-207 frames zero trust around resource protection and discrete authentication and authorization before resource sessions, rather than implicit trust based on network location or ownership. Applied to agents, policy should be enforced at each tool/resource boundary and consider the runtime identity, represented principal, requested operation, target resource, and relevant context. Model-generated intent or a tool description should never itself confer authority.

Practical least-privilege examples include read-only or constrained database access; separating email read, draft, send, and mailbox-administration permissions; separating public web retrieval from authenticated actions; and limiting job submission, inspection, cancellation, queues, projects, and environments. These are implementation implications of the NIST principles, not prescriptions stated verbatim in SP 800-207.

### Prompt injection and side effects
OWASP identifies prompt injection as crafted input that can cause a model to ignore prior instructions or perform unintended actions, with possible data leakage and unauthorized access. The InjecAgent benchmark provides empirical evidence that indirect prompt injection can affect tool-integrated agents, but its reported rates should not be generalized across models or deployments.

The controls address different failure modes and are complementary:

| Control layer | Primary purpose | Suitable emphasis | Limitation / trade-off |
|---|---|---|---|
| Resource- and operation-scoped authorization | Limit what a tool call can do | Authenticated databases, mailboxes, web accounts, and job systems | Fine-grained policy and credential management add complexity; authorization alone does not ensure user intent is followed. |
| Untrusted-content handling and call validation | Reduce instruction confusion from retrieved content | Web search, fetched pages, email bodies, and other external text | Filtering and sanitization cannot be treated as complete defenses. |
| Confirmation for consequential actions | Catch unintended high-impact side effects before execution | Sending email, modifying records, creating/canceling jobs | Adds friction and may be ineffective if approvals are not meaningfully reviewed. |
| Correlated, protected audit logs | Support detection, reconstruction, and investigation | All tool calls, especially high-impact or sensitive workflows | Logs can expose sensitive data; logging is primarily detective, not preventive. |

For auditability, a useful event record should link the user request/run to each tool call and completion or failure. Candidate fields include timestamp, correlation ID, agent/service and represented identity, tool, operation, target, safe parameter references, result/status, error, and duration. Protect write/delete access, monitor missing or delayed events, and set retention deliberately. Prefer metadata or references over full query results, email bodies, or job payloads; redact or tokenize secrets and personal data. The accessible NIST SP 800-92 publication page verifies the guide's broad log-management purpose but does not establish this agent-specific schema or universal retention/integrity settings.

### Overall assessment
The strongest design is layered: authorization limits the blast radius; untrusted-content handling reduces the chance that external text redirects the agent; confirmation gates reduce unintended consequential actions; and protected audit records support detection and investigation. For low-risk public read-only retrieval, content separation, call validation, and basic event logging may be proportionate. Authenticated or high-impact workflows warrant narrower credentials, explicit action gates, and stronger monitoring. The evidence does not quantify the cost, false-positive rate, or comparative effectiveness of these controls.

## Recommendations
1. **Use explicit identities and per-resource policy.** Authenticate the runtime and the principal on whose behalf it acts. Authorize each tool, operation, and target independently; deny by default and avoid shared administrator credentials.
2. **Separate capabilities by risk.** Provide distinct read/query, draft, send, modify, schedule, cancel, and administrative operations. Constrain database schemas/operations, email identities and recipients, authenticated web scopes, and job queues/projects/environments.
3. **Treat all external content as untrusted.** Keep retrieved text separate from trusted instructions. Validate every proposed tool call against the user's request and the authorized scope; reject calls justified only by instructions embedded in retrieved content. Do not rely on prompt wording or sanitization as the sole defense.
4. **Gate consequential side effects.** Require explicit confirmation for actions such as sending external email, changing sensitive records, or creating recurring/high-impact jobs. Present the exact target and action for review, and retain least-privilege enforcement even after approval.
5. **Make actions reconstructable.** Correlate the initiating request, authorization decision, tool call, and outcome. Record identity, operation, target, timestamp, status, and safe parameter references; protect logs against unauthorized alteration/deletion and alert on gaps or unusual high-impact activity.
6. **Balance audit detail with privacy.** Avoid logging secrets and full sensitive payloads by default. Use redaction/tokenization, access controls, purpose-based retention, and controlled archival/deletion; capture content only when justified and protected.
7. **Test the control chain.** Exercise indirect prompt-injection scenarios and verify that policy enforcement, confirmation, and logging still work when retrieved content attempts to redirect the agent. Treat benchmark results as motivation for testing, not as a deployment-specific risk estimate.

## Limitations
- The evidence preserves **four distinct source pages**, fewer than the requested minimum of five. Search and researcher budgets were exhausted before a fifth reliable page could be added; no irrelevant link is included to pad the source list.
- NIST SP 800-207 is general zero-trust architecture guidance, not an agent-specific authorization standard. Tool-specific examples are reasoned applications.
- The accessible NIST SP 800-92 publication page supports the guide's broad log-management scope, but detailed event fields, integrity mechanisms, retention periods, and alert thresholds in this report are implementation recommendations rather than verified requirements from the accessible text.
- InjecAgent's results are specific to its benchmark, tested agents, tools, and attack setup; they do not establish real-world prevalence or current performance across deployments. No complete prompt-injection defense is established by the sources.
- The findings do not quantify operational cost, user friction, false positives, or comparative control effectiveness. Recommendations should be validated against the deployment's threat model, data sensitivity, and legal/records obligations.

## References
1. [NIST SP 800-207, Zero Trust Architecture](https://csrc.nist.gov/pubs/sp/800/207/final) — official NIST source.
2. [OWASP LLM01:2023 – Prompt Injections](https://owasp.github.io/www-project-top-10-for-large-language-model-applications/Archive/0_1_vulns/Prompt_Injection.html) — OWASP source.
3. [InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents](https://arxiv.org/abs/2403.02691) — research paper hosted on arXiv.
4. [NIST SP 800-92, Guide to Computer Security Log Management](https://csrc.nist.gov/pubs/sp/800/92/final) — official NIST source.

**Source-count note:** The findings preserve four distinct URL pages (NIST SP 800-207, OWASP LLM01, InjecAgent, and NIST SP 800-92). The final report therefore does not meet the requested minimum of five distinct source links; this gap is disclosed rather than filled with an unverified or irrelevant source.
