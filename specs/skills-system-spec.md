# Agent Skills System (Claude Code Style)

**Created**: 2026-01-13
**Last Updated**: 2026-01-13
**Version**: 1.0
**Status**: Draft

---

## 🔑 Critical Design Decision (Based on Claude Code Research)

**Skills are NOT in the system prompt.** After researching Claude Code's actual implementation, we discovered that skills are presented through **progressive disclosure at the TOOL level**:

- ✅ Skills list embedded in the `SkillTool` description (not system prompt)
- ✅ Format: `"skill-name": description` in `<available_skills>` XML section
- ✅ Full SKILL.md content returned ONLY when tool is invoked
- ✅ Zero context cost until skill is actually used

**Sources:**
- [Claude Code System Prompts Repository](https://github.com/Piebald-AI/claude-code-system-prompts) - v2.1.6 (Jan 2026)
- [Inside Claude Code Skills](https://mikhail.io/2025/10/claude-code-skills/) - Technical deep dive
- [Claude Agent Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/) - First principles analysis

This approach is fundamentally different from embedding instructions in the system prompt and provides true progressive disclosure.

---

## Overview

The Agent Skills System brings Claude Code's powerful skills architecture to OmniForge, enabling agents to discover and execute specialized capabilities defined in simple Markdown files. Skills are directories containing a SKILL.md file with instructions, optional reference documentation, and executable scripts. Unlike OmniForge's existing internal functions (Python functions invoked via FunctionTool), Skills are declarative instruction sets that augment an agent's behavior through natural language guidance, tool restrictions, and bash script execution - all while maintaining a minimal context footprint through progressive disclosure.

**Key Architecture:**
- **Tools** (BashTool, ReadTool, WriteTool, etc.) = Core actions/capabilities
- **FunctionTool** = Invokes internal Python functions (renamed from existing SkillTool)
- **SkillTool** = Loads agent skills from SKILL.md files (NEW - this spec)
- **Skills USE Tools** to accomplish complex tasks

This system enables a new paradigm: **skills as knowledge**, where domain expertise, workflows, and operational procedures can be captured in Markdown files that agents automatically discover and apply based on task context. A "deploy-to-kubernetes" skill doesn't need to be a coded function - it can be a SKILL.md with deployment instructions, allowed tools, and helper scripts that the agent loads and follows when deployment tasks arise.

---

## Alignment with Product Vision

This specification advances OmniForge's core vision in several ways:

- **Agents Build Agents**: Skills can be authored by agents themselves, enabling agents to create reusable capabilities for other agents. A platform agent could generate a SKILL.md based on user requirements, creating new agent capabilities without code.

- **No-Code Agent Creation**: Markdown skills are the ultimate no-code capability definition. Business users can define complex workflows, procedures, and specialized behaviors in plain Markdown that agents automatically apply.

- **Enterprise-Ready from Day One**: The storage hierarchy (Enterprise > Personal > Project > Plugin) enables centralized governance. Enterprise admins can deploy approved skills across all tenants while teams customize at project level.

- **Simplicity Over Flexibility**: Skills are just Markdown files in directories. No SDK knowledge required. The format is immediately understandable and editable by anyone.

- **Dual Deployment Support**: Skills work identically in the open-source SDK (local directories) and premium platform (managed storage with UI), enabling seamless migration between deployment modes.

---

## User Personas

### Primary Users

#### SDK Developer (Skill Author)

A developer using the Python SDK who wants to give their agents specialized capabilities without writing Python code.

**Context**: Working on complex projects where agents need domain-specific knowledge, tool restrictions, or multi-step workflows that are easier to express in natural language than code.

**Goals**:
- Define agent capabilities in version-controlled Markdown files
- Restrict agent tool usage for specific tasks (e.g., "only use filesystem and bash for this skill")
- Include reference documentation that agents can consult without bloating initial context
- Create reusable skills that work across multiple agents and projects

**Pain Points**:
- Writing Python skills for every new capability is time-consuming
- Hard to express complex procedural knowledge in code
- Reference documentation for skills is often separate from skill definitions
- Difficult to restrict agent behavior to specific tools for specialized tasks

**Key Quote**: "I want to define a code review skill by writing instructions in Markdown, not by implementing a CodeReviewSkill class with a dozen methods."

---

#### Platform Developer (Skill Library Curator)

A developer creating reusable skill libraries for distribution across teams or the OmniForge community.

**Context**: Building collections of skills that multiple teams or organizations will use, requiring consistent structure, clear documentation, and proper isolation.

**Goals**:
- Create skill packages that can be installed from registries (npm-style for skills)
- Ensure skills are isolated and don't leak context inappropriately
- Version skills and manage dependencies between them
- Test skills work correctly across different agent configurations

**Pain Points**:
- No standard way to package and distribute agent capabilities
- Skills tightly coupled to specific agent implementations
- Difficult to maintain compatibility across OmniForge versions
- No tooling for testing skill behavior

**Key Quote**: "I want to publish a 'database-operations' skill pack that any OmniForge agent can install and immediately use for database tasks."

---

#### Enterprise Administrator (Skill Governance)

A technical administrator responsible for controlling what capabilities agents have access to within their organization.

**Context**: Managing agent deployments across multiple teams, ensuring compliance with policies, and maintaining security boundaries around agent capabilities.

**Goals**:
- Deploy organization-approved skills to all agents centrally
- Override or disable project-level skills that violate policies
- Audit which skills agents are using and when
- Restrict skill creation to authorized personnel

**Pain Points**:
- No visibility into what capabilities agents have across teams
- Teams deploying unapproved or risky skills
- Difficult to enforce consistent agent behavior across organization
- No way to disable problematic skills organization-wide

**Key Quote**: "When a team creates a skill that uses external APIs, I need to know about it, approve it, and be able to disable it instantly if there's a security concern."

---

#### End User (Skill Beneficiary)

A business user interacting with agents through the chatbot interface who benefits from skills without knowing they exist.

**Context**: Using agents to accomplish tasks, unaware of the underlying skill system but experiencing better, more specialized agent behavior.

**Goals**:
- Agents that "just work" for their domain and use cases
- Consistent agent behavior for repeated tasks
- Specialized capabilities without requesting IT involvement

**Pain Points**:
- Generic agents that don't understand their specific workflows
- Having to explain domain context repeatedly
- Agents that use inappropriate tools or approaches for their domain

**Key Quote**: "I don't care how it works, I just want the agent to know how to properly format our legal documents every time, not just when I remember to explain it."

---

### Secondary Users

#### QA/Testing Engineer

Responsible for validating that skills produce expected agent behavior.

**Goals**: Test skill discovery, verify tool restrictions are enforced, ensure progressive disclosure works correctly.

---

#### External Contributor (Open Source)

Community member contributing skills to OmniForge's skill library.

**Goals**: Submit skills following documented standards, understand review criteria, receive feedback.

---

## Problem Statement

### The Capability Definition Gap

Currently, giving an OmniForge agent specialized capabilities requires one of two approaches:

1. **Python Functions (Internal)**: Write Python functions registered with FunctionRegistry (via FunctionTool). This works well for programmatic operations but is overkill for procedural knowledge, workflow guidance, or domain-specific instructions.

2. **System Prompts**: Embed instructions in the agent's system prompt. This works for simple guidance but doesn't scale - prompts become bloated, instructions conflict, and there's no way to restrict tools or include reference documentation.

Neither approach addresses the need for **modular, discoverable, context-efficient capability definitions** that agents can apply automatically based on task context.

### The Context Window Limitation

Agents have limited context windows. Loading comprehensive documentation for every possible skill an agent might use is wasteful and often impossible. Current approaches either:
- Front-load all instructions (bloating context)
- Require explicit user requests for capabilities (poor UX)
- Hard-code capabilities in agent logic (inflexible)

What's needed is **progressive disclosure**: load minimal skill metadata for discovery, full instructions only when activated, and reference docs on-demand during execution.

### The Tool Restriction Challenge

Agents often need to be restricted to specific tools for specific tasks. A "file-organization" skill should only use filesystem tools, not make API calls. A "database-migration" skill should have database access but not modify files directly.

Current OmniForge has no mechanism for skill-specific tool restrictions. Either agents have access to all their tools, or complex permission logic must be implemented per-agent.

### The Script Execution Dilemma

Complex skills often need helper scripts - bash scripts for deployment, Python scripts for data transformation, shell commands for environment setup. Loading script contents into agent context wastes tokens and is error-prone. The agent should execute scripts as black boxes, not read and interpret them.

---

## Core Design: The Skill Structure

### Skill Directory Layout

```
my-skill/
  SKILL.md              # Required: Skill definition and instructions
  docs/                 # Optional: Reference documentation
    architecture.md
    api-reference.md
    troubleshooting.md
  scripts/              # Optional: Executable scripts
    deploy.sh
    validate.py
    setup.sh
  examples/             # Optional: Example files
    config-template.yaml
    sample-input.json
```

### SKILL.md Format

```markdown
---
name: kubernetes-deployment
description: Deploy applications to Kubernetes clusters with proper health checks and rollback capabilities
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
model: claude-sonnet-4
context: fork
hooks:
  pre: scripts/validate-cluster.sh
  post: scripts/verify-deployment.sh
---

# Kubernetes Deployment Skill

You are an expert Kubernetes deployment specialist. When users request deployments, follow these procedures exactly.

## Pre-Deployment Checklist

Before any deployment:
1. Verify cluster connectivity using `kubectl cluster-info`
2. Check namespace exists or create it
3. Validate manifest files in the deployment directory

## Deployment Procedure

[Detailed instructions for the agent to follow...]

## Rollback Procedure

If deployment fails:
1. Check pod status: `kubectl get pods -n {namespace}`
2. Review logs: `kubectl logs -n {namespace} {pod-name}`
3. Execute rollback: `kubectl rollout undo deployment/{name} -n {namespace}`

## Reference

- See `docs/architecture.md` for cluster architecture details
- See `docs/troubleshooting.md` for common issues
```

### YAML Frontmatter Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique skill identifier (kebab-case) |
| `description` | string | Yes | One-line description for discovery matching |
| `allowed-tools` | string[] | No | Tool allowlist (if omitted, all tools available) |
| `model` | string | No | Preferred model for this skill (default: agent's model) |
| `context` | enum | No | `inherit` (default) or `fork` for isolated sub-agent |
| `agent` | string | No | Specific agent type to spawn (requires `context: fork`) |
| `hooks.pre` | string | No | Script to run before skill execution |
| `hooks.post` | string | No | Script to run after skill execution |
| `priority` | number | No | Override priority (higher wins in conflicts) |
| `tags` | string[] | No | Categorization tags for organization |

---

## Progressive Disclosure Architecture

### The Three-Stage Loading Model

Progressive disclosure ensures minimal context consumption while maintaining full capability. Information loads in stages:

**Stage 1: Discovery (Always Loaded)**
```
For each skill in scope:
  - name
  - description (one line)
  - tags
```

This minimal metadata enables the agent to identify relevant skills based on task description matching. Loaded at agent initialization. Typical size: ~50 bytes per skill.

**Stage 2: Activation (On-Demand)**
```
When skill is activated:
  - Full SKILL.md content (instructions)
  - Tool restrictions applied
  - Hooks registered
```

Loaded when the agent determines a skill is relevant to the current task. Full instructions guide agent behavior. Typical size: 1-10KB per skill.

**Stage 3: Reference (On-Demand)**
```
During skill execution:
  - Reference docs loaded via Read tool
  - Scripts executed via Bash (content NOT loaded)
  - Examples accessed as needed
```

Reference documentation is never pre-loaded. The agent uses the Read tool to access docs when needed during execution. Scripts are executed via Bash without loading contents into context.

### Discovery Matching Algorithm

The agent determines skill relevance through semantic matching:

```
For each task:
  1. Extract task intent and domain signals
  2. For each skill in scope:
     a. Compare task description against skill.description
     b. Check for tag matches
     c. Check for explicit skill invocation (e.g., "/deploy")
  3. Rank skills by relevance score
  4. Activate top-matching skill(s) above threshold
```

The matching is model-assisted - the agent's LLM determines relevance based on the skill descriptions it has in context from Stage 1.

### Script Execution Model

Scripts are executed, never loaded:

```
Agent needs to run deployment:
  1. Agent decides to run scripts/deploy.sh
  2. Agent calls Bash tool: `bash scripts/deploy.sh --env production`
  3. Script executes externally
  4. Output returned to agent
  5. Script contents NEVER enter agent context
```

This is critical for context efficiency. A 500-line deployment script consumes zero context tokens - only the execution command and output are in context.

---

## Storage Hierarchy and Override Behavior

### Four Storage Layers

Skills can be defined at four levels, listed from highest to lowest priority:

1. **Enterprise** (`~/.omniforge/enterprise/skills/`)
   - Organization-wide skills deployed by administrators
   - Highest priority - can override any other level
   - Managed through platform admin interface or CLI
   - Synced across all users in the organization

2. **Personal** (`~/.omniforge/skills/`)
   - User-specific skills for personal workflows
   - Override project skills but not enterprise
   - Portable across projects
   - Private to the user

3. **Project** (`.omniforge/skills/` in project root)
   - Project-specific skills checked into version control
   - Shared with all project contributors
   - Override plugin skills only

4. **Plugin** (installed skill packages)
   - Skills from installed packages/registries
   - Lowest priority
   - Community-contributed or vendor-provided
   - Installed via `omniforge skill install <package>`

### Override Rules

When multiple skills have the same name across layers:

```
Resolution order (highest priority wins):
  Enterprise > Personal > Project > Plugin

Example:
  Plugin has: deploy-to-kubernetes
  Project has: deploy-to-kubernetes (customized for project)
  Enterprise has: deploy-to-kubernetes (with compliance requirements)

  -> Enterprise version is used, others ignored
```

Override is **complete replacement**, not merge. The winning skill entirely replaces lower-priority versions.

### Skill Scoping

Not all skills are available to all agents:

```yaml
# In SKILL.md frontmatter
scope:
  agents: ["cot-agent", "research-agent"]  # Only these agent types
  tenants: ["tenant-123"]                   # Only these tenants
  environments: ["production"]              # Only in production
```

Scoping enables fine-grained control over skill availability.

---

## Agent Integration

### Skill Discovery Flow

```
Agent Initialization:
  1. Scan all storage layers for SKILL.md files
  2. Parse frontmatter from each (Stage 1 only)
  3. Build skill index: {name -> {description, path, priority}}
  4. Add skill descriptions to agent's tool/capability list

Task Processing:
  1. Receive task
  2. Agent evaluates task against skill descriptions
  3. If match found:
     a. Load full SKILL.md content (Stage 2)
     b. Apply tool restrictions
     c. Execute pre-hook if defined
     d. Agent follows skill instructions
     e. Execute post-hook if defined
  4. If no match: proceed with standard agent behavior
```

### Skill Tool Description (Progressive Disclosure at Tool Level)

**Critical Design Decision**: Skills are NOT embedded in the main system prompt. Instead, skills are presented through the **Skill Tool description**, following Claude Code's progressive disclosure pattern.

The `SkillTool` has this description (embedded in the tool definition):

```markdown
# Skill Tool

Execute specialized skills within the main conversation. When users request task execution or you identify a relevant capability, use this tool to invoke the corresponding skill.

## How to Invoke Skills

Use the tool with the skill name:
- `skill: "commit-message"` - basic invocation
- `skill: "code-review", args: "pr-123"` - with arguments

## Available Skills

The following skills are available:

<available_skills>
"commit-message-generator": Generates clear, conventional commit messages from git diffs. Use when writing commit messages or reviewing staged changes.

"pdf-processing": Extract text and tables from PDFs, fill form fields, merge documents. Use when working with PDF files, forms, or document processing.

"kubernetes-deploy": Deploy applications to Kubernetes following team standards. Use when deploying to K8s or managing cluster resources.
</available_skills>

## Important Requirements

- **IMMEDIATELY invoke** this tool as your first action when a skill is relevant
- **NEVER just announce** a skill without calling the tool
- **Only use skills** listed in <available_skills> above
- **Don't invoke** already-running skills
- **Don't use** this tool for built-in CLI commands

## What Happens When You Invoke

When you invoke a skill:
1. The skill loads with message: `The "{name}" skill is loading`
2. You receive the complete SKILL.md content
3. Follow the skill's instructions precisely
4. The skill may include tool restrictions (allowed-tools)

## Progressive Disclosure

Skills use progressive disclosure:

**Stage 1 (Tool Description)**: Only name + description visible (current view)
**Stage 2 (Tool Invocation)**: Full SKILL.md content returned in tool result
**Stage 3 (Skill Execution)**: Reference docs loaded on-demand, scripts executed

This keeps context lean while providing full capability when needed.
```

**Key Differences from System Prompt Approach:**

1. **Location**: Embedded in TOOL description, not system prompt
2. **Dynamic Loading**: Skills list (`<available_skills>`) is dynamically generated from available SKILL.md files
3. **Zero Initial Cost**: Skill descriptions are part of tool definition, not consuming conversation context
4. **True Progressive Disclosure**: Full SKILL.md only loaded when tool is invoked

**Tool Invocation Flow:**

```
1. Agent sees SkillTool in available tools
2. Tool description contains skill list
3. Agent identifies relevant skill from description
4. Agent invokes: {"skill_name": "code-review"}
5. Tool returns ToolResult with:
   - success: true
   - result: {
       "skill_name": "code-review",
       "base_path": "/path/to/.claude/skills/code-review",
       "content": "<full SKILL.md markdown content>"
     }
6. Agent now has full skill instructions in context
7. Agent follows skill instructions
```

**Navigation Within Skills (Explicit Instructions for All LLMs)**

Once the SKILL.md content is loaded, the agent needs **explicit instructions on how to navigate the skill**. These instructions must work across all LLMs (Claude, GPT-4, etc.), not rely on implicit intelligence.

**CRITICAL**: These navigation instructions are added to the **agent's system prompt** (not the tool description), ensuring all agents know how to use skills:

```markdown
## Skill Navigation Instructions (System Prompt Addition)

When a skill is loaded, you receive:
- skill_name: The skill identifier
- base_path: Full path to the skill directory
- content: The SKILL.md markdown content

### Loading Reference Documents

When you see markdown links in the skill content:
```
For advanced features, see [reference.md](reference.md)
```

**Action**: Use the Read tool with: `{base_path}/reference.md`
- Resolve relative paths using the base_path
- Example: base_path="/skills/pdf" → Read "/skills/pdf/reference.md"
- Load content only when you need the information

### Executing Scripts

When you see bash code blocks with commands:
```
Run the validation script:
```bash
python scripts/validate.py input.txt
```
```

**Action**: Use the Bash tool with the command, resolving paths:
- Command: `python {base_path}/scripts/validate.py input.txt`
- Example: `python /skills/pdf/scripts/validate.py input.txt`
- **IMPORTANT**: Execute the script, don't load its contents into context
- Only the script's output will be visible to you

### Following Explicit Instructions

When you see instructions like:
```
If you need to fill out a PDF form, read forms.md and follow its instructions
```

**Action**:
1. Use Read tool: `{base_path}/forms.md`
2. Apply the loaded instructions to your task
3. Continue following the skill workflow

### Path Resolution Rules

- Relative paths (e.g., `reference.md`, `scripts/tool.py`) → `{base_path}/{relative_path}`
- Absolute paths (e.g., `/etc/config`) → Use as-is
- URLs (e.g., `https://...`) → Use as-is
- Always use forward slashes (/) for paths, even on Windows
```

**Why This Matters for Multi-LLM Support:**

| Aspect | Claude Code (Native) | OmniForge (Multi-LLM) |
|--------|---------------------|----------------------|
| Navigation | Implicit understanding | **Explicit instructions required** |
| Path resolution | Built-in intelligence | **System prompt teaches path resolution** |
| Script vs. read decision | Infers from context | **Explicit rules: bash blocks = execute, links = read** |
| Works across LLMs | Claude only | **GPT-4, Claude, Gemini, etc.** |

**Implementation Note**: The navigation instructions above are added to the agent's base system prompt during initialization. This ensures **every agent**, regardless of underlying LLM, knows how to navigate skills correctly.

---

### Tool Calling Instructions (System Prompt for All Agents)

All agents need explicit instructions on **how to use OmniForge's tool system**. These instructions are added to the agent's base system prompt:

```markdown
## OmniForge Tool System

You have access to tools that extend your capabilities. Tools are functions you can invoke to perform actions like reading files, executing commands, searching, or invoking skills.

### Available Tools

Each tool has a definition with:
- **name**: Tool identifier (e.g., `read_file`, `bash_exec`, `skill`)
- **description**: What the tool does and when to use it
- **parameters**: List of parameters the tool accepts
  - **name**: Parameter identifier
  - **type**: `string`, `integer`, `float`, `boolean`, `array`, `object`
  - **description**: What the parameter is for
  - **required**: Whether the parameter must be provided
  - **default**: Default value if not required

### How to Call Tools

**1. Identify the Right Tool**
- Read tool descriptions to find what you need
- Match the task to the tool's purpose

**2. Prepare Arguments**
Provide arguments as a dictionary (JSON object):
```json
{
  "parameter_name": "value",
  "another_param": 123
}
```

**Parameter Type Guidelines:**
- `string`: Text values → `"hello"`
- `integer`: Whole numbers → `42`
- `float`: Decimal numbers → `3.14`
- `boolean`: True/false → `true` or `false`
- `array`: Lists → `["item1", "item2"]`
- `object`: Nested dictionaries → `{"key": "value"}`

**3. Invoke the Tool**
Call the tool with your arguments. The system will:
- Validate arguments against required parameters
- Check parameter types match definitions
- Execute the tool
- Return a ToolResult

### Understanding Tool Results

Every tool returns a `ToolResult` with:

```json
{
  "success": true/false,
  "result": {
    "key": "value",
    "data": [...]
  },
  "error": "error message if failed",
  "duration_ms": 150,
  "tokens_used": 0,
  "cost_usd": 0.0,
  "cached": false,
  "retry_count": 0
}
```

**Result Fields:**
- **success** (boolean): Whether execution succeeded
- **result** (dict): Data returned by the tool (only if success=true)
- **error** (string): Error message (only if success=false)
- **duration_ms** (integer): How long execution took
- **tokens_used** (integer): LLM tokens consumed (for LLM tools)
- **cost_usd** (float): USD cost (for LLM tools)
- **cached** (boolean): Whether result came from cache
- **retry_count** (integer): Number of retries attempted

**Interpreting Results:**

If `success = true`:
- The tool completed successfully
- Use `result` dictionary for the output data
- Example: `result["content"]`, `result["output"]`, `result["data"]`

If `success = false`:
- The tool failed
- Read `error` message to understand why
- Adjust your approach and try again, or inform the user

### Example Tool Usage

**Example 1: Reading a File**
```
Tool: read_file
Parameters:
- file_path (string, required): Path to file
- encoding (string, optional): File encoding, default="utf-8"

Your call:
{
  "file_path": "/path/to/document.txt"
}

Result:
{
  "success": true,
  "result": {
    "content": "File contents here...",
    "size_bytes": 1024,
    "encoding": "utf-8"
  },
  "duration_ms": 45
}

What you do:
- Extract content: result["content"]
- Use it for your task
```

**Example 2: Executing a Bash Command**
```
Tool: bash_exec
Parameters:
- command (string, required): Command to execute
- timeout_ms (integer, optional): Timeout in milliseconds

Your call:
{
  "command": "python scripts/validate.py input.txt",
  "timeout_ms": 10000
}

Result:
{
  "success": true,
  "result": {
    "stdout": "Validation passed\n",
    "stderr": "",
    "return_code": 0
  },
  "duration_ms": 234
}

What you do:
- Check return_code: 0 = success
- Read stdout for output
- Read stderr for errors
```

**Example 3: Tool Failure**
```
Tool: read_file
Your call:
{
  "file_path": "/nonexistent/file.txt"
}

Result:
{
  "success": false,
  "error": "File not found: /nonexistent/file.txt",
  "duration_ms": 5
}

What you do:
- Recognize the failure (success=false)
- Read error message
- Inform user or try alternative approach
```

### Error Handling

When tools fail:
1. **Check error message**: It explains what went wrong
2. **Common errors**:
   - "Missing required parameter: X" → You forgot a required parameter
   - "Invalid parameter type: expected string, got integer" → Wrong type
   - "File not found" → Path doesn't exist
   - "Permission denied" → Access restriction
   - "Timeout exceeded" → Operation took too long
3. **Respond appropriately**:
   - Fix the issue if possible (correct path, provide missing param)
   - Inform the user if it's a permission/access issue
   - Try alternative approaches

### Best Practices

1. **Read tool descriptions carefully** before invoking
2. **Provide all required parameters** with correct types
3. **Check success field first** before accessing result
4. **Handle errors gracefully** by reading error messages
5. **Use tool results appropriately** - extract the data you need
6. **Don't assume tool success** - always check the result
7. **For bash commands**: Check return_code and read stdout/stderr
```

**Why This Matters:**

This system prompt section ensures agents understand:
- ✅ Tool structure and definitions
- ✅ How to prepare arguments correctly
- ✅ How to interpret ToolResult objects
- ✅ Error handling patterns
- ✅ Works across all LLMs (ChatGPT, Claude, Gemini)

**Context Impact:**

- Tool description: ~200-500 tokens (regardless of skill count)
- Skill list in tool: ~50 bytes per skill
- Full SKILL.md: Loaded only when invoked (0 tokens until needed)
- Total overhead: Minimal compared to system prompt approach

---

### Complete Agent System Prompt Structure

The complete system prompt that **every agent receives** consists of:

```markdown
┌─────────────────────────────────────────────────────────────┐
│              OmniForge Agent System Prompt                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Agent Role and Identity (~50-200 tokens)                │
│     - Who you are                                           │
│     - Your capabilities                                     │
│     - Your constraints                                      │
│                                                             │
│  2. OmniForge Tool System (~800-1000 tokens)                │
│     - Tool structure (ToolDefinition)                       │
│     - How to call tools (arguments dict)                    │
│     - Understanding ToolResult                              │
│     - Parameter types                                       │
│     - Error handling                                        │
│     - Examples (read_file, bash_exec, failures)            │
│                                                             │
│  3. Skill Navigation Instructions (~400-600 tokens)         │
│     - Loading reference documents (markdown links)          │
│     - Executing scripts (bash code blocks)                  │
│     - Path resolution rules                                 │
│     - Progressive disclosure pattern                        │
│                                                             │
│  4. Project-Specific Instructions (variable)                │
│     - CLAUDE.md content (if present)                        │
│     - Project guidelines                                    │
│     - Custom instructions                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Total Base Overhead: ~1,250-1,800 tokens
(Before project-specific content)
```

**Token Budget Breakdown:**

| Component | Tokens | Purpose |
|-----------|--------|---------|
| Tool System Instructions | ~800-1000 | Teach how to use tools |
| Skill Navigation Instructions | ~400-600 | Teach how to navigate skills |
| Agent Role/Identity | ~50-200 | Define agent purpose |
| **Total Base Cost** | **~1,250-1,800** | **Fixed overhead per agent** |
| Project CLAUDE.md | Variable | Project-specific guidelines |
| Available Tool Descriptions | Variable | Dynamic based on tools available |
| Skill Descriptions (in tool) | ~50 bytes/skill | Only in SkillTool description |
| **Full SKILL.md Content** | **0 until invoked** | **Loaded on-demand via tool** |

**Key Optimization:**
- Skills don't bloat the system prompt
- Skill descriptions live in tool description (not system prompt)
- Full skill content loaded only when needed via tool invocation
- Scales to 100s of skills with minimal overhead

This design enables OmniForge agents to work consistently across all LLMs (Claude, GPT-4, Gemini) with explicit, clear instructions.

### Tool Restriction Enforcement

When a skill specifies `allowed-tools`:

```python
# Conceptual implementation
class SkillContext:
    def __init__(self, skill: MarkdownSkill, agent: BaseAgent):
        self.original_tools = agent.available_tools
        self.restricted_tools = [t for t in agent.available_tools
                                  if t.name in skill.allowed_tools]

    def enter(self):
        # Replace agent's tool list with restricted set
        self.agent.available_tools = self.restricted_tools

    def exit(self):
        # Restore original tools
        self.agent.available_tools = self.original_tools
```

The agent literally cannot call tools outside the allowlist while the skill is active. This is enforced at the tool execution layer, not just suggested in instructions.

### Context Forking (`context: fork`)

When a skill specifies `context: fork`:

```
Normal execution (context: inherit):
  - Skill instructions added to current agent context
  - Agent continues with expanded capabilities
  - Tool restrictions apply to current agent

Forked execution (context: fork):
  - New sub-agent spawned
  - Skill instructions are sub-agent's primary instructions
  - Sub-agent has isolated context (no parent conversation)
  - Results returned to parent agent
  - Sub-agent context discarded after completion
```

Forking is useful for:
- Skills that shouldn't see parent conversation (privacy)
- Skills that need clean context (long conversations)
- Skills that might pollute parent context (verbose output)

### Integration with Existing FunctionTool

The Skills system complements, not replaces, the existing Python FunctionTool:

```
Tool Types:
  - function           -> FunctionTool + FunctionRegistry (existing, renamed)
  - skill              -> SkillTool + SkillLoader (new)

Both available to agents:
  - Functions: programmatic, fast, typed Python code
  - Skills: declarative, flexible, knowledge-based procedures

Example hybrid usage:
  1. Agent skill "code-review" loaded via SkillTool
  2. Skill instructions say: "Use the analyze_code function for static analysis"
  3. Agent calls Python function "analyze_code" via FunctionTool
  4. Function returns structured analysis
  5. Agent continues following skill instructions
```

---

## Security and Isolation

### Script Execution Security

Scripts in skills can execute arbitrary commands. Security measures:

1. **Sandboxing**: Skills can be marked to run in sandboxed environments
   ```yaml
   execution:
     sandbox: true
     allowed-paths: ["/project", "/tmp"]
     network: restricted
   ```

2. **Approval Requirements**: Enterprise can require approval for skills with scripts
   ```yaml
   # Enterprise policy
   skill-policy:
     require-approval-for:
       - scripts
       - network-tools
       - file-write
   ```

3. **Audit Logging**: All script executions logged with full command and output
   ```
   [AUDIT] Skill: deploy-to-k8s | Script: deploy.sh | User: alice | Time: 2026-01-13T10:30:00Z
   [AUDIT] Command: bash scripts/deploy.sh --env prod
   [AUDIT] Exit code: 0 | Duration: 45s
   ```

4. **Path Restrictions**: Scripts can only access paths within skill directory or explicitly allowed paths

### Context Isolation

When `context: fork` is used:

- Parent conversation not visible to skill sub-agent
- Skill cannot access parent's memory or state
- Only explicit inputs passed to skill
- Only explicit outputs returned to parent

This enables sensitive skills (e.g., credential management) to operate without exposing data to the broader conversation.

### Tool Restriction Security

Tool restrictions are enforced at the execution layer:

```python
class ToolExecutor:
    def execute(self, tool_call: ToolCall, context: ExecutionContext) -> ToolResult:
        # Check if tool is allowed in current skill context
        if context.active_skill and context.active_skill.allowed_tools:
            if tool_call.tool_name not in context.active_skill.allowed_tools:
                return ToolResult(
                    success=False,
                    error=f"Tool '{tool_call.tool_name}' not allowed by active skill '{context.active_skill.name}'"
                )

        # Proceed with execution
        return self._execute_tool(tool_call)
```

The agent cannot bypass restrictions through creative prompting - the restriction is in the execution layer.

### Enterprise Security Controls

Enterprise administrators have additional controls:

1. **Skill Approval Workflow**: New skills require admin approval before activation
2. **Skill Scanning**: Automated scanning of SKILL.md and scripts for policy violations
3. **Allowlist/Blocklist**: Define which skills are permitted or prohibited
4. **Override Authority**: Enterprise skills can force-override any lower-level skill
5. **Audit Dashboard**: View all skill activations across the organization

---

## User Journeys

### Journey 1: Developer Creates a Code Review Skill

**Persona**: SDK Developer
**Context**: Developer wants agents to follow their team's code review standards

1. **Developer creates skill directory**:
   ```
   .omniforge/skills/code-review/
     SKILL.md
     docs/style-guide.md
     scripts/run-linters.sh
   ```

2. **Developer writes SKILL.md**:
   ```markdown
   ---
   name: code-review
   description: Review code changes following team standards with automated linting
   allowed-tools:
     - Read
     - Bash
     - Glob
   ---

   # Code Review Skill

   When reviewing code, follow these steps...
   [Team-specific review procedures]
   ```

3. **Developer commits to project** - Skill is now available to all agents working on this project

4. **User requests code review** - "Review the changes in the auth module"

5. **Agent discovers skill** - Matches "code review" against skill descriptions, finds code-review skill

6. **Agent activates skill** - Loads full SKILL.md, restricts to Read/Bash/Glob

7. **Agent follows skill instructions** - Reviews code per team standards, runs linters via script

8. **Agent produces review** - Follows skill's output format requirements

**Key Experience**: The developer defined complex review procedures in Markdown. No Python code. The skill is version-controlled with the project. All team members' agents now follow the same standards.

---

### Journey 2: Enterprise Admin Deploys Compliance Skill

**Persona**: Enterprise Administrator
**Context**: Organization requires all agents to follow data handling compliance procedures

1. **Admin creates compliance skill**:
   ```markdown
   ---
   name: data-handling
   description: Ensure all data operations follow corporate compliance requirements
   priority: 1000  # High priority to override project skills
   scope:
     environments: ["production"]
   ---

   # Data Handling Compliance

   CRITICAL: All data operations must follow these rules...
   [Compliance requirements]
   ```

2. **Admin deploys to enterprise layer**:
   ```bash
   omniforge skill deploy data-handling --scope enterprise
   ```

3. **Skill syncs to all organization agents** - Automatic distribution

4. **Project tries to override** - Project creates their own `data-handling` skill

5. **Enterprise version wins** - Override rules ensure compliance skill takes precedence

6. **Admin monitors usage** - Audit dashboard shows skill activations across teams

**Key Experience**: Admin defined compliance requirements in Markdown. Single deployment reaches all agents. Cannot be bypassed by project-level skills. Full audit trail.

---

### Journey 3: Agent Builds an Agent's Skill

**Persona**: End User (via Platform Chatbot)
**Context**: User wants to create a new capability for their agent

1. **User requests capability**: "I want my agent to be able to generate weekly status reports from our Jira board"

2. **Platform agent understands request** - Determines this is a skill creation task

3. **Agent creates skill directory**:
   ```
   .omniforge/skills/weekly-status-report/
     SKILL.md
     docs/report-format.md
   ```

4. **Agent writes SKILL.md**:
   ```markdown
   ---
   name: weekly-status-report
   description: Generate weekly status reports from Jira board data
   allowed-tools:
     - ExternalAPI
     - Write
   ---

   # Weekly Status Report Generation

   When asked to generate a status report:
   1. Query Jira API for issues updated this week...
   [Auto-generated instructions based on user's request]
   ```

5. **Agent confirms with user**: "I've created a skill for generating weekly status reports. Would you like me to test it?"

6. **Skill is now available** - User's agents can generate status reports automatically

**Key Experience**: The user described what they wanted in natural language. An agent created the skill - Markdown file, instructions, tool restrictions. **Agents building agents** in action.

---

### Journey 4: Developer Uses Progressive Disclosure

**Persona**: SDK Developer
**Context**: Skill has extensive reference documentation that shouldn't be loaded upfront

1. **Developer creates documentation-heavy skill**:
   ```
   aws-deployment/
     SKILL.md (2KB instructions)
     docs/
       services-reference.md (50KB)
       troubleshooting.md (30KB)
       architecture.md (20KB)
   ```

2. **Agent initializes** - Only skill name/description loaded (Stage 1: ~100 bytes)

3. **User requests AWS deployment** - "Deploy our service to AWS ECS"

4. **Agent activates skill** - Full SKILL.md loaded (Stage 2: 2KB)

5. **Agent encounters unfamiliar service** - Instructions say "see docs/services-reference.md for service configuration"

6. **Agent loads reference doc** - `Read("aws-deployment/docs/services-reference.md")` (Stage 3: on-demand)

7. **Agent finds answer** - Continues deployment with specific knowledge

8. **Context efficiency**: Only loaded what was needed. 100KB of docs available, maybe 5KB actually used.

**Key Experience**: Developer organized knowledge in reference docs. Agent loads only what it needs, when it needs it. Massive documentation library has minimal context impact.

---

## Success Criteria

### User Outcomes

#### For SDK Developers
- **Skill Creation Time**: Create a new skill in under 5 minutes (just write Markdown)
- **No Python Required**: Define complex agent capabilities without any Python code
- **Version Control Native**: Skills live in project repos, tracked with git
- **Clear Tool Boundaries**: Explicit tool restrictions enforced, not just suggested

#### For Platform Developers
- **Package Distribution**: Publish skills to registries, install with single command
- **Compatibility**: Skills work across OmniForge versions without modification
- **Testing**: Skills can be tested in isolation with mock contexts

#### For Enterprise Administrators
- **Centralized Control**: Single point for deploying/revoking skills across organization
- **Policy Enforcement**: Skills cannot bypass enterprise policies
- **Complete Audit Trail**: All skill activations logged with full context
- **Override Authority**: Enterprise skills definitively override lower levels

#### For End Users
- **Seamless Experience**: Benefits from skills without knowing they exist
- **Consistent Behavior**: Agents apply appropriate skills automatically
- **No IT Dependency**: Agents "just know" domain procedures

### Technical Outcomes

- **Context Efficiency**: Stage 1 loading adds < 1KB to agent context regardless of skill count
- **Discovery Speed**: Skill discovery completes in < 100ms for up to 1000 skills
- **Activation Latency**: Skill activation adds < 50ms to task processing
- **Tool Restriction Enforcement**: 100% of tool calls checked against skill allowlist
- **Script Isolation**: Script contents never enter agent context

### Business Outcomes

- **Enterprise Adoption**: Governance features address enterprise control requirements
- **Community Growth**: Markdown format enables broad contribution
- **Platform Differentiation**: Progressive disclosure and tool restrictions are unique capabilities
- **No-Code Enablement**: Business users can define agent capabilities

---

## Key Experiences

### The "It Just Works" Moment

When a user makes a request and the agent automatically applies the right skill without any explicit invocation. The user doesn't know a skill was used - they just experience competent, specialized agent behavior.

**What makes this moment great**:
- No "/skill" command or explicit activation
- Agent reasoning shows skill discovery naturally
- Output follows skill's quality standards
- User feels the agent "understands" their domain

### The "I Wrote This in 5 Minutes" Moment

When a developer creates a new skill by writing a simple Markdown file and immediately sees it working in their agent.

**What makes this moment great**:
- No boilerplate, no registration code
- Drop SKILL.md in directory, it works
- Natural language instructions, not code
- Version control just works (it's a file)

### The "Total Control" Moment

When an enterprise admin deploys a compliance skill and sees it immediately active across all organization agents, with confidence it cannot be bypassed.

**What makes this moment great**:
- Single action affects entire organization
- Clear override rules provide certainty
- Audit trail shows enforcement
- No team can work around it

### The "Context Efficiency" Moment

When a developer realizes their 100KB documentation library is available to agents without consuming context until actually needed.

**What makes this moment great**:
- All docs accessible, none pre-loaded
- Agent fetches only what it needs
- Massive capability, minimal footprint
- Scripts execute without loading

---

## Edge Cases and Considerations

### Skill Name Conflicts

**Scenario**: Two plugins define skills with the same name.

**Handling**:
- Last-installed plugin wins at plugin layer
- Clear warning in logs about conflict
- Explicit resolution via skill aliasing: `skill-name@package-name`
- Recommendation: use namespaced names (e.g., `acme/deploy` not just `deploy`)

### Circular Skill Dependencies

**Scenario**: Skill A references Skill B, which references Skill A.

**Handling**:
- Track skill activation stack
- Detect cycles and prevent with clear error
- Maximum skill activation depth (default: 5)
- Error message shows the cycle for debugging

### Large Skill Directories

**Scenario**: Project has hundreds of skills affecting discovery performance.

**Handling**:
- Index skills at project open, cache index
- Incremental index updates on file changes
- Skill categories for faster filtering
- Warn when skill count exceeds recommended limits

### Skill Activation During Streaming

**Scenario**: Agent activates a skill mid-stream while responding to user.

**Handling**:
- Skill activation is a visible reasoning step
- Stream shows: "Activating 'code-review' skill..."
- Tool restrictions apply immediately
- Previous streaming context remains valid

### Malicious Skills

**Scenario**: Skill contains instructions that attempt to bypass safety guidelines or exfiltrate data.

**Handling**:
- Skills do not override agent safety guidelines
- Enterprise scanning can detect suspicious patterns
- Skill execution logged for audit
- Sandboxing prevents unauthorized access
- Scripts run in restricted environment

### Reference Doc Not Found

**Scenario**: SKILL.md references a doc that doesn't exist.

**Handling**:
- Agent's Read tool returns file-not-found error
- Agent handles gracefully (it's trained for missing files)
- Skill validation tool can pre-check references
- Warning logged for skill maintainers

### Tool Restriction Conflicts

**Scenario**: Skill restricts to tools A, B, but task requires tool C.

**Handling**:
- Agent cannot use tool C while skill is active
- Agent can deactivate skill if task cannot be completed
- Agent explains limitation to user
- Logging shows restriction prevented operation

---

## Open Questions

### Skill Versioning
- How do we handle versioned skills (v1 vs v2)?
- Should agents be able to request specific skill versions?
- How do we manage breaking changes in skills?

### Skill Composition
- Can skills reference other skills as dependencies?
- How do tool restrictions compose across nested skills?
- Should there be skill "inheritance" (base skills with overrides)?

### Learning from Skill Execution
- Should successful skill executions inform skill improvements?
- Can agents suggest skill modifications based on execution patterns?
- How do we capture skill feedback for curation?

### Cross-Language Scripts
- Should we support non-bash scripts (Python, Node)?
- How do we handle script dependencies?
- What's the security model for different script types?

### Skill Testing
- What does a skill test look like?
- How do we mock tool responses for skill testing?
- Should skills have formal test suites?

### Platform UI
- How do users browse/discover skills in the platform?
- What does skill management UI look like?
- How do we visualize skill activation in conversation view?

### Skill Analytics
- What metrics should we track per skill?
- How do we identify underperforming skills?
- What does skill usage reporting look like?

---

## Out of Scope (For Now)

### Skill Marketplace
A public marketplace for discovering and installing community skills. Future premium platform feature.

### Visual Skill Builder
A drag-and-drop interface for creating skills without writing Markdown. Future no-code enhancement.

### Skill Chaining
Defining explicit sequences of skills that execute in order. Current model: agent decides skill activation.

### Skill Training
Using skill execution data to train improved skill behavior. Requires ML infrastructure not yet in place.

### Multi-Skill Activation
Activating multiple skills simultaneously with merged tool restrictions. V1 supports single active skill.

### Skill IDE Integration
VS Code / IDE extensions for skill authoring with validation. Community contribution opportunity.

### Skill Rollback
Reverting skill changes across deployments. Requires skill versioning (open question).

---

## Technical Constraints

### Integration with Existing Architecture

The Markdown skills system must integrate with:

- **SkillTool (existing)**: Markdown skills coexist with Python skills. Different tool types, same agent.
- **CoT Reasoning Chain**: Skill activation appears as reasoning step. Tool restrictions visible in chain.
- **Unified Tool Interface**: Skills use existing tools (Bash, Read, etc.) through unified interface.
- **Storage System**: Skill index persisted for fast startup. Configurable backends.
- **RBAC**: Skill access controlled by existing permission system.
- **Multi-tenancy**: Skills scoped to tenants. Enterprise skills cross-tenant.

### Performance Requirements

- **Skill Discovery**: < 100ms for up to 1000 skills
- **Skill Activation**: < 50ms to load and apply skill
- **Index Rebuild**: < 5s for full project scan
- **Memory Overhead**: < 10MB for skill index of 1000 skills

### Storage Requirements

- **Index Size**: ~1KB per skill (name, description, path, metadata)
- **Skill Loading**: Full SKILL.md loaded on activation (typically 1-10KB)
- **No Pre-loading**: Reference docs never pre-loaded
- **Cache**: Optional caching of recently-used skills

### File System Requirements

- **Directory Structure**: Standard filesystem hierarchy
- **Watch Support**: File watching for live reload (optional)
- **Permissions**: Read access to skill directories, execute for scripts
- **Path Resolution**: Relative paths within skill, absolute for storage layers

---

## Evolution Notes

### 2026-01-13 v1.0 (Initial Draft)

Created specification based on Claude Code skills documentation and OmniForge requirements.

**Key Design Decisions**:

1. **Complement, Don't Replace**: Markdown skills complement Python skills. Different use cases, same agent. Python for programmatic operations, Markdown for knowledge and procedures.

2. **Progressive Disclosure as Core Architecture**: Not an optimization, but fundamental design. Three-stage loading (discovery -> activation -> reference) ensures context efficiency at scale.

3. **Scripts Execute, Never Load**: Critical for context efficiency. A 1000-line deployment script uses zero context tokens. Agent calls Bash, gets output.

4. **Four-Layer Hierarchy with Clear Override**: Enterprise > Personal > Project > Plugin. No ambiguity about which skill wins. Enterprise has ultimate control.

5. **Tool Restrictions at Execution Layer**: Not suggestions, not prompts - actual enforcement. Agent cannot call disallowed tools. Period.

**Alignment with Product Vision**:
- Markdown format enables no-code capability definition
- Storage hierarchy enables enterprise governance
- Progressive disclosure supports "simplicity over flexibility"
- Agents can create skills, enabling "agents build agents"

**Reference**: Claude Code skills documentation at https://code.claude.com/docs/en/skills

**Next Steps**:
1. Technical planning phase for implementation architecture
2. Define SkillLoader and SkillIndex components
3. Design integration with existing ToolExecutor for restrictions
4. Plan storage layer for enterprise/personal/project hierarchy
5. Create CLI commands for skill management

---

## References

**OmniForge Internal:**
- [OmniForge Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [CoT Agent with Unified Tools Specification](/Users/sohitkumar/code/omniforge/specs/cot-agent-with-unified-tools-spec.md)
- [Existing SkillTool Implementation](/Users/sohitkumar/code/omniforge/src/omniforge/tools/builtin/skill.py)
- [TASK-405: Internal Skill Tool](/Users/sohitkumar/code/omniforge/specs/tasks/cot-agent/phase-4/TASK-405-skill-tool.md)

**External References:**
- Claude Code Skills Documentation: https://code.claude.com/docs/en/skills
