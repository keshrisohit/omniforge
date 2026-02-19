# Skill Creation Assistant Agent

**Created**: 2026-01-26
**Last Updated**: 2026-01-26
**Version**: 2.0
**Status**: Draft

---

## Overview

The Skill Creation Assistant Agent is an intelligent conversational agent that helps users create new skills for the OmniForge platform through natural dialogue. Skills in OmniForge are **SKILL.md files** - Markdown documents with YAML frontmatter containing instructions for LLM agents to follow. Rather than requiring users to understand the skill file format, write Markdown from scratch, or manually configure frontmatter fields, users simply describe what they want their skill to accomplish. The assistant asks clarifying questions, gathers requirements, generates the SKILL.md file with proper structure, optionally creates hook scripts, and saves the skill to the appropriate storage layer in the 4-layer filesystem hierarchy.

This agent embodies OmniForge's core vision of "agents build agents" by enabling the creation of reusable agent capabilities through conversation alone. It bridges the gap between non-technical users who have domain knowledge and the technical structure of SKILL.md files, making skill creation accessible to everyone while maintaining proper format compliance and enterprise governance standards.

---

## Alignment with Product Vision

This specification advances OmniForge's core vision in multiple ways:

| Vision Principle | How This Agent Delivers |
|------------------|------------------------|
| **Agents Build Agents** | The assistant agent creates agent skills (SKILL.md files) through conversation |
| **No-Code Interface** | Users describe skills in plain English, never write YAML or Markdown unless they want to |
| **Enterprise-Ready from Day One** | Skills are saved to proper storage layers with correct priority handling |
| **Simplicity Over Flexibility** | Guided workflow with smart defaults; advanced options available but not required |
| **Multi-tenancy** | Skills are automatically saved to the correct layer (Enterprise, Personal, Project, Plugin) |
| **Open Source Compatibility** | Generated skills follow Claude Code SKILL.md format for portability |

**Strategic Importance**: This agent is a key enabler for the premium platform's value proposition. It transforms skill creation from a Markdown-authoring activity into something any team member can do, dramatically accelerating the customization of agent capabilities for specific business needs.

---

## User Personas

### Primary Users

#### Platform User (Skill Requester)

A business user or team member who needs custom agent capabilities but doesn't write code or Markdown.

**Context**: Working on a project where existing skills don't quite meet their needs. They understand their domain and workflow but not the technical details of SKILL.md structure.

**Goals**:
- Create custom skills by describing what they need in plain language
- Get skills that guide agents correctly without writing Markdown
- Have skills properly saved to the right storage layer
- Iterate on skill instructions through conversation

**Pain Points**:
- Current skill creation requires understanding YAML frontmatter syntax
- Don't know which frontmatter fields are required vs optional
- Unsure how to structure clear instructions for LLM agents
- No guidance on best practices for skill design

**Key Quote**: "I know exactly what I want the agent to do, but I shouldn't have to learn Markdown frontmatter syntax to make it happen."

---

#### SDK Developer (Power User)

A developer using OmniForge who wants to accelerate skill creation or prototype quickly.

**Context**: Comfortable with Markdown but wants to speed up the skill creation process, or wants to generate well-structured skills and then customize.

**Goals**:
- Rapidly prototype skill ideas through conversation
- Generate properly structured SKILL.md files to customize further
- Validate skill concepts before investing in detailed instructions
- Create skills for all types (simple, multi-step, hook-based, restricted)

**Pain Points**:
- Writing YAML frontmatter for every new skill is tedious
- Maintaining consistency across skill files
- Remembering all valid frontmatter fields and their formats
- Testing skill instructions for clarity

**Key Quote**: "I can write the Markdown, but if an AI can generate a solid starting point with proper structure, I'll create skills 5x faster."

---

#### Enterprise Administrator (Governance Overseer)

A technical administrator responsible for skill governance across their organization.

**Context**: Managing skill deployments, ensuring compliance, and maintaining quality standards for skills created by various team members.

**Goals**:
- Ensure all skills meet organizational standards
- Track who creates skills and when
- Review skills before enterprise-wide deployment
- Maintain skills in the correct storage layers

**Pain Points**:
- No visibility into skill creation process
- Skills created with unclear instructions or missing fields
- Inconsistent skill quality across teams
- Difficulty enforcing standards without blocking productivity

**Key Quote**: "I need to trust that skills created through this system are well-structured, clear, and saved to the right location."

---

### Secondary Users

#### QA/Testing Engineer

Responsible for validating skills work as expected.

