# Opik LLM Tracing Guide

OmniForge integrates with [Opik](https://www.comet.com/site/products/opik/) for LLM call tracing and observability. This is useful for debugging agent behavior during development.

## Quick Setup (2 minutes)

### 1. Install Opik

```bash
pip install "omniforge[tracing]"
```

Or if you already have omniforge installed:

```bash
pip install opik
```

### 2. Get Opik API Key

- Sign up for free at [https://www.comet.com/signup](https://www.comet.com/signup)
- Navigate to Opik (from the products menu)
- Create a new workspace or use the default one
- Get your API key from Settings → API Keys

### 3. Configure Environment Variables

Add to your `.env` file:

```bash
OPIK_API_KEY=your-api-key-here
OPIK_WORKSPACE=default  # or your workspace name
```

### 4. Run Your Agent

No code changes needed! Just run your agent as usual:

```bash
python your_agent.py
```

You'll see a confirmation message:

```
✓ Opik tracing enabled (workspace: default)
```

### 5. View Traces

Open the Opik dashboard at [https://www.comet.com/](https://www.comet.com/) to view your traces.

## What Gets Traced

Every LLM call made through OmniForge is automatically traced with:

- **Model name** (including fallback attempts)
- **Full prompt** (input messages)
- **Full response** (output text)
- **Token counts** (input/output)
- **Latency** (milliseconds)
- **Errors** (if any)
- **Fallback chain** (if fallbacks were triggered)

## Switching to Self-Hosted Opik (Later)

To use a self-hosted Opik instance instead of the cloud:

```bash
OPIK_BASE_URL=https://your-opik-instance.com
OPIK_API_KEY=your-self-hosted-key
OPIK_WORKSPACE=my-workspace
```

## Disabling Tracing

Simply remove or unset the `OPIK_API_KEY` environment variable:

```bash
unset OPIK_API_KEY
```

Or remove it from your `.env` file. The agent will run normally without any overhead.

## Troubleshooting

### "Opik not installed" message

Install opik: `pip install opik`

### No traces appearing in dashboard

1. Check that `OPIK_API_KEY` is set correctly
2. Verify your API key is valid in Opik settings
3. Check that you're looking at the correct workspace
4. Ensure your LLM calls are actually executing (check for errors)

### Tracing affecting performance

Tracing is fire-and-forget and should not affect agent execution. If Opik's API is slow or down, it will not block your agent - traces are sent asynchronously.

## Example Output

When tracing is enabled, you'll see LLM calls in the Opik dashboard with full context:

```
Trace: agent_execution_12345
├── LLM Call 1: gpt-4o-mini (200ms, 150 tokens)
│   Input: "What is the capital of France?"
│   Output: "The capital of France is Paris."
├── LLM Call 2: claude-sonnet-4 (350ms, 500 tokens)
│   Input: "Explain photosynthesis..."
│   Output: "Photosynthesis is the process..."
```

## Privacy Note

**All prompts and responses are sent to Opik's servers.** Make sure you understand the implications:

- ✅ Safe for development and debugging
- ⚠️ May contain user data or sensitive information
- ⚠️ Consider using self-hosted Opik for production if handling PII

For production use with sensitive data, use a self-hosted Opik instance.
