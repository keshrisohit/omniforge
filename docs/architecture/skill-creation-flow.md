# Skill Creation System - Detailed Flow

## State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> IDLE

    IDLE --> COLLECTING_REQUIREMENTS: User initiates skill creation

    COLLECTING_REQUIREMENTS --> ANALYZING_PATTERNS: Requirements complete
    COLLECTING_REQUIREMENTS --> ERROR: Collection fails

    ANALYZING_PATTERNS --> GENERATING_SKILL: Pattern detected
    ANALYZING_PATTERNS --> ERROR: Analysis fails

    GENERATING_SKILL --> GENERATING_SCRIPTS: Skill body generated
    GENERATING_SKILL --> ERROR: Generation fails

    GENERATING_SCRIPTS --> GENERATING_REFERENCES: Scripts complete
    GENERATING_SCRIPTS --> GENERATING_ASSETS: No scripts needed
    GENERATING_SCRIPTS --> ERROR: Script generation fails

    GENERATING_REFERENCES --> GENERATING_ASSETS: References complete
    GENERATING_REFERENCES --> VALIDATING: No references needed
    GENERATING_REFERENCES --> ERROR: Reference generation fails

    GENERATING_ASSETS --> VALIDATING: Assets complete
    GENERATING_ASSETS --> VALIDATING: No assets needed
    GENERATING_ASSETS --> ERROR: Asset generation fails

    VALIDATING --> COMPLETED: Validation passed
    VALIDATING --> ERROR: Validation failed

    ERROR --> COLLECTING_REQUIREMENTS: Retry from requirements
    ERROR --> IDLE: User cancels

    COMPLETED --> [*]

    note right of COLLECTING_REQUIREMENTS
        LLM generates questions
        Extracts user requirements
        Builds requirement state
    end note

    note right of ANALYZING_PATTERNS
        Detects 1 of 4 patterns:
        - SIMPLE
        - WORKFLOW
        - REFERENCE_HEAVY
        - SCRIPT_BASED
    end note

    note right of GENERATING_SKILL
        LLM generates SKILL.md
        Applies path normalization
        Converts paths to {baseDir}
    end note

    note right of VALIDATING
        Validates against Anthropic spec
        Checks frontmatter structure
        Verifies portability
    end note
```

## Component Interaction Diagram

```mermaid
graph TB
    subgraph "User Interface"
        User[User Input]
        CLI[CLI/API]
    end

    subgraph "Orchestration"
        Agent[SkillCreationAgent<br/>FSM Controller]
        StateManager[State Manager<br/>11 States]
    end

    subgraph "Core Components"
        Extractor[Requirements<br/>Extractor]
        Detector[Pattern<br/>Detector]
        Generator[Skill<br/>Generator]
        Validator[Skill<br/>Validator]
    end

    subgraph "LLM Integration"
        LLMGen[LLM Response<br/>Generator]
        Prompts[Prompt<br/>Templates]
    end

    subgraph "File Generation"
        SkillMd[SKILL.md<br/>Generator]
        ScriptGen[Script<br/>Generator]
        RefGen[Reference<br/>Generator]
        AssetGen[Asset<br/>Generator]
    end

    subgraph "Post-Processing"
        PathNorm[Path<br/>Normalizer]
        Formatter[Content<br/>Formatter]
    end

    subgraph "Storage"
        SkillRepo[Skill<br/>Repository]
        FileSystem[File<br/>System]
    end

    %% User flow
    User --> CLI
    CLI --> Agent

    %% FSM control
    Agent --> StateManager
    StateManager --> Extractor
    StateManager --> Detector
    StateManager --> Generator
    StateManager --> Validator

    %% Requirements extraction
    Extractor --> LLMGen
    LLMGen --> Prompts
    Prompts --> LLMGen

    %% Pattern detection
    Detector --> Extractor

    %% Generation flow
    Generator --> SkillMd
    Generator --> ScriptGen
    Generator --> RefGen
    Generator --> AssetGen

    SkillMd --> LLMGen
    ScriptGen --> LLMGen
    RefGen --> LLMGen
    AssetGen --> LLMGen

    %% Post-processing
    SkillMd --> PathNorm
    ScriptGen --> PathNorm
    RefGen --> PathNorm
    AssetGen --> PathNorm

    PathNorm --> Formatter

    %% Validation
    Formatter --> Validator

    %% Storage
    Validator --> SkillRepo
    Validator --> FileSystem

    %% Results
    SkillRepo --> CLI
    FileSystem --> CLI
    CLI --> User

    %% Styling
    classDef userClass fill:#e1f5ff,stroke:#01579b
    classDef orchestrationClass fill:#fff9c4,stroke:#f57f17
    classDef coreClass fill:#c8e6c9,stroke:#2e7d32
    classDef llmClass fill:#f8bbd0,stroke:#c2185b
    classDef genClass fill:#d1c4e9,stroke:#512da8
    classDef processClass fill:#ffccbc,stroke:#d84315
    classDef storageClass fill:#b2dfdb,stroke:#00695c

    class User,CLI userClass
    class Agent,StateManager orchestrationClass
    class Extractor,Detector,Generator,Validator coreClass
    class LLMGen,Prompts llmClass
    class SkillMd,ScriptGen,RefGen,AssetGen genClass
    class PathNorm,Formatter processClass
    class SkillRepo,FileSystem storageClass