**Goals**: Access generated SKILL.md files, understand skill instructions, verify tool restrictions work correctly.

---

#### Team Lead (Skill Curator)

Oversees team's skill library and ensures coherent skill organization.

**Goals**: Review skill requests, guide skill design decisions, prevent duplicate skills.

---

## Problem Statement

### The SKILL.md Authoring Barrier

Creating new skills in OmniForge requires understanding the SKILL.md format:

1. **YAML Frontmatter**: Understanding required fields (name, description), optional fields (allowed-tools, model, context, priority, tags, hooks), and forbidden fields
2. **Markdown Instructions**: Writing clear, imperative instructions that guide LLM behavior effectively
3. **Hook Scripts**: Creating bash/Python scripts in the correct directories for pre/post tool use automation
4. **Storage Layer Selection**: Knowing where to save skills (Enterprise, Personal, Project, Plugin) based on scope

This creates a fundamental tension: **the people who understand what skills are needed (domain experts, business users) are often not the people who can author proper SKILL.md files**.

### The Instruction Quality Challenge

Even when developers create skills, quality varies:
- Some skills have clear, step-by-step instructions; others are vague
- Some follow best practices for LLM guidance; others use confusing language
- Some properly use tool restrictions; others leave agents with too much or too little capability
- Some have proper hooks for automation; others miss opportunities for scripted validation

There's no enforced quality bar, and skills created in isolation often don't provide effective guidance.

### The Discoverability Problem

Before creating a new skill, users should check if a similar skill already exists. But:
- No natural way to search for skills by describing what you need
- Existing skills may partially meet needs but users don't know how to find them
- Duplicate skills proliferate, creating maintenance burden

### The Storage Layer Requirement

Skills must be saved to the correct storage layer:
- Enterprise skills (`~/.omniforge/enterprise/skills/`) for organization-wide deployment
- Personal skills (`~/.omniforge/skills/`) for individual users
- Project skills (`.omniforge/skills/`) for project-specific needs
- Plugin skills (configurable paths) for distributed packages

Currently, getting the storage layer right requires understanding the 4-layer hierarchy and priority system.

---

## Core Design: Conversational Skill Creation

### The Conversation-First Approach

The Skill Creation Assistant uses conversation as the primary interface, not forms or configuration files. This enables:

1. **Natural Requirements Gathering**: Users describe needs in their own words
2. **Intelligent Clarification**: The assistant asks targeted questions to fill gaps
3. **Iterative Refinement**: Users and assistant collaborate to refine instructions
4. **Validation Through Dialogue**: Generated content reviewed conversationally

### What Skills Actually Are

**Skills are SKILL.md files** - Markdown documents that provide instructions for LLM agents. They are NOT:
- Python code or functions
- Database entries (except for marketplace publishing)
- External API integrations as code
- Custom tool implementations

**A skill consists of**:

1. **SKILL.md File** with:
   - YAML frontmatter (metadata configuration)
   - Markdown body (instructions for the LLM agent)

2. **Optional Hook Scripts** in `scripts/`, `bin/`, or `tools/` directories:
   - PreToolUse hooks (run before specified tools)
   - PostToolUse hooks (run after specified tools)
   - Stop hooks (run when agent stops)

3. **Optional Reference Documents** in `docs/` directory

### Skill Types Supported

The assistant can create four types of skills:

#### 1. Simple Skills

Basic skills with instructions for common tasks.

**Example User Request**: "I need a skill that helps agents format product names consistently - first letter capitalized, removes extra spaces, handles suffixes correctly."

**Generated Artifact**: SKILL.md with clear formatting instructions, examples, and edge case handling guidance.

---

#### 2. Multi-Step Skills

Skills with sequential procedures for complex workflows.

**Example User Request**: "Create a skill for daily operations briefings that pulls data, checks for overdue items, and generates a formatted report."

**Generated Artifact**: SKILL.md with numbered steps, conditional logic guidance, and clear output format specifications.

---

#### 3. Hook-Based Skills

Skills with automation scripts for pre/post processing.

**Example User Request**: "I need a skill for deploying to Kubernetes that validates cluster connectivity before any deployment and verifies deployment success afterward."

**Generated Artifact**: SKILL.md with hook configuration in frontmatter plus bash scripts in `scripts/` directory.

---

#### 4. Restricted Skills

Skills with explicit tool allowlists to constrain agent behavior.

**Example User Request**: "Create a code review skill that can only read files and run analysis tools - no file modifications allowed."

**Generated Artifact**: SKILL.md with `allowed-tools` field specifying only Read, Glob, Grep, and Bash for linting.

