# TASK-022: Create migration guide documentation

**Priority:** P1 (Should Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-019

---

## Description

Create comprehensive migration guide documentation for existing skill authors to adopt autonomous execution. Document the new features, configuration options, best practices, and step-by-step migration path from legacy to autonomous execution.

## Files to Create

- `docs/guides/autonomous-skill-migration.md` - Main migration guide
- `docs/guides/skill-best-practices.md` - Best practices for autonomous skills

## Documentation Requirements

### Migration Guide Structure

```markdown
# Migrating to Autonomous Skill Execution

## Overview
- What is autonomous skill execution?
- Key benefits (error recovery, progressive loading, etc.)
- Backward compatibility guarantees

## Quick Start
- Minimal changes to enable autonomous execution
- Default behavior (autonomous is now default)

## Step-by-Step Migration

### Step 1: Verify Existing Skill Works
- Test your skill without changes
- Note any issues or failures

### Step 2: Add Autonomous Configuration (Optional)
```yaml
---
name: my-skill
execution-mode: autonomous  # Optional, this is default
max-iterations: 15
---
```

### Step 3: Optimize for Progressive Context Loading
- Keep SKILL.md under 500 lines
- Move detailed documentation to supporting files
- Reference supporting files in SKILL.md

### Step 4: Add Dynamic Context Injection (Optional)
```yaml
---
allowed-tools: [Bash(gh:*)]
---

## Current State
!`gh pr diff`
!`gh pr checks`
```

### Step 5: Configure Model Selection (Optional)
```yaml
---
model: haiku  # Fast, cheap for simple tasks
---
```

## Feature Reference

### Execution Modes
| Mode | Description | When to Use |
|------|-------------|-------------|
| autonomous | Iterative ReAct loop | Default, most skills |
| simple | Single-pass execution | Simple, deterministic tasks |

### Configuration Options
| Field | Default | Description |
|-------|---------|-------------|
| max-iterations | 15 | Maximum ReAct loop iterations |
| max-retries-per-tool | 3 | Retries per failed tool |
| model | sonnet | LLM model (haiku/sonnet/opus) |

### Variable Substitution
| Variable | Description |
|----------|-------------|
| $ARGUMENTS | Invocation arguments |
| ${SKILL_DIR} | Skill directory path |
| ${SESSION_ID} | Unique session ID |

### Dynamic Injection Syntax
```
!`command` - Execute command and inject output
```

## Common Migration Patterns

### Pattern 1: Simple Skill (No Changes Needed)
```yaml
# Before and after - works unchanged
---
name: simple-skill
allowed-tools: [read, write]
---
```

### Pattern 2: Large Skill (Split Content)
```yaml
# Before (won't work - too long)
---
name: api-skill
---
[5000 lines of documentation...]

# After (split into files)
---
name: api-skill
---
Quick reference. See reference.md for full documentation.
```

### Pattern 3: Context-Heavy Skill (Use Injection)
```yaml
# Before (wastes iterations fetching context)
---
name: pr-reviewer
---
1. First, get the PR diff using gh pr diff
2. Then analyze...

# After (context injected before execution)
---
name: pr-reviewer
allowed-tools: [Bash(gh:*)]
---
## PR Data
!`gh pr diff`
!`gh pr checks`

Now analyze the above PR data...
```

## Troubleshooting

### Skill Takes Too Many Iterations
- Reduce scope of task
- Add more specific instructions
- Use progressive loading

### Tool Failures Not Recovering
- Check allowed-tools configuration
- Verify error messages are informative
- Consider adding alternative approaches in instructions

### Token Limit Exceeded
- Keep SKILL.md under 500 lines
- Use progressive loading for large documentation
- Choose smaller model (haiku) for simple tasks

## FAQ

Q: Will my existing skills break?
A: No, existing skills work unchanged with autonomous execution.

Q: How do I opt out of autonomous execution?
A: Add `execution-mode: simple` to your skill metadata.

Q: What's the maximum SKILL.md size?
A: 500 lines. Move additional content to supporting files.
```

### Best Practices Guide Structure

```markdown
# Best Practices for Autonomous Skills

## SKILL.md Structure

### Keep It Concise
- Under 500 lines
- Focus on essential instructions
- Reference supporting files for details

### Clear Task Description
- Explicit goal statement
- Step-by-step approach
- Success criteria

### Error Handling Guidance
- Common failure modes
- Alternative approaches
- Graceful degradation

## Progressive Context Loading

### Organizing Supporting Files
```
my-skill/
├── SKILL.md          # Core instructions (<500 lines)
├── reference.md      # Detailed documentation
├── examples.md       # Usage examples
├── templates/        # Output templates
└── scripts/          # Helper scripts
```

### Referencing Files
```markdown
## Quick Reference
[Summary here]

## When You Need More
- See reference.md for complete API documentation
- See examples.md for usage patterns
```

## Model Selection

### When to Use Haiku
- Simple file operations
- Pattern matching
- Quick searches
- High iteration count tasks

### When to Use Sonnet
- General purpose (default)
- Balanced cost/capability
- Most common choice

### When to Use Opus
- Complex reasoning
- Code analysis
- Multi-step problem solving

## Security Considerations

### Script Execution
- Scripts must be in skill directory
- Use allowed-tools to restrict commands
- Test in sandbox first

### Dynamic Injection
- Only inject trusted commands
- Validate command output
- Avoid sensitive data in injections
```

## Acceptance Criteria

- [ ] Migration guide covers all new features
- [ ] Step-by-step instructions are clear
- [ ] Common patterns documented
- [ ] Troubleshooting section helpful
- [ ] Best practices comprehensive
- [ ] Code examples are correct
- [ ] Documentation follows OmniForge style

## Technical Notes

- Use Markdown format for docs
- Include code examples for all features
- Link to API documentation where appropriate
- Consider adding video tutorials (future)
- Keep language accessible to non-experts
