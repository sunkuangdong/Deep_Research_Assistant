# Secure Browser-to-Private-Object-Storage Uploads: Research Report

## Background

Presigned requests let an application authorize a browser to upload directly to private object storage without exposing long-lived cloud credentials or routing the entire file through the application server. The security model is a delegated, time-limited capability: the URL or signed request grants a specific operation on a storage resource, and anyone who obtains it may be able to use it while valid. This makes authorization, destination selection, validation, post-upload handling, and auditability parts of one end-to-end design—not properties guaranteed by the presigned request alone.

The evidence base comprises five distinct pages: AWS S3 presigned uploads, Google Cloud Storage signed URLs, OWASP file-upload guidance, AWS S3 server access logging, and Google Cloud Storage audit logging. The analysis distinguishes documented provider behavior from application-level recommendations.

## Key Findings

1. **Treat each presigned request as a secret bearer capability.** Authenticate and authorize the user in the application before issuing it. Grant only the intended operation on the intended object, and do not expose storage credentials. AWS states that a presigned URL's authority is bounded by the signing principal's permissions; Google describes signed URLs as usable by anyone possessing them for the specified action during the active period. [AWS S3 presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html); [Google Cloud Storage signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls)

2. **Choose the object key server-side and account for overwrite behavior.** AWS's documented PUT flow targets a specified bucket and key; uploading to an existing key replaces that object. Use unique, application-selected keys and avoid letting untrusted clients choose arbitrary storage destinations. Sign relevant request attributes where supported and ensure the browser sends the matching request. The evidence does not establish specific POST-policy size or prefix conditions, so do not assume those constraints without verifying the exact mechanism and configuration. [AWS S3 presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html)

3. **Use the shortest practical expiration, but do not treat expiry as single-use or leak protection.** AWS documents up to seven days for SDK/CLI-generated presigned URLs; Google says a signed URL ceases to work at expiry or signing-key rotation. A valid URL remains usable by its holder during its validity window, so short expiry complements—not replaces—narrow scope and careful handling. [AWS S3 presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html); [Google Cloud Storage signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls)

4. **Validate files in layers and keep uploads untrusted until checks pass.** OWASP recommends extension allowlists, filename decoding before validation, treating client-provided content type as untrusted, size limits, authorization checks, server-generated filenames, and file-signature checks only as a supplementary signal. Antivirus or sandbox scanning and Content Disarm & Reconstruct (CDR) may be appropriate where available and relevant. A quarantine-and-release workflow is a sound implementation pattern, but the cited guidance does not prescribe a cloud-specific quarantine service or state machine. [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html)

