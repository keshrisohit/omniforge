# Gap Analysis: OmniForge vs Claude Code Skills

**Date:** 2026-01-26
**Reference:** https://code.claude.com/docs/en/skills

---

## Comparison Matrix

| Claude Code Feature | Status | Notes |
|---------------------|--------|-------|
| **Core Execution** | | |
| Autonomous ReAct loop | ✅ Covered | FR-1: Autonomous execution with iterations |
| Error recovery & retry | ✅ Covered | FR-2: 80%+ recovery rate goal |
| Progressive context loading | ✅ Covered | FR-3: Load supporting files on-demand |
| Sub-agent execution (`context: fork`) | ✅ Covered | FR-5: Forked context support |
| Max iterations configuration | ✅ Covered | FR-8: Configurable per skill |
| | | |
| **Skill Configuration (Frontmatter)** | | |
| `name` | ✅ Covered | Existing in OmniForge |
| `description` | ✅ Covered | Existing in OmniForge |
| `allowed-tools` | ✅ Covered | Existing in OmniForge |
| `context: fork` | ✅ Covered | FR-5: Sub-agent execution |
| `agent` (specify agent type) | ✅ Covered | FR-5: Explore, Plan, etc. |
| `model` (LLM model selection) | ❌ Missing | Not in spec |
| `disable-model-invocation` | ⚠️ Partial | Have execution_mode but not exact match |
| `user-invocable` | ❌ Missing | Not in spec |
| `argument-hint` | ❌ Missing | Not in spec |
| `hooks` | ❌ Missing | Not in spec |
| | | |
| **String Substitutions** | | |
| `$ARGUMENTS` | ❌ Missing | Not in spec |
| `${CLAUDE_SESSION_ID}` | ❌ Missing | Not in spec |
| | | |
| **Dynamic Context Injection** | | |
| `` !`command` `` syntax | ❌ Missing | **Critical: Not in spec** |
| Pre-execution command output | ❌ Missing | Example: `` !`gh pr diff` `` |
| | | |
| **Script Execution** | | |
| Bundle scripts in skill directory | ⚠️ Mentioned | Scripts/ folder shown but no execution spec |
| Execute Python/JS/shell scripts | ❌ Missing | **Critical: Not in spec** |
| Generate visual output (HTML) | ❌ Missing | **Critical: Not in spec** |
| Scripts as supporting files | ⚠️ Mentioned | Listed but not executable |
| | | |
| **Progressive Disclosure (UI)** | | |
| FULL/SUMMARY/HIDDEN levels | ✅ Covered | FR-4: User-facing disclosure |
| Role-based filtering | ✅ Covered | FR-4: END_USER, DEVELOPER, ADMIN |
| Tool-type rules | ✅ Covered | FR-4: Hide DATABASE, etc. |
| | | |
| **Other Features** | | |
| Supporting files structure | ✅ Covered | FR-3: reference.md, examples.md |
| Streaming events | ✅ Covered | FR-7: TaskEvent system |
| Backward compatibility | ✅ Covered | FR-6: Legacy skills work |
| Configuration & tuning | ✅ Covered | FR-8: Per-skill and platform-level |

---

## Critical Missing Features

### 1. Script Execution ⚠️ **HIGH PRIORITY**

**Claude Code Capability:**
```yaml
# SKILL.md
---
name: codebase-visualizer
description: Generate interactive HTML visualization
allowed-tools: Bash(python:*)
---

Run the visualization script:
```bash
python ~/.claude/skills/codebase-visualizer/scripts/visualize.py .
```

This creates `codebase-map.html` and opens it in your browser.
```

**What's Missing in Spec:**
- No mention of how skills execute bundled scripts
- Scripts listed in file structure but marked "not loaded (executed directly)"
- No mechanism for agent to run Python/JS/shell scripts from skill directory

**Impact:**
- Skills cannot generate complex outputs (visualizations, reports)
- Cannot leverage existing tools/libraries (pandas, matplotlib, etc.)
- Limited to built-in tools only

**Recommendation:** Add FR-9: Script Execution Support

---

