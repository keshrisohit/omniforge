# OmniForge Skills Directory

This directory contains agent skills that extend OmniForge capabilities. Skills are loaded by the Skills System and made available to agents through the SkillTool.

## What are Skills?

Skills are reusable capabilities that agents can invoke to perform specialized tasks. Each skill is:
- **Self-contained** - Includes all necessary scripts, documentation, and dependencies
- **Tool-based** - Uses tools (Bash, Read, Write, etc.) to accomplish tasks
- **Well-documented** - Provides clear instructions in SKILL.md
- **Progressive** - Loads metadata first, full content on-demand

## Directory Structure

```
.claude/skills/
├── README.md                    # This file
├── pdf-generator/               # Example skill
│   ├── SKILL.md                # Main skill documentation (required)
│   ├── scripts/                # Executable scripts (optional)
│   │   └── generate_pdf.py     # PDF generation script
│   ├── reference.md            # Reference documentation (optional)
│   └── examples.md             # Usage examples (optional)
└── [other-skills]/             # Additional skills...
```

## SKILL.md Format

Every skill must have a `SKILL.md` file with YAML frontmatter:

```yaml
---
name: skill-name                 # Kebab-case identifier (required)
description: Short description   # One-line summary (required)
allowed-tools:                   # Tools this skill can use (optional)
  - Bash
  - Read
  - Write
model: claude-opus-4-5-20251101  # Preferred LLM (optional)
context: inherit                 # Context mode: inherit or fork (optional)
priority: 0                      # Override priority (optional)
tags:                           # Categorization tags (optional)
  - category1
  - category2
---

# Skill Title

Skill documentation in markdown format...
```

## Required Fields

- `name` - Unique identifier in kebab-case (e.g., `pdf-generator`)
- `description` - One-line summary of what the skill does

## Optional Fields

- `allowed-tools` - List of tools the skill is allowed to use (if omitted, all tools are allowed)
- `model` - Preferred LLM model for this skill
- `context` - Whether to inherit or fork the conversation context
- `priority` - Override priority for conflict resolution (default: 0)
- `tags` - Categorization tags for organization

## Tool Restrictions

The `allowed-tools` field restricts which tools agents can use while executing the skill:

```yaml
allowed-tools:
  - Bash      # Execute commands/scripts
  - Read      # Read files
  - Write     # Write files
  - Grep      # Search patterns
  - Glob      # Find files
```

If omitted, all tools are allowed. This provides security by limiting tool access.

## Creating a New Skill

1. **Create skill directory**:
   ```bash
   mkdir -p .claude/skills/my-skill/scripts
   ```

2. **Create SKILL.md**:
   ```bash
   cat > .claude/skills/my-skill/SKILL.md << 'EOF'
   ---
   name: my-skill
   description: Description of what the skill does
   allowed-tools:
     - Bash
     - Read
   ---

   # My Skill

   Instructions on how to use this skill...
   EOF
   ```

3. **Add scripts** (optional):
   ```bash
   cat > .claude/skills/my-skill/scripts/do_something.py << 'EOF'
   #!/usr/bin/env python3
   import sys
   print("Doing something...")
   EOF
   chmod +x .claude/skills/my-skill/scripts/do_something.py
   ```

4. **Test the skill**:
   - Skills are automatically discovered by SkillLoader
   - Invoke via SkillTool with skill name

## How Skills Work

### Discovery (Stage 1)
- SkillLoader scans this directory for SKILL.md files
- Parses YAML frontmatter to extract metadata
- Skills appear in SkillTool description with name and description

### Activation (Stage 2)
- Agent invokes SkillTool with skill name
- Full SKILL.md content is loaded and returned
- Agent receives base_path for resolving relative references

### Execution (Stage 3)
- Agent follows instructions in SKILL.md
- Loads reference docs using Read tool: `{base_path}/reference.md`
- Executes scripts using Bash tool: `cd {base_path} && python scripts/script.py`
- **IMPORTANT**: Scripts are EXECUTED, never read (for context efficiency)