---

### The Creation Workflow

```
User Initiates Skill Creation
           |
           v
+---------------------+
|  Intent Detection   |  <-- "I want to create a skill that..."
+---------------------+
           |
           v
+---------------------+
| Requirements        |  <-- Clarifying questions about purpose,
| Gathering           |      behavior, tool needs, hooks
+---------------------+
           |
           v
+---------------------+
| Skill Type          |  <-- Assistant determines best skill type
| Selection           |      based on requirements
+---------------------+
           |
           v
+---------------------+
| Specification       |  <-- Confirm understanding with user
| Confirmation        |      before generation
+---------------------+
           |
           v
+---------------------+
| SKILL.md Generation |  <-- Generate frontmatter + instructions
| (via LLM)           |      following OmniForge patterns
+---------------------+
           |
           v
+---------------------+
| Hook Script         |  <-- If needed, generate bash/Python
| Generation          |      scripts for automation
+---------------------+
           |
           v
+---------------------+
| Validation          |  <-- Parse with SkillParser to validate
|                     |      structure and frontmatter
+---------------------+
           |
    +------+------+
    |             |
    v             v
+--------+   +---------+
| PASS   |   | FAIL    | --> Fix and retry
+--------+   +---------+
    |
    v
+---------------------+
| Storage Layer       |  <-- Save to correct directory in
| Selection & Save    |      4-layer hierarchy
+---------------------+
           |
           v
+---------------------+
| Confirmation &      |  <-- Provide skill details
| Usage Instructions  |      and how to invoke it
+---------------------+
```

---

## Detailed User Journeys

### Journey 1: Non-Technical User Creates First Skill

**Persona**: Platform User (Marketing Manager)
**Context**: Needs a skill to standardize product names in documents

1. **User Initiates**:
   ```
   User: "I want to create a skill that helps agents format product names"
   ```

2. **Assistant Clarifies**:
   ```
   Bot: "I'd be happy to help you create a product name formatting skill!

        To make sure I understand your needs:

        1. What does 'formatting' mean for your product names?
           - Standardizing capitalization?
           - Removing extra spaces?
           - Expanding abbreviations?
           - Something else?

        2. Can you give me a few examples of product names
           before and after formatting?"
   ```

3. **User Provides Examples**:
   ```
   User: "Our product names should always be title case, no extra
         spaces, and we have abbreviations that should be expanded.

         Examples:
         - 'pro   analytics' -> 'Pro Analytics'
         - 'PA' -> 'Pro Analytics'
         - 'ENTERPRISE  SUITE' -> 'Enterprise Suite'
         - 'es' -> 'Enterprise Suite'"
   ```

4. **Assistant Confirms Understanding**:
   ```
   Bot: "Got it! I'll create a skill that guides agents to:

        1. Convert product names to Title Case
        2. Remove extra whitespace
        3. Expand these abbreviations:
           - PA -> Pro Analytics
           - ES -> Enterprise Suite

        A few more questions:
        - Should I include case-insensitive abbreviation matching?
          (e.g., 'pa', 'PA', and 'Pa' all become 'Pro Analytics')
        - Are there other abbreviations to include?
        - Should agents have any tool restrictions for this skill?"
   ```

5. **User Confirms and Adds**:
   ```
   User: "Yes, case-insensitive. Also add:
         - DSL -> Data Science Lab
         - AI -> Analytics Intelligence

         No tool restrictions needed."
   ```

6. **Assistant Generates and Validates**:
   ```
   Bot: "Creating your 'product-name-formatter' skill now...

        [Generating SKILL.md]
        [Validating with SkillParser]

        Validation passed! Here's a preview:

        ---
        name: product-name-formatter
        description: Format product names with consistent capitalization and abbreviation expansion
        tags:
          - formatting
          - product-names
        ---

        # Product Name Formatter

        When asked to format or clean up product names, follow these rules:

        ## Formatting Rules
        1. Convert all product names to Title Case
        2. Remove extra whitespace between words
        3. Expand abbreviations (case-insensitive matching)

        ## Abbreviation Mappings
        - PA -> Pro Analytics
        - ES -> Enterprise Suite
        - DSL -> Data Science Lab
        - AI -> Analytics Intelligence

        ## Examples
        - Input: 'pro   analytics' -> Output: 'Pro Analytics'
        - Input: 'PA' -> Output: 'Pro Analytics'
        ...

        Where would you like me to save this skill?
        - Personal (~/.omniforge/skills/) - Only you can use it
        - Project (.omniforge/skills/) - Team members can use it"
   ```

