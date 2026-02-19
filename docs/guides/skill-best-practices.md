# Best Practices for Autonomous Skills

This guide provides recommendations for creating high-quality, efficient, and maintainable autonomous skills in OmniForge.

## SKILL.md Structure

### Keep It Concise

**Rule of thumb: Under 500 lines**

Why?
- Reduces token usage and cost
- Faster initial loading
- Easier to maintain
- Prevents context length errors

**Example - Concise skill:**
```yaml
---
name: test-runner
description: Runs Python tests and reports results
allowed-tools: [bash, read]
model: haiku
---

# Test Runner

Run Python tests using pytest and analyze results.

## Process
1. Find test files using pattern: test_*.py or *_test.py
2. Run: pytest --verbose --tb=short
3. Analyze output and report:
   - Total tests passed/failed
   - Failed test details
   - Recommendations

## Tips
- Use -v for verbose output
- Use --tb=short for concise tracebacks
- Check exit code: 0 = success, 1 = failures
```

This skill is clear, focused, and well under 500 lines.

### Clear Task Description

Every skill should have:

1. **Explicit goal** - What the skill accomplishes
2. **Step-by-step approach** - How to achieve the goal
3. **Success criteria** - When the task is complete

**Example - Clear structure:**
```yaml
---
name: code-formatter
---

# Code Formatter

**Goal**: Format Python code files according to PEP 8 standards.

## Approach

1. **Find files**: Use glob to find all .py files
2. **Format**: Run black on each file
3. **Verify**: Check black exit code
4. **Report**: List formatted files and any errors

## Success Criteria

- All .py files formatted successfully
- No black errors reported
- Summary of changes provided
```

### Error Handling Guidance

Help the agent recover from errors by providing:

**1. Common failure modes:**
```yaml
## Common Issues

- **Black not installed**: Try pip install black first
- **File permissions**: Check if files are writable
- **Syntax errors**: Report which files have invalid Python
```

**2. Alternative approaches:**
```yaml
## Alternatives

If black fails:
1. Try autopep8 instead
2. If that fails, report files that need manual formatting
```

**3. Graceful degradation:**
```yaml
## Partial Success

If some files fail:
- Format the files that work
- Report which files failed and why
- Continue with remaining files
```

**Complete example:**
```yaml
---
name: dependency-updater
allowed-tools: [bash, read, write]
max-retries-per-tool: 5
---

# Dependency Updater

Update Python package dependencies to latest versions.

## Process

1. Read requirements.txt
2. Check latest versions: pip index versions <package>
3. Update requirements.txt with new versions
4. Verify: pip install --dry-run -r requirements.txt

## Error Handling

**Common Issues:**
- Package not found: Skip and note in report
- Version conflicts: Keep current version, note conflict
- Network issues: Retry up to 5 times (configured above)

**Alternatives:**
- If pip index fails, try: pip search <package>
- If all network calls fail, report packages that need checking
- Always create backup: requirements.txt.backup

**Graceful Degradation:**
- Update packages that work
- Skip problematic packages
- Report summary of updated vs skipped packages
```

## Progressive Context Loading

### Organizing Supporting Files

**Recommended structure:**

```
my-skill/
├── SKILL.md              # Core instructions (<500 lines)
├── reference.md          # Detailed API/spec documentation
├── examples.md           # Usage examples and patterns
├── templates/            # Output templates
│   ├── report.md
│   └── summary.md
├── schemas/              # Data schemas (JSON, YAML)
│   ├── input.json
│   └── output.json
└── scripts/              # Helper scripts (if needed)
    └── helper.sh
```

**File organization principles:**

