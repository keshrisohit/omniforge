# Product Specification: Autonomous Skill Execution

**Version:** 1.0
**Date:** 2026-01-26
**Status:** Draft
**Owner:** OmniForge Core Team

---

## Executive Summary

Transform OmniForge skills from single-pass execution into autonomous agents that iteratively work toward task completion. Skills will use a ReAct (Reason → Act → Observe) loop with error recovery, progressive disclosure, and multi-turn conversation, enabling them to handle complex tasks without user intervention.

**Key Benefits:**
- **Autonomous Execution**: Skills iterate until task completion (up to 15 iterations)
- **Error Recovery**: Automatic retries with alternative approaches
- **Smart Context Management**: Only load relevant skill files into LLM context (saves tokens)
- **Progressive UI Disclosure**: Users see clean progress, developers see full trace
- **Better UX**: No overwhelming users with 50+ tool calls or bloated context
- **Higher Success Rate**: 80%+ error recovery for common failures

---

## Problem Statement

### Current State (Pain Points)

**Single-Pass Execution:**
```python
# executor.py - Current implementation
execute(request):
    plan = llm.plan_tools(request)  # One-time planning
    results = execute_tools(plan)    # Execute once
    return synthesize(results)       # Done - no retry
```

**Problems:**
1. ❌ No iteration - if first plan fails, entire task fails
2. ❌ No error recovery - tool failures are fatal
3. ❌ No smart context loading - all skill files loaded upfront (wastes tokens)
4. ❌ No progressive UI disclosure - users see all tool calls or nothing
5. ❌ No conversation context - can't build on previous observations
6. ❌ Overwhelming output - developers see 50+ tool calls with no summary

**User Impact:**
- Business users frustrated by failures on retryable errors
- Developers struggle to debug without seeing reasoning
- Skills fail tasks that could succeed with retry/alternative approach

---

## Vision & Goals

### Vision
Skills execute autonomously like experienced engineers: plan, try, observe results, adjust approach, and keep working until the task is complete or proven impossible.

### Goals

**Primary Goals:**
1. **Autonomous Execution**: Skills iterate until completion (max 15 iterations)
2. **Error Recovery**: 80%+ recovery rate for common tool failures
3. **Progressive Disclosure**: Clean UX with optional detail drill-down
4. **Backward Compatibility**: Existing skills continue to work

**Secondary Goals:**
5. **Sub-agent Support**: Skills can fork isolated execution contexts
6. **Performance**: <500ms overhead per iteration for reasoning
7. **Observability**: Full trace available for debugging
8. **Configurability**: Skills control iteration budget and behavior

---

## User Personas & Journeys

### Persona 1: Technical Business User (No-code Interface)

**Profile:**
- Name: Sarah (Product Manager)
- Role: Creates and uses agents through chat interface
- Technical Level: Can describe workflows, not a coder
- Goal: Automate data processing without writing code

**Current Journey (Pain):**
1. Sarah: "Process this CSV file and generate a report"
2. Skill executes → Tool fails (file encoding issue)
3. ❌ Skill returns error: "UnicodeDecodeError"
4. Sarah doesn't understand error, asks for help
5. Developer manually fixes and reruns

**Desired Journey (Autonomous):**
1. Sarah: "Process this CSV file and generate a report"
2. Skill starts execution (Sarah sees: "🔄 Processing data...")
3. **Iteration 1**: Skill tries UTF-8 encoding → fails
4. **Iteration 2**: Skill detects error, tries Latin-1 → success!
5. **Iterations 3-8**: Validates, transforms, generates report
6. ✅ Sarah sees: "✅ Processed 100 rows, generated report.pdf"
7. (Optional) Sarah clicks "View details" → sees summary of 8 steps

**Key Moments:**
- ✅ Error automatically recovered (no manual intervention)
- ✅ Clean progress updates (not overwhelmed with details)
- ✅ Task completed successfully despite initial failure

---

### Persona 2: Developer (SDK)

**Profile:**
- Name: Alex (Senior Engineer)
- Role: Builds custom skills and agents
- Technical Level: Expert Python developer
- Goal: Create reliable, debuggable autonomous skills

**Current Journey (Pain):**
1. Alex writes SKILL.md: "Analyze code quality and suggest improvements"
2. Tests skill → fails on complex codebase
3. ❌ Single error log: "Tool 'grep' failed"
4. Alex can't see reasoning: why did it call grep? what was it looking for?
5. Adds debug logging manually, reruns multiple times