```

## Detailed Sequence Flow

```mermaid
sequenceDiagram
    participant User
    participant Agent as SkillCreationAgent
    participant State as StateManager
    participant Extractor as RequirementsExtractor
    participant LLM as LLMGenerator
    participant Detector as PatternDetector
    participant Generator as SkillGenerator
    participant PathNorm as PathNormalizer
    participant Validator as SkillValidator
    participant Storage as SkillRepository

    User->>Agent: Create skill request
    Agent->>State: Set IDLE → COLLECTING_REQUIREMENTS

    %% Requirements Collection Loop
    loop Until requirements complete
        Agent->>Extractor: Get next question
        Extractor->>LLM: Generate question prompt
        LLM-->>Extractor: Question
        Extractor->>User: Ask question
        User->>Extractor: Provide answer
        Extractor->>LLM: Extract structured data
        LLM-->>Extractor: Requirement fields
        Extractor->>State: Update requirements
    end

    Agent->>State: Set COLLECTING → ANALYZING_PATTERNS

    %% Pattern Analysis
    Agent->>Detector: Analyze requirements
    Detector->>Detector: Check for patterns:<br/>1. SCRIPT_BASED (scripts/CLI tools)<br/>2. REFERENCE_HEAVY (docs/data)<br/>3. WORKFLOW (multi-step)<br/>4. SIMPLE (default)
    Detector-->>Agent: Pattern identified

    Agent->>State: Set ANALYZING → GENERATING_SKILL

    %% Skill Generation
    Agent->>Generator: Generate SKILL.md
    Generator->>LLM: Generate skill body
    LLM-->>Generator: Skill content
    Generator->>PathNorm: Normalize paths
    PathNorm->>PathNorm: Convert to {baseDir}:<br/>/home/user/skill → {baseDir}<br/>python /path/script.py → python {baseDir}/script.py
    PathNorm-->>Generator: Normalized content

    alt Pattern includes scripts
        Agent->>State: Set GENERATING → GENERATING_SCRIPTS
        Agent->>Generator: Generate scripts
        Generator->>LLM: Generate script content
        LLM-->>Generator: Script files
        Generator->>PathNorm: Normalize script paths
        PathNorm-->>Generator: Normalized scripts
    end

    alt Pattern includes references
        Agent->>State: Set GENERATING → GENERATING_REFERENCES
        Agent->>Generator: Generate references
        Generator->>LLM: Generate reference docs
        LLM-->>Generator: Reference files
        Generator->>PathNorm: Normalize reference paths
        PathNorm-->>Generator: Normalized references
    end

    alt Pattern includes assets
        Agent->>State: Set GENERATING → GENERATING_ASSETS
        Agent->>Generator: Generate assets
        Generator->>LLM: Generate asset files
        LLM-->>Generator: Asset files
        Generator->>PathNorm: Normalize asset paths
        PathNorm-->>Generator: Normalized assets
    end

    Agent->>State: Set GENERATING → VALIDATING

    %% Validation
    Agent->>Validator: Validate skill
    Validator->>Validator: Check frontmatter
    Validator->>Validator: Verify structure
    Validator->>Validator: Check portability

    alt Validation passes
        Validator-->>Agent: Valid
        Agent->>State: Set VALIDATING → COMPLETED
        Agent->>Storage: Save skill files
        Storage-->>Agent: Saved
        Agent->>User: Skill created successfully
    else Validation fails
        Validator-->>Agent: Errors
        Agent->>State: Set VALIDATING → ERROR
        Agent->>User: Validation errors
        User->>Agent: Fix and retry
        Agent->>State: Set ERROR → COLLECTING_REQUIREMENTS
    end