1. **SKILL.md** - Only essential instructions
2. **reference.md** - Comprehensive technical details
3. **examples.md** - Real-world usage examples
4. **templates/** - Reusable output formats
5. **schemas/** - Structured data definitions
6. **scripts/** - Executable helpers

### Referencing Supporting Files

**In SKILL.md, reference supporting files clearly:**

```yaml
---
name: api-documenter
---

# API Documenter

Create comprehensive API documentation.

## Quick Start

1. Read the OpenAPI specification
2. Generate documentation for each endpoint
3. Use the templates in templates/ for consistent formatting

## Need More Info?

- **OpenAPI spec details**: Read `reference.md`
- **Example outputs**: Read `examples.md`
- **Templates**: Read files in `templates/`
- **Response schemas**: Read files in `schemas/`

## Process

[Core instructions here...]
```

**Benefits:**
- Agent knows where to find information
- Files loaded only when needed
- Clear separation of concerns
- Easy to maintain and update

### When to Use Progressive Loading

**Use progressive loading when:**

- Total documentation exceeds 500 lines
- Different tasks need different reference materials
- Supporting data is large (schemas, examples, templates)
- Multiple variations of similar processes exist

**Example - API documentation skill:**

Instead of embedding all this in SKILL.md:
- OpenAPI 3.0 spec (200 lines)
- Example API responses (150 lines)
- Documentation templates (100 lines)
- Common patterns (100 lines)

Split into:
- SKILL.md (50 lines) - Core process
- reference.md (200 lines) - OpenAPI spec
- examples.md (150 lines) - API examples
- templates/ (100 lines) - Templates
- patterns.md (100 lines) - Common patterns

Agent loads reference.md only when it needs OpenAPI details.

## Dynamic Context Injection

### When to Use Injection

Use dynamic injection (`!`command``) when:

1. **Current state matters** - Git status, PR diffs, system state
2. **Context is expensive to fetch** - Large command outputs
3. **Data changes frequently** - Real-time information
4. **Multiple related commands** - Batch context gathering

**Good candidates for injection:**
- `git status`, `git log`, `git diff`
- `gh pr view`, `gh pr checks`, `gh pr diff`
- `kubectl get pods`, `kubectl get services`
- `ls -la`, `find`, `du -sh`
- `cat config.json`, `cat .env.example`

**Poor candidates (don't inject):**
- Simple deterministic data
- Data already in arguments
- Data that doesn't change
- Very large outputs (>10K lines)

### Injection Best Practices

**1. Group related injections:**

```yaml
## Current State

### Git Status
!`git status --short`

### Recent Commits
!`git log --oneline -10`

### Current Branch
!`git branch --show-current`
```

**2. Use concise commands:**

```yaml
# Good - Concise output
!`git log --oneline -20`

# Bad - Too verbose
!`git log -20`
```

**3. Add context headers:**

```yaml
## Pull Request Information

**Title and Description:**
!`gh pr view --json title,body,number`

**Changed Files:**
!`gh pr diff --name-only`

**CI Status:**
!`gh pr checks`
```

**4. Handle failures gracefully:**

```yaml
## Docker Status

**Running Containers:**
!`docker ps --format "table {{.Names}}\t{{.Status}}"`

Note: If docker is not running, this will show an error.
Proceed without Docker context if needed.
```

### Injection Security

**Important security considerations:**

1. **Only inject trusted commands** - Never inject user input directly
2. **Use allowed-tools restrictions** - Limit command scope
3. **Validate command safety** - Review before injection
4. **Avoid sensitive data** - Don't inject secrets, tokens, passwords

**Example - Safe injection with restrictions:**

```yaml
---
name: pr-reviewer
allowed-tools: [Bash(gh:*)]  # Only allow gh commands
---

## PR Data
!`gh pr diff`        # Safe - gh command
!`gh pr checks`      # Safe - gh command

# !`cat ~/.ssh/id_rsa`  # BLOCKED - not a gh command
```

**Example - Unsafe (don't do this):**

```yaml
# BAD - User input in command
!`git log -n $ARGUMENTS`  # Dangerous if $ARGUMENTS = "10; rm -rf /"

# GOOD - Validate input first
# In instructions: Parse $ARGUMENTS safely, validate it's a number
```

## Model Selection

### When to Use Haiku

**Characteristics:**
- Fastest execution
- Lowest cost
- Basic reasoning capability
- Best for high-volume, simple tasks

**Ideal use cases:**

1. **File operations**
   ```yaml
   ---
   name: file-organizer
   model: haiku
   ---
   ```
   - Moving files
   - Renaming files
   - Simple filtering
   - Directory cleanup

2. **Pattern matching**
   ```yaml
   ---
   name: log-filter
   model: haiku
   ---
   ```
   - Text search
   - Regex matching
   - Simple parsing
   - Data extraction

3. **Template expansion**
   ```yaml
   ---
   name: template-renderer
   model: haiku
   ---
   ```
   - Variable substitution
   - Format conversion
   - Simple transformations

4. **Quick searches**
   ```yaml
   ---
   name: file-finder
   model: haiku
   ---
   ```
   - Finding files
   - Counting matches
   - Basic statistics

**When NOT to use Haiku:**
- Complex reasoning needed
- Code analysis required
- Multi-step problem solving
- Nuanced decision-making

### When to Use Sonnet

**Characteristics:**
- Balanced speed and capability
- Moderate cost
- Strong reasoning ability
- Default choice for most skills

**Ideal use cases:**

1. **Code reviews**
   ```yaml
   ---
   name: code-reviewer
   model: sonnet
   ---
   ```

2. **Documentation generation**
   ```yaml
   ---
   name: doc-generator
   model: sonnet
   ---
   ```

3. **Data analysis**
   ```yaml
   ---
   name: data-analyzer
   model: sonnet
   ---
   ```

4. **Test writing**
   ```yaml
   ---
   name: test-generator
   model: sonnet
   ---
   ```

5. **Bug investigation**
   ```yaml
   ---
   name: bug-investigator
   model: sonnet
   ---
   ```

**Use Sonnet when:**
- Moderate complexity
- General-purpose task
- Balance of speed and quality needed
- Not sure which model to choose (default)

### When to Use Opus

**Characteristics:**
- Strongest reasoning
- Highest cost
- Slower execution
- Best for complex tasks

**Ideal use cases:**

1. **Architecture design**
   ```yaml
   ---
   name: architecture-designer
   model: opus
   ---
   ```

2. **Complex refactoring**
   ```yaml
   ---
   name: refactoring-planner
   model: opus
   ---
   ```

3. **Multi-file analysis**
   ```yaml
   ---
   name: codebase-analyzer
   model: opus
   max-iterations: 30
   ---
   ```

4. **Strategic planning**
   ```yaml
   ---
   name: tech-debt-planner
   model: opus
   ---
   ```

5. **Advanced debugging**
   ```yaml
   ---
   name: memory-leak-detective
   model: opus
   max-iterations: 25
   ---
   ```

**Use Opus when:**
- Complex reasoning required
- Multi-step analysis needed
- High-stakes decisions
- Quality more important than speed/cost

### Model Selection Decision Tree

```
Is the task simple and deterministic?
├─ Yes → Use Haiku
└─ No → Does it require deep reasoning?
    ├─ Yes → Use Opus
    └─ No → Use Sonnet (default)
```

## Configuration Best Practices

### Max Iterations

**Default: 15**

**When to increase:**
- Complex multi-step tasks
- Many files to process
- Exploratory tasks (searching, analyzing)

**When to decrease:**
- Simple, focused tasks
- To enforce efficiency
- Testing and debugging

**Examples:**

```yaml
# Simple task - Low iterations
---
name: file-counter
max-iterations: 5
model: haiku
---

# Complex task - High iterations
---
name: codebase-refactor
max-iterations: 30
model: opus
---

# Balanced task - Default
---
name: doc-generator
# max-iterations: 15 (default, omitted)
model: sonnet
---
```

### Max Retries Per Tool

**Default: 3**

**When to increase:**
- Network operations (API calls)
- Flaky commands (timing-dependent)
- External service integrations

**When to decrease:**
- Deterministic operations
- Fast-failing scenarios
- Testing

**Examples:**

```yaml
# Network operations - More retries
---
name: api-client
max-retries-per-tool: 5
---

# File operations - Default retries
---
name: file-processor
# max-retries-per-tool: 3 (default)
---

# Fast failing - Fewer retries
---
name: syntax-checker
max-retries-per-tool: 1
---
```

### Allowed Tools

**Principle: Grant minimum necessary permissions**

**Examples:**

```yaml
# Restrictive - Only read and glob
---
name: file-finder
allowed-tools:
  - read
  - glob
---

# Moderate - Common tool set
---
name: code-reviewer
allowed-tools:
  - read
  - grep
  - bash
---

# Specific restrictions - Only gh commands
---
name: pr-manager
allowed-tools:
  - read
  - write
  - Bash(gh:*)  # Only gh CLI commands
---

# Permissive - All tools (be careful)
---
name: system-admin
allowed-tools:
  - read
  - write
  - bash
  - grep
  - glob
  - llm
---
```

**Tool restriction patterns:**

```yaml
# Git commands only
allowed-tools: [Bash(git:*)]

# Read-only operations
allowed-tools: [read, grep, glob]

# No destructive operations
allowed-tools: [read, bash]  # Avoid write

# Everything except write
allowed-tools: [read, bash, grep, glob, llm]
```

## Security Considerations

### Script Execution

**Rule: Scripts must be in the skill directory**

```yaml
---
name: data-processor
allowed-tools:
  - bash
  - read
---

# Script location: ${SKILL_DIR}/scripts/process.sh

## Process Data

Run the processing script:
```bash
bash ${SKILL_DIR}/scripts/process.sh input.csv
```
```

**Security best practices:**

1. **Use absolute paths with ${SKILL_DIR}**
   ```yaml
   # Good
   bash ${SKILL_DIR}/scripts/helper.sh

   # Bad - Relative path could be manipulated
   bash scripts/helper.sh
   ```

2. **Validate script inputs**
   ```yaml
   ## Run Script

   Validate that $ARGUMENTS contains only alphanumeric characters.
   Then run: bash ${SKILL_DIR}/process.sh "$ARGUMENTS"
   ```

3. **Restrict bash commands**
   ```yaml
   ---
   allowed-tools: [Bash(python3:*, pip:*)]
   ---
   # Only python3 and pip commands allowed
   ```

4. **Review scripts before deployment**
   - Check for unsafe operations
   - Validate input handling
   - Test in sandbox environment

### Dynamic Injection Security

**Rule: Only inject trusted commands**

**Safe injections:**

```yaml
# Safe - Fixed commands
!`git status --short`
!`gh pr view --json title,body`
!`cat ${SKILL_DIR}/config.json`
```

**Unsafe injections:**

```yaml
# UNSAFE - User input in command
!`git log -n $ARGUMENTS`  # Can be exploited

# UNSAFE - Arbitrary command
!`$USER_COMMAND`  # Never do this

# UNSAFE - Sensitive data
!`cat ~/.ssh/id_rsa`  # Don't expose secrets
```

**How to handle user input safely:**

```yaml
# Instead of injecting user input:
# !`some-command $ARGUMENTS`  # DON'T

# Do this:
Parse $ARGUMENTS, validate it's safe, then use in command.
Example: If $ARGUMENTS should be a number, verify it contains only digits.
```

### Sensitive Data Protection

**Never:**
- Inject secrets, tokens, API keys
- Read credential files
- Execute commands that expose sensitive data
- Store sensitive data in skill files

**Example - Safe credential handling:**

```yaml
---
name: api-caller
---

# API Caller

Call external API with credentials.

## Important

API credentials should be in environment variables:
- API_KEY (never hardcode)
- API_SECRET (never hardcode)

Use environment variables in bash:
```bash
curl -H "Authorization: Bearer $API_KEY" api.example.com
```

Never log or display credentials.
```

## Testing Best Practices

### Test Your Skill

**Before deploying, test:**

1. **Happy path** - Normal successful execution
2. **Error cases** - Tool failures, missing files
3. **Edge cases** - Empty input, large input, special characters
4. **Resource limits** - Max iterations, token limits

**Example test checklist:**

```markdown
## Test Checklist for "code-formatter" skill

- [ ] Happy path: Format single Python file
- [ ] Multiple files: Format directory with multiple .py files
- [ ] No files: Handle directory with no Python files
- [ ] Syntax error: Handle file with invalid Python
- [ ] Permission error: Handle read-only file
- [ ] Black not installed: Handle missing black
- [ ] Large file: Format file with 10,000+ lines
- [ ] Max iterations: Verify completes within iteration limit
```

### Iteration Monitoring

**Track iteration usage during testing:**

```yaml
# During testing
max-iterations: 15

# If skill consistently uses 12-14 iterations:
# - Either increase limit or optimize skill
# - If using 3-5 iterations, consider reducing limit
```

**Optimization tips:**

1. **High iteration usage (10+)**
   - Add dynamic context injection
   - Provide more specific instructions
   - Reduce scope
   - Split into multiple skills

2. **Low iteration usage (2-3)**
   - Consider simple mode
   - Reduce max-iterations
   - Use cheaper model (haiku)

### Error Recovery Testing

**Test error recovery:**

```yaml
# Create failure scenario
# Example: Remove required tool

# Before
allowed-tools: [bash, read, write]

# Test without write
allowed-tools: [bash, read]  # Remove write

# Verify:
# - Does skill detect missing tool?
# - Does it try alternatives?
# - Does it fail gracefully?
```

**Good error recovery example:**

```yaml
---
name: file-writer
allowed-tools: [read, write, bash]
max-retries-per-tool: 3
---

# File Writer

Write content to file.

## Process

1. Try: Use write tool directly
2. If write fails: Try bash echo > file
3. If that fails: Report error and suggest manual write

Always verify write succeeded by reading back file.
```

## Optimization Strategies

### Reduce Token Usage

**Strategies:**

1. **Shorter SKILL.md** (<500 lines)
2. **Smaller model** (haiku for simple tasks)
3. **Progressive loading** (supporting files)
4. **Concise injections** (limit output with flags)

**Example - Concise injection:**

```yaml
# Verbose
!`git log`

# Concise
!`git log --oneline -20`

# Even more concise
!`git log --oneline -10 --format="%h %s"`
```

### Reduce Execution Time

**Strategies:**

1. **Lower max-iterations** (force efficiency)
2. **Faster model** (haiku vs sonnet)
3. **Context injection** (avoid fetch loops)
4. **Specific instructions** (less exploration)

**Example - Fast execution:**

```yaml
---
name: quick-search
model: haiku          # Fast model
max-iterations: 5     # Low limit
---

# Quick Search

Find files matching pattern: $ARGUMENTS

Use glob with pattern, return first 10 matches.
```

### Reduce Cost

**Strategies:**

1. **Use haiku** (cheapest model)
2. **Reduce iterations** (fewer LLM calls)
3. **Inject context** (avoid redundant fetches)
4. **Simple mode** (single LLM call)

**Example - Cost optimized:**

```yaml
---
name: file-organizer
model: haiku              # Cheap
max-iterations: 5         # Few iterations
execution-mode: simple    # Single call (if possible)
---
```

## Common Pitfalls

### Pitfall 1: Too Broad Scope

**Problem:**
```yaml
---
name: codebase-improver
---

Improve the entire codebase: fix bugs, add tests, refactor, update docs.
```

**Why it's bad:**
- Too many tasks
- Unclear success criteria
- Will hit iteration limits
- Difficult to test

**Solution - Focused skills:**

```yaml
# Create separate skills:

---
name: bug-fixer
---
Find and fix bugs in Python files.

---
name: test-generator
---
Generate unit tests for Python functions.

---
name: refactorer
---
Refactor Python code for readability.

---
name: doc-generator
---
Generate docstrings for Python functions.
```

### Pitfall 2: Vague Instructions

**Problem:**
```yaml
---
name: analyzer
---

Analyze the code and tell me what you find.
```

**Why it's bad:**
- No specific goal
- Agent will explore aimlessly
- Wastes iterations
- Unpredictable results

**Solution - Specific instructions:**

```yaml
---
name: security-analyzer
---

# Security Analyzer

Analyze Python code for security vulnerabilities.

## Check For

1. **SQL Injection**: Direct SQL string concatenation
2. **XSS**: Unescaped user input in HTML
3. **Command Injection**: User input in subprocess/os.system
4. **Path Traversal**: Unvalidated file paths
5. **Hardcoded Secrets**: API keys, passwords in code

## Process

1. Use glob to find all .py files
2. Read each file
3. Search for patterns above
4. Report findings with file:line:issue format

## Output

List each vulnerability found with:
- File path
- Line number
- Vulnerability type
- Suggested fix
```

### Pitfall 3: Missing Error Handling

**Problem:**
```yaml
---
name: deployer
---

Deploy the application:
1. Run tests
2. Build Docker image
3. Push to registry
4. Deploy to production
```

**Why it's bad:**
- No handling for failures
- No fallback options
- Could deploy broken code
- Unclear what to do on error

**Solution - Explicit error handling:**

```yaml
---
name: deployer
allowed-tools: [bash, read]
max-retries-per-tool: 3
---

# Deployer

Deploy application with safety checks.

## Process

1. **Run Tests**
   - Command: pytest
   - If fails: STOP, report test failures
   - If passes: Continue

2. **Build Docker Image**
   - Command: docker build -t app:latest .
   - If fails: Check Dockerfile, report error
   - If passes: Continue

3. **Run Security Scan**
   - Command: docker scan app:latest
   - If critical issues: STOP, report
   - If passes: Continue

4. **Push to Registry**
   - Command: docker push app:latest
   - Retry up to 3 times on network errors
   - If fails: Report error, DO NOT deploy

5. **Deploy to Production**
   - Only if ALL above steps passed
   - Command: kubectl apply -f deploy.yaml
   - Verify: kubectl rollout status

## Error Recovery

- Test failures: Fix tests before deploy
- Build failures: Check Dockerfile syntax
- Network errors: Retry automatically
- ANY failure: Do NOT proceed to next step
```

### Pitfall 4: Ignoring Token Limits

**Problem:**
```yaml
---
name: api-documenter
---

[3000 lines of OpenAPI specification, examples, templates...]
```

**Why it's bad:**
- Exceeds token limits
- Slow initial load
- High cost
- May fail on large contexts

**Solution - Progressive loading:**

See [Progressive Context Loading](#progressive-context-loading) section above.

### Pitfall 5: Wrong Model Choice

**Problem:**
```yaml
# Using opus for simple task
---
name: file-counter
model: opus
---
Count Python files in directory.

# Using haiku for complex task
---
name: architecture-designer
model: haiku
---
Design microservices architecture for e-commerce platform.
```

**Why it's bad:**
- Opus: Expensive and slow for simple counting
- Haiku: Insufficient reasoning for architecture design

**Solution - Match model to complexity:**

```yaml
# Simple task - Haiku
---
name: file-counter
model: haiku
---

# Complex task - Opus
---
name: architecture-designer
model: opus
max-iterations: 25
---
```

## Summary Checklist

Use this checklist when creating or reviewing skills:

### Structure
- [ ] SKILL.md under 500 lines
- [ ] Clear goal and process defined
- [ ] Success criteria specified
- [ ] Supporting files organized logically

### Configuration
- [ ] Appropriate model selected (haiku/sonnet/opus)
- [ ] Max iterations set appropriately
- [ ] Allowed tools minimal but sufficient
- [ ] Retries configured for flaky operations

### Instructions
- [ ] Specific, actionable instructions
- [ ] Error handling guidance provided
- [ ] Alternative approaches documented
- [ ] Examples included where helpful

### Security
- [ ] Scripts in ${SKILL_DIR} only
- [ ] No sensitive data in injections
- [ ] Input validation described
- [ ] Tool restrictions appropriate

### Testing
- [ ] Happy path tested
- [ ] Error cases tested
- [ ] Edge cases considered
- [ ] Iteration count reasonable

### Optimization
- [ ] Context injected where beneficial
- [ ] Progressive loading used for large docs
- [ ] Token usage minimized
- [ ] Execution time reasonable

## Additional Resources

- [Migration Guide](autonomous-skill-migration.md) - How to migrate existing skills
- [Autonomous Execution Architecture](../architecture/autonomous-execution.md) - Technical details
- [Tool Reference](../tools/tool-reference.md) - Available tools documentation
- [Security Guide](../security/skills-security.md) - Security best practices

---

**Questions or feedback?** Open an issue on GitHub or reach out in the community forum.