**Desired Journey (Autonomous):**
1. Alex writes SKILL.md with instructions and allowed_tools
2. Deploys: `await skill_executor.execute("analyze codebase")`
3. Skill executes (Alex sees full trace in developer mode):
   ```
   Iteration 1: Thought: Need to find Python files
                Tool: glob(pattern="**/*.py") → 47 files

   Iteration 2: Thought: Check for common code smells
                Tool: grep(pattern="TODO|FIXME") → 23 matches

   Iteration 3: Thought: Analyze complexity of main modules
                Tool: bash(command="radon cc src/") → Failed (radon not installed)

   Iteration 4: Thought: Radon missing, use simpler approach
                Tool: read(file="src/main.py") → 342 lines
                Tool: count_lines_and_functions() → ...

   ... 8 more iterations with full reasoning ...

   Iteration 12: Final Answer: Found 5 critical issues, 12 improvements
   ```
4. ✅ Alex sees complete reasoning chain
5. ✅ Tool failure handled gracefully (switched approach)
6. ✅ Can debug by reviewing thought process

**Key Moments:**
- ✅ Full visibility into reasoning (every thought, tool call, result)
- ✅ Error recovery visible (can see alternative approach)
- ✅ Debuggable (understands why skill made each decision)

---

### Persona 3: Platform Admin

**Profile:**
- Name: Jordan (DevOps/Platform Engineer)
- Role: Manages OmniForge deployment for organization
- Technical Level: Infrastructure expert
- Goal: Monitor, optimize, and ensure platform reliability

**Current Journey (Pain):**
1. Jordan sees skill execution metrics: 45% failure rate
2. ❌ No insight into why skills fail
3. ❌ Can't tell if failures are retryable or fatal
4. Manually reviews logs to understand patterns

**Desired Journey (Autonomous):**
1. Jordan views skill execution dashboard:
   ```
   Skill: "data-processor"
   - Success Rate: 87% (↑ from 45%)
   - Avg Iterations: 4.2
   - Error Recovery Rate: 82%
   - Most Common Recovery: File encoding fallback (34%)
   ```
2. ✅ Sees improvement from autonomous execution
3. ✅ Understands recovery patterns
4. Jordan configures visibility rules:
   ```yaml
   default_visibility: SUMMARY
   roles:
     END_USER: SUMMARY
     DEVELOPER: FULL
     ADMIN: FULL
   sensitive_tools:
     - type: DATABASE
       visibility: HIDDEN
   ```
5. ✅ Controls what users see based on role

**Key Moments:**
- ✅ Clear metrics on autonomous execution effectiveness
- ✅ Configurable visibility per role and tool type
- ✅ Audit trail of all skill executions

---

## Feature Requirements Summary

This specification defines **12 feature requirements** for autonomous skill execution:

**Core Autonomous Execution (P0):**
- **FR-1**: Autonomous ReAct Loop - Iterative Think → Act → Observe pattern
- **FR-2**: Error Recovery & Retry Logic - 80%+ recovery rate goal
- **FR-3**: Progressive Context Loading - Load skill files on-demand
- **FR-4**: User-Facing Progressive Disclosure - FULL/SUMMARY/HIDDEN UI visibility
- **FR-9**: Script Execution Support - Bundle and run Python/JS/shell scripts
- **FR-10**: Dynamic Context Injection - Inject command output before execution

**Integration & Compatibility (P0-P1):**
- **FR-5**: Sub-Agent Execution - Forked context for isolated execution
- **FR-6**: Backward Compatibility - Existing skills work unchanged
- **FR-7**: Streaming Events - Real-time progress updates

**Configuration & Optimization (P1-P2):**
- **FR-8**: Configuration & Tuning - Per-skill and platform-level settings
- **FR-11**: String Substitutions - Variables like $ARGUMENTS, ${SESSION_ID}
- **FR-12**: Model Selection - Choose haiku/sonnet/opus per skill

**Feature Parity with Claude Code Skills:** 95%+ (deferred: hooks, argument-hints, user-invocable)

---

## Feature Requirements

### FR-1: Autonomous ReAct Loop

**Description:** Skills execute using ReAct pattern (Reason → Act → Observe → repeat)

**Behavior:**
```python
# Autonomous execution loop
for iteration in range(max_iterations):
    # Think: Analyze current situation
    thought = reason_about_next_step(task, observations)

    # Act: Call tools if needed
    if needs_tool_call:
        result = execute_tool(tool_name, args)
        observations.append(result)

    # Check: Is task complete?
    if is_complete(observations):
        return final_answer

    # Observe: Tool failed?
    if tool_failed:
        analyze_error_and_plan_alternative()
```

**Acceptance Criteria:**
- [ ] Skills iterate up to `max_iterations` (default: 15)
- [ ] Each iteration includes: thought → optional tool call → observation
- [ ] Skills can terminate early when task is complete
- [ ] Skills respect iteration budget (no infinite loops)
- [ ] Conversation history maintained across iterations

**Priority:** P0 (Must Have)
**Effort:** Large