### 2. Dynamic Context Injection ⚠️ **HIGH PRIORITY**

**Claude Code Capability:**
```yaml
# SKILL.md
---
name: pr-summary
description: Summarize GitHub PR
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

**What happens:**
1. Commands execute **before** skill content sent to LLM
2. Output replaces the `` !`command` `` placeholder
3. LLM receives actual PR data, not the command

**What's Missing in Spec:**
- No support for `` !`command` `` syntax
- No pre-processing of skill content before execution
- Agent would see the command text, not the output

**Impact:**
- Skills cannot inject live data (git diffs, PR info, system state)
- Must use tool calls during execution (slower, more iterations)
- Cannot provide up-to-date context in initial prompt

**Recommendation:** Add FR-10: Dynamic Context Injection

---

### 3. String Substitutions ⚠️ **MEDIUM PRIORITY**

**Claude Code Capability:**
```yaml
# SKILL.md
---
name: session-logger
---

Log to logs/${CLAUDE_SESSION_ID}.log:

$ARGUMENTS
```

**Substitutions:**
- `$ARGUMENTS` - All arguments passed to skill
- `${CLAUDE_SESSION_ID}` - Current session ID

**What's Missing in Spec:**
- No mention of variable substitution
- No mechanism to pass arguments to skills
- No session tracking in skill context

**Impact:**
- Skills cannot be parameterized easily
- Cannot create session-specific files/logs
- Less flexible skill invocation

**Recommendation:** Add to FR-8 (Configuration & Tuning)

---

### 4. Visual Output Generation ⚠️ **MEDIUM PRIORITY**

**Claude Code Example:**
Skills can generate HTML files with interactive visualizations:
- Codebase explorer (collapsible tree)
- Dependency graphs
- Test coverage reports
- Database schema visualizations

**What's Missing in Spec:**
- No mention of generating non-text outputs
- No support for opening files in browser
- Limited to text-based results

**Impact:**
- Skills cannot create rich, interactive outputs
- Harder to visualize complex data
- Less engaging user experience

**Recommendation:** Add to FR-9 (Script Execution) as output format

---

### 5. Skill-Specific Hooks ⚠️ **LOW PRIORITY**

**Claude Code Capability:**
```yaml
# SKILL.md
---
name: auto-commit
hooks:
  after-tool:
    - tool: Write
      command: git add $FILE_PATH
---
```

**What's Missing in Spec:**
- No lifecycle hooks for skills
- Cannot trigger actions after tool execution
- No event-driven automation

**Impact:**
- Skills cannot automate follow-up actions
- Manual orchestration required
- Less autonomous behavior

**Recommendation:** Phase 2 (Future)

---

### 6. Model Selection per Skill ⚠️ **LOW PRIORITY**

**Claude Code Capability:**
```yaml
---
name: fast-search
model: haiku  # Use fast model
---

---
name: deep-analysis
model: opus   # Use powerful model
---
```

**What's Missing in Spec:**
- All skills use same model
- No per-skill model configuration

**Impact:**
- Cannot optimize cost/speed per skill
- Simple skills pay for expensive model
- Complex skills limited by default model

**Recommendation:** Add to FR-8 (Configuration)

---

## Recommended Additions to Spec

### FR-9: Script Execution Support

**Description:** Skills can bundle and execute scripts (Python, JS, shell) to generate complex outputs

**Behavior:**
```yaml
# SKILL.md
---
name: data-visualizer
allowed-tools: Bash(python:*), Read, Write
---

Generate visualization:
1. Prepare data file
2. Run visualization script:
   `python $SKILL_DIR/scripts/visualize.py --input data.csv --output viz.html`
3. Open viz.html in browser
```

**Script Execution:**
```python
# During autonomous execution
Iteration 5:
  Thought: "Need to generate interactive visualization"
  Tool: bash(command="python /skills/visualizer/scripts/gen.py data.csv")
  Result: Generated viz.html (opened in browser)
