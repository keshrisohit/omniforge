# Migrating to Autonomous Skill Execution

## Overview

Autonomous skill execution brings powerful new capabilities to OmniForge skills, enabling them to iteratively solve complex problems through a ReAct (Reasoning + Acting) loop. This guide will help you migrate your existing skills to take advantage of these new features.

### What is Autonomous Skill Execution?

Autonomous execution allows skills to:
- **Iteratively reason and act** - Break down complex tasks into steps
- **Recover from errors** - Automatically retry failed operations
- **Load context progressively** - Fetch only needed information when needed
- **Execute dynamically** - Make decisions based on real-time results

### Key Benefits

- **Error Recovery**: Automatic retries and alternative approaches for failed tool calls
- **Progressive Loading**: Inject dynamic context at execution time to avoid wasted iterations
- **Flexible Execution**: Skills can adapt their approach based on intermediate results
- **Cost Optimization**: Choose appropriate LLM models (haiku/sonnet/opus) for the task complexity
- **Backward Compatible**: Existing skills work unchanged with autonomous execution

### Backward Compatibility Guarantees

All existing skills continue to work without modification. Autonomous execution is now the default mode, but skills can opt out by setting `execution-mode: simple` in their metadata.

## Quick Start

For most skills, no changes are needed! Autonomous execution is now the default and your existing skill will work as-is.

### Minimal Changes to Enable Features

To take advantage of advanced features, add optional configuration to your skill's frontmatter:

```yaml
---
name: my-skill
execution-mode: autonomous  # Optional, this is the default
max-iterations: 15          # Optional, customize iteration limit
model: sonnet               # Optional, choose LLM model
---
```

### Default Behavior

- **Execution mode**: `autonomous` (ReAct loop with error recovery)
- **Max iterations**: 15 (configurable)
- **Max retries per tool**: 3 (configurable)
- **Model**: `sonnet` (balanced cost/capability)

## Step-by-Step Migration

Follow these steps to migrate your skill and take full advantage of autonomous execution features.

### Step 1: Verify Existing Skill Works

Before making any changes, test your skill with autonomous execution:

```bash
# Test your skill with the new autonomous executor
omniforge skill run my-skill "test task"
```

**What to check:**
- Does the skill complete successfully?
- Are there any error messages or warnings?
- Does the output match expectations?

**Note any issues** - These will guide your optimization in later steps.

### Step 2: Add Autonomous Configuration (Optional)

If your skill needs customization, add metadata fields to the frontmatter:

```yaml
---
name: my-skill
description: Brief description of what the skill does
allowed-tools:
  - read
  - write
  - bash

# Autonomous execution settings (all optional)
execution-mode: autonomous  # Default, can be omitted
max-iterations: 15          # Adjust based on task complexity
max-retries-per-tool: 3     # Retries for failed tool calls
model: sonnet               # haiku | sonnet | opus
---
```

**When to customize:**
- **max-iterations**: Increase for complex multi-step tasks, decrease for simple tasks
- **max-retries-per-tool**: Increase for flaky operations (network calls, etc.)
- **model**: Use `haiku` for simple tasks, `opus` for complex reasoning

### Step 3: Optimize for Progressive Context Loading

Keep your `SKILL.md` file concise (under 500 lines) by moving detailed documentation to supporting files.

#### Before (Large, Monolithic SKILL.md)

```yaml
---
name: api-documenter
description: Documents REST APIs
allowed-tools: [read, write, bash]
---

# API Documenter

You are an API documentation specialist...

## OpenAPI Specification Reference

[200+ lines of OpenAPI spec details...]

## Example API Responses

[100+ lines of example responses...]

## Output Templates

[100+ lines of templates...]

## Common Patterns

[100+ lines of patterns...]
```

#### After (Optimized with Supporting Files)

**Directory Structure:**
```
api-documenter/
├── SKILL.md          # Core instructions (<500 lines)
├── reference.md      # OpenAPI spec details
├── examples.md       # Example responses
├── templates/        # Output templates
│   ├── endpoint.md
│   └── schema.md
└── patterns.md       # Common patterns
```

