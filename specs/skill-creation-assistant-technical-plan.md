# Skill Creation Assistant Agent - Technical Implementation Plan

**Created**: 2026-02-03
**Version**: 1.1
**Status**: Draft
**Last Updated**: 2026-02-03 (Aligned with Official Anthropic Agent Skills Guidelines)

---

## Executive Summary

This technical plan outlines the implementation of the Skill Creation Assistant Agent, a conversational agent that enables users to create OmniForge skills (SKILL.md files) through natural dialogue. The agent embodies the "agents build agents" vision by allowing non-technical users to create skills without understanding YAML frontmatter or Markdown syntax.

**Key Architectural Decisions:**

1. **State Machine Architecture**: Multi-turn conversation managed by an explicit finite state machine for predictable, testable flows
2. **LLM-Powered Generation**: Using existing `LLMResponseGenerator` infrastructure with specialized prompts for SKILL.md generation
3. **Integration-First Design**: Leverage existing `SkillParser`, `SkillLoader`, `StorageConfig`, and `SkillStorageManager`
4. **MVP-First Approach**: Start with Simple skills and Project storage layer, then expand incrementally
5. **Official Guidelines Compliance**: Strict adherence to Anthropic Agent Skills specification

**Estimated Effort**: 4-6 weeks for full implementation (2-3 weeks MVP)

---

## Official Anthropic Agent Skills Guidelines Reference

This plan is aligned with the official Anthropic documentation:
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices

### Key Official Requirements

| Requirement | Specification |
|-------------|---------------|
| **Frontmatter Fields** | ONLY `name` and `description` (no other fields in frontmatter) |
| **Name Format** | Max 64 chars, lowercase letters/numbers/hyphens only, no reserved words |
| **Description Format** | Max 1024 chars, third person, includes WHAT it does AND WHEN to use it |
| **SKILL.md Body Limit** | Under 500 lines (~5k tokens) |
| **Progressive Disclosure** | 3 levels: Metadata (always loaded), Body (on trigger), Resources (as needed) |

---

## Table of Contents