---

### FR-2: Error Recovery & Retry Logic

**Description:** Skills automatically retry failed tool calls with alternative approaches

**Behavior:**
```python
# Error recovery example
Iteration 3: Tool: read(file="/data/file.csv", encoding="utf-8") → FAILED
             Error: UnicodeDecodeError

Iteration 4: Thought: UTF-8 failed, trying Latin-1 encoding
             Tool: read(file="/data/file.csv", encoding="latin-1") → SUCCESS

# Alternative approach example
Iteration 7: Tool: bash("radon cc src/") → FAILED (command not found)
Iteration 8: Thought: Radon not available, using alternative approach
             Tool: read("src/main.py") → SUCCESS
             Tool: count_complexity() → SUCCESS
```

**Rules:**
- Max 3 retry attempts per tool with same arguments
- After 3 failures, must try different approach/tool
- Track failed approaches to avoid loops
- Graceful degradation if all approaches fail

**Acceptance Criteria:**
- [ ] Tool failures trigger reasoning about alternatives
- [ ] Max 3 retries per tool/approach combination
- [ ] Different encoding/parameters count as different attempts
- [ ] Error messages inform next reasoning step
- [ ] Partial results returned if complete solution impossible
- [ ] 80%+ recovery rate for common errors (encoding, missing files, etc.)

**Priority:** P0 (Must Have)
**Effort:** Large

---

### FR-3: Progressive Context Loading (Smart Context Management)

**Description:** Only load relevant skill files into LLM context when needed to save context window space

**Problem:**
Skills can have multiple files (SKILL.md, reference.md, examples.md, templates/, etc.). Loading everything upfront wastes context window and increases costs.

**Solution - Lazy Loading:**
```
my-skill/
├── SKILL.md              # Always loaded (core instructions, <500 lines)
├── reference.md          # Loaded only when agent needs it
├── examples.md           # Loaded only when agent needs it
├── templates/
│   └── report.md         # Loaded only when generating report
└── scripts/
    └── helper.py         # Not loaded (executed directly)
```

**Initial Load (Iteration 1):**
```python
# Only load core instructions
system_prompt = f"""
You are executing the '{skill.name}' skill.

SKILL INSTRUCTIONS:
{skill.content}  # Only SKILL.md content (~500 lines)

AVAILABLE SUPPORTING FILES (load on-demand with 'read' tool):
- reference.md: Complete API documentation (1,200 lines)
- examples.md: Usage examples (800 lines)
- templates/report.md: Report template (300 lines)

AVAILABLE TOOLS:
{tool_descriptions}
"""
```

**On-Demand Loading (Iteration 5):**
```python
# Agent decides it needs more detail
Iteration 5:
  Thought: "I need to understand the API format. Let me check reference.md"
  Tool: read(file=".claude/skills/my-skill/reference.md")
  Result: [API documentation loaded into context]

Iteration 6:
  Thought: "Now I understand the format, making API call"
  Tool: api_call(endpoint="/data", format="json")
```

**Benefits:**
- **Context Savings**: Load 500 lines instead of 3,000 lines upfront
- **Cost Reduction**: Smaller context = lower token costs per iteration
- **Flexibility**: Agent loads only what it needs for current task
- **Scalability**: Skills can have extensive documentation without bloating context

**SKILL.md Best Practices:**
```markdown
---
name: data-processor
description: Process data files with validation and transformation
max_iterations: 15
---

# Data Processor Skill

## Quick Start
1. Read input file with appropriate encoding
2. Validate format (see reference.md for details)
3. Transform data (see examples.md for patterns)
4. Generate report (see templates/report.md)

## When You Need More Information
- **API Details**: Read reference.md for complete API specs
- **Usage Examples**: Read examples.md for transformation patterns
- **Report Format**: Read templates/report.md for output structure

## Core Instructions
[Essential instructions here, keep under 500 lines]
```

**Acceptance Criteria:**
- [ ] Initial system prompt includes only SKILL.md content
- [ ] SKILL.md limited to 500 lines (validation at load time)
- [ ] Supporting files referenced in SKILL.md (with descriptions)
- [ ] Agent can use 'read' tool to load supporting files on-demand
- [ ] Context usage tracked per iteration (metrics)
- [ ] Warning if SKILL.md exceeds 500 lines
- [ ] Supporting files organized in skill directory structure

**Priority:** P0 (Must Have)
**Effort:** Medium

---

### FR-4: User-Facing Progressive Disclosure

**Description:** Users see appropriate level of UI detail based on role (separate from context management)

**Visibility Levels:**
1. **FULL**: Every thought, tool call, result (for developers/debugging)
2. **SUMMARY**: High-level progress milestones (for end users)
3. **HIDDEN**: Completely hidden (for sensitive operations)

