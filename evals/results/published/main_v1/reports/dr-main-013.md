# Secure Browser-to-Private-Object-Storage Upload Patterns

## Background

Direct browser uploads to private object storage can reduce application-server bandwidth and avoid exposing long-lived storage credentials to clients. A common pattern is for an authenticated application backend to authorize an upload and issue a short-lived, narrowly scoped presigned request for one object and one operation. The browser then sends the file directly to storage. This is a temporary bearer capability: anyone who obtains the URL may use it within its scope and validity, so the design must combine authorization, validation, lifecycle controls, and observability.

The evidence reviewed here includes official Amazon S3 and Google Cloud Storage signed-request documentation and the OWASP File Upload Cheat Sheet. The findings preserve only three distinct source pages, below the requested minimum of five. The researcher delegation limit was exhausted before additional focused evidence could be collected; this report does not pad the source list with unverified or irrelevant links.

## Key Findings

1. **Validate files in layers, not by browser metadata alone.** OWASP recommends a narrow extension allowlist, treating the submitted `Content-Type` as untrusted, combining MIME consistency checks with file-signature checks, enforcing a size limit, and using server-generated object names. No single check is sufficient. The appropriate size threshold and accepted formats depend on the application. [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

2. **Scope each signed request to one intended object and operation.** Google Cloud Storage signed URLs are resource- and request-specific, time-limited access mechanisms; the signing identity must have the required permission. S3 presigned URLs likewise identify a bucket/key and operation and use the permissions of the signing principal. A unique server-generated key per upload and private-by-default bucket configuration are prudent least-privilege design choices; the cited provider pages do not prescribe a universal key-generation scheme. [Google Cloud Storage Signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls) · [Amazon S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html)

3. **Treat URLs as credentials and choose expiry around the upload workflow.** Both providers’ signed URLs are bearer-style capabilities. Shorter validity reduces the exposure window, but an overly short lifetime can disrupt slow uploads or retries. S3 checks expiry when a request starts; an in-progress transfer may continue, while a retry started after expiry can fail. Effective S3 validity can also be shortened by temporary credential expiry or policy restrictions. These details are provider-specific and should not be generalized. [Amazon S3 presigned URLs](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html) · [Google Cloud Storage Signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls)

4. **Keep uploaded content untrusted until validation and any required scanning finish.** OWASP identifies antivirus or sandbox scanning where available and content disarm and reconstruction (CDR) for applicable document types as defense-in-depth options. A staging/quarantine state and explicit release after checks are sensible architectural controls, but the evidence collected does not establish a specific provider scanning workflow, coverage guarantee, or quarantine feature.

5. **Auditability needs both storage-side and application-side evidence.** The evidence collected for this run does not establish a complete audit-log configuration or prove what a particular provider records for presigned URL issuance and use. As a design principle, record the authenticated actor/tenant, upload authorization decision, intended object key, issuance time, and outcome in application logs, and correlate these with object-level storage events where configured. Do not log the full presigned URL because it is a bearer credential. These are recommendations, not claims verified by the collected logging documentation.

## Evidence and Analysis

### Control comparison and trade-offs

| Control | Security value | Operational trade-off | Evidence confidence |
|---|---|---|---|
| Layered file validation | Reduces spoofed-type, filename, and resource-exhaustion risks; avoids relying on one bypassable signal. | Requires format-specific allowlists, size policy, and server-side validation. | Strong qualitative support from OWASP; no universal numeric limits. |
| Narrow key and operation scope | Limits what a leaked URL can do and reduces accidental overwrite risk. | Requires backend authorization and key allocation/mapping. | Provider docs support resource/request scope; unique server-generated keys are a design implication. |
| Short-lived signed requests | Limits the time a leaked bearer URL remains useful. | Too-short expiry can break slow transfers or retries; request-signature details can cause client failures. | Strong provider-specific evidence; no universal duration. |
| Malware scanning/quarantine | Can add a content-focused detection layer beyond metadata and signatures. | Adds latency, service dependencies, and a need to gate downstream access. | OWASP supports scanning as defense in depth; implementation evidence is insufficient. |
| Audit logging | Supports investigation and accountability when application and storage events can be correlated. | Requires deliberate event selection, retention, access controls, and correlation identifiers. | Insufficient source evidence in this run for provider-specific logging claims. |

The strongest evidence supports layered validation and narrowly scoped, expiring signed requests. These controls are complementary: signed-request scope limits the capability granted to the browser, while validation addresses the content and resource risks of what is uploaded. Scanning and audit logging are important lifecycle controls, but the collected evidence is not sufficient to specify a complete implementation or assert provider-specific guarantees.

### Source-count and evidence gap

Only three distinct in-run source pages were preserved in findings: OWASP File Upload Cheat Sheet, Google Cloud Storage Signed URLs, and Amazon S3 presigned URLs. The requested minimum of five distinct HTTP(S) sources is therefore not met. Repeated citations to the same page do not count as additional sources. No additional links are introduced to disguise this gap.

## Recommendations

1. Have the backend authenticate and authorize each upload before issuing a signed request. Generate a unique object key server-side (an implementation recommendation derived from resource scoping, not an explicit provider requirement), bind the request to that exact key and intended method, and keep the bucket private. Do not give the browser storage credentials.
2. Use a short validity period that accommodates expected upload duration and retry behavior. Apply provider-specific policy constraints where available, and ensure the browser sends the exact method, headers, and parameters covered by the signature.
3. Enforce a narrow extension allowlist, server-side filename handling, application-appropriate size limits, and layered content checks. Treat browser MIME metadata as untrusted; use signature checks only as one signal, not as a standalone guarantee.
4. Keep new objects in an untrusted staging state. Where the threat model warrants it, scan with antivirus/sandbox tooling and use CDR for applicable formats; release objects to downstream consumers only after required checks complete. Verify the chosen scanner’s coverage, failure behavior, and result signaling before relying on it.
5. Build an audit trail that records authorization and upload lifecycle events without storing the signed URL itself. Correlate application records with configured object-level storage events, and define retention and access controls. Verify the exact event coverage and cost for the selected provider and deployment.
6. Test negative cases such as expired URLs, attempts to write a different key or use a different method, oversized files, spoofed MIME types, disallowed extensions, signature mismatches, scanner errors, and missing audit events. These are recommended test cases, not findings established by the collected sources.

## Limitations

- The findings preserve three distinct source pages, fewer than the requested five. The researcher delegation budget was exhausted; the report explicitly discloses this shortfall rather than adding unverified sources.
- No successfully collected findings document a complete malware-scanning/quarantine workflow or provider-specific audit-log configuration. Recommendations in those areas are architectural guidance and should be validated against the selected storage and scanning services.
- OWASP guidance is qualitative and does not set a universal file-size limit or accepted-format policy.
- Expiration, endpoint, and request-signing behavior varies by provider. The S3 and Google Cloud Storage details cited here should not be assumed to apply to other object-storage services.
- The report does not establish a complete implementation, service-level guarantees, or compliance sufficiency; these depend on the application threat model and deployment configuration.

## References

1. [File Upload - OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html) — validation and defense-in-depth guidance.
2. [Google Cloud Storage Signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls) — signed URL scope, authorization, and expiry semantics.
3. [Download and upload objects with presigned URLs — Amazon S3 User Guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html) — S3 presigned request behavior, expiry, and policy constraints.

## Source-count note

This report contains three distinct verified source pages, not five. The minimum-source requirement remains unmet because additional researcher delegations were unavailable and the remaining evidence was not sufficient to justify adding other links.