```

## Skill Patterns and Detection Logic

```mermaid
flowchart TD
    Start[Analyze Requirements] --> CheckScripts{Contains scripts,<br/>CLI tools, or<br/>automation?}

    CheckScripts -->|Yes| ScriptBased[SCRIPT_BASED Pattern]
    CheckScripts -->|No| CheckDocs{Contains extensive<br/>documentation,<br/>references, or<br/>knowledge base?}

    CheckDocs -->|Yes| RefHeavy[REFERENCE_HEAVY Pattern]
    CheckDocs -->|No| CheckSteps{Contains multi-step<br/>workflow or<br/>process?}

    CheckSteps -->|Yes| Workflow[WORKFLOW Pattern]
    CheckSteps -->|No| Simple[SIMPLE Pattern]

    ScriptBased --> SetTools1[Required Tools:<br/>bash, read, write]
    RefHeavy --> SetTools2[Required Tools:<br/>read, grep, glob]
    Workflow --> SetTools3[Required Tools:<br/>read, write]
    Simple --> SetTools4[Required Tools:<br/>read]

    SetTools1 --> Generate[Generate Skill]
    SetTools2 --> Generate
    SetTools3 --> Generate
    SetTools4 --> Generate

    Generate --> Normalize[Path Normalization]
    Normalize --> Validate[Validation]
    Validate --> Done[Completed]

    style ScriptBased fill:#ffcccc
    style RefHeavy fill:#ccffcc
    style Workflow fill:#ccccff
    style Simple fill:#ffffcc
```

## Path Normalization Examples

### Before Normalization
```markdown
## Scripts

Run the analysis script:
```bash
python /Users/dev/omniforge/skills/my-skill/scripts/analyze.py
```

See the documentation at:
/home/user/omniforge/skills/my-skill/references/guide.md
```

### After Normalization
```markdown
## Scripts

Run the analysis script:
```bash
python {baseDir}/scripts/analyze.py
```

