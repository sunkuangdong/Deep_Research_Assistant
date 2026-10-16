# Continuous Delivery Practices for AI Agent Applications

## Background

AI agent applications combine ordinary application code with probabilistic model behavior, tool integrations, prompts, and often mutable external state. A reliable delivery process therefore needs more than conventional unit tests: it must distinguish deterministic application contracts from variable model outcomes, validate integrations in controlled environments, and make each release reproducible and reversible.

The evidence base for this report consists of four distinct official documentation pages: LangChain’s testing guidance, OpenAI’s agent-evaluation guide, GitHub Actions workflow documentation, and Anthropic’s evaluation guidance. The recommendations below synthesize those sources with explicit operational practices; where a source does not prescribe a specific mechanism, that is identified as a recommendation rather than a vendor requirement.

## Key Findings

### 1. Separate deterministic tests from probabilistic evaluation

Use deterministic tests for properties owned by the application: routing logic under controlled inputs, tool argument schemas, call counts, state transitions, serialization, error handling, and output contracts. Replace model and tool dependencies with fixed-response fakes or mocks so tests are fast, repeatable, and do not incur API costs or external side effects. LangChain’s testing guidance distinguishes unit tests using in-memory fakes from integration tests that exercise real network calls, and notes that agent applications often need integration coverage because they compose multiple components and model behavior is nondeterministic ([LangChain testing guidance](https://docs.langchain.com/oss/python/langchain/test)).

Mocks should verify both outputs and interactions: for example, assert that the agent requested the expected tool with valid arguments, and that the application handled the tool result or failure correctly. For integration tests that write data, use disposable databases, temporary storage, transactions, or sandboxed services. These isolation details are engineering recommendations derived from the documented fake-versus-real integration boundary, not a specific prescription from the cited framework documentation.

### 2. Use evaluations for workflow quality, not as deterministic guarantees

A fixed evaluation set can test representative agent tasks, edge cases, and expected outcomes across candidate changes. OpenAI’s documentation addresses evaluating agent workflows ([OpenAI agent evaluations](https://developers.openai.com/api/docs/guides/agent-evals)); Anthropic recommends specific, measurable success criteria and evaluation cases that reflect the real task distribution, including edge cases, with exact-match checks where appropriate ([Anthropic evaluation guidance](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)).

Treat evaluation results as evidence about a versioned test set, not proof that every future run will behave identically. Use exact assertions for objective properties and rubric- or judge-based evaluation only for qualities that cannot be captured mechanically. As an operational recommendation, use repeated runs or aggregate metrics for stochastic outcomes and compare against a baseline; avoid blocking a release on a single noisy sample unless the check is a hard safety invariant.

### 3. Add live smoke tests after deployment to an isolated environment

Mocks cannot establish that credentials, network access, deployed configuration, model endpoints, or real tool integrations work together. After deploying to staging, run a small set of live smoke tests with synthetic, non-sensitive inputs. Check endpoint availability, response schema, a critical end-to-end path, expected tool-call behavior, and essential safety constraints. Keep tests bounded with timeouts and limited retries, and use staging credentials and tools that cannot affect production data.

Live smoke tests are a recommended operational layer, not a protocol specified by the cited pages. They are inherently more expensive and less deterministic than mocked tests; isolate side effects and interpret transient model variation with explicit tolerances.

### 4. Version prompts and evaluation inputs as release artifacts

Treat prompts as executable configuration. Store prompt revisions in source control or an immutable versioned store, assign each revision an identifier, and record it with the model identifier, tool/schema versions, evaluation-set revision, and application artifact. This makes a regression attributable and supports rollback to a known-good combination. Anthropic’s evaluation guidance supports measuring candidate behavior against defined criteria and representative cases, but does not prescribe a particular prompt registry or versioning product. The versioning scheme here is an operational recommendation.

### 5. Make regression gates staged and traceable

GitHub Actions workflows support automated processes organized around triggers, jobs, runners, artifacts, and deployment environments ([GitHub Actions workflow concepts](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)). A practical release gate can use that structure:

- **Pull request:** run deterministic unit tests, mocked-tool contract tests, static checks, and a compact offline evaluation suite.
- **Merge/build:** run broader regression evaluations; preserve the exact application, prompt, tool-schema, and evaluation-set revisions as build metadata or artifacts.
- **Staging deployment:** run live smoke tests with isolated credentials and synthetic inputs.
- **Promotion:** block release if hard deterministic checks fail, evaluation metrics exceed agreed regression tolerances, or smoke tests fail. Use protected deployment environments or approval for high-impact changes.

Set thresholds before observing candidate results, compare against a known baseline, and retain test outputs for audit and diagnosis. The exact pipeline and thresholds are organization-specific; the cited workflow and evaluation pages provide building blocks and evaluation principles, not universal agent-release thresholds.

## Recommendations

1. **Build a test pyramid:** many fast deterministic tests with fake models/tools; a smaller set of integration tests against sandboxed services; and a compact, representative live smoke suite after staging deployment.
2. **Define tool contracts explicitly:** validate tool input/output schemas, authorization boundaries, error behavior, and side effects. In unit tests, use mocks that record calls; in integration tests, use disposable or sandboxed resources.
3. **Maintain a versioned evaluation set:** include common tasks, edge cases, failure cases, and safety-critical scenarios. Keep evaluation data and scoring criteria under revision control, and distinguish hard invariants from quality metrics.
4. **Gate on multiple signals:** deterministic test failures and critical safety violations should block immediately; stochastic quality metrics should use baselines, tolerances, and sufficient repeated observations to reduce noise.
5. **Make releases reproducible:** record application build, prompt revision, model identifier, tool/schema versions, evaluation-set revision, and deployment configuration together. Preserve artifacts and logs, and define a rollback path to a known-good combination.
6. **Keep live tests safe and small:** use staging-only credentials, synthetic inputs, bounded retries/timeouts, and tools with no production side effects. Do not use a live smoke test as a substitute for deterministic coverage.

## Limitations

The sources establish useful testing distinctions, evaluation principles, and CI workflow concepts, but they do not define a universal agent-specific CI/CD standard. In particular, the cited documentation does not prescribe a standard live-smoke protocol, prompt registry, regression threshold, or acceptable stochastic variance. Those controls must be tailored to the application’s risk, model behavior, and tool permissions.

The OpenAI agent-evaluation page was retrieved, but the available content was limited; this report therefore avoids claims about specific evaluator APIs or configurations. Some recommendations—such as prompt revision metadata, staging isolation, and multi-stage release gates—are operational synthesis rather than direct vendor requirements. Live model and external-service tests can be costly, nondeterministic, and sensitive to changing dependencies; results should be interpreted with those constraints in mind.

## References

1. [LangChain: Test](https://docs.langchain.com/oss/python/langchain/test)
2. [OpenAI API: Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals)
3. [GitHub Docs: Workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows)
4. [Claude Platform Docs: Define success criteria and build evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)