**Examples:**

**FULL Visibility (Developer):**
```
🔄 Skill: data-processor [Iteration 3/15]

💭 Thought: Need to validate CSV format before processing
🔧 Tool Call: bash(command="csvlint /data/input.csv")
   Arguments: {"command": "csvlint /data/input.csv"}
✅ Tool Result: Valid CSV, 100 rows, 5 columns
   Duration: 0.23s

💭 Thought: Validation passed, now transforming data
🔧 Tool Call: write(file="/tmp/transform.py", content="...")
   Arguments: {"file_path": "/tmp/transform.py", "content": "... [245 bytes]"}
✅ Tool Result: File written successfully
```

**SUMMARY Visibility (End User):**
```
🔄 Processing data file...

✅ Input validated (100 rows)
⏳ Transforming data (step 2 of 5)...
```

**HIDDEN (Sensitive Tools):**
```
🔄 Processing data...

[Database query execution hidden]

✅ Data retrieved successfully
```

**Configuration:**
```python
visibility_rules = VisibilityConfiguration(
    default_level=VisibilityLevel.SUMMARY,
    rules_by_role={
        Role.END_USER: VisibilityLevel.SUMMARY,
        Role.DEVELOPER: VisibilityLevel.FULL,
    },
    rules_by_tool_type={
        ToolType.DATABASE: VisibilityLevel.HIDDEN,  # Hide DB queries
        ToolType.BASH: VisibilityLevel.SUMMARY,     # Summarize commands
    },
    sensitive_fields=["password", "api_key", "token", "secret"]
)
```

**Acceptance Criteria:**
- [ ] Three visibility levels: FULL, SUMMARY, HIDDEN
- [ ] Role-based filtering (END_USER, DEVELOPER, ADMIN)
- [ ] Tool-type-based rules (DATABASE, API, etc.)
- [ ] Automatic PII/credential redaction
- [ ] UI supports drill-down ("Show full details" button)
- [ ] Sensitive fields always redacted regardless of level

**Priority:** P0 (Must Have)
**Effort:** Medium (uses existing CoT visibility system)

---

### FR-5: Sub-Agent Execution (Forked Context)

**Description:** Skills with `context: fork` in metadata run in isolated context

**Behavior:**
```yaml
# SKILL.md with forked context
---
name: deep-analysis
description: Analyze code quality in detail
context: fork
agent: Explore
max_iterations: 20
---

Perform deep analysis:
1. Find all Python files
2. Check for security vulnerabilities
3. Calculate complexity metrics
4. Generate detailed report
```

**When invoked:**
1. Skill instructions become system prompt for sub-agent
2. Sub-agent runs in isolated context (no access to parent conversation)
3. Sub-agent uses specified agent type (`Explore`, `Plan`, etc.)
4. Results summarized and returned to parent
5. Full trace available for debugging

**Acceptance Criteria:**
- [ ] Skills with `context: fork` create sub-agent
- [ ] Sub-agent runs in isolation (no parent context)
- [ ] Supports agent types: Explore, Plan, general-purpose, custom
- [ ] Parent receives summary + link to full trace
- [ ] Sub-agent respects skill's `max_iterations`
- [ ] Sub-agent uses skill's `allowed_tools`

**Priority:** P1 (Should Have)
**Effort:** Medium (leverages existing sub-agent infrastructure)

---

### FR-6: Backward Compatibility

**Description:** Existing skills continue to work without modification

**Requirements:**
- Skills without `execution_mode` metadata default to autonomous
- Skills can opt-in to legacy mode: `execution_mode: simple`
- Existing SkillTool API remains functional
- No breaking changes to SKILL.md format

**Migration Path:**
```yaml
# Legacy skill (still works)
---
name: old-skill
description: Works as before
---

# Explicitly simple execution (non-autonomous)
---
name: simple-skill
description: Single-pass execution
execution_mode: simple
---

# Autonomous execution (new default)
---
name: auto-skill
description: Autonomous with retry
execution_mode: autonomous  # Optional, this is default
max_iterations: 15
---
```

**Acceptance Criteria:**
- [ ] All existing skills work without changes
- [ ] `execution_mode: simple` available for opt-out
- [ ] Default is autonomous execution
- [ ] No breaking API changes
- [ ] Migration guide for updating skills

**Priority:** P0 (Must Have)
**Effort:** Small

---

### FR-7: Streaming Events

**Description:** Skill execution emits real-time events for UI updates

**Event Types:**
```python
# Status events
TaskStatusEvent(state=TaskState.RUNNING)

# Progress updates (summary level)
TaskMessageEvent(
    message="Reading input file...",
    visibility=VisibilityLevel.SUMMARY
)

# Detailed steps (full level)
TaskMessageEvent(
    message="Tool: read(file='/data/input.csv')",
    visibility=VisibilityLevel.FULL
)

# Completion
TaskDoneEvent(state=TaskState.COMPLETED)

# Errors
TaskErrorEvent(
    error_code="TOOL_FAILED",
    error_message="Failed to read file after 3 attempts"
)
```