7. **User Selects Storage**:
   ```
   User: "Save it to the project so the team can use it."

   Bot: "Skill 'product-name-formatter' saved to .omniforge/skills/product-name-formatter/SKILL.md

        Your team's agents will now automatically apply these
        formatting rules when working with product names.

        To manually invoke: 'Use the product-name-formatter skill'"
   ```

**Key Experience**: The marketing manager created a working skill through pure conversation, never writing YAML or Markdown but getting exactly what they needed.

---

### Journey 2: Developer Creates Hook-Based Skill

**Persona**: SDK Developer
**Context**: Needs a skill with automation scripts for API integration setup

1. **User Initiates with Technical Detail**:
   ```
   User: "Create a skill for setting up API integrations. It should:
         - Validate API credentials exist before any setup
         - Run a connection test after setup completes
         - Only allow Bash and Read tools during setup"
   ```

2. **Assistant Confirms and Asks for Details**:
   ```
   Bot: "I'll create a hook-based skill for API integration setup.

        Configuration I'll implement:
        - PreToolUse hook: Validate credentials (env vars exist)
        - PostToolUse hook: Test connection
        - Tool restriction: Bash, Read only

        A few questions:
        1. What environment variables should the pre-hook check for?
        2. What should the connection test do? (Ping endpoint? Auth check?)
        3. What timeout should hooks have?"
   ```

3. **Developer Provides Details**:
   ```
   User: "Check for API_KEY and API_ENDPOINT env vars.
         Connection test should curl the health endpoint.
         30 second timeout for hooks."
   ```

4. **Assistant Generates with Full Visibility**:
   ```
   Bot: "Creating 'api-integration-setup' skill with hooks...

        Generated files:
        1. SKILL.md - Main skill file
        2. scripts/validate-credentials.sh - Pre-hook
        3. scripts/test-connection.sh - Post-hook

        SKILL.md preview:
        ---
        name: api-integration-setup
        description: Set up API integrations with credential validation and connection testing
        allowed-tools:
          - Bash
          - Read
        hooks:
          PreToolUse:
            - command: scripts/validate-credentials.sh
              timeout_ms: 30000
          PostToolUse:
            - command: scripts/test-connection.sh
              timeout_ms: 30000
        ---

        # API Integration Setup

        When setting up API integrations, follow these procedures...

        ---

        validate-credentials.sh preview:
        #!/bin/bash
        if [ -z "$API_KEY" ]; then
          echo "Error: API_KEY environment variable not set"
          exit 1
        fi
        ...

        Would you like to see the full files or modify anything?"
   ```

5. **Developer Approves**:
   ```
   User: "Looks good, save to project"

   Bot: "Saved 'api-integration-setup' skill:
        - .omniforge/skills/api-integration-setup/SKILL.md
        - .omniforge/skills/api-integration-setup/scripts/validate-credentials.sh
        - .omniforge/skills/api-integration-setup/scripts/test-connection.sh

        Hook scripts are executable (chmod +x applied).

        Agents using this skill will:
        1. Validate credentials before any tool use
        2. Only have access to Bash and Read tools
        3. Test connection after tool execution"
   ```

**Key Experience**: The developer got a production-ready skill with automation hooks - all through conversation with full file visibility.

---

### Journey 3: Creating a Multi-Step Skill with Tool Restrictions

**Persona**: Platform User (Operations Lead)
**Context**: Needs a skill for code review with restricted capabilities

1. **User Describes Requirements**:
   ```
   User: "I need a code review skill that:
         1. Reads changed files
         2. Runs linters
         3. Generates review comments

         But it should NOT be able to modify any files."
   ```

2. **Assistant Identifies Restrictions**:
   ```
   Bot: "I'll create a 'code-review' skill with restricted tools.

        Tool restrictions to enforce:
        - Read: To read changed files
        - Glob: To find files by pattern
        - Grep: To search for patterns
        - Bash: To run linting commands

        Explicitly NOT included (cannot modify files):
        - Write
        - Edit

        For the review process:
        - Which linters should it run? (eslint, ruff, etc.)
        - What format for review comments? (Markdown list? Per-file?)
        - Should it check for specific patterns or anti-patterns?"
   ```

3. **User Provides Details**:
   ```
   User: "Use ruff for Python files.
         Comments should be per-file markdown.
         Check for TODO comments and missing docstrings."
   ```

