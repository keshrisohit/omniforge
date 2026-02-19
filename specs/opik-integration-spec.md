# Opik Integration: LLM Observability for OmniForge

**Created**: 2026-02-02
**Last Updated**: 2026-02-02
**Version**: 1.0
**Status**: Draft

## Overview

Integrate Opik (cloud free tier) into OmniForge's LLM layer to give SDK developers visibility into every LLM call their agents make. Today, when an agent produces unexpected output or fails silently, developers have no structured way to inspect what prompts were sent, what came back, how long it took, or where in a multi-step agent flow things went wrong. This integration wraps all LiteLLM calls with Opik tracing so developers can open a dashboard and immediately see the full execution timeline of their agent, from the first prompt to the final response.

## Alignment with Product Vision

The product vision states that "a developer can create and deploy an agent using the SDK in under 5 minutes." Debugging is a core part of the development loop. Without observability, developers spend disproportionate time adding print statements, reading logs, and guessing what went wrong. Opik integration directly supports the SDK-first, developer-friendly principle by making agent behavior transparent out of the box.

This also aligns with the "cost" principle -- Opik's free cloud tier means zero additional cost for developers getting started, and the tracing data (tokens, latency) helps developers optimize their agents for cost and performance.

## User Personas

### Primary Users
- **SDK Developer (Solo/Small Team)**: Building agents with OmniForge's Python SDK. Uses 1-3 LLM providers. Needs to understand why their agent produced a bad response, which step in a chain-of-thought went off track, or why a fallback model was triggered. Currently relies on print statements and log files.

- **SDK Developer (Evaluating OmniForge)**: Trying OmniForge for the first time. Wants to understand what happens under the hood when they run an agent. Observability makes OmniForge feel transparent and trustworthy compared to opaque alternatives.

### Secondary Users
- **Platform Developer (Future)**: When the chatbot-driven platform is built, the same tracing layer can power a monitoring dashboard for no-code users. Not in scope now, but the integration should not preclude this.

## Problem Statement

When an OmniForge agent produces unexpected results, developers currently have no structured way to answer basic debugging questions:

1. **What prompt was actually sent?** -- Agents construct prompts dynamically (system prompts, skill content, conversation history). The final prompt sent to the LLM is often different from what the developer wrote.
2. **What did the LLM actually return?** -- Raw responses get processed, parsed, and transformed. Developers need the unprocessed response.
3. **Why is this slow?** -- Multi-step agents make several LLM calls. Without per-call latency data, developers cannot identify bottlenecks.
4. **Why did the fallback trigger?** -- OmniForge has automatic model fallback (primary -> fallback models -> OpenRouter). When a fallback activates, developers need to know which model failed and why.
5. **How much is this costing?** -- Token counts per call let developers estimate costs and optimize prompts.
6. **Where in the agent flow did things go wrong?** -- A skill orchestrator agent might: analyze intent (LLM call 1), select a skill (LLM call 2), execute the skill (LLM calls 3-N). Developers need to see these as a connected trace, not isolated calls.

The current workaround is print statements (there are literal `print("llm_traces")` calls in the codebase). This is fragile, clutters output, and provides no structure or persistence.

## User Journeys

### Journey 1: First-Time Setup (2 minutes)

1. Developer installs OmniForge SDK and wants tracing enabled.
2. Developer signs up for Opik cloud free tier at opik.com, gets an API key.
3. Developer sets two environment variables:
   ```
   OPIK_API_KEY=op-...
   OPIK_WORKSPACE=my-workspace
   ```
4. Developer runs their agent as usual. No code changes needed.
5. Developer opens Opik dashboard and sees traces appearing automatically.

**Key moment**: Zero code changes. If the env vars are set, tracing is on. If they are not set, nothing changes.

### Journey 2: Debugging a Bad Agent Response

1. Developer's agent produces an incorrect answer to a user query.
2. Developer opens Opik dashboard, finds the trace for that request (searchable by time, trace ID, or metadata).
3. Developer sees the full trace tree:
   - Root span: "agent_execution" with the user's original query
   - Child span 1: "intent_analysis" -- sees the prompt and LLM response that classified the intent
   - Child span 2: "skill_selection" -- sees which skill was chosen and why
   - Child span 3: "skill_execution" -- sees the actual skill prompt and response
4. Developer identifies that the intent analysis misclassified the query, leading to the wrong skill being selected.
5. Developer adjusts the system prompt and re-runs. New trace confirms the fix.

### Journey 3: Investigating Fallback Behavior

1. Developer notices their agent is slower than expected.
2. Developer opens Opik dashboard and sees that the primary model call has an error tag.
3. The trace shows: primary model returned 429 (rate limit), fallback model 1 also returned 429, fallback model 2 succeeded but took 8 seconds.
4. Developer sees the model name, error message, and latency for each attempt.
5. Developer adjusts their rate limiting strategy or switches default model.

### Journey 4: Disabling Tracing for Production

1. Developer is ready to deploy their agent.
2. Developer removes (or never sets) the `OPIK_API_KEY` environment variable.
3. Agent runs exactly as before with zero overhead. No Opik code is imported or executed.

## What Should Be Tracked