**Acceptance Criteria:**
- [ ] Events stream in real-time (not buffered)
- [ ] Events include visibility level
- [ ] Frontend filters events by user role
- [ ] Events support reconnection (event replay)
- [ ] Progress percentage calculated and included

**Priority:** P1 (Should Have)
**Effort:** Small (uses existing event system)

---

### FR-8: Configuration & Tuning

**Description:** Skills and admins can configure autonomous behavior

**Skill-Level Configuration:**
```yaml
---
name: configurable-skill
description: Skill with custom settings
execution_mode: autonomous
max_iterations: 20          # Custom iteration budget
max_retries_per_tool: 5     # More aggressive retries
timeout_per_iteration: 30s  # Longer timeout
early_termination: true     # Stop early if confident
---
```

**Platform-Level Configuration:**
```python
# Admin dashboard settings
autonomous_config = AutonomousConfig(
    default_max_iterations=15,
    default_max_retries=3,
    enable_error_recovery=True,
    visibility_defaults={
        Role.END_USER: VisibilityLevel.SUMMARY,
        Role.DEVELOPER: VisibilityLevel.FULL,
    }
)
```

**Acceptance Criteria:**
- [ ] Skills can override max_iterations
- [ ] Skills can set max_retries_per_tool
- [ ] Platform admins can set global defaults
- [ ] Configuration validated at skill load time
- [ ] Invalid config provides clear error messages

**Priority:** P2 (Nice to Have)
**Effort:** Small

---

### FR-9: Script Execution Support

**Description:** Skills can bundle and execute scripts (Python, JavaScript, shell) to generate complex outputs

**Problem:**
Skills are limited to built-in tools. They cannot leverage existing libraries (pandas, matplotlib) or generate complex visualizations.

**Solution:**
```
my-skill/
├── SKILL.md
├── scripts/
│   ├── visualize.py      # Python script for data viz
│   ├── analyze.js        # JS script for analysis
│   └── helper.sh         # Shell script for preprocessing
└── templates/
    └── report.html       # HTML template
```

**Usage in SKILL.md:**
```yaml
---
name: data-visualizer
description: Generate interactive data visualizations
allowed-tools: Bash(python:*), Read, Write
---

# Data Visualizer

Generate interactive visualization:

1. Read and validate input data
2. Run visualization script:
   ```bash
   python ${SKILL_DIR}/scripts/visualize.py --input $1 --output viz.html
   ```
3. Script generates self-contained HTML file
4. Open viz.html in browser (automatic)

The visualization includes:
- Interactive charts (zoom, pan)
- Collapsible data tables
- Export to PNG/PDF options
```

**Autonomous Execution Example:**
```python
Iteration 3:
  Thought: "Data validated, now generating visualization"
  Tool: bash(
    command="python /skills/visualizer/scripts/visualize.py data.csv viz.html"
  )
  Result: SUCCESS - Generated viz.html (2.3 MB)
          [Opened in browser automatically]

Iteration 4:
  Thought: "Visualization complete, summarizing results"
  Final Answer: "Created interactive visualization with 5 charts.
                 Open viz.html to explore the data."
```

**Script Capabilities:**
- **Python**: Use pandas, matplotlib, seaborn, plotly for analysis
- **JavaScript**: Generate D3.js visualizations, manipulate JSON
- **Shell**: Preprocess data, call CLI tools, manage files
- **Output**: HTML files, images, JSON reports, PDFs

**Security:**
- Scripts validated at skill load time
- `allowed-tools` must include `Bash(python:*)` or similar
- Scripts run in sandboxed environment (if configured)
- Resource limits enforced (memory, CPU, timeout)

**Acceptance Criteria:**
- [ ] Skills can bundle scripts in `scripts/` directory
- [ ] Agent can execute scripts via Bash tool during iterations
- [ ] `${SKILL_DIR}` variable resolves to skill directory path
- [ ] Scripts can generate HTML/images/JSON outputs
- [ ] Generated HTML files can auto-open in browser
- [ ] Script execution errors trigger retry logic
- [ ] Scripts respect `allowed-tools` permissions
- [ ] Resource limits prevent runaway scripts

**Priority:** P0 (Must Have)
**Effort:** Medium

---

### FR-10: Dynamic Context Injection

**Description:** Skills can inject live command output into their content before execution starts

**Problem:**
Skills need current state (PR diffs, system info, git status) but must use tool calls during execution, wasting iterations.