4. **Assistant Creates Restricted Skill**:
   ```
   Bot: "Creating 'code-review' skill with tool restrictions...

        ---
        name: code-review
        description: Review code changes with linting and pattern checks (read-only)
        allowed-tools:
          - Read
          - Glob
          - Grep
          - Bash
        tags:
          - code-review
          - quality
        ---

        # Code Review Skill

        When asked to review code, follow this procedure:

        ## Step 1: Identify Changed Files
        Use Glob to find files matching the review scope...

        ## Step 2: Run Linters
        For Python files, run: `ruff check {file_path}`
        ...

        ## Step 3: Check for Patterns
        - Search for TODO comments with Grep
        - Check for missing docstrings
        ...

        ## Step 4: Generate Review
        Format findings as per-file markdown...

        ---

        IMPORTANT: You cannot modify files with this skill.
        The allowed-tools list restricts you to read-only operations.

        Save to project?"
   ```

**Key Experience**: The operations lead created a capability-restricted skill that enforces read-only behavior during code reviews.

---

### Journey 4: Updating Skill Instructions and Adding Hooks

**Persona**: Platform User
**Context**: Skill needs updates based on real-world usage

1. **User Reports Need**:
   ```
   User: "The product-name-formatter skill needs updates:
         1. Add 'MVP' -> 'Minimum Viable Product' abbreviation
         2. Add a hook that logs all formatting operations"
   ```

2. **Assistant Investigates**:
   ```
   Bot: "Let me check the current 'product-name-formatter' skill...

        Current abbreviation mappings:
        - PA -> Pro Analytics
        - ES -> Enterprise Suite
        - DSL -> Data Science Lab
        - AI -> Analytics Intelligence

        Current hooks: None

        I'll:
        1. Add 'MVP -> Minimum Viable Product' to the instructions
        2. Create a PostToolUse hook for logging

        For the logging hook:
        - Where should logs be written? (File path or stdout?)
        - What should be logged? (Input, output, timestamp?)"
   ```

3. **User Provides Details**:
   ```
   User: "Log to /var/log/formatting.log with timestamp, input, and output"
   ```

4. **Assistant Updates and Saves**:
   ```
   Bot: "Updating 'product-name-formatter' skill...

        Changes:
        + Added 'MVP -> Minimum Viable Product' to abbreviations
        + Created scripts/log-formatting.sh hook
        + Added PostToolUse hook configuration

        Updated frontmatter:
        ---
        name: product-name-formatter
        description: Format product names with consistent capitalization and abbreviation expansion
        hooks:
          PostToolUse:
            - command: scripts/log-formatting.sh
              timeout_ms: 5000
        tags:
          - formatting
          - product-names
        ---

        Updated abbreviation section in instructions:
        ## Abbreviation Mappings
        - PA -> Pro Analytics
        - ES -> Enterprise Suite
        - DSL -> Data Science Lab
        - AI -> Analytics Intelligence
        - MVP -> Minimum Viable Product  [NEW]

        Skill updated at .omniforge/skills/product-name-formatter/"
   ```

**Key Experience**: The user updated their skill through conversation, adding new instructions and automation hooks without manually editing files.

---

## Success Criteria

### User Outcomes

#### For Platform Users (Non-Technical)
- **Creation Success Rate**: 90%+ of skill creation conversations result in a valid SKILL.md file
- **Time to Working Skill**: Users can create a simple skill in under 5 minutes of conversation
- **Zero Markdown Required**: Users never need to see or write YAML/Markdown to create functional skills
- **Iteration Simplicity**: Users can modify existing skills through conversation without understanding file structure

#### For SDK Developers
- **Acceleration Factor**: Skill creation is 3-5x faster through conversation vs. manual authoring
- **Format Quality**: Generated skills pass SkillParser validation
- **Customization Access**: Developers can view, modify, and export generated content at any point
- **All Skill Types**: Can create all four skill types through conversation

#### For Enterprise Administrators
- **Storage Layer Control**: All skills saved to appropriate storage layer
- **Quality Assurance**: All skills validated before saving
- **Visibility**: Clear confirmation of where skills are saved and what they contain

### Technical Outcomes

- **Validation Rate**: 95%+ of generated skills pass SkillParser validation on first generation
- **Frontmatter Compliance**: 100% of generated frontmatter uses only allowed fields
- **Storage Success**: 99%+ of skills save successfully to the correct layer
- **Hook Script Quality**: Generated scripts are executable and syntactically valid

### Business Outcomes

- **Skill Creation Democratization**: 5x increase in skills created by non-developers
- **Developer Productivity**: Developers report 50%+ time savings on skill creation
- **Platform Stickiness**: Skill library growth increases platform engagement
- **Support Reduction**: Fewer support tickets for "how do I create a skill"