**SKILL.md (Optimized):**
```yaml
---
name: api-documenter
description: Documents REST APIs
allowed-tools: [read, write, bash]
---

# API Documenter

You are an API documentation specialist. Your task is to create comprehensive,
clear documentation for REST APIs.

## Quick Reference

1. Read the API specification (OpenAPI/Swagger)
2. Identify all endpoints, methods, and parameters
3. Document each endpoint with examples
4. Generate markdown documentation

See `reference.md` for complete OpenAPI specification details.
See `examples.md` for documentation examples and patterns.
See `templates/` for output templates.

## Process

1. **Analyze**: Read API spec and understand structure
2. **Document**: Create docs for each endpoint
3. **Validate**: Check completeness and accuracy
4. **Output**: Generate final documentation

## When You Need More Information

- For OpenAPI spec details: Read `reference.md`
- For example output formats: Read `examples.md`
- For specific templates: Read files in `templates/`
```

**Benefits of this approach:**
- Initial prompt stays under 500 lines
- Skill can load additional context only when needed
- Faster initial execution
- More maintainable documentation

### Step 4: Add Dynamic Context Injection (Optional)

For skills that need current state information (like PR reviews, git status, etc.), use dynamic command injection to populate context before execution.

#### Before (Manual Context Fetching)

```yaml
---
name: pr-reviewer
allowed-tools: [bash]
---

# PR Reviewer

Review the current pull request.

## Process

1. First, run `gh pr diff` to get the PR changes
2. Then run `gh pr checks` to get the CI status
3. Analyze the changes and checks
4. Provide review feedback
```

**Problem**: The skill wastes 2-3 iterations just fetching context that could be provided upfront.

#### After (Dynamic Context Injection)

```yaml
---
name: pr-reviewer
allowed-tools: [Bash(gh:*)]
---

# PR Reviewer

Review the current pull request based on the data below.

## Current PR Data

### Changes
!`gh pr diff`

### CI Status
!`gh pr checks`

## Your Task

Analyze the above changes and CI status, then provide:

1. **Code Quality**: Issues with the changes
2. **CI Status**: Summary of check results
3. **Recommendations**: Suggested improvements
4. **Approval**: Should this PR be approved?
```

**Benefits:**
- Context is injected before execution starts (iteration 0)
- Skill can immediately begin analysis
- Saves 2-3 iterations on context fetching
- More reliable (no risk of forgetting to fetch context)

**Dynamic Injection Syntax:**
```yaml
!`command`  # Execute command and inject output
```

**Supported commands:**
- Any command allowed by `allowed-tools` configuration
- Commands with tool restrictions: `Bash(gh:*)` allows only `gh` commands
- Multiple injections in sequence

### Step 5: Configure Model Selection (Optional)

Choose the appropriate LLM model based on your skill's complexity:

```yaml
---
name: simple-file-organizer
model: haiku  # Fast and cheap for simple tasks
---
```

```yaml
---
name: code-analyzer
model: sonnet  # Balanced for general tasks (default)
---
```

```yaml
---
name: architecture-reviewer
model: opus  # Powerful for complex reasoning
---
```