5. **Configure storage logs deliberately and supplement them for end-to-end auditability.** AWS S3 server access logging can record bucket requests, but delivery is best effort and records may be delayed, duplicated, or absent; it should not be the sole transactional audit ledger. Google Cloud Storage audit logs provide categorized API activity, including `DATA_WRITE`, but Data Access logging must be enabled. Storage logs alone may not capture application authorization decisions, scan outcomes, or release decisions; record those workflow events in application-level audit records when required. [AWS S3 server access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html); [Google Cloud Storage audit logging](https://docs.cloud.google.com/storage/docs/audit-logging)

## Evidence and Analysis

### Authorization, key scope, and expiration

Both providers' signed requests are bearer capabilities, so the application should make the identity and authorization decision before issuing one. The storage request should be constrained to a specific resource and operation. AWS's documented upload example binds the request to a bucket/key and can bind a content type; the request must match the signed parameters. Existing-key replacement makes key uniqueness important for both isolation and retry behavior. Google documents resource/action-specific signed URLs and notes that they use XML API endpoints.

Shorter validity reduces the time available for a leaked URL to be abused, but it does not prevent use or repeated attempts while the URL remains valid. Expiry can also create operational friction for slow uploads or retries. The appropriate lifetime is therefore the shortest one compatible with the expected upload workflow, with a controlled re-authorization path for expired requests. The evidence does not establish a Google maximum lifetime comparable to AWS's documented SDK/CLI maximum.

### Validation and malware handling

A presigned request authorizes transfer; it does not establish that the content is safe. Layered validation should combine business-specific type allowlists, size limits, safe server-generated object names, and content inspection. Client-supplied MIME type is not trustworthy, and file signatures should not be treated as a complete defense. Where risk and file types warrant it, scan with antivirus or sandbox tooling and consider CDR.

A practical architecture is to upload into a private quarantine location or state, then make the object available to downstream consumers only after validation and scanning succeed. This quarantine/release design is an implementation inference from OWASP's defense-in-depth guidance, not a cloud-specific workflow specified by the cited sources. Scanning adds processing time and operational complexity; the evidence provides no comparative detection rates or latency measurements.

### Audit logging and provider trade-offs

AWS S3 server access logs provide request-level visibility and can be delivered to CloudWatch Logs or an S3 bucket. AWS explicitly warns that delivery is best effort, with possible delay, duplication, or omission. Google Cloud Storage audit logging offers categories including Admin Activity, Data Access (`ADMIN_READ`, `DATA_READ`, `DATA_WRITE`), and System Event; Data Access logging must be enabled. These mechanisms support investigation, but neither source establishes a complete record of the full application workflow.

For a defensible audit trail, configure the relevant storage data-access events, protect and retain logs according to organizational requirements, and correlate them with application records for user authorization, issued upload capability, object identity, validation/scanning result, and release or rejection. These are recommendations; the sources do not specify retention periods, alerting rules, or a compliance-ready configuration.

### Overall assessment

Direct browser-to-storage uploads can reduce application-server bandwidth and avoid exposing long-lived credentials, but they shift security emphasis to capability scope and post-upload controls. The strongest pattern supported by the evidence is: application authorization → server-selected unique key and narrow short-lived request → private upload/quarantine → layered validation and malware scanning → explicit release decision → correlated storage and application audit records. Provider-specific request and logging behavior must be verified for the chosen service; the evidence does not support a universal provider ranking.

## Recommendations

1. Authenticate and authorize each upload request in the application before issuing a presigned capability; bind it to the narrowest practical object, operation, and request attributes.
2. Generate unique object keys server-side. Prevent unintended overwrites and do not accept arbitrary client-selected bucket/key destinations.
3. Set the shortest practical expiration, protect the URL as a secret, and provide a controlled way to obtain a new capability after expiry. Do not assume expiry makes a URL single-use.
4. Enforce file-size and business-type limits and use layered validation. Treat filename and client MIME type as untrusted; use signature checks only as one signal.
5. Keep new objects private and unavailable to ordinary consumers until required validation and malware scanning pass. Record explicit pass/fail and release decisions; use sandboxing or CDR where appropriate and available.
6. Enable the storage audit categories needed for data writes and access. Account for AWS S3 server access logging's best-effort delivery and Google Cloud Storage Data Access logging's enablement requirement.
7. Maintain application-level audit events for authorization, capability issuance, object key, scan result, and release/rejection, and correlate them with provider logs when a complete workflow history is required.
8. Verify provider-specific constraints—especially POST policy conditions, size limits, and request matching—against the exact API and configuration before relying on them. The evidence reviewed here does not substantiate specific AWS POST-policy conditions.

## Limitations

The evidence is limited to five distinct official/security-guidance pages and does not provide a complete implementation specification. The AWS POST-policy conditions page was not retrieved, so no specific POST-policy syntax or enforced size/prefix constraint is asserted. The Google signed-URL page content was reported as truncated in the findings; the comparison is limited to the statements preserved there, and no comparable Google maximum URL lifetime is established. OWASP guidance does not define a cloud quarantine state machine, scan trigger, release policy, or malware-detection performance. The logging sources do not establish retention, cost, delivery-latency distributions, alerting, tamper resistance, or compliance mappings. No quantitative evidence supports provider rankings or estimates of risk reduction.

**Sources (official provider documentation and security guidance):** [AWS S3 presigned uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/PresignedUrlUploadObject.html); [Google Cloud Storage signed URLs](https://docs.cloud.google.com/storage/docs/access-control/signed-urls); [AWS S3 server access logging](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerLogs.html); [Google Cloud Storage audit logging](https://docs.cloud.google.com/storage/docs/audit-logging); [OWASP File Upload Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html).