---

## Key Experiences

### The "It Understood Me" Moment

When the assistant correctly interprets a vague request and asks exactly the right clarifying questions, users feel understood. The assistant doesn't just parrot back the request - it demonstrates understanding of skill design.

**What makes this moment great**:
- Questions are specific and relevant to skill authoring
- Assistant anticipates needed frontmatter fields
- Suggestions show understanding of what makes good LLM instructions
- User feels their intent was captured accurately

---

### The "Just Works" Moment

When the generated skill validates successfully and agents immediately start following its instructions, users feel the magic of AI-powered authoring.

**What makes this moment great**:
- SkillParser validation passes on first try
- Skill appears in available skills list
- Agents naturally apply the skill's guidance
- No debugging or manual editing needed

---

### The "Full Control" Moment (for Developers)

When developers can see the generated SKILL.md content, understand the structure, and modify it if desired, they feel empowered rather than constrained.

**What makes this moment great**:
- Generated content is well-formatted and readable
- Follows OmniForge conventions
- Easy to export and customize further
- Can switch between conversation and file editing freely

---

### The "Right Place" Moment (for Admins)

When an admin confirms a skill was saved to the correct storage layer with proper priority, they feel confident in the governance model.

**What makes this moment great**:
- Clear confirmation of storage location
- Understanding of priority implications
- Ability to verify before saving
- Full visibility into file structure created

---

## Edge Cases and Considerations

### Ambiguous Requirements

**Scenario**: User describes a skill vaguely without clear instructions.

**Handling**:
- Assistant asks targeted clarifying questions
- Provides examples of similar skills for reference
- Suggests concrete instruction structures to confirm
- If user remains vague, creates minimal skill with clear guidance on how to expand

---

### Duplicate Skill Detection

**Scenario**: User requests a skill that already exists (exact or similar).

**Handling**:
- Before generation, search existing skills for name matches
- Present existing skills that might meet the need: "I found 'format-names' which does something similar. Want to use it, modify it, or create something new?"
- If user chooses to create new, suggest meaningful name differentiation

---

### Generated Content Fails Validation

**Scenario**: SkillParser rejects the generated SKILL.md.

**Handling**:
- Analyze validation errors
- Attempt automatic fix (correct frontmatter, fix formatting)
- If still failing, explain the issue to user
- Offer to show the raw content for manual review

---

### Invalid Frontmatter Fields

**Scenario**: User requests a frontmatter field that isn't allowed.

**Handling**:
- Explain which fields are valid (name, description, allowed-tools, model, context, user-invocable, priority, tags, scope, hooks)
- Explain forbidden fields (schedule, trigger, created-by, source, author)
- Suggest alternatives or explain why the field isn't supported

---

### Hook Script Complexity

**Scenario**: User requests hook behavior that requires complex scripting.

**Handling**:
- Generate basic script structure
- Clearly document what the script does
- Flag when scripts may need manual review
- Suggest simpler alternatives when appropriate

---

### Storage Layer Permissions

**Scenario**: User tries to save to enterprise layer without admin permissions.

**Handling**:
- Detect permission issue before attempting save
- Explain storage layer hierarchy and permissions
- Suggest appropriate alternative layer
- Guide user to request proper access if needed

---

### Long Skill Instructions

**Scenario**: User requirements would generate instructions exceeding 5KB limit.

**Handling**:
- Warn when approaching size limit
- Suggest splitting into multiple focused skills
- Recommend using reference docs for detailed content
- Prioritize most critical instructions

---

### Tool Restriction Conflicts

**Scenario**: User requests tool restrictions that would make the skill unusable.

**Handling**:
- Analyze if restricted tools can accomplish the skill's purpose
- Warn about potential limitations
- Suggest minimum tool set for the skill to function
- Allow user to override with understanding of trade-offs

---

## Open Questions

### Skill Versioning

- Should skills support version numbers in directory names (e.g., `skill-name-v1.0.0/`)?
- Should the YAML include a version field?
- How do we handle skill updates vs new versions?

### Skill Templates

- Should we provide templates for common skill patterns?
- Can users save custom templates for their organization?
- How do templates interact with the conversational flow?

### Skill Testing

- How do we validate that skill instructions are clear and effective?
- Should there be a "dry run" mode to test skills?
- How do we test hook scripts without real execution?

### Multi-Language Support

- Should generated skills support non-English instructions?
- How do we handle skill descriptions in multiple languages?
- Does the assistant work in languages other than English?

### Skill Dependencies

- Can skills reference other skills?
- How do we handle skill composition?
- Should there be explicit dependency declarations?