See the [Model Selection Guide](#model-selection-reference) below for detailed recommendations.

## Feature Reference

### Execution Modes

| Mode | Description | Behavior | When to Use |
|------|-------------|----------|-------------|
| `autonomous` | Iterative ReAct loop | Agent reasons, acts, observes in loop | Default, most skills |
| `simple` | Single-pass execution | Prompt sent once, response returned | Simple, deterministic tasks |

**Example: Forcing simple mode**
```yaml
---
name: template-expander
execution-mode: simple  # No iteration needed
---
```

### Configuration Options

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `execution-mode` | string | `autonomous` | Execution mode (autonomous or simple) |
| `max-iterations` | integer | 15 | Maximum ReAct loop iterations |
| `max-retries-per-tool` | integer | 3 | Max retries per failed tool call |
| `model` | string | `sonnet` | LLM model (haiku/sonnet/opus) |
| `allowed-tools` | list | all | Tools the skill can use |

**Example: Complete configuration**
```yaml
---
name: data-processor
execution-mode: autonomous
max-iterations: 20
max-retries-per-tool: 5
model: sonnet
allowed-tools:
  - read
  - write
  - bash
  - glob
---
```

### Variable Substitution

Use variables in your skill instructions for dynamic content:

| Variable | Description | Example |
|----------|-------------|---------|
| `$ARGUMENTS` | User's invocation arguments | `$ARGUMENTS` → `"analyze Q1 sales"` |
| `${SKILL_DIR}` | Absolute path to skill directory | `${SKILL_DIR}/templates/` |
| `${SESSION_ID}` | Unique session identifier | `session-abc123` |

**Example usage:**
```yaml
---
name: report-generator
---

Generate a report based on: $ARGUMENTS

Use the template at: ${SKILL_DIR}/templates/report.md
Save output to: /tmp/report-${SESSION_ID}.md
```

### Dynamic Injection Syntax

Execute commands at skill load time and inject their output:

**Syntax:**
```yaml
!`command`  # Execute and inject output
```

**Examples:**

1. **Inject Git Status:**
```yaml
## Current Repository State
!`git status --short`
```

2. **Inject PR Information:**
```yaml
## Pull Request Details
!`gh pr view --json title,body,number`
```

3. **Inject File Contents:**
```yaml
## Configuration
!`cat config.json`
```

**Important Notes:**
- Commands must be allowed by `allowed-tools` configuration
- Commands execute in the skill directory
- Output is injected as-is (preserve formatting)
- Failed commands show error message in output

### Model Selection Reference

Choose the right model for your skill's complexity:

| Model | Speed | Cost | Capability | Best For |
|-------|-------|------|------------|----------|
| `haiku` | Fastest | Lowest | Basic | Simple file ops, pattern matching |
| `sonnet` | Medium | Medium | Strong | General purpose, most skills |
| `opus` | Slower | Highest | Strongest | Complex reasoning, code analysis |

**Haiku Examples:**
- File organization and renaming
- Simple text search and replace
- Basic data formatting
- Template expansion

**Sonnet Examples:**
- Code reviews
- Documentation generation
- Data analysis
- Test writing

**Opus Examples:**
- Architecture design
- Complex refactoring
- Multi-file code analysis
- Strategic planning

## Common Migration Patterns

### Pattern 1: Simple Skill (No Changes Needed)

Most simple skills work unchanged with autonomous execution.

**Before and After - Identical:**
```yaml
---
name: file-counter
description: Counts files in a directory
allowed-tools: [bash, glob]
---

# File Counter

Count the number of files matching the given pattern.

Use `glob` to find files matching the pattern.
Count and report the total.
```

**No changes needed** - This skill works perfectly with autonomous execution.

### Pattern 2: Large Skill (Split Content)

For skills with extensive documentation, split into multiple files.

**Before (Won't work - too long):**
```yaml
---
name: api-tester
---

# API Tester

[5000+ lines of API testing documentation, examples, schemas, etc.]
```

**After (Split into files):**
```
api-tester/
├── SKILL.md          # Core instructions
├── reference.md      # API reference
├── examples.md       # Test examples
└── schemas/          # Request/response schemas
    ├── auth.json
    └── users.json
```

**SKILL.md:**
```yaml
---
name: api-tester
---

# API Tester

Quick reference for testing REST APIs.

## Process
1. Read API specification
2. Generate test cases
3. Execute tests
4. Report results

## Resources
- See `reference.md` for complete API documentation
- See `examples.md` for test case examples
- See `schemas/` for request/response schemas
```

### Pattern 3: Context-Heavy Skill (Use Injection)

Skills that need current state should inject context upfront.

**Before (Wastes iterations):**
```yaml
---
name: deployment-checker
---

# Deployment Checker

Check the status of the current deployment.

## Steps
1. Run `kubectl get pods` to see pod status
2. Run `kubectl get services` to see services
3. Analyze the deployment state
4. Report any issues
```

**After (Context injected):**
```yaml
---
name: deployment-checker
allowed-tools: [Bash(kubectl:*)]
---

# Deployment Checker

Check the deployment status based on the current state below.

## Current State

### Pods
!`kubectl get pods -o wide`

### Services
!`kubectl get services`

### Recent Events
!`kubectl get events --sort-by='.lastTimestamp' | tail -20`

## Your Task

Analyze the above Kubernetes state and report:
1. Pod health status
2. Service availability
3. Recent errors or warnings
4. Recommended actions
```

**Benefits:**
- All context loaded before iteration 1
- Skill starts analysis immediately
- More reliable and faster execution

### Pattern 4: Error-Prone Operations (Increase Retries)

For skills with flaky operations, increase retry limits.

**Before (Default retries):**
```yaml
---
name: api-integration
---
```

**After (Increased retries):**
```yaml
---
name: api-integration
max-retries-per-tool: 5  # Network calls may fail
---
```

**Use cases:**
- Network API calls
- Database operations
- File system operations on slow storage
- External service integrations

### Pattern 5: Simple Deterministic Tasks (Use Simple Mode)

For straightforward tasks with no iteration needed, use simple mode.

**Example:**
```yaml
---
name: template-renderer
execution-mode: simple  # No ReAct loop needed
---

# Template Renderer

Replace variables in the template with provided values.

Template: $ARGUMENTS

Replace all `{{variable}}` placeholders with actual values.
```

**When to use simple mode:**
- Template rendering
- Simple text transformations
- Deterministic calculations
- No decision-making required

## Troubleshooting

### Skill Takes Too Many Iterations

**Symptoms:**
- Hits max-iterations limit
- Loops without making progress
- Repeats same actions

**Solutions:**

1. **Reduce scope** - Break complex skills into smaller, focused skills
2. **Add specific instructions** - Be more explicit about the approach
3. **Use progressive loading** - Inject context instead of fetching
4. **Increase max-iterations** - If legitimately complex task

**Example fix:**
```yaml
# Before: Vague instructions
---
name: code-analyzer
---
Analyze the codebase and find issues.

# After: Specific instructions
---
name: code-analyzer
max-iterations: 20
---
Analyze Python files for:
1. Security vulnerabilities (SQL injection, XSS)
2. Performance issues (N+1 queries, inefficient loops)
3. Code style violations (PEP 8)

Use glob to find .py files, read each file, analyze, report findings.
```

### Tool Failures Not Recovering

**Symptoms:**
- Same tool fails repeatedly
- No alternative approach attempted
- Skill exits with error

**Solutions:**

1. **Check allowed-tools** - Ensure needed tools are allowed
2. **Improve error messages** - Make them actionable
3. **Add alternative approaches** - Suggest fallback methods

**Example fix:**
```yaml
# Before: No alternatives
---
name: dependency-checker
allowed-tools: [bash]
---
Check for outdated dependencies using pip list --outdated

# After: With alternatives
---
name: dependency-checker
allowed-tools: [bash, read]
max-retries-per-tool: 5
---
Check for outdated dependencies:

1. Try: pip list --outdated
2. If that fails, try: pip freeze > /tmp/deps.txt and analyze manually
3. If pip not available, read requirements.txt and check versions online
```

### Token Limit Exceeded

**Symptoms:**
- "Context length exceeded" error
- Skill fails with large files
- Progress lost due to context limits

**Solutions:**

1. **Keep SKILL.md under 500 lines** - Move docs to supporting files
2. **Use progressive loading** - Load only needed information
3. **Choose smaller model** - Use `haiku` for simple tasks
4. **Process in chunks** - Break large files into smaller pieces

**Example fix:**
```yaml
# Before: Large prompt
---
name: log-analyzer
---
[1000 lines of log format documentation and examples]

# After: Optimized
---
name: log-analyzer
model: haiku  # Simple pattern matching
---
Analyze logs for errors and warnings.
See reference.md for log format details.

Process logs in chunks of 1000 lines to avoid token limits.
```

### Dynamic Injection Failing

**Symptoms:**
- `!` command output shows errors
- Missing context in skill prompt
- Injection commands not executing

**Solutions:**

1. **Verify allowed-tools** - Injection commands must be allowed
2. **Check command syntax** - Ensure command is valid
3. **Test command manually** - Run in terminal first
4. **Use absolute paths** - Avoid relative path issues

**Example fix:**
```yaml
# Before: Command not allowed
---
name: git-analyzer
allowed-tools: [read, write]
---
!`git log --oneline`  # FAILS - bash not allowed

# After: Tool allowed
---
name: git-analyzer
allowed-tools: [bash, read, write]
---
!`git log --oneline -20`  # SUCCESS
```

### Skill Runs Too Slowly

**Symptoms:**
- Takes many iterations to complete
- Unnecessary tool calls
- Expensive model for simple task

**Solutions:**

1. **Use haiku for simple tasks** - Much faster than sonnet/opus
2. **Inject context upfront** - Avoid fetching in loop
3. **Simplify instructions** - Remove unnecessary complexity
4. **Reduce max-iterations** - Force efficiency

**Example fix:**
```yaml
# Before: Slow execution
---
name: file-organizer
model: opus  # Overkill for simple task
---
Organize files by extension.

# After: Fast execution
---
name: file-organizer
model: haiku  # Simple pattern matching
max-iterations: 5  # Should be quick
---
Move files to folders based on extension:
- .py → python/
- .js → javascript/
- .md → docs/
```

## FAQ

### Will my existing skills break?

**No.** All existing skills work unchanged with autonomous execution. The system is fully backward compatible.

### How do I opt out of autonomous execution?

Add `execution-mode: simple` to your skill metadata:

```yaml
---
name: my-skill
execution-mode: simple
---
```

### What's the maximum SKILL.md size?

**500 lines** is the recommended limit. Larger files may cause token limit issues. Move additional content to supporting files that can be loaded progressively.

### Can I use multiple models in one skill?

No, each skill uses one model specified in its metadata. However, you can create multiple skills with different models for different complexity levels.

### Do dynamic injections cost iterations?

No, dynamic injections (`!`command``) execute before the ReAct loop starts (iteration 0). They're "free" in terms of iteration count.

### Can I inject files instead of commands?

Yes, use a command that outputs the file:

```yaml
!`cat ${SKILL_DIR}/reference.md`
```

### What happens if injection command fails?

The error message is injected into the prompt instead of the output. The skill execution continues, allowing the agent to handle the missing context gracefully.

### Can I change the model at runtime?

No, the model is set in the skill metadata and cannot be changed during execution. Create separate skills if you need different models for different scenarios.

### How many supporting files can I have?

No hard limit, but keep it reasonable (typically 5-10 files). Each file the skill reads costs tokens and iterations.

### Can skills call other skills?

Not directly in autonomous mode. Skills execute independently. Use the orchestration layer for multi-skill workflows.

### Is there a way to debug skill execution?

Yes, autonomous execution provides detailed logs showing:
- Each iteration's reasoning
- Tool calls and results
- Error recovery attempts
- Final outcome

Enable debug logging in your OmniForge configuration.

### Can I use custom tools?

Yes, but they must be registered in the OmniForge tool registry and specified in `allowed-tools`. See the [Custom Tools Guide](../tools/custom-tools.md) for details.

## Next Steps

1. **Test your migrated skill** - Run with various inputs
2. **Monitor performance** - Check iteration counts and execution time
3. **Optimize as needed** - Adjust configuration based on results
4. **Share feedback** - Help improve the autonomous execution system

## Additional Resources

- [Best Practices for Autonomous Skills](skill-best-practices.md)
- [Autonomous Execution Architecture](../architecture/autonomous-execution.md)
- [Tool Reference](../tools/tool-reference.md)
- [Troubleshooting Guide](../troubleshooting.md)

---

**Need help?** Open an issue on GitHub or reach out in the community forum.