## Best Practices

### Documentation
- **Clear instructions** - Explain how to use the skill step-by-step
- **Examples** - Provide concrete usage examples
- **Troubleshooting** - Include common errors and solutions

### Scripts
- **Error handling** - Scripts should validate inputs and provide clear error messages
- **Help text** - Include usage instructions when run without arguments
- **Dependencies** - Document all required packages

### Organization
- **Modular** - Break complex skills into smaller, focused capabilities
- **Self-contained** - Include all necessary files within the skill directory
- **Portable** - Avoid hardcoded paths or environment-specific assumptions

### Naming
- **Kebab-case** - Use lowercase with hyphens: `pdf-generator`, not `PDF_Generator`
- **Descriptive** - Name should indicate what the skill does
- **Concise** - Keep names reasonably short (2-3 words)

## Available Tools

Skills can use the following tools (if allowed):

| Tool | Purpose | Example |
|------|---------|---------|
| **Bash** | Execute commands and scripts | `python scripts/process.py input.txt` |
| **Read** | Read file contents | Read `{base_path}/config.json` |
| **Write** | Write files | Write output to `results.txt` |
| **Grep** | Search patterns | Search for "error" in log files |
| **Glob** | Find files | Find all `*.py` files |

## Storage Layers

Skills can be placed in different storage layers:

1. **Enterprise** (`~/.omniforge/enterprise/skills/`) - Highest priority, managed by admins
2. **Personal** (`~/.omniforge/skills/`) - User-specific skills
3. **Project** (`.claude/skills/`) - Project-specific skills (this directory)
4. **Plugin** (plugin directories) - Third-party skill packages

Higher priority layers override lower ones if skills have the same name.

## Example Skills

### PDF Generator (included)
Generate PDF documents from text using Python's reportlab library.

```bash
# Quick example
cd .claude/skills/pdf-generator
python scripts/generate_pdf.py "Hello, World!" output.pdf
```

### Ideas for More Skills

- **code-review** - Automated code review using linters and static analysis
- **data-analysis** - Analyze CSV/JSON data and generate reports
- **api-tester** - Test REST APIs and validate responses
- **image-processor** - Resize, compress, or convert images
- **log-analyzer** - Parse and analyze log files for errors
- **markdown-to-html** - Convert markdown documents to HTML
- **git-helper** - Common git workflows and operations
- **database-backup** - Automated database backup and restore
- **security-scan** - Scan code for security vulnerabilities
- **performance-test** - Run performance benchmarks

## Contributing Skills

To share skills with the community:

1. Create skill following this structure
2. Test thoroughly with different inputs
3. Document all dependencies and requirements
4. Include comprehensive examples
5. Add troubleshooting guide

## Troubleshooting

### Skill not found
- Check that SKILL.md exists with valid YAML frontmatter
- Verify `name` field matches skill directory name
- Ensure skill directory is in a scanned location

### Tool restriction error
- Check `allowed-tools` includes the tool being used
- Remove `allowed-tools` field to allow all tools
- Verify tool names match exactly (case-insensitive)

### Script execution fails
- Make scripts executable: `chmod +x script.py`
- Verify dependencies are installed
- Check script has proper shebang: `#!/usr/bin/env python3`
- Test script standalone before using in skill

### Permission denied
- Check file/directory permissions
- Ensure scripts are executable
- Verify write permissions for output directories

## Learn More

- See [SKILL.md](pdf-generator/SKILL.md) for an example skill
- Read [examples.md](pdf-generator/examples.md) for usage patterns
- Check [reference.md](pdf-generator/reference.md) for technical details

## Support

For questions or issues:
- Review skill documentation
- Check skill YAML frontmatter syntax
- Verify tool restrictions are correct
- Test scripts independently before integration