### Conversation Persistence

- How long do we retain skill creation conversations?
- Can users resume interrupted conversations?
- Should conversation context improve future generations?

---

## Out of Scope (For Now)

### Visual Skill Builder
A drag-and-drop interface for creating skills visually. Current scope is conversation-only.

### Skill Marketplace Publishing
Publishing skills to the public marketplace. V1 focuses on local skill creation only.

### Skill Performance Analytics
Detailed analytics on skill usage and effectiveness. Separate feature from creation assistant.

### Automatic Skill Migration
Migrating skills between storage layers automatically. V1 is creation-focused.

### Natural Language Skill Invocation
Invoking skills through natural language rather than skill names. Separate feature.

### Skill Import/Export
Importing skills from external sources or exporting as packages. Future portability feature.

---

## Technical Constraints

### Integration with Existing Architecture

The Skill Creation Assistant must integrate with:

- **SkillParser**: Use existing parser to validate generated SKILL.md content
- **SkillStorageManager**: Use storage manager to save skills to correct layer
- **SkillLoader**: Skills must be loadable by the existing loader
- **4-Layer Hierarchy**: Enterprise > Personal > Project > Plugin priority
- **SkillMdGenerator**: Leverage existing generation components if available
- **SkillWriter**: Use existing writer for filesystem operations

### SKILL.md Requirements

Generated skills must comply with:

- **Required Frontmatter Fields**: name (kebab-case), description
- **Optional Frontmatter Fields**: allowed-tools, model, context, user-invocable, priority, tags, scope, hooks
- **Forbidden Frontmatter Fields**: schedule, trigger, created-by, source, author
- **Maximum Size**: 5KB per SKILL.md file
- **Name Format**: kebab-case matching `^[a-z][a-z0-9-]*$`

### Storage Hierarchy

Skills are stored in filesystem directories:

| Layer | Path | Priority |
|-------|------|----------|
| Enterprise | `~/.omniforge/enterprise/skills/` | Highest (4) |
| Personal | `~/.omniforge/skills/` | High (3) |
| Project | `.omniforge/skills/` | Medium (2) |
| Plugin | Configurable paths | Lowest (1) |

**Priority Calculation**: `(Layer Priority * 1000) + Explicit Priority`

### Hook Script Requirements

When generating hook scripts:

- **Locations**: `scripts/`, `bin/`, or `tools/` directories within skill directory
- **Hook Types**: PreToolUse, PostToolUse, Stop
- **Configuration**: In YAML frontmatter under `hooks` field
- **Execution**: Scripts are executed, content NOT loaded into agent context
- **Script Read Blocking**: Agents cannot read their own hook scripts (security)

### LLM Requirements

- **Instruction Generation**: Requires capable model for clear, imperative instructions
- **Context Window**: Must handle skill context + examples + conversation history
- **Cost Tracking**: All LLM calls attributed to tenant with cost tracking
- **Rate Limiting**: Respect per-tenant rate limits for LLM usage

### Performance Requirements

- **Generation Time**: Simple skills generated in < 30 seconds
- **Validation Time**: SkillParser validation completes in < 5 seconds
- **Save Time**: Skill writing completes in < 5 seconds
- **Conversation Latency**: Response time < 3 seconds for clarifying questions

---

## Evolution Notes

### 2026-01-26 v2.0 (Aligned with Actual Skill System)

**Major Revision**: Updated specification to align with the actual OmniForge skill system architecture.

**Critical Corrections Made**:

1. **Skills are SKILL.md files, not Python code**: Removed all references to function-based skills, external API skills as code, composite skills as code, and custom tool implementations. Skills are Markdown documents with YAML frontmatter.

2. **4-Layer Filesystem Storage**: Skills are stored in filesystem directories (Enterprise, Personal, Project, Plugin), not primarily in database. PublicSkillModel is for marketplace only.

3. **Skill Types Revised**: Changed from (Function, API, Composite, Custom Tool) to (Simple, Multi-step, Hook-based, Restricted) - reflecting what SKILL.md files actually support.

4. **Hook Scripts, Not Code Generation**: Skills can include bash/Python scripts for automation via hooks, but the core skill is always a Markdown document with instructions.

5. **Tool Restrictions via Frontmatter**: The `allowed-tools` field in YAML frontmatter constrains what tools agents can use, not code-level enforcement.

6. **SkillLoader Integration**: Skills are loaded via two-stage loading (metadata first, full content on activation) with TTL-based caching.

7. **Validation via SkillParser**: Generated skills must pass existing SkillParser validation, not custom testing.