1. [Requirements Analysis](#1-requirements-analysis)
2. [Constraints and Assumptions](#2-constraints-and-assumptions)
3. [System Architecture](#3-system-architecture)
4. [Technology Stack](#4-technology-stack)
5. [Component Specifications](#5-component-specifications)
6. [Data Models](#6-data-models)
7. [LLM Integration](#7-llm-integration)
8. [Validation and Error Handling](#8-validation-and-error-handling)
9. [Storage Layer Management](#9-storage-layer-management)
10. [Testing Strategy](#10-testing-strategy)
11. [Implementation Phases](#11-implementation-phases)
12. [Risk Assessment](#12-risk-assessment)
13. [Alternative Approaches](#13-alternative-approaches)

---

## 1. Requirements Analysis

### 1.1 Functional Requirements

**Core Capabilities (from spec):**

| Requirement | Priority | Description |
|-------------|----------|-------------|
| FR-01: Conversational Skill Creation | P0 | Create skills through natural dialogue without Markdown knowledge |
| FR-02: Intent Detection | P0 | Detect when user wants to create a skill |
| FR-03: Requirements Gathering | P0 | Ask clarifying questions to understand skill purpose |
| FR-04: SKILL.md Generation | P0 | Generate valid SKILL.md with ONLY name/description frontmatter |
| FR-05: Validation | P0 | Validate against official Anthropic format before saving |
| FR-06: Storage Layer Selection | P1 | Save to correct layer (Personal, Project, Enterprise) |
| FR-07: Skill Type Detection | P1 | Classify into Simple, Multi-step, Workflow-based |
| FR-08: Progressive Disclosure Support | P1 | Generate skills with proper reference file structure |
| FR-09: Bundled Resource Generation | P2 | Generate scripts/, references/, assets/ as needed |
| FR-10: Skill Update Support | P2 | Modify existing skills through conversation |
| FR-11: Duplicate Detection | P2 | Check for similar existing skills before creation |

**Supported Skill Patterns (per official guidelines):**

1. **Simple Skills**: Basic instructions for common tasks
2. **Workflow Skills**: Sequential procedures with checklists
3. **Reference-Heavy Skills**: Skills with bundled reference documents
4. **Script-Based Skills**: Skills with executable scripts in scripts/ folder

### 1.2 Non-Functional Requirements

| Requirement | Target | Rationale |
|-------------|--------|-----------|
| Generation Time | < 30 seconds | User experience for simple skills |
| Validation Time | < 5 seconds | Quick feedback loop |
| Conversation Latency | < 3 seconds | Responsive dialogue |
| Validation Success Rate | > 95% first attempt | Quality generation |
| Session Persistence | In-memory (MVP) | Simplicity for initial version |

### 1.3 Success Metrics

- 90%+ skill creation conversations result in valid SKILL.md
- Simple skills created in < 5 minutes of conversation
- 95%+ generated skills pass validation on first try
- **100% frontmatter compliance** (ONLY `name` and `description` fields)
- **100% description format compliance** (third person, WHAT + WHEN)

---

## 2. Constraints and Assumptions

### 2.1 Technical Constraints

**From CLAUDE.md and existing codebase:**

- Python 3.9+ required
- Line length: 100 characters (black/ruff)
- Type checking: mypy with `disallow_untyped_defs = true`
- Test coverage: pytest with coverage by default
- Backend code in `src/omniforge/`

**From Official Anthropic Agent Skills Specification:**

| Constraint | Value | Source |
|------------|-------|--------|
| **Frontmatter fields** | ONLY `name` and `description` | Official docs |
| **Name max length** | 64 characters | Official docs |
| **Name format** | `^[a-z][a-z0-9-]*$` (lowercase, numbers, hyphens) | Official docs |
| **Name style** | Gerund form preferred (e.g., "processing-pdfs") | Official docs |
| **Description max length** | 1024 characters | Official docs |
| **Description format** | Third person, non-empty | Official docs |
| **Description content** | MUST include WHAT it does AND WHEN to use it | Official docs |
| **SKILL.md body limit** | Under 500 lines (~5k tokens) | Official docs |
| **Metadata token budget** | ~100 tokens (name + description) | Official docs |
| **Reserved words** | Cannot use reserved skill names | Official docs |
| **Path separators** | Forward slashes only | Official docs |

**Progressive Disclosure (3 Levels):**

| Level | Content | When Loaded | Token Budget |
|-------|---------|-------------|--------------|
| Level 1 | Metadata (name + description) | Always in context | ~100 tokens |
| Level 2 | SKILL.md body | When skill triggers | <500 lines (~5k tokens) |
| Level 3 | Bundled resources (scripts/, references/, assets/) | As needed by Claude | Unlimited |

**Storage Hierarchy:**

| Layer | Path | Priority |
|-------|------|----------|
| Enterprise | `~/.omniforge/enterprise/skills/` | 4 (highest) |
| Personal | `~/.omniforge/skills/` | 3 |
| Project | `.omniforge/skills/` | 2 |
| Plugin | Configurable | 1 (lowest) |

### 2.2 Existing Infrastructure to Leverage

| Component | Location | Purpose |
|-----------|----------|---------|
| `SkillParser` | `src/omniforge/skills/parser.py` | Parse and validate SKILL.md |
| `SkillLoader` | `src/omniforge/skills/loader.py` | Load/cache skills, 500-line validation |
| `SkillStorageManager` | `src/omniforge/skills/storage.py` | 4-layer hierarchy management |
| `StorageConfig` | `src/omniforge/skills/storage.py` | Storage path configuration |
| `SkillMetadata` | `src/omniforge/skills/models.py` | Frontmatter model with validation |
| `LLMResponseGenerator` | `src/omniforge/chat/llm_generator.py` | LLM calls with fallback |
| `LLMIntentAnalyzer` | `src/omniforge/conversation/intent_analyzer.py` | Intent classification pattern |
| `ConversationRepository` | `src/omniforge/conversation/repository.py` | Message persistence |
| `ChatService` | `src/omniforge/chat/service.py` | Chat orchestration pattern |

### 2.3 Assumptions

1. **Single-session conversations**: MVP will not persist conversations across sessions
2. **Project storage default**: MVP defaults to Project layer (`.omniforge/skills/`)
3. **English-only**: MVP supports English instructions only
4. **No versioning**: Skills are created/updated without version tracking
5. **LLM availability**: Assumes configured LLM provider is available
6. **File system access**: Agent has write access to skill directories

---

## 3. System Architecture

### 3.1 High-Level Architecture

```
+-----------------------------------------------------------------------------------+
|                              Skill Creation Assistant                              |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-------------------------+    +------------------------+    +----------------+  |
|  |   SkillCreationAgent    |    |  ConversationManager   |    |  SkillWriter   |  |
|  |  (Orchestration Layer)  |<-->|   (State Machine)      |<-->|  (Persistence) |  |
|  +-------------------------+    +------------------------+    +----------------+  |
|            |                              |                           |           |
|            v                              v                           v           |
|  +-------------------------+    +------------------------+    +----------------+  |
|  | RequirementsGatherer    |    |   SkillMdGenerator     |    |SkillValidator  |  |
|  | (Clarification Logic)   |    | (Official Format Gen)  |    |(Anthropic Spec)|  |
|  +-------------------------+    +------------------------+    +----------------+  |
|            |                              |                           |           |
+------------|------------------------------|---------------------------|----------+
             |                              |                           |
             v                              v                           v
+---------------------------+  +------------------------+  +------------------------+
|   LLMResponseGenerator    |  |     SkillParser        |  |  SkillStorageManager   |
|   (Existing Component)    |  |  (Existing Component)  |  |  (Existing Component)  |
+---------------------------+  +------------------------+  +------------------------+
```

### 3.2 Conversation Flow State Machine

```
                    +-------------------+
                    |      IDLE         |
                    +-------------------+
                             |
                   User message detected
                             v
                    +-------------------+
                    |  INTENT_DETECTION |
                    +-------------------+
                             |
              +--------------+--------------+
              |                             |
        Create skill              Not skill-related
              |                             |
              v                             v
    +-------------------+           +-------------------+
    | GATHERING_PURPOSE |           |    PASS_THROUGH   |
    +-------------------+           +-------------------+
              |
    Clarifying questions
              v
    +-------------------+
    |  GATHERING_DETAILS|
    +-------------------+
              |
       +------+------+
       |             |
   Simple      Workflow-based
       |             |
       v             v
    +-------------------+
    | CONFIRMING_SPEC   |<----+
    +-------------------+     |
              |               |
    User confirms     User requests changes
              |               |
              v               |
    +-------------------+     |
    |    GENERATING     |-----+
    +-------------------+
              |
    Generation complete
              v
    +-------------------+
    |    VALIDATING     |
    +-------------------+
              |
       +------+------+
       |             |
    Valid       Invalid
       |             |
       v             v
    +-------------------+   +-------------------+
    | SELECTING_STORAGE |   |  FIXING_ERRORS    |
    +-------------------+   +-------------------+
              |                      |
              v                      |
    +-------------------+            |
    |      SAVING       |<-----------+
    +-------------------+
              |
              v
    +-------------------+
    |    COMPLETED      |
    +-------------------+
```

### 3.3 Module Boundaries and Responsibilities

| Module | Responsibility | Dependencies |
|--------|----------------|--------------|
| `SkillCreationAgent` | Orchestrates conversation flow, emits events | ConversationManager, SkillWriter |
| `ConversationManager` | State machine, context tracking | RequirementsGatherer |
| `RequirementsGatherer` | Generate clarifying questions | LLMResponseGenerator |
| `SkillMdGenerator` | Generate SKILL.md in official Anthropic format | LLMResponseGenerator |
| `SkillValidator` | Validate against official Anthropic specification | SkillParser |
| `SkillWriter` | Write files to storage layer | SkillStorageManager |
| `ResourceGenerator` | Generate bundled resources (scripts, references) | LLMResponseGenerator |

### 3.4 Data Flow

```
User Message
     |
     v
+--------------------+
| Intent Detection   | --> Is this a skill creation request?
+--------------------+
     |
     v
+--------------------+
| State Machine      | --> Which state are we in? What's next?
+--------------------+
     |
     v
+--------------------+
| Context Manager    | --> What do we know? What do we need?
+--------------------+
     |
     v (if gathering)
+--------------------+
| Clarification Gen  | --> What questions should we ask?
+--------------------+
     |
     v (if ready)
+--------------------+
| SKILL.md Generator | --> Generate with ONLY name + description frontmatter
+--------------------+
     |
     v
+--------------------+
| Official Format    | --> Validate against Anthropic spec
| Validation         |     (name/description only, third person, WHAT+WHEN)
+--------------------+
     |
     v (if valid)
+--------------------+
| Storage Selection  | --> Personal? Project? Enterprise?
+--------------------+
     |
     v
+--------------------+
| File Writer        | --> Write SKILL.md and bundled resources
+--------------------+
     |
     v
+--------------------+
| Confirmation       | --> Success message + usage instructions
+--------------------+
```

---

## 4. Technology Stack

### 4.1 Core Technologies

| Category | Technology | Rationale |
|----------|------------|-----------|
| Language | Python 3.9+ | Project standard |
| Framework | Pydantic v2 | Existing validation pattern |
| LLM Client | litellm | Existing integration |
| Async | asyncio | Existing pattern for streaming |
| Testing | pytest | Project standard |
| Typing | mypy | Strict type checking |

### 4.2 Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| pydantic | ^2.0 | Data validation, models |
| litellm | existing | LLM provider abstraction |
| pyyaml | existing | YAML frontmatter parsing |
| tiktoken | existing | Token counting |

### 4.3 File Structure

```
src/omniforge/
|-- agents/
|   +-- skill_creation_agent.py      # Main agent orchestration
|
|-- skills/
|   |-- creation/                    # New module for skill creation
|   |   |-- __init__.py
|   |   |-- agent.py                 # SkillCreationAgent
|   |   |-- conversation.py          # ConversationManager, state machine
|   |   |-- gatherer.py              # RequirementsGatherer
|   |   |-- generator.py             # SkillMdGenerator (official format)
|   |   |-- validator.py             # SkillValidator (Anthropic spec)
|   |   |-- writer.py                # SkillWriter
|   |   |-- resources.py             # ResourceGenerator (scripts, references)
|   |   |-- prompts.py               # LLM prompt templates
|   |   +-- models.py                # State, context models
|   |
|   |-- parser.py                    # Existing - reuse
|   |-- storage.py                   # Existing - reuse
|   |-- loader.py                    # Existing - reuse
|   +-- models.py                    # Existing - reuse
|
tests/
+-- skills/
    +-- creation/
        |-- test_agent.py
        |-- test_conversation.py
        |-- test_gatherer.py
        |-- test_generator.py
        |-- test_validator.py
        +-- test_writer.py
```

---

## 5. Component Specifications

### 5.1 SkillCreationAgent

**Purpose**: Main entry point for skill creation conversations. Extends `BaseAgent` pattern.

**Interface:**

```python
class SkillCreationAgent(BaseAgent):
    """Conversational agent for skill creation following Anthropic guidelines."""

    identity = AgentIdentity(
        id="skill-creation-assistant",
        name="Skill Creation Assistant",
        description="Create OmniForge skills through natural conversation",
        version="1.0.0",
    )

    def __init__(
        self,
        llm_generator: Optional[LLMResponseGenerator] = None,
        storage_config: Optional[StorageConfig] = None,
        skill_loader: Optional[SkillLoader] = None,
    ) -> None: ...

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process skill creation task with streaming events."""
        ...

    async def handle_message(
        self,
        message: str,
        session_id: str,
        conversation_history: Optional[list[Message]] = None,
    ) -> AsyncIterator[str]:
        """Handle conversational message for skill creation."""
        ...
```

**Responsibilities:**
- Initialize conversation manager and sub-components
- Route messages to appropriate state handlers
- Emit task events for progress tracking
- Coordinate skill writing on completion
- Ensure all generated skills comply with official Anthropic format

### 5.2 ConversationManager

**Purpose**: Manage conversation state machine and context.

**Interface:**

```python
class ConversationState(str, Enum):
    """States in skill creation conversation."""
    IDLE = "idle"
    INTENT_DETECTION = "intent_detection"
    GATHERING_PURPOSE = "gathering_purpose"
    GATHERING_DETAILS = "gathering_details"
    CONFIRMING_SPEC = "confirming_spec"
    GENERATING = "generating"
    VALIDATING = "validating"
    FIXING_ERRORS = "fixing_errors"
    SELECTING_STORAGE = "selecting_storage"
    SAVING = "saving"
    COMPLETED = "completed"

class ConversationContext(BaseModel):
    """Context accumulated during conversation."""
    session_id: str
    state: ConversationState = ConversationState.IDLE

    # Core skill specification (per official format)
    skill_name: Optional[str] = None           # kebab-case, max 64 chars
    skill_description: Optional[str] = None    # Third person, WHAT + WHEN, max 1024 chars
    skill_purpose: Optional[str] = None        # User's raw description

    # Gathered details for body generation
    skill_pattern: Optional[SkillPattern] = None
    examples: list[dict[str, str]] = []        # input/output examples
    workflow_steps: list[str] = []             # for workflow-based skills
    references_needed: list[str] = []          # bundled reference topics

    # Storage and output
    storage_layer: str = "project"
    generated_content: Optional[str] = None
    generated_resources: dict[str, str] = {}   # {"scripts/example.py": content}

    # Validation state
    validation_attempts: int = 0
    validation_errors: list[str] = []
    max_validation_retries: int = 3

    # Conversation tracking
    message_history: list[dict[str, str]] = []

class ConversationManager:
    """Manage skill creation conversation state."""

    def __init__(self, gatherer: RequirementsGatherer, generator: SkillMdGenerator) -> None: ...

    async def process_message(
        self,
        message: str,
        context: ConversationContext,
    ) -> tuple[str, ConversationContext]:
        """Process message, return response and updated context."""
        ...

    def get_next_state(self, context: ConversationContext, user_response: str) -> ConversationState:
        """Determine next state based on current state and user input."""
        ...

    def is_complete(self, context: ConversationContext) -> bool:
        """Check if conversation has reached terminal state."""
        ...
```

**State Transitions:**

| Current State | User Input | Next State |
|---------------|------------|------------|
| IDLE | "Create a skill..." | GATHERING_PURPOSE |
| GATHERING_PURPOSE | Describes purpose | GATHERING_DETAILS |
| GATHERING_DETAILS | Provides examples | CONFIRMING_SPEC |
| CONFIRMING_SPEC | "yes" / confirms | GENERATING |
| CONFIRMING_SPEC | requests changes | GATHERING_DETAILS |
| GENERATING | (auto) | VALIDATING |
| VALIDATING | valid | SELECTING_STORAGE |
| VALIDATING | invalid | FIXING_ERRORS |
| FIXING_ERRORS | (auto retry) | VALIDATING |
| SELECTING_STORAGE | selects layer | SAVING |
| SAVING | (auto) | COMPLETED |

### 5.3 RequirementsGatherer

**Purpose**: Generate contextual clarifying questions following best practices.

**Interface:**

```python
class SkillPattern(str, Enum):
    """Skill patterns based on official guidelines."""
    SIMPLE = "simple"              # Basic instructions
    WORKFLOW = "workflow"          # Sequential procedures with checklists
    REFERENCE_HEAVY = "reference"  # Skills with bundled reference docs
    SCRIPT_BASED = "script"        # Skills with executable scripts

class RequirementsGatherer:
    """Generate clarifying questions for skill requirements."""

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def detect_skill_pattern(self, purpose: str) -> SkillPattern:
        """Classify skill pattern based on user's description."""
        ...

    async def generate_clarifying_questions(
        self,
        context: ConversationContext,
    ) -> list[str]:
        """Generate questions based on what's missing."""
        ...

    def extract_requirements(
        self,
        user_response: str,
        context: ConversationContext,
    ) -> dict[str, Any]:
        """Extract structured requirements from user response."""
        ...

    def has_sufficient_context(self, context: ConversationContext) -> bool:
        """Check if we have enough info to generate."""
        ...

    async def generate_description(
        self,
        context: ConversationContext,
    ) -> str:
        """Generate description in official format: third person, WHAT + WHEN."""
        ...
```

**Question Templates by Pattern (per official best practices):**

```python
QUESTIONS_BY_PATTERN = {
    SkillPattern.SIMPLE: [
        "What specific task should this skill help Claude accomplish?",
        "Can you give 2-3 examples of inputs and expected outputs?",
        "When should Claude use this skill? What triggers it?",
    ],
    SkillPattern.WORKFLOW: [
        "What are the steps in this workflow?",
        "What should be checked/validated at each step?",
        "What's the final output or deliverable?",
        "What should happen if a step fails?",
    ],
    SkillPattern.REFERENCE_HEAVY: [
        "What reference information does Claude need access to?",
        "Should this information be in the main skill or separate files?",
        "How should Claude decide which reference to load?",
    ],
    SkillPattern.SCRIPT_BASED: [
        "What specific operations should the scripts perform?",
        "What inputs do the scripts need?",
        "What language should the scripts be in (Python/Bash)?",
    ],
}
```

### 5.4 SkillMdGenerator

**Purpose**: Generate SKILL.md content strictly following official Anthropic format.

**CRITICAL: Official Format Requirements:**

```yaml
---
name: skill-name-here           # ONLY these two fields
description: Description here   # No other frontmatter allowed
---
```

**Interface:**

```python
class SkillMdGenerator:
    """Generate SKILL.md content following official Anthropic format.

    CRITICAL CONSTRAINTS (from official docs):
    - Frontmatter: ONLY `name` and `description` fields
    - Name: max 64 chars, lowercase letters/numbers/hyphens, gerund preferred
    - Description: max 1024 chars, third person, includes WHAT and WHEN
    - Body: under 500 lines (~5k tokens)
    - Concise: assume Claude is smart, only add what it doesn't know
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def generate(self, context: ConversationContext) -> str:
        """Generate complete SKILL.md content in official format."""
        ...

    def generate_frontmatter(self, context: ConversationContext) -> str:
        """Generate YAML frontmatter with ONLY name and description.

        Returns:
            YAML frontmatter string with exactly two fields
        """
        ...

    async def generate_body(self, context: ConversationContext) -> str:
        """Generate Markdown instruction body under 500 lines."""
        ...

    async def generate_description_official_format(
        self,
        purpose: str,
        triggers: list[str],
    ) -> str:
        """Generate description following official format.

        Official format requirements:
        - Third person (e.g., "Formats product names..." not "Format product names")
        - Includes WHAT the skill does
        - Includes WHEN to use it (triggers/contexts)
        - Max 1024 characters

        Example:
        "Formats product names by applying title case, removing extra whitespace,
        and expanding abbreviations. Use when standardizing product names for
        documentation, reports, or customer-facing materials."
        """
        ...

    def validate_name_format(self, name: str) -> tuple[bool, Optional[str]]:
        """Validate skill name against official requirements.

        Requirements:
        - Max 64 characters
        - Lowercase letters, numbers, hyphens only
        - Must start with letter
        - Gerund form preferred (processing-pdfs, not pdf-processor)
        - No reserved words

        Returns:
            (is_valid, error_message)
        """
        ...

    async def fix_validation_errors(
        self,
        content: str,
        errors: list[str],
    ) -> str:
        """Attempt to fix validation errors in generated content."""
        ...
```

**Generation Strategy:**

1. **Frontmatter Generation**: Strict template with ONLY name and description
2. **Description Generation**: LLM-powered with explicit third-person, WHAT+WHEN requirements
3. **Body Generation**: LLM-powered with conciseness focus (assume Claude is smart)
4. **Validation Loop**: Up to 3 retry attempts on validation failure

### 5.5 SkillValidator

**Purpose**: Validate generated content against official Anthropic specification.

**Interface:**

```python
class ValidationResult(BaseModel):
    """Result of skill validation against official Anthropic spec."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    parsed_skill: Optional[Skill] = None

class SkillValidator:
    """Validate SKILL.md content against official Anthropic specification.

    Validation Rules (from official docs):
    1. Frontmatter has ONLY `name` and `description` fields
    2. Name: max 64 chars, lowercase letters/numbers/hyphens, starts with letter
    3. Description: non-empty, max 1024 chars, third person
    4. Description: includes WHAT and WHEN (trigger context)
    5. Body: under 500 lines
    6. No time-sensitive information
    7. Consistent terminology throughout
    """

    def __init__(self, parser: SkillParser) -> None: ...

    def validate(self, content: str, skill_name: str) -> ValidationResult:
        """Validate SKILL.md content string against official spec."""
        ...

    def validate_frontmatter_fields(self, frontmatter: dict[str, Any]) -> list[str]:
        """Ensure frontmatter has ONLY name and description.

        Returns list of errors if extra fields present.
        """
        allowed_fields = {"name", "description"}
        extra_fields = set(frontmatter.keys()) - allowed_fields
        if extra_fields:
            return [f"Frontmatter contains unauthorized fields: {extra_fields}. "
                    f"Only 'name' and 'description' are allowed."]
        return []

    def validate_name(self, name: str) -> list[str]:
        """Validate name against official requirements."""
        errors = []

        if len(name) > 64:
            errors.append(f"Name exceeds 64 characters (has {len(name)})")

        if not re.match(r"^[a-z][a-z0-9-]*$", name):
            errors.append("Name must be lowercase letters, numbers, hyphens; start with letter")

        # Check reserved words
        reserved = {"skill", "agent", "tool", "system", "admin", "root"}
        if name in reserved:
            errors.append(f"Name '{name}' is reserved")

        return errors

    def validate_description(self, description: str) -> list[str]:
        """Validate description against official requirements."""
        errors = []

        if not description or not description.strip():
            errors.append("Description cannot be empty")

        if len(description) > 1024:
            errors.append(f"Description exceeds 1024 characters (has {len(description)})")

        # Check for third person (heuristic: should not start with imperative verb)
        imperative_starts = ["format", "create", "build", "process", "handle", "manage",
                           "generate", "convert", "extract", "analyze"]
        first_word = description.strip().split()[0].lower() if description.strip() else ""
        if first_word in imperative_starts:
            errors.append(f"Description should be in third person. "
                         f"Instead of '{first_word}...', use '{first_word}s...'")

        # Check for WHEN trigger context (heuristic: should contain trigger words)
        trigger_indicators = ["use when", "use for", "applies when", "triggered by",
                             "invoke when", "helpful for", "designed for"]
        has_trigger = any(ind in description.lower() for ind in trigger_indicators)
        if not has_trigger:
            errors.append("Description should include WHEN to use the skill "
                         "(e.g., 'Use when...', 'Applies when...', 'Helpful for...')")

        return errors

    def validate_body_length(self, body: str) -> list[str]:
        """Validate body is under 500 lines."""
        line_count = body.count("\n") + 1
        if line_count > 500:
            return [f"Body exceeds 500 lines (has {line_count}). "
                    f"Move detailed content to references/ files."]
        return []

    def check_time_sensitive_content(self, content: str) -> list[str]:
        """Warn about time-sensitive information (per best practices)."""
        warnings = []
        time_patterns = [
            r"\b20\d{2}\b",  # Years like 2024, 2025
            r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+20\d{2}\b",
            r"\bcurrently\b", r"\brecently\b", r"\blatest\b",
        ]
        for pattern in time_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append("Content may contain time-sensitive information. "
                               "Consider using relative terms instead.")
                break
        return warnings
```

**Validation Pipeline:**

```
Generated Content
       |
       v
+----------------------+
| Frontmatter Parse    | --> Invalid YAML? Return parse error
+----------------------+
       |
       v
+----------------------+
| Fields Check         | --> Has fields other than name/description?
| (ONLY name, desc)    |     Return "unauthorized fields" error
+----------------------+
       |
       v
+----------------------+
| Name Validation      | --> Max 64 chars, lowercase+numbers+hyphens,
|                      |     starts with letter, no reserved words
+----------------------+
       |
       v
+----------------------+
| Description Valid.   | --> Non-empty, max 1024 chars, third person,
|                      |     includes WHAT and WHEN
+----------------------+
       |
       v
+----------------------+
| Body Line Count      | --> Over 500 lines? Return size error
+----------------------+
       |
       v
+----------------------+
| Time-Sensitive Check | --> Warn about dates, "currently", etc.
+----------------------+
       |
       v
    VALID
```

### 5.6 SkillWriter

**Purpose**: Write skill files to appropriate storage layer.

**Interface:**

```python
class SkillWriter:
    """Write skills to filesystem following official structure."""

    def __init__(self, storage_manager: SkillStorageManager) -> None: ...

    async def write_skill(
        self,
        skill_name: str,
        content: str,
        storage_layer: str,
        resources: Optional[dict[str, str]] = None,
    ) -> Path:
        """Write skill to storage layer, return path.

        Creates official directory structure:
        skill-name/
        |-- SKILL.md (required)
        |-- scripts/     (optional)
        |-- references/  (optional)
        +-- assets/      (optional)
        """
        ...

    def get_skill_directory(self, skill_name: str, storage_layer: str) -> Path:
        """Get target directory for skill."""
        ...

    def skill_exists(self, skill_name: str, storage_layer: str) -> bool:
        """Check if skill already exists."""
        ...

    async def write_bundled_resource(
        self,
        skill_dir: Path,
        resource_path: str,  # e.g., "scripts/process.py" or "references/api.md"
        content: str,
    ) -> Path:
        """Write bundled resource file.

        Note: Uses forward slashes for paths (per official requirement).
        """
        ...
```

### 5.7 ResourceGenerator

**Purpose**: Generate bundled resources (scripts, references, assets).

**Interface:**

```python
class ResourceGenerator:
    """Generate bundled resources for skills.

    Following official progressive disclosure pattern:
    - scripts/: Executable code for deterministic operations
    - references/: Documentation loaded as needed
    - assets/: Files used in output (templates, images)
    """

    def __init__(self, llm_generator: LLMResponseGenerator) -> None: ...

    async def generate_reference_doc(
        self,
        topic: str,
        context: ConversationContext,
    ) -> str:
        """Generate reference documentation file.

        Best practices:
        - Keep one level deep from SKILL.md
        - Include table of contents for files >100 lines
        - Structure for grep-ability
        """
        ...

    async def generate_script(
        self,
        purpose: str,
        language: str = "python",
    ) -> str:
        """Generate executable script for scripts/ folder.

        Best practices:
        - Scripts should be executable without loading into context
        - Include clear docstrings and error handling
        """
        ...

    def determine_resource_structure(
        self,
        context: ConversationContext,
    ) -> dict[str, list[str]]:
        """Determine what bundled resources are needed.

        Returns:
            {"scripts": [...], "references": [...], "assets": [...]}
        """
        ...
```

---

## 6. Data Models

### 6.1 Conversation Models

```python
# src/omniforge/skills/creation/models.py

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
from uuid import uuid4
import re


class ConversationState(str, Enum):
    """States in skill creation conversation."""
    IDLE = "idle"
    INTENT_DETECTION = "intent_detection"
    GATHERING_PURPOSE = "gathering_purpose"
    GATHERING_DETAILS = "gathering_details"
    CONFIRMING_SPEC = "confirming_spec"
    GENERATING = "generating"
    VALIDATING = "validating"
    FIXING_ERRORS = "fixing_errors"
    SELECTING_STORAGE = "selecting_storage"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"


class SkillPattern(str, Enum):
    """Skill patterns based on official guidelines."""
    SIMPLE = "simple"
    WORKFLOW = "workflow"
    REFERENCE_HEAVY = "reference"
    SCRIPT_BASED = "script"


class OfficialSkillSpec(BaseModel):
    """Skill specification following official Anthropic format.

    CRITICAL: Frontmatter has ONLY name and description.
    """
    name: str = Field(..., max_length=64)
    description: str = Field(..., max_length=1024)

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, v: str) -> str:
        """Validate name follows official format."""
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(
                "Name must be lowercase letters, numbers, hyphens; start with letter"
            )
        return v

    @field_validator("description")
    @classmethod
    def validate_description_format(cls, v: str) -> str:
        """Validate description is non-empty."""
        if not v or not v.strip():
            raise ValueError("Description cannot be empty")
        return v


class ConversationContext(BaseModel):
    """Context accumulated during skill creation conversation."""
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    state: ConversationState = ConversationState.IDLE

    # Core skill specification (per official format)
    skill_name: Optional[str] = None           # kebab-case, max 64 chars
    skill_description: Optional[str] = None    # Third person, WHAT + WHEN, max 1024 chars
    skill_purpose: Optional[str] = None        # User's raw description (before formatting)

    # Pattern and details
    skill_pattern: Optional[SkillPattern] = None
    examples: list[dict[str, str]] = []        # {"input": ..., "output": ...}
    workflow_steps: list[str] = []             # For workflow pattern
    triggers: list[str] = []                   # WHEN to use (for description)

    # Bundled resources needed
    references_topics: list[str] = []          # Topics for references/ files
    scripts_needed: list[dict[str, str]] = []  # {"name": ..., "purpose": ...}

    # Storage and output
    storage_layer: str = "project"
    generated_content: Optional[str] = None
    generated_resources: dict[str, str] = {}   # {"scripts/example.py": content}

    # Validation state
    validation_attempts: int = 0
    validation_errors: list[str] = []
    max_validation_retries: int = 3

    # Conversation tracking
    message_history: list[dict[str, str]] = []

    def to_official_spec(self) -> Optional[OfficialSkillSpec]:
        """Convert to official specification if complete."""
        if not self.skill_name or not self.skill_description:
            return None

        return OfficialSkillSpec(
            name=self.skill_name,
            description=self.skill_description,
        )


class ValidationResult(BaseModel):
    """Result of skill validation against official spec."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    skill_path: Optional[str] = None
```

---

## 7. LLM Integration

### 7.1 Prompt Templates (Aligned with Official Guidelines)

```python
# src/omniforge/skills/creation/prompts.py

INTENT_DETECTION_PROMPT = """Analyze if the user wants to create or modify a skill.

User message: {message}

Respond with JSON:
{{
  "is_skill_creation": true/false,
  "is_skill_modification": true/false,
  "skill_name_mentioned": "string or null",
  "confidence": 0.0-1.0
}}
"""

SKILL_PATTERN_CLASSIFICATION_PROMPT = """Classify this skill request into one of these patterns:

1. SIMPLE: Basic instructions for common tasks (formatting, standardization)
2. WORKFLOW: Sequential procedures with steps and checklists
3. REFERENCE: Needs bundled reference documents for detailed info
4. SCRIPT: Needs executable scripts for deterministic operations

User request: {purpose}

Respond with JSON:
{{
  "pattern": "simple|workflow|reference|script",
  "reasoning": "brief explanation",
  "suggested_name": "kebab-case-name-gerund-form"
}}
"""

CLARIFYING_QUESTIONS_PROMPT = """Generate 2-3 clarifying questions to understand this skill better.

Skill purpose: {purpose}
Skill pattern: {pattern}
Already known:
{known_details}

Questions should help determine:
1. WHAT exactly the skill does (specific behavior)
2. WHEN the skill should be used (trigger contexts)
3. Examples of inputs/outputs

Keep questions concise. Respond with JSON:
{{
  "questions": ["question1", "question2"]
}}
"""

# CRITICAL: Official description format prompt
DESCRIPTION_GENERATION_PROMPT = """Generate a skill description following EXACT official requirements:

REQUIREMENTS:
1. Third person (e.g., "Formats..." not "Format...")
2. Must include WHAT the skill does
3. Must include WHEN to use it (triggers/contexts)
4. Maximum 1024 characters
5. No time-sensitive information (no dates, "currently", etc.)

Skill purpose: {purpose}
Specific triggers/contexts: {triggers}
Examples of use cases: {examples}

Generate ONLY the description text (no quotes, no explanation):
"""

# CRITICAL: Official SKILL.md format prompt
SKILL_MD_GENERATION_PROMPT = """Generate a SKILL.md file following EXACT official Anthropic format.

CRITICAL REQUIREMENTS:
1. Frontmatter must have ONLY `name` and `description` fields (NO other fields)
2. Name: "{name}" (already validated)
3. Description: "{description}" (already validated)
4. Body: Clear, concise instructions under 500 lines
5. Assume Claude is smart - only add knowledge Claude doesn't have
6. Use imperative form in instructions
7. No time-sensitive information

Purpose: {purpose}
Pattern: {pattern}
Examples: {examples}
Workflow steps (if applicable): {workflow_steps}

Generate the complete SKILL.md content.
Start with exactly:
---
name: {name}
description: {description}
---

Then add the Markdown body with instructions:
"""

SKILL_NAME_GENERATION_PROMPT = """Generate a skill name following official requirements:

REQUIREMENTS:
1. Max 64 characters
2. Lowercase letters, numbers, hyphens only
3. Must start with letter
4. Prefer gerund form (e.g., "processing-pdfs" not "pdf-processor")
5. Descriptive but concise

Skill purpose: {purpose}

Generate ONLY the skill name (no explanation):
"""

FIX_VALIDATION_ERRORS_PROMPT = """Fix these validation errors in the SKILL.md:

ERRORS:
{errors}

CURRENT CONTENT:
```
{content}
```

CRITICAL RULES:
1. Frontmatter must have ONLY `name` and `description` fields
2. Description must be third person and include WHAT and WHEN
3. Body must be under 500 lines

Fix the errors and output the corrected SKILL.md:
"""

REFERENCE_DOC_GENERATION_PROMPT = """Generate a reference document for a skill's references/ folder.

Topic: {topic}
Skill purpose: {skill_purpose}
Context: {context}

REQUIREMENTS:
1. Keep focused on the specific topic
2. Include table of contents if over 100 lines
3. Structure for grep-ability (clear headings)
4. No time-sensitive information

Generate the reference document in Markdown:
"""

SCRIPT_GENERATION_PROMPT = """Generate a {language} script for a skill's scripts/ folder.

Purpose: {purpose}
Script name: {name}

REQUIREMENTS:
1. Must be executable standalone
2. Include clear docstring and usage
3. Handle errors gracefully
4. Exit with appropriate codes

Generate the complete script:
"""
```

### 7.2 LLM Configuration

```python
# Generation settings per use case
LLM_CONFIGS = {
    "intent_detection": {
        "temperature": 0.1,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    },
    "pattern_classification": {
        "temperature": 0.1,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    },
    "clarifying_questions": {
        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": {"type": "json_object"},
    },
    "description_generation": {
        "temperature": 0.5,
        "max_tokens": 300,  # Description max is 1024 chars
    },
    "name_generation": {
        "temperature": 0.3,
        "max_tokens": 100,
    },
    "skill_generation": {
        "temperature": 0.7,
        "max_tokens": 4000,  # Body can be up to ~5k tokens
    },
    "error_fixing": {
        "temperature": 0.3,
        "max_tokens": 4000,
    },
    "reference_generation": {
        "temperature": 0.6,
        "max_tokens": 3000,
    },
    "script_generation": {
        "temperature": 0.5,
        "max_tokens": 2000,
    },
}
```

### 7.3 Cost and Rate Limiting Considerations

- Intent detection: ~200 tokens per call
- Clarification: ~500 tokens per call
- Description generation: ~300 tokens per call
- SKILL.md generation: ~4000 tokens per call
- Typical conversation: 5-8 LLM calls total
- Estimated cost per skill: $0.01-0.05 (depending on model)

Use existing `LLMResponseGenerator` fallback logic for reliability.

---

## 8. Validation and Error Handling

### 8.1 Validation Pipeline (Per Official Spec)

```
Generated Content
       |
       v
+------------------------+
| YAML Parse Check       | --> Invalid YAML? Return parse error
+------------------------+
       |
       v
+------------------------+
| Frontmatter Fields     | --> Has ANY field other than name/description?
| (STRICT: only 2)       |     Return "unauthorized fields" error
+------------------------+
       |
       v
+------------------------+
| Name Validation        | --> Max 64 chars?
|                        |     Lowercase + numbers + hyphens only?
|                        |     Starts with letter?
|                        |     Not reserved word?
+------------------------+
       |
       v
+------------------------+
| Description Valid.     | --> Non-empty?
|                        |     Max 1024 chars?
|                        |     Third person? (not imperative)
|                        |     Includes WHAT and WHEN?
+------------------------+
       |
       v
+------------------------+
| Body Line Count        | --> Over 500 lines? Return size error
+------------------------+
       |
       v
+------------------------+
| Time-Sensitive Check   | --> Contains dates, "currently", etc.?
| (Warning only)         |     Add warning
+------------------------+
       |
       v
+------------------------+
| SkillParser            | --> Full parse with existing parser
+------------------------+
       |
       v
    VALID
```

### 8.2 Error Recovery Strategy

| Error Type | Recovery Action |
|------------|-----------------|
| YAML parse error | LLM fix with specific error message |
| Unauthorized frontmatter fields | Auto-remove extra fields, regenerate |
| Name too long | LLM shorten while preserving meaning |
| Name format invalid | Auto-convert to kebab-case |
| Description empty | LLM generate from purpose |
| Description not third person | LLM rewrite in third person |
| Description missing WHEN | LLM add trigger context |
| Content too long | LLM summarize, move details to references/ |

### 8.3 Retry Logic

```python
MAX_VALIDATION_RETRIES = 3

async def validate_with_retry(content: str, context: ConversationContext) -> ValidationResult:
    """Validate with automatic retry on failure."""

    for attempt in range(MAX_VALIDATION_RETRIES):
        result = validator.validate(content, context.skill_name)

        if result.is_valid:
            return result

        if attempt < MAX_VALIDATION_RETRIES - 1:
            # Attempt to fix errors
            content = await generator.fix_validation_errors(content, result.errors)
            context.validation_attempts += 1

    # All retries exhausted
    return result
```

### 8.4 User-Friendly Error Messages

```python
ERROR_MESSAGES = {
    "yaml_parse": "The skill file has a formatting issue. Let me fix that...",
    "unauthorized_fields": "I included some extra fields that aren't allowed. "
                          "Fixing to use only name and description...",
    "name_too_long": "The skill name is too long (max 64 characters). Shortening...",
    "name_format": "Skill names must be lowercase with hyphens. Converting...",
    "description_empty": "The skill needs a description. Generating one...",
    "description_not_third_person": "Description should be third person. Rewriting...",
    "description_missing_when": "Description should explain when to use the skill. Adding...",
    "too_long": "The instructions are too long. Moving details to reference files...",
    "time_sensitive": "Note: The skill contains potentially time-sensitive information. "
                     "Consider using relative terms.",
}
```

---

## 9. Storage Layer Management

### 9.1 Layer Selection Logic

```python
async def select_storage_layer(context: ConversationContext) -> str:
    """Determine appropriate storage layer."""

    # Check for explicit user preference
    if context.storage_layer_preference:
        return context.storage_layer_preference

    # Default heuristics
    if context.is_enterprise_admin:
        return "enterprise"  # Admins default to enterprise

    if context.project_context_available:
        return "project"  # Project context = project skills

    return "personal"  # Fallback to personal
```

### 9.2 Permission Checking

```python
def check_storage_permission(layer: str, user_context: dict) -> tuple[bool, str]:
    """Check if user can write to storage layer."""

    if layer == "enterprise":
        if not user_context.get("is_enterprise_admin"):
            return False, "Enterprise skills require admin permissions"

    if layer == "project":
        project_root = user_context.get("project_root")
        if not project_root or not Path(project_root).exists():
            return False, "No project context available"

    return True, ""
```

### 9.3 Path Resolution

```python
def get_skill_path(skill_name: str, layer: str, config: StorageConfig) -> Path:
    """Get full path for skill directory."""

    base_paths = {
        "enterprise": config.enterprise_path,
        "personal": config.personal_path,
        "project": config.project_path,
    }

    base = base_paths.get(layer)
    if not base:
        raise ValueError(f"Invalid storage layer: {layer}")

    return base / skill_name
```

---

## 10. Testing Strategy

### 10.1 Unit Tests

**Test Coverage Targets:**

| Component | Coverage Target |
|-----------|-----------------|
| ConversationManager | 90% |
| RequirementsGatherer | 85% |
| SkillMdGenerator | 90% |
| SkillValidator | 95% |
| SkillWriter | 90% |

**Key Test Cases:**

```python
# test_conversation.py
class TestConversationManager:
    def test_state_transitions_happy_path(self): ...
    def test_state_transitions_with_errors(self): ...
    def test_context_accumulation(self): ...
    def test_is_complete_detection(self): ...

# test_gatherer.py
class TestRequirementsGatherer:
    def test_skill_pattern_detection_simple(self): ...
    def test_skill_pattern_detection_workflow(self): ...
    def test_question_generation_by_pattern(self): ...
    def test_sufficient_context_detection(self): ...

# test_generator.py
class TestSkillMdGenerator:
    """Tests for official format compliance."""

    def test_frontmatter_only_name_description(self):
        """Verify frontmatter has ONLY name and description."""
        ...

    def test_description_third_person(self):
        """Verify description is in third person."""
        ...

    def test_description_includes_what_and_when(self):
        """Verify description includes WHAT and WHEN."""
        ...

    def test_name_max_64_chars(self):
        """Verify name is max 64 characters."""
        ...

    def test_name_kebab_case(self):
        """Verify name is lowercase with hyphens."""
        ...

    def test_body_under_500_lines(self):
        """Verify body is under 500 lines."""
        ...

    def test_fix_validation_errors(self): ...

# test_validator.py
class TestSkillValidator:
    """Tests for official specification validation."""

    def test_valid_skill_passes(self): ...
    def test_extra_frontmatter_fields_rejected(self):
        """Verify unauthorized frontmatter fields are rejected."""
        ...
    def test_missing_name_fails(self): ...
    def test_missing_description_fails(self): ...
    def test_name_too_long_fails(self): ...
    def test_name_invalid_format_fails(self): ...
    def test_description_imperative_fails(self):
        """Verify imperative description is flagged."""
        ...
    def test_description_missing_when_flagged(self):
        """Verify missing WHEN trigger is flagged."""
        ...
    def test_body_over_500_lines_fails(self): ...
    def test_time_sensitive_content_warned(self): ...

# test_writer.py
class TestSkillWriter:
    def test_write_to_project_layer(self): ...
    def test_write_with_references(self): ...
    def test_write_with_scripts(self): ...
    def test_overwrite_protection(self): ...
    def test_permission_checking(self): ...
```

### 10.2 Integration Tests

```python
# tests/skills/creation/test_integration.py

class TestSkillCreationIntegration:
    """End-to-end integration tests with mocked LLM."""

    async def test_full_simple_skill_creation(self):
        """Test complete flow for simple skill with official format."""
        ...

    async def test_full_workflow_skill_creation(self):
        """Test complete flow for workflow skill."""
        ...

    async def test_validation_retry_recovery(self):
        """Test recovery from validation errors."""
        ...

    async def test_storage_layer_selection(self):
        """Test storage layer selection flow."""
        ...

    async def test_frontmatter_compliance(self):
        """Verify all generated skills have only name/description in frontmatter."""
        ...

    async def test_description_format_compliance(self):
        """Verify all descriptions are third person with WHAT + WHEN."""
        ...
```

### 10.3 Mock Strategy

```python
# Fixture for mocked LLM responses (compliant with official format)
@pytest.fixture
def mock_llm_responses():
    return {
        "intent_detection": {"is_skill_creation": True, "confidence": 0.9},
        "pattern": {"pattern": "simple", "suggested_name": "formatting-products"},
        "questions": {"questions": ["What inputs?", "When to use?"]},
        "description": "Formats product names by applying title case and expanding "
                      "abbreviations. Use when standardizing product names for "
                      "documentation or customer-facing materials.",
        "name": "formatting-product-names",
        "generation": """---
name: formatting-product-names
description: Formats product names by applying title case and expanding abbreviations. Use when standardizing product names for documentation or customer-facing materials.
---

# Formatting Product Names

Apply these formatting rules to product names:

1. Convert to Title Case
2. Remove extra whitespace
3. Expand abbreviations (PA -> Pro Analytics)

## Examples

- Input: "pa  enterprise" -> Output: "Pro Analytics Enterprise"
""",
    }

@pytest.fixture
def mock_llm_generator(mock_llm_responses):
    """Mock LLM generator that returns predefined responses."""
    generator = MagicMock(spec=LLMResponseGenerator)
    # Configure mock to return appropriate responses
    ...
    return generator
```

---

## 11. Implementation Phases

### Phase 1: MVP (2-3 weeks)

**Scope:**
- Simple skills only
- Project storage layer only
- **Strict official format compliance** (name/description only frontmatter)
- Basic validation

**Deliverables:**

| Week | Tasks |
|------|-------|
| 1 | ConversationManager, state machine, context models |
| 1 | RequirementsGatherer with Simple skill questions |
| 2 | SkillMdGenerator with official format compliance |
| 2 | SkillValidator with official spec validation |
| 2 | SkillWriter for Project layer |
| 3 | Integration, testing, bug fixes |

**Exit Criteria:**
- Can create Simple skills through conversation
- **100% frontmatter compliance** (only name and description)
- **100% description format compliance** (third person, WHAT + WHEN)
- 90%+ validation success on first attempt
- Unit test coverage > 80%

### Phase 2: Full Patterns (1-2 weeks)

**Scope:**
- Workflow skills
- Reference-heavy skills
- Script-based skills
- Progressive disclosure support

**Deliverables:**

| Week | Tasks |
|------|-------|
| 4 | Workflow skill generation templates |
| 4 | ResourceGenerator for references/ and scripts/ |
| 5 | Progressive disclosure structure validation |
| 5 | Integration testing for all patterns |

**Exit Criteria:**
- All 4 skill patterns supported
- References generated with proper structure
- Scripts generated and validated

### Phase 3: Storage and UX (1 week)

**Scope:**
- All storage layers (Personal, Enterprise)
- Permission checking
- Enhanced user experience
- Duplicate detection

**Deliverables:**

| Week | Tasks |
|------|-------|
| 6 | Storage layer selection dialogue |
| 6 | Permission checking implementation |
| 6 | Duplicate skill detection |
| 6 | Improved error messages and UX |

**Exit Criteria:**
- All storage layers supported
- Proper permission enforcement
- Duplicate warnings functional

### Phase 4: Polish and Documentation (1 week)

**Scope:**
- Skill update/modification support
- Evaluation-driven improvements
- Performance optimization

**Deliverables:**

| Week | Tasks |
|------|-------|
| 7 | Skill modification flow |
| 7 | Build eval suite for generated skills |
| 7 | Performance tuning |
| 7 | Final testing and release |

**Exit Criteria:**
- All spec requirements met
- Eval suite passing
- Ready for production

---

## 12. Risk Assessment

### 12.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| LLM generates unauthorized frontmatter fields | Medium | High | Post-processing strip, strict validation |
| LLM description not third person | Medium | Medium | Explicit prompt instructions, validation check |
| LLM description missing WHEN trigger | Medium | Medium | Explicit prompt with examples, validation check |
| Name generation exceeds 64 chars | Low | Low | Truncation with meaning preservation |
| Body exceeds 500 lines | Medium | Medium | Progressive disclosure to references/ |
| State machine complexity | Low | Medium | Thorough testing, explicit state transitions |

### 12.2 Integration Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| SkillParser incompatible with new validation | Low | High | Reuse existing parser, extend carefully |
| SkillLoader cache issues | Low | Low | Invalidate cache after skill creation |
| LLM API rate limits | Medium | Medium | Use existing fallback logic |

### 12.3 Contingency Plans

1. **LLM generates non-compliant format**: Post-processing layer to enforce compliance
2. **Description validation too strict**: Add "soft" warnings vs "hard" errors
3. **Body too long**: Automatic split to references/ with summary in SKILL.md

---

## 13. Alternative Approaches

### 13.1 Alternative A: Template-First Generation

**Approach**: Use rigid templates with LLM only for filling placeholders.

**Pros:**
- Higher validation success rate
- Guaranteed format compliance
- Lower LLM costs

**Cons:**
- Less flexible
- Skills may feel formulaic
- Limited to predefined patterns

**When to use**: If LLM generation quality is consistently poor.

### 13.2 Alternative B: Form-Based Collection

**Approach**: Use structured form/wizard instead of free-form conversation.

**Pros:**
- Guaranteed data collection
- Simpler implementation
- No intent detection needed

**Cons:**
- Less natural interaction
- Not "conversational"
- Doesn't match spec vision

**When to use**: If conversational UX proves too complex.

### 13.3 Alternative C: Two-Stage Generation

**Approach**: Generate outline first, then fill in details.

**Pros:**
- User can review structure before content
- Easier to fix structural issues
- More collaborative

**Cons:**
- More conversation turns
- Longer creation time
- More complex state management

**When to use**: For complex skills where structure validation is critical.

### 13.4 Recommendation

**Primary approach**: Full conversational with LLM generation (as specified).

**Fallback**: Template-first generation if validation rates drop below 80%.

The conversational approach aligns with the product vision and provides the best user experience for non-technical users. The risk of format compliance issues is manageable through strict post-processing and validation.

---

## Appendix A: Example Conversation Flow (Official Format)

```
User: "I want to create a skill that helps format product names"

Bot: "I'd be happy to help you create a product name formatting skill!

     To make sure I understand your needs:
     1. What specific formatting should be applied?
        (e.g., capitalization, spacing, abbreviations)
     2. Can you give me examples of before/after formatting?
     3. When should this skill be used? What triggers it?"

User: "Title case, remove spaces, expand abbreviations like PA -> Pro Analytics.
       Use it when writing docs or customer materials."

Bot: "Got it! I'll create a skill that:
     - Converts product names to Title Case
     - Removes extra whitespace
     - Expands abbreviations (PA -> Pro Analytics)

     Triggered when: Writing documentation or customer-facing materials

     Here's the preview:

     ---
     name: formatting-product-names
     description: Formats product names by applying title case, removing extra
       whitespace, and expanding abbreviations. Use when standardizing product
       names for documentation, reports, or customer-facing materials.
     ---

     # Formatting Product Names

     Apply these formatting rules to product names:
     1. Convert to Title Case
     2. Remove extra whitespace
     3. Expand abbreviations:
        - PA -> Pro Analytics
        - ES -> Enterprise Suite

     ## Examples
     - Input: 'pa  enterprise' -> Output: 'Pro Analytics Enterprise'

     Where would you like to save this skill?
     - Personal (~/.omniforge/skills/) - Only you can use it
     - Project (.omniforge/skills/) - Team members can use it"

User: "Save to project"

Bot: "Skill 'formatting-product-names' saved to .omniforge/skills/formatting-product-names/

     Your team's agents will now apply these formatting rules when standardizing
     product names for documentation or customer materials.

     To invoke manually: 'Use the formatting-product-names skill'"
```

---

## Appendix B: SKILL.md Templates (Official Format)

### Simple Skill Template

```markdown
---
name: {skill-name}
description: {Third person description of WHAT it does. Use when TRIGGER/CONTEXT.}
---

# {Skill Title}

{Brief overview - 1-2 sentences.}

## Instructions

{Clear, imperative instructions. Assume Claude is smart.}

## Examples

### Example 1
- Input: {input}
- Output: {output}
```

### Workflow Skill Template

```markdown
---
name: {skill-name}
description: {Third person description of WHAT workflow it provides. Use when TRIGGER/CONTEXT.}
---

# {Skill Title}

{Brief overview of the workflow.}

## Workflow

### Step 1: {Step Name}
- [ ] {Checklist item}
- [ ] {Checklist item}

### Step 2: {Step Name}
- [ ] {Checklist item}

## Error Handling

{What to do if steps fail.}
```

### Reference-Heavy Skill Template

```markdown
---
name: {skill-name}
description: {Third person description. Use when TRIGGER/CONTEXT.}
---

# {Skill Title}

{Brief overview.}

## Quick Start

{Essential instructions.}

## Detailed References

- **{Topic 1}**: See [references/{topic1}.md](references/{topic1}.md)
- **{Topic 2}**: See [references/{topic2}.md](references/{topic2}.md)
```

### Script-Based Skill Template

```markdown
---
name: {skill-name}
description: {Third person description. Use when TRIGGER/CONTEXT.}
---

# {Skill Title}

{Brief overview.}

## Available Scripts

### {script-name}.py
{Description of what the script does.}

Usage:
```bash
python scripts/{script-name}.py [arguments]
```

## When to Use Scripts vs Instructions

- Use scripts for: {deterministic operations}
- Use instructions for: {flexible tasks}
```

---

## Appendix C: Dependency Diagram

```
                    SkillCreationAgent
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
  ConversationManager   SkillWriter    BaseAgent (inherit)
          |                |
    +-----+-----+          |
    |           |          |
    v           v          v
Requirements  SkillMd   SkillStorage
Gatherer      Generator   Manager
    |           |          |
    |     +-----+-----+    |
    |     |           |    |
    v     v           v    v
LLMResponse   Skill      Storage
Generator     Validator   Config
    |           |
    |           v
    |       SkillParser
    |           |
    +-----+-----+
          |
          v
       litellm
```

---

## Appendix D: Official Format Compliance Checklist

**Frontmatter Validation:**
- [ ] Contains ONLY `name` and `description` fields
- [ ] No `tags`, `allowed-tools`, `hooks`, `priority`, or other fields
- [ ] YAML is valid

**Name Validation:**
- [ ] Max 64 characters
- [ ] Lowercase letters, numbers, hyphens only
- [ ] Starts with letter
- [ ] Not a reserved word
- [ ] Preferably gerund form (e.g., "processing-pdfs")

**Description Validation:**
- [ ] Non-empty
- [ ] Max 1024 characters
- [ ] Third person (not imperative)
- [ ] Includes WHAT the skill does
- [ ] Includes WHEN to use it (trigger context)
- [ ] No time-sensitive information

**Body Validation:**
- [ ] Under 500 lines
- [ ] Concise (assumes Claude is smart)
- [ ] Uses imperative form for instructions
- [ ] No time-sensitive information
- [ ] Consistent terminology

**Progressive Disclosure:**
- [ ] SKILL.md body is focused and concise
- [ ] Detailed content in references/ (one level deep)
- [ ] Scripts in scripts/ for deterministic operations
- [ ] Forward slashes for all paths

---

**Document History:**
- 2026-02-03: Initial version created
- 2026-02-03: Updated to align with official Anthropic Agent Skills guidelines
  - Changed frontmatter to ONLY name and description (removed tags, hooks, allowed-tools, etc.)
  - Added third-person description requirement
  - Added WHAT + WHEN requirement for descriptions
  - Updated validation rules to match official spec
  - Updated prompts for official format compliance
  - Replaced skill types with patterns (Simple, Workflow, Reference, Script)
  - Added progressive disclosure requirements
  - Updated templates to official format
  - Added compliance checklist

**Next Steps:**
1. Review technical plan with team
2. Confirm MVP scope
3. Begin Phase 1 implementation
4. Set up task tracking for implementation