**Solution - Preprocessing:**
```yaml
---
name: pr-reviewer
description: Review GitHub pull requests
allowed-tools: Bash(gh:*), Read
---

# PR Reviewer

## Current PR State (injected before execution)
- **Diff**: !`gh pr diff`
- **Status Checks**: !`gh pr checks`
- **Comments**: !`gh pr view --comments`
- **Modified Files**: !`gh pr diff --name-only`

## Review Instructions
Analyze the above PR data and provide:
1. Code quality assessment
2. Security concerns
3. Suggested improvements
4. Approval recommendation
```

**Processing Flow:**
```python
# Step 1: Parse SKILL.md for !`command` patterns
skill_content = """
- **Diff**: !`gh pr diff`
- **Status Checks**: !`gh pr checks`
"""

# Step 2: Extract and execute commands
commands = ["gh pr diff", "gh pr checks"]
outputs = {
    "gh pr diff": "[actual 200 lines of diff]",
    "gh pr checks": "✓ All checks passing (5/5)"
}

# Step 3: Replace placeholders
processed_content = """
- **Diff**: [actual 200 lines of diff]
- **Status Checks**: ✓ All checks passing (5/5)
"""

# Step 4: Send processed content to LLM
# Agent sees actual data, not commands!
```

**Benefits:**
- **Faster**: No tool calls needed to fetch context
- **Cheaper**: Data loaded once, not per iteration
- **Richer**: Agent starts with full context
- **Cleaner**: No "Iteration 1: fetch data" overhead

**Examples:**
```yaml
# Git information
!`git log -5 --oneline`
!`git status --short`

# System information
!`uname -a`
!`df -h | head -5`

# Project metrics
!`find . -name "*.py" | wc -l` Python files
!`git log --since="1 week ago" --oneline | wc -l` commits this week
```