**Alignment with Skills System Spec**:
- Follows SKILL.md format from skills-system-spec.md
- Uses SkillStorageManager for 4-layer hierarchy
- Integrates with SkillParser for validation
- Supports progressive disclosure architecture

**Key Design Decisions Preserved**:
- Conversation-first design for accessibility
- No-code interface for non-technical users
- Full visibility for developers who want to customize
- Storage layer selection for proper governance

**Next Steps**:
1. Technical planning phase for assistant agent architecture
2. Define conversation state machine and dialog flows
3. Design generation prompts for SKILL.md content
4. Plan integration with SkillParser validation
5. Implement storage layer selection logic

---

## References

**OmniForge Internal:**
- [OmniForge Product Vision](/Users/sohitkumar/code/omniforge/specs/product-vision.md)
- [Skills System Specification](/Users/sohitkumar/code/omniforge/specs/skills-system-spec.md)
- [Skills System Technical Plan](/Users/sohitkumar/code/omniforge/specs/skills-system-technical-plan.md)
- [TASK-001: Skill Models](/Users/sohitkumar/code/omniforge/specs/tasks/skills-system/TASK-001-skill-models-and-errors.md)
- [TASK-003: Skill Storage Manager](/Users/sohitkumar/code/omniforge/specs/tasks/skills-system/TASK-003-skill-storage-manager.md)
- [TASK-007: SkillTool Implementation](/Users/sohitkumar/code/omniforge/specs/tasks/skills-system/TASK-007-skill-tool-implementation.md)
- [TASK-102: SKILL.md Generator](/Users/sohitkumar/code/omniforge/specs/tasks/conversational-skill-builder/phase-1-mvp/TASK-102-skill-md-generator.md)

**External References:**
- Claude Code Skills Documentation: https://code.claude.com/docs/en/skills

---

## Appendix A: Skill Type Decision Matrix

| User Request Pattern | Recommended Skill Type | Key Characteristics |
|---------------------|----------------------|---------------------|
| "Format/standardize X" | Simple | Clear instructions, examples, no special tools needed |
| "Do A, then B, then C" | Multi-step | Numbered steps, sequential procedures |
| "Validate before X, verify after Y" | Hook-based | Pre/post hooks with automation scripts |
| "Review but don't modify" | Restricted | Tool allowlist constrains capabilities |
| "Complex workflow with automation" | Hook-based + Multi-step | Combines hooks with sequential instructions |

---

## Appendix B: Sample Clarifying Questions by Skill Type

### Simple Skills

1. "What exactly should agents do when this skill applies?"
2. "Can you give me examples of inputs and expected outputs?"
3. "Are there edge cases or exceptions to handle?"
4. "What should agents do if they encounter unexpected input?"

### Multi-Step Skills

1. "What are the steps in this workflow?"
2. "Which steps depend on previous steps?"
3. "What should happen if a step fails?"
4. "What's the final output format?"

### Hook-Based Skills

1. "What should be validated/checked before the main task?"
2. "What should be verified after completion?"
3. "What environment variables or files do hooks need access to?"
4. "What should hooks do if validation fails?"

### Restricted Skills

1. "What specific tools does this skill need?"
2. "What tools should be explicitly blocked?"
3. "Can the skill accomplish its goal with these restrictions?"
4. "Are there alternative approaches if tools are too restricted?"

---

## Appendix C: SKILL.md Template

```markdown
---
name: skill-name-here
description: One-line description of what this skill does
allowed-tools:    # Optional: List of allowed tools
  - Read
  - Bash
  - Glob
model: claude-sonnet-4  # Optional: Preferred model
context: inherit        # Optional: inherit or fork
user-invocable: true    # Optional: Can user invoke directly?
priority: 100           # Optional: Explicit priority (0-999)
tags:                   # Optional: Categorization tags
  - category
  - type
hooks:                  # Optional: Automation hooks
  PreToolUse:
    - command: scripts/pre-hook.sh
      timeout_ms: 30000
  PostToolUse:
    - command: scripts/post-hook.sh
      timeout_ms: 30000
---

# Skill Title

Brief description of when and how to use this skill.

## Prerequisites

What must be true before using this skill.

## Instructions

Step-by-step guidance for the agent.

### Step 1: First Action
Details about the first step...

### Step 2: Second Action
Details about the second step...

## Error Handling

What to do when things go wrong.

## Examples

### Example 1: Common Case
- Input: ...
- Expected Output: ...

### Example 2: Edge Case
- Input: ...
- Expected Output: ...
```