```

**Acceptance Criteria:**
- [ ] Skills can bundle Python/JS/shell scripts in `scripts/` directory
- [ ] Agent can execute scripts via Bash tool
- [ ] `$SKILL_DIR` variable resolves to skill directory path
- [ ] Scripts can generate HTML/images/other outputs
- [ ] Generated files can be opened in browser (via tool or auto-open)
- [ ] Script errors handled gracefully (retry logic applies)

---

### FR-10: Dynamic Context Injection

**Description:** Skills can inject command output into their content before execution

**Syntax:**
```yaml
# SKILL.md
---
name: pr-reviewer
---

## Current PR State
- Diff: !`gh pr diff`
- Status checks: !`gh pr checks`
- Modified files: !`gh pr diff --name-only | wc -l` files changed

## Review Task
Analyze the above changes and provide feedback.
```

**Processing:**
```python
# Before skill execution
1. Parse SKILL.md for !`command` patterns
2. Execute each command and capture output
3. Replace !`command` with actual output
4. Send processed content to LLM

# Example result:
## Current PR State
- Diff: [actual 200 lines of diff]
- Status checks: All checks passing ✓
- Modified files: 5 files changed

## Review Task
Analyze the above changes and provide feedback.
```

**Acceptance Criteria:**
- [ ] Parse `` !`command` `` syntax in SKILL.md
- [ ] Execute commands before skill starts
- [ ] Replace placeholders with command output
- [ ] Handle command failures gracefully
- [ ] Security: Validate commands against allowed patterns
- [ ] Cache command outputs (don't re-run per iteration)

---

### FR-11: String Substitutions (Add to FR-8)

**Variables:**
- `$ARGUMENTS` - All arguments passed when invoking skill
- `${CLAUDE_SESSION_ID}` - Unique session identifier
- `${SKILL_DIR}` - Path to skill directory
- `${WORKSPACE}` - Current working directory

**Usage:**
```yaml
---
name: session-logger
---

Log activity to: ${SKILL_DIR}/logs/${CLAUDE_SESSION_ID}.log

Task details:
$ARGUMENTS
```

**Acceptance Criteria:**
- [ ] Substitute `$ARGUMENTS` with invocation arguments
- [ ] Substitute `${CLAUDE_SESSION_ID}` with session ID
- [ ] Substitute `${SKILL_DIR}` with skill directory path
- [ ] Substitute `${WORKSPACE}` with working directory
- [ ] Substitution happens before skill execution
- [ ] Undefined variables log warning (don't fail)

---

### FR-12: Model Selection (Add to FR-8)

**Configuration:**
```yaml
---
name: quick-search
model: haiku  # Fast, cheap model for simple tasks
---

---
name: complex-analysis
model: opus   # Powerful model for reasoning
---
```

**Acceptance Criteria:**
- [ ] Skills can specify `model` in frontmatter
- [ ] Supported models: haiku, sonnet, opus
- [ ] Falls back to platform default if not specified
- [ ] Model selection logged in metrics
- [ ] Cost tracking per model

---

## Updated Priority Matrix

| Feature | Priority | Effort | Impact | Phase |
|---------|----------|--------|--------|-------|
| FR-9: Script Execution | P0 | Large | High | Phase 1 |
| FR-10: Dynamic Context Injection | P0 | Medium | High | Phase 1 |
| FR-11: String Substitutions | P1 | Small | Medium | Phase 1 |
| FR-12: Model Selection | P2 | Small | Medium | Phase 1 |
| Skill-specific Hooks | P3 | Medium | Low | Phase 2 |
| `user-invocable` control | P3 | Small | Low | Phase 2 |
| `argument-hint` | P3 | Small | Low | Phase 2 |

---

## Recommendation

**Update the specification with:**
1. ✅ Keep all existing FRs (FR-1 through FR-8)
2. ➕ Add FR-9: Script Execution Support (P0)
3. ➕ Add FR-10: Dynamic Context Injection (P0)
4. ➕ Extend FR-8 with String Substitutions (P1)
5. ➕ Extend FR-8 with Model Selection (P2)

This brings OmniForge skills to **95% feature parity** with Claude Code skills, with only minor UX features deferred to Phase 2.

---

**End of Gap Analysis**