**Security:**
- Commands validated against allowed patterns
- Must match `allowed-tools` restrictions
- Timeout per command (default: 5 seconds)
- Output size limited (max 10,000 characters per command)
- Failed commands show error message (don't fail skill)

**Acceptance Criteria:**
- [ ] Parse `` !`command` `` syntax in skill content
- [ ] Execute commands before first iteration
- [ ] Replace placeholders with command output
- [ ] Handle command failures gracefully (show error in content)
- [ ] Validate commands against `allowed-tools`
- [ ] Timeout protection (5 seconds per command)
- [ ] Output size limits (10K chars per command)
- [ ] Cache outputs (don't re-run per iteration)
- [ ] Log all command executions for audit

**Priority:** P0 (Must Have)
**Effort:** Medium

---

### FR-11: String Substitutions & Variables

**Description:** Skills support variable substitution for dynamic content

**Variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `$ARGUMENTS` | All arguments passed when invoking skill | `process data.csv --format json` |
| `${CLAUDE_SESSION_ID}` | Unique session identifier | `session-2026-01-26-abc123` |
| `${SKILL_DIR}` | Absolute path to skill directory | `/home/user/.claude/skills/my-skill` |
| `${WORKSPACE}` | Current working directory | `/home/user/projects/myapp` |
| `${USER}` | Current user name | `alice` |
| `${DATE}` | Current date (YYYY-MM-DD) | `2026-01-26` |

**Usage Examples:**

**1. Session-specific logging:**
```yaml
---
name: session-logger
---

# Session Logger

Log all activity to: ${SKILL_DIR}/logs/${CLAUDE_SESSION_ID}.log

Task details:
$ARGUMENTS

Start time: ${DATE}
```

**2. Parameterized execution:**
```yaml
---
name: file-processor
---

# Process file: $ARGUMENTS

1. Read file from: ${WORKSPACE}/$ARGUMENTS
2. Process data
3. Save output to: ${SKILL_DIR}/output/${DATE}/$ARGUMENTS.processed
```

**3. Script invocation:**
```yaml
---
name: data-analyzer
---

Run analysis:
```bash
python ${SKILL_DIR}/scripts/analyze.py \
  --input "${WORKSPACE}/$ARGUMENTS" \
  --output "${WORKSPACE}/analysis-${DATE}.html" \
  --session ${CLAUDE_SESSION_ID}
```
```

**Substitution Timing:**
- Happens **after** dynamic context injection (`` !`command` ``)
- Happens **before** sending to LLM
- Applies to all skill content (SKILL.md and supporting files)

**Fallback for $ARGUMENTS:**
If skill doesn't include `$ARGUMENTS` but arguments are passed, they're automatically appended:
```
[Skill content]

ARGUMENTS: process data.csv --format json
```

**Acceptance Criteria:**
- [ ] Substitute all defined variables in skill content
- [ ] `$ARGUMENTS` receives invocation arguments
- [ ] `${CLAUDE_SESSION_ID}` generates unique session ID
- [ ] `${SKILL_DIR}` resolves to absolute skill path
- [ ] `${WORKSPACE}` resolves to current working directory
- [ ] `${USER}`, `${DATE}` resolve correctly
- [ ] Undefined variables log warning (don't fail)
- [ ] Auto-append $ARGUMENTS if not in skill content
- [ ] Substitution applies to SKILL.md and supporting files

**Priority:** P1 (Should Have)
**Effort:** Small

---

### FR-12: Model Selection per Skill

**Description:** Skills can specify which LLM model to use for reasoning

**Problem:**
All skills use the same model. Simple skills waste money on expensive models, complex skills limited by default.

**Configuration:**
```yaml
---
name: quick-search
description: Fast file search
model: haiku              # Fast, cheap model
max_iterations: 5
---

---
name: complex-analysis
description: Deep code analysis
model: opus               # Powerful reasoning model
max_iterations: 20
---

---
name: balanced-task
description: Standard processing
model: sonnet             # Default, balanced
---
```

**Supported Models:**
- `haiku` - Fast, low-cost (simple tasks, high iteration count)
- `sonnet` - Balanced (default)
- `opus` - Powerful, expensive (complex reasoning)
- `custom` - Custom model name (future: fine-tuned models)

**Cost Optimization Example:**
```yaml
# Bad: Everything uses expensive model
Default: opus
- quick-search: $0.50 per execution
- file-rename: $0.30 per execution
- data-processor: $1.20 per execution
Total: $2.00 per run

# Good: Right model for each task
- quick-search (haiku): $0.05 per execution
- file-rename (haiku): $0.03 per execution
- data-processor (opus): $1.20 per execution
Total: $1.28 per run (36% savings!)
```

**Acceptance Criteria:**
- [ ] Skills can specify `model` in frontmatter
- [ ] Supported models: haiku, sonnet, opus
- [ ] Falls back to platform default if not specified
- [ ] Model selection logged in execution metrics
- [ ] Cost tracking per model in analytics
- [ ] Model can be overridden at invocation time (admin)

**Priority:** P2 (Nice to Have)
**Effort:** Small

---

## Success Metrics

### Primary Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| **Task Success Rate** | 45% | 85% | % of skill executions that complete successfully |
| **Error Recovery Rate** | 0% | 80% | % of tool failures that are automatically recovered |
| **User Satisfaction** | 3.2/5 | 4.5/5 | Post-execution survey rating |
| **Avg Iterations** | 1.0 | 3-5 | Average iterations per successful execution |

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Execution Time** | <10s for simple tasks | p50 execution duration |
| **Iteration Overhead** | <500ms per iteration | Time spent in reasoning vs. tools |
| **Developer Debug Time** | -50% | Time to understand failure cause |
| **Partial Success Rate** | >60% | Tasks with partial results when complete solution impossible |

### Leading Indicators

- **Week 1**: Autonomous loop executes without crashes
- **Week 2**: Error recovery working for encoding errors
- **Week 3**: Progressive disclosure showing in UI
- **Week 4**: 5+ skills migrated and showing improvement

---

## Technical Considerations

### Integration Points

1. **SkillLoader** - Loads SKILL.md with new metadata fields
2. **ToolExecutor** - Executes tools and returns detailed results
3. **ReasoningEngine** - Manages ReAct loop and visibility
4. **LLMGenerator** - Provides reasoning and planning
5. **EventBus** - Streams events to frontend
6. **VisibilityController** - Filters events by role

### Performance

**Concerns:**
- Each iteration adds LLM call overhead (~500ms)
- 15 iterations = up to 7.5s additional latency

**Mitigations:**
- Use fast models for reasoning (Haiku)
- Cache common reasoning patterns
- Early termination when high confidence
- Parallel tool execution where possible

### Security

**Concerns:**
- Long-running iterations could be abused
- Autonomous retries might hit rate limits
- Sensitive data in reasoning chain

**Mitigations:**
- Max iterations enforced (no infinite loops)
- Rate limiting per skill/user
- Visibility system hides sensitive data
- Audit logging for all executions

---

## Out of Scope (Future Phases)

### Phase 2 (Future)
- **Multi-Skill Coordination**: Skills that coordinate with each other
- **Learning from Past Executions**: Skills improve from previous runs
- **Cost Optimization**: Caching reasoning patterns to reduce LLM calls
- **Advanced Error Recovery**: ML-based failure prediction

### Phase 3 (Future)
- **Skill Composition**: Combine multiple skills into workflows
- **Human-in-the-Loop**: Request user input mid-execution
- **Distributed Execution**: Skills running across multiple workers
- **A/B Testing**: Compare autonomous vs. simple execution

---

## Open Questions

1. **Iteration Budget**: Should max_iterations be per-skill or per-task?
   - **Recommendation**: Per-skill (configurable in SKILL.md)

2. **Cost Management**: How to prevent runaway LLM costs?
   - **Recommendation**: Cost tracking + alerts + per-user budgets

3. **Reasoning Model**: Use same model for reasoning and tool planning?
   - **Recommendation**: Use fast model (Haiku) for reasoning, allow override

4. **Partial Results**: How to communicate partial success to users?
   - **Recommendation**: Final message: "Completed 3 of 5 objectives. See details for limitations."

5. **Sub-Agent Limits**: Should sub-agents have lower iteration budget?
   - **Recommendation**: Yes, 50% of parent's budget (prevent recursion explosion)

---

## Appendix

### References

- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [ReAct Paper: Reasoning and Acting in LLMs](https://arxiv.org/abs/2210.03629)
- OmniForge `autonomous_simple.py` - Existing ReAct implementation
- OmniForge `cot/visibility.py` - Progressive disclosure system

### Glossary

- **ReAct**: Reasoning and Acting pattern (Think → Act → Observe loop)
- **Progressive Context Loading**: Only loading relevant skill files into LLM context when needed (saves context window space)
- **Progressive Disclosure (UI)**: Showing detail incrementally to users based on their role (FULL/SUMMARY/HIDDEN)
- **CoT**: Chain of Thought (reasoning chain with steps)
- **Visibility Level**: FULL, SUMMARY, or HIDDEN
- **Sub-Agent**: Isolated agent execution context
- **Forked Context**: New context without parent conversation history
- **Supporting Files**: Additional skill files (reference.md, examples.md) loaded on-demand

### Example Scenarios

#### Scenario 1: CSV Processing with Encoding Error
```
User: "Process data.csv and create summary report"

Iteration 1:
  Thought: Need to read the CSV file first
  Tool: read(file="data.csv", encoding="utf-8")
  Result: FAILED - UnicodeDecodeError

Iteration 2:
  Thought: UTF-8 encoding failed, trying Latin-1
  Tool: read(file="data.csv", encoding="latin-1")
  Result: SUCCESS - 100 rows loaded

Iteration 3:
  Thought: Data loaded, now validating format
  Tool: bash("csvlint data.csv")
  Result: SUCCESS - Valid CSV

Iterations 4-7:
  [Data transformation and analysis]

Iteration 8:
  Thought: Analysis complete, generating report
  Tool: write(file="summary.txt", content="...")
  Result: SUCCESS

Final Answer: "Processed 100 rows, generated summary.txt"
```

**User Sees (SUMMARY):**
```
✅ File loaded successfully
✅ Data validated (100 rows)
⏳ Analyzing data...
✅ Report generated

📄 summary.txt created
```

#### Scenario 2: Progressive Context Loading Example

**Skill Structure:**
```
.claude/skills/api-integration/
├── SKILL.md              # 450 lines - core instructions
├── reference.md          # 1,200 lines - complete API docs
├── examples.md           # 800 lines - usage examples
└── templates/
    └── response.json     # 300 lines - response template
```

**Without Progressive Loading (❌ Old Approach):**
```python
# Load everything upfront
system_prompt = f"""
{skill_content}           # 450 lines
{reference_content}       # 1,200 lines
{examples_content}        # 800 lines
{template_content}        # 300 lines
"""
# Total: 2,750 lines loaded every iteration
# Cost: ~55K tokens × 15 iterations = 825K tokens
```

**With Progressive Loading (✅ New Approach):**
```python
# Initial load (Iteration 1)
system_prompt = f"""
SKILL INSTRUCTIONS (450 lines):
{skill_content}

SUPPORTING FILES (load on-demand):
- reference.md: Complete API documentation
- examples.md: Integration examples
- templates/response.json: Response format
"""
# Initial: 450 lines = ~9K tokens

# Iteration 4: Agent needs API details
Thought: "I need to understand the authentication format"
Tool: read(file=".claude/skills/api-integration/reference.md")
Result: [API docs loaded - 1,200 lines added to context]

# Iteration 7: Agent needs example
Thought: "Let me see an example of error handling"
Tool: read(file=".claude/skills/api-integration/examples.md")
Result: [Examples loaded - 800 lines added to context]

# Final: 450 + 1,200 + 800 = 2,450 lines (only what was needed)
# Cost: (9K × 3 iterations) + (33K × 12 iterations) = 423K tokens
# Savings: 402K tokens (48% reduction!)
```

**Key Insight:**
- Agent only loads `reference.md` and `examples.md` when it needs them
- Never loads `templates/response.json` (didn't need it for this task)
- Context grows intelligently based on actual needs
- Saves ~48% tokens by not loading everything upfront

---

**End of Specification**
