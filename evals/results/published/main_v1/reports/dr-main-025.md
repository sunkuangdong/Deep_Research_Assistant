# Continuous Delivery Practices for AI Agent Applications

## Background

AI agent releases combine conventional software changes with probabilistic model behavior, prompts, tool integrations, and external services. A useful delivery process therefore needs both repeatable checks for properties that can be asserted exactly and carefully bounded evaluations for behavior that is inherently variable. The evidence reviewed here supports a layered approach: representative evaluation cases with explicit pass criteria (a practical recommendation; detailed grader procedures were not verified in the retrieved OpenAI material), controlled tool boundaries, CI regression gates, traceable prompt/configuration changes, and a small deployment-stage validation layer.

## Key Findings

### Deterministic tests and regression suites

Treat agent behavior as a versioned test surface. Maintain representative inputs and expected outcomes, and rerun them when prompts, models, tools, or orchestration change. OpenAI's eval guidance supports evaluating application behavior against defined test cases; for agent systems, deterministic assertions are best applied to objectively checkable properties such as structured fields, tool choice and arguments, state transitions, and task completion. Exact string matching is often too brittle for open-ended language, so qualitative criteria should be separated from hard assertions. Preserve per-case results and execution traces where possible so regressions can be diagnosed rather than reduced to a single aggregate score. [OpenAI evals documentation](https://developers.openai.com/api/docs/guides/evals)

### Mocked tools and controlled boundaries

Use fake or mocked tools in fast tests to return controlled data and isolate orchestration logic from network, database, or third-party variability. Assert that the agent selects the intended tool, passes valid arguments, handles tool errors, and incorporates returned data correctly. LangChain's overview demonstrates a custom deterministic tool function, which illustrates a useful seam, but it is not a dedicated testing guide and does not prescribe a mocking framework. Accordingly, the specific test design above is an engineering recommendation rather than a documented LangChain requirement. [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview)

### Live smoke tests and deployment-stage checks

Mocks cannot establish that deployed credentials, network access, provider configuration, or the live endpoint work together. Add a small, bounded smoke suite against a staging or canary deployment: verify health, one representative end-to-end task, expected tool connectivity, and safe failure behavior. Keep these checks separate from broad evaluation suites, use controlled test accounts/data, and avoid side effects. GitHub Actions environments provide a way to model staging and production targets, apply protection rules, require reviewers, restrict branches, and control access to environment secrets. This is deployment infrastructure guidance, not agent-specific smoke-test guidance; the smoke-test design is a recommendation. [GitHub deployment environments](https://docs.github.com/zh/actions/writing-workflows/choosing-what-your-workflow-does/using-environments-for-deployment)

### Prompt versioning and regression gates

Store prompts and evaluation configuration in version control alongside application code. Associate each evaluation run with the commit SHA and CI run identifier, retain machine-readable and human-readable results, and make prompt/configuration changes trigger evaluation. Promptfoo's CI/CD guide demonstrates running evaluations in pull requests, exporting reports, tagging runs with Git metadata, and failing a workflow when failures or configured thresholds are reached. This provides traceability and a practical regression gate, but it does not establish a dedicated immutable prompt registry or a complete production rollout/rollback system. [Promptfoo CI/CD integration](https://www.promptfoo.dev/docs/integrations/ci-cd/)

A practical gate sequence is: (1) deterministic unit and tool-contract tests on every change; (2) a representative evaluation suite for prompt/model/orchestration changes; (3) security or red-team checks on relevant changes and periodically; (4) staging smoke tests after deployment; and (5) protected promotion to production. Define thresholds and exceptions explicitly, retain artifacts, and require review for intentional behavior changes rather than silently weakening tests.

## Recommendations

1. **Separate test layers by cost and determinism.** Run fast deterministic tests with mocked tools on every change. Use a broader evaluation suite for behavior-level regressions, and reserve live tests for a small number of high-value end-to-end checks.
2. **Assert contracts, not arbitrary prose.** Check tool selection/arguments, schemas, state transitions, safety constraints, and task outcomes. Use semantic or human-reviewed evaluation for open-ended response quality; do not treat a model-graded score as perfectly deterministic.
3. **Version the full behavior configuration.** Commit prompts, tool schemas, model identifiers/settings, orchestration code, and evaluation datasets/configuration. Record the commit SHA, model/provider details, and evaluation run ID with results so a release can be reproduced as far as external model behavior permits.
4. **Make regression gates actionable.** Set explicit pass criteria, retain per-case failures and traces, and block merges or promotion on material regressions. Provide a documented review path for accepted changes; do not hide regressions by changing thresholds without review.
5. **Use live smoke tests sparingly and safely.** Run them against staging or canary after deployment, with bounded calls, test data, controlled credentials, and clear cleanup. Gate production promotion on their result and use environment protections or equivalent controls.
6. **Keep security checks distinct from quality checks.** Schedule or trigger red-team/security evaluations as a complementary gate; a passing functional eval does not establish security.

## Limitations

The evidence base is small and documentation-led. OpenAI's eval page supports the general evaluation approach, but the retrieved material did not verify detailed grader procedures. LangChain's current overview demonstrates a deterministic custom tool but is not a dedicated testing guide; specific mock/fake recommendations are therefore implementation guidance. Promptfoo documents CI evaluation, metadata, artifacts, and failure thresholds, but not a complete prompt registry, canary strategy, or rollback process. GitHub documents deployment environments and protection controls, not AI-agent-specific smoke-test cases. Live model outputs and provider behavior can change even when application code and prompts are unchanged, so reproducibility is bounded rather than absolute.

This run used `--no-analysis`; no analyst phase was performed.

### References

1. [Working with evals | OpenAI API](https://developers.openai.com/api/docs/guides/evals) — primary documentation.
2. [LangChain overview | Docs by LangChain](https://docs.langchain.com/oss/python/langchain/overview) — primary documentation.
3. [CI/CD Integration for LLM Eval and Security | Promptfoo](https://www.promptfoo.dev/docs/integrations/ci-cd/) — primary documentation.
4. [Using environments for deployment | GitHub Docs](https://docs.github.com/zh/actions/writing-workflows/choosing-what-your-workflow-does/using-environments-for-deployment) — primary documentation.