See the documentation at:
{baseDir}/references/guide.md
```

## Validation Rules

The SkillValidator enforces:

1. **Frontmatter Structure**
   - Required: `name`, `description`
   - Optional: `allowed-tools`, `priority`, `tags`
   - YAML format correctness

2. **Description Standards**
   - Third-person voice
   - Describes WHAT, not HOW
   - Clear activation triggers (WHEN)

3. **Portability**
   - No absolute paths (must use `{baseDir}`)
   - Platform-independent commands
   - No hardcoded credentials or secrets

4. **Content Organization**
   - Clear section structure
   - Concrete examples
   - Actionable guidance

5. **Tool Permissions**
   - All required tools declared
   - Minimal permission scope
   - Security-conscious defaults

## Key Components Details

### SkillCreationAgent (src/omniforge/skills/creation/agent.py)
- FSM controller orchestrating the entire creation process
- Manages state transitions across 11 states
- Coordinates LLM interactions and component calls
- ~500 LOC

### RequirementsExtractor (src/omniforge/skills/creation/extractor.py)
- Generates contextual questions for users
- Extracts structured requirement data from responses
- Builds comprehensive requirement state
- ~400 LOC

### PatternDetector (src/omniforge/skills/creation/detector.py)
- Analyzes requirements to identify skill patterns
- Maps patterns to required tools and resources
- Determines generation strategy
- ~300 LOC

### SkillGenerator (src/omniforge/skills/creation/generator.py)
- Generates SKILL.md content via LLM
- Creates scripts, references, and assets
- Applies path normalization
- Formats final output
- ~1,200 LOC

### PathNormalizer (in SkillGenerator)
- Detects absolute path patterns
- Converts to `{baseDir}` placeholder
- Handles multiple path formats (Unix, Windows)
- Ensures portability
- ~150 LOC

### SkillValidator (src/omniforge/skills/creation/validator.py)
- Validates against Anthropic specification
- Checks frontmatter structure and content
- Verifies portability (no hardcoded paths)
- Provides detailed error messages
- ~600 LOC

## LLM Prompts Structure

### Question Generation Prompt
```python
GENERATE_QUESTION_PROMPT = """
Given the current skill requirements:
{current_requirements}

Generate the next question to ask the user.
Focus on: {focus_area}

Return JSON:
{
  "question": "...",
  "rationale": "..."
}
"""
```

### Skill Body Generation Prompt
```python
GENERATE_SKILL_BODY_PROMPT = """
Generate a SKILL.md file for:
- Name: {name}
- Description: {description}
- Pattern: {pattern}

CRITICAL: Use {baseDir} for all paths.

Requirements:
{requirements}

Follow Anthropic Claude Skills specification.
"""
```

### Script Generation Prompt
```python
GENERATE_SCRIPT_PROMPT = """
Generate a {language} script for:
{script_purpose}

CRITICAL: Use {baseDir} for all file references.

Example:
# Good: config_path = os.path.join(os.environ['baseDir'], 'config.yaml')
# Bad: config_path = '/home/user/skill/config.yaml'
"""
```

## File Output Structure

```
skills/my-skill/
├── SKILL.md                 # Main skill definition
├── scripts/                 # Generated scripts (if SCRIPT_BASED)
│   ├── main.py
│   └── utils.py
├── references/              # Reference documentation (if REFERENCE_HEAVY)
│   ├── guide.md
│   └── examples.md
└── assets/                  # Asset files (if needed)
    ├── template.json
    └── data.csv
```

## Performance Metrics

| Operation | Average Time | LLM Calls |
|-----------|--------------|-----------|
| Requirements Collection | 30-60s | 3-7 |
| Pattern Detection | <1s | 0 |
| Skill Generation | 10-20s | 1 |
| Script Generation | 5-10s each | 1 per script |
| Reference Generation | 5-10s each | 1 per reference |
| Validation | <1s | 0 |
| **Total** | **60-120s** | **5-15** |

## Error Handling

The system handles errors at multiple levels:

1. **State Level**: ERROR state for recovery
2. **Component Level**: Try-catch with detailed logging
3. **LLM Level**: Retry logic with backoff
4. **Validation Level**: Detailed error messages for user correction

## Recent Improvements (February 2026)

✅ **Path Normalization**: Comprehensive `{baseDir}` conversion
✅ **Enhanced Prompts**: Explicit portability requirements
✅ **Dual Validation**: LLM prompts + post-processing
✅ **Pattern Detection**: 4 distinct patterns
✅ **FSM Refinement**: 11-state workflow
✅ **Test Coverage**: 203 passing tests

## Known Gaps

⚠️ **Tool Permissions**: `determine_required_tools()` is stubbed
⚠️ **Reference Generation**: Missing directory creation
⚠️ **Asset Generation**: Missing directory creation
⚠️ **Interactive Editing**: No in-flow editing capability