### Per LLM Call (Span)
| Data | Source | Why It Matters |
|------|--------|----------------|
| Model name | LiteLLM call args | Know which model actually responded (especially with fallbacks) |
| Provider | Derived from model | Identify provider-specific issues |
| Input messages (full prompt) | LiteLLM call args | See exactly what was sent to the LLM |
| Output response (full text) | LiteLLM response | See exactly what came back |
| Input tokens | LiteLLM response usage | Cost tracking, prompt optimization |
| Output tokens | LiteLLM response usage | Cost tracking, response length monitoring |
| Latency (ms) | Measured around call | Performance debugging |
| Status (success/error) | LiteLLM response or exception | Error identification |
| Error message | Exception details | Root cause analysis |
| Temperature | LiteLLM call args | Reproduce behavior |
| Max tokens | LiteLLM call args | Understand truncation |
| Is fallback attempt | Internal tracking | Know when fallbacks activated |
| Fallback reason | Exception from previous attempt | Know why primary failed |

### Per Agent Execution (Trace)
| Data | Source | Why It Matters |
|------|--------|----------------|
| Trace ID | Generated at agent entry point | Correlate all LLM calls for one user request |
| Agent type | Agent class name | Filter by agent type in dashboard |
| User query (input) | Agent input | Search traces by query content |
| Final response (output) | Agent output | See end-to-end result |
| Total duration | Measured at agent level | End-to-end performance |
| Total tokens | Sum of all spans | Aggregate cost view |
| Skill name (if applicable) | Skill orchestrator | Know which skill was executed |
| Number of LLM calls | Count of child spans | Identify chatty agents |

## Success Criteria

### User Outcomes
- A developer can go from "my agent gave a wrong answer" to "I can see exactly which LLM call went wrong and what prompt caused it" in under 60 seconds using the Opik dashboard.
- A developer can enable tracing by setting environment variables only -- zero code changes to their existing agent code.
- A developer who does NOT set `OPIK_API_KEY` experiences zero performance impact and zero import errors (Opik is not imported at all).
- Multi-step agent traces (e.g., skill orchestrator: intent -> selection -> execution) appear as a single connected trace with parent-child spans in Opik.

### Technical Outcomes
- All LiteLLM `acompletion` calls across the codebase are traced (there are 5 call sites: `llm_generator.py`, `llm.py` tool, `intent_analyzer.py`).
- Fallback attempts within `_execute_with_rate_limit_fallback` are captured as sibling spans under a parent span, showing the progression from primary to fallback models.
- The `print("llm_traces")` debug statements in `llm.py` can be removed after this integration.

## Key Experiences

- **Zero-config activation**: Setting `OPIK_API_KEY` is the only thing needed. No `opik.init()` calls in user code, no config objects to create, no decorators to add. The SDK handles it internally.

- **Trace hierarchy matches mental model**: When a developer looks at a trace, the structure should match how they think about their agent. A skill orchestrator trace should show "intent analysis" then "skill selection" then "skill execution" as distinct, labeled steps -- not a flat list of anonymous LLM calls.

- **Graceful absence**: If Opik is not installed (`pip install omniforge` without opik extra) or not configured, there is no warning, no error, no degraded behavior. The tracing code path is simply not executed.

## Edge Cases and Considerations

- **Opik cloud is unreachable**: Tracing should be fire-and-forget. If Opik's API is down, the agent must continue working without errors. Tracing failures must be silently logged (at DEBUG level), never raised.

- **Streaming responses**: The `execute_streaming` method in `LLMTool` yields tokens incrementally. The trace should capture the complete accumulated response, not individual chunks. The span should close when streaming is done.

- **Sensitive data in prompts**: Some prompts may contain API keys or user data. This spec does NOT add redaction -- that is a future concern. For now, developers should be aware that prompts are sent to Opik cloud. This should be documented.

- **Opik as optional dependency**: Opik should be an optional pip extra (`pip install omniforge[tracing]`). The core SDK must not depend on it. Use lazy imports and check for availability at runtime.

- **Multiple agents in one process**: If a developer runs multiple agents, each should produce its own trace. Trace context should not leak between concurrent agent executions.

- **LiteLLM's built-in callbacks**: LiteLLM has a callback system that Opik may already support. Evaluate whether using `litellm.callbacks` or `litellm.success_callback` is simpler than manual wrapping. If so, prefer that approach -- less code to maintain.

## Open Questions

- **LiteLLM + Opik native integration**: Does Opik already provide a LiteLLM callback? If so, the implementation could be as simple as registering a callback when `OPIK_API_KEY` is present. This should be investigated before writing custom wrapping code.

- **Trace context propagation**: How should trace context flow from an agent's top-level execution through the LLM generator, tool executor, and into individual LiteLLM calls? Need to evaluate Opik's Python SDK for context propagation patterns (e.g., context managers, decorators, or explicit trace passing).

- **Opik free tier limits**: What are the free tier limits on traces, spans, and data retention? This determines whether the integration is viable for active development without hitting walls.

- **Project/workspace naming**: Should OmniForge auto-create an Opik project named after the agent or skill? Or use a single default project? Need to decide the default behavior.

## Out of Scope (For Now)

- **Prompt redaction/masking** -- No PII or secret filtering. Developers are responsible for knowing that prompts go to Opik cloud.
- **Custom metrics/evaluation** -- Opik supports custom metrics and eval. Not in this phase.
- **Platform integration** -- No UI in the OmniForge platform for viewing traces. Developers go to Opik dashboard directly.
- **Self-hosted Opik** -- Only cloud free tier for now. Self-hosted can be added later via `OPIK_BASE_URL` config.
- **Non-LLM tool tracing** -- Only LLM calls are traced. Bash tool execution, file operations, etc. are not traced.
- **Alerting** -- No alerts on errors or cost thresholds. Pure observability.

## Evolution Notes

### 2026-02-02
Initial specification created. Key architectural decision pending: whether to use LiteLLM's native callback system or manual span creation. This should be resolved during the technical planning phase by investigating Opik's LiteLLM integration documentation.
