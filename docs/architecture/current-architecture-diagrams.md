# OmniForge Current Architecture Diagrams

## Overview

This document provides visual diagrams of the current OmniForge architecture, highlighting areas with SOLID principle violations.

---

## 1. Tool Execution System (Current State)

### Component Diagram

```mermaid
graph TB
    subgraph "ReasoningEngine"
        RE[ReasoningEngine<br/>Orchestration]
    end

    subgraph "ToolExecutor - VIOLATION: SRP"
        TE[ToolExecutor<br/>173-270 lines!]
        TE_EXEC[Tool Execution<br/>+ Retry Logic]
        TE_SKILL[Skill Management<br/>+ Stack Tracking]
        TE_RATE[Rate Limiting<br/>+ Quota Check]
        TE_COST[Cost Tracking<br/>+ Recording]
        TE_CHAIN[Chain Recording<br/>+ Step Creation]

        TE --> TE_EXEC
        TE --> TE_SKILL
        TE --> TE_RATE
        TE --> TE_COST
        TE --> TE_CHAIN
    end

    subgraph "Dependencies"
        REG[ToolRegistry]
        RL[RateLimiter<br/>Optional]
        CT[CostTracker<br/>Optional]
        CHAIN[ReasoningChain<br/>Optional]
    end

    subgraph "Tools"
        BASH[BashTool]
        READ[ReadTool]
        LLM[LLMTool]
    end

    RE -->|"self._executor._registry<br/>❌ VIOLATION: DIP"| TE
    TE --> REG
    TE -.->|optional| RL
    TE -.->|optional| CT
    TE -.->|optional| CHAIN

    REG --> BASH
    REG --> READ
    REG --> LLM

    style TE fill:#ffcccc
    style TE_EXEC fill:#ffe6e6
    style TE_SKILL fill:#ffe6e6
    style TE_RATE fill:#ffe6e6
    style TE_COST fill:#ffe6e6
    style TE_CHAIN fill:#ffe6e6
```

### Problems Highlighted
- 🔴 **SRP Violation**: ToolExecutor has 5+ responsibilities
- 🔴 **DIP Violation**: ReasoningEngine accesses `_executor._registry` (private member)
- 🔴 **ISP Violation**: All dependencies required even when not needed

---

## 2. Database System (Current State)

### Component Diagram

```mermaid
graph TB
    subgraph "Application Code"
        APP[Application]
    end

    subgraph "Database - VIOLATION: OCP"
        DB[Database Class]
        INIT[_initialize_engines<br/>Creates BOTH engines]
        DETECT[_is_async_context<br/>❌ Runtime Detection]
        SESSION[session<br/>Lines 104-121<br/>Complex Branching]

        DB --> INIT
        DB --> DETECT
        DB --> SESSION

        SESSION -->|if async| ASYNC_PATH[AsyncSession Path]
        SESSION -->|else| SYNC_PATH[Session Path<br/>❌ Cannot extend!]
    end

    subgraph "SQLAlchemy"
        SYNC_ENG[Sync Engine]
        ASYNC_ENG[Async Engine]
        SYNC_SESS[Session]
        ASYNC_SESS[AsyncSession]
    end

    APP -->|db.session| DB

    INIT --> SYNC_ENG
    INIT --> ASYNC_ENG
    ASYNC_PATH --> ASYNC_SESS
    SYNC_PATH --> SYNC_SESS

    style DB fill:#ffcccc
    style DETECT fill:#ffe6e6
    style SESSION fill:#ffe6e6
    style SYNC_PATH fill:#ffe6e6
```

### Problems Highlighted
- 🔴 **OCP Violation**: Cannot add new session patterns without modifying code
- 🔴 **SRP Violation**: Handles engine creation, session management, AND runtime detection
- 🔴 **Type Safety**: Union[Session, AsyncSession] loses type information
- 🔴 **Performance**: Runtime context detection on every session creation

---

## 3. Tool Definition System (Current State)

### Class Diagram

```mermaid
classDiagram
    class ToolDefinition {
        ❌ ISP VIOLATION: Fat Interface
        +name: str
        +type: ToolType
        +description: str
        +parameters: list~ToolParameter~
        +timeout_ms: Optional~int~
        +retry_config: Optional~ToolRetryConfig~
        +cache_ttl_seconds: Optional~int~
        +visibility: ToolVisibilityConfig
        +permissions: ToolPermissions
        +cost_estimate: Optional~float~
        +tags: list~str~
    }

    class BashTool {
        Uses: name, type, description, timeout_ms
        ❌ Forced to provide: retry_config, cache_ttl, permissions
        Even though not needed!
    }

    class ReadTool {
        Uses: name, type, description
        ❌ Forced to provide: timeout_ms, retry_config, permissions
        Even though read-only!
    }

    class LLMTool {
        Uses: ALL fields
        Only tool that needs everything!
    }

    BashTool --> ToolDefinition : "forced dependency"
    ReadTool --> ToolDefinition : "forced dependency"
    LLMTool --> ToolDefinition : "needs all"

    note for ToolDefinition "11 configuration concerns\nForced on ALL tools\nEven simple ones!"
```

### Problems Highlighted
- 🔴 **ISP Violation**: Tools forced to implement 11 config concerns
- 🔴 **Complexity**: Simple tools need complex configuration
- 🔴 **Coupling**: All tools coupled to full definition model

---

## 4. LLM Tool Provider Setup (Current State)

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant LLMTool
    participant Setup as _setup_litellm()
    participant Env as Environment

    Client->>LLMTool: __init__(config)
    LLMTool->>Setup: _setup_litellm()

    Note over Setup: ❌ OCP VIOLATION<br/>Hardcoded provider logic

    Setup->>Setup: if provider == "azure":
    Setup->>Env: os.environ["AZURE_API_BASE"] = ...
    Setup->>Env: os.environ["AZURE_API_VERSION"] = ...

    Setup->>Setup: if provider == "openai":
    Setup->>Env: os.environ["OPENAI_ORGANIZATION"] = ...

    Setup->>Setup: if provider == "anthropic":
    Setup->>Env: os.environ["ANTHROPIC_API_KEY"] = ...

    Note over Setup: To add new provider:<br/>❌ Must modify this method!

    Setup-->>LLMTool: configured
    LLMTool-->>Client: ready
```

### Problems Highlighted
- 🔴 **OCP Violation**: Adding new provider requires modifying `_setup_litellm()`
- 🔴 **Extensibility**: Cannot add providers without code changes
- 🔴 **Testability**: Difficult to test provider-specific logic

---

## 5. Agent-Tool-Registry Dependencies (Current State)

### Dependency Graph

```mermaid
graph LR
    subgraph "High-Level Modules"
        RE[ReasoningEngine]
        SA[SimpleAutonomousAgent]
        CA[CoTAgent]
    end

    subgraph "Low-Level Modules"
        TE[ToolExecutor<br/>Concrete Class]
        TR[ToolRegistry<br/>Concrete Class]
        LLC[LLMConfig<br/>Concrete Class]
    end

    subgraph "❌ DIP VIOLATIONS"
        V1["RE → TE<br/>Depends on concrete<br/>executor"]
        V2["RE → TE._registry<br/>Accesses private<br/>member"]
        V3["LLMTool → LLMConfig<br/>Depends on concrete<br/>config"]
    end

    RE -->|"Type: ToolExecutor"| TE
    RE -.->|"self._executor._registry"| TR
    SA --> TR
    CA --> TR

    TE --> TR

    style V1 fill:#ffcccc
    style V2 fill:#ffcccc
    style V3 fill:#ffcccc
    style TE fill:#ffe6e6
    style TR fill:#ffe6e6
    style LLC fill:#ffe6e6
```

### Problems Highlighted
- 🔴 **DIP Violation**: High-level modules depend on concrete implementations
- 🔴 **Coupling**: Direct access to private members (`_registry`)
- 🔴 **Testability**: Cannot mock easily - need real instances

---

## 6. Streaming Tool Hierarchy (Current State)

### Class Hierarchy Diagram

```mermaid
classDiagram
    class BaseTool {
        <<abstract>>
        +definition: ToolDefinition
        +execute(context, args)* ToolResult
        +generate_summary() str
    }

    class StreamingTool {
        <<abstract>>
        ❌ LSP VIOLATION
        +execute(context, args)* ToolResult
        +execute_streaming(context, args)* AsyncIterator
        +generate_summary() str
    }

    class BashTool {
        +execute() ToolResult
        ❌ Does not stream
    }

    class LLMTool {
        +execute() ToolResult
        +execute_streaming() AsyncIterator
        ✅ Both methods
    }

    BaseTool <|-- StreamingTool
    BaseTool <|-- BashTool
    StreamingTool <|-- LLMTool

    note for StreamingTool "Cannot substitute for BaseTool<br/>Adds new method<br/>Breaks Liskov Substitution"

    note for BashTool "Client code must check:<br/>if isinstance(tool, StreamingTool)<br/>❌ Violates polymorphism"
```

### Problems Highlighted
- 🔴 **LSP Violation**: StreamingTool not substitutable for BaseTool
- 🔴 **Polymorphism**: Need runtime type checks
- 🔴 **Parallel Hierarchies**: Two execution patterns instead of unified

---

## 7. Complete System Architecture (Current State)

### High-Level Architecture

```mermaid
graph TB
    subgraph "API Layer"
        API[FastAPI Routes]
        MW[Middleware]
    end

    subgraph "Agent Layer"
        SA[SimpleAutonomousAgent]
        CA[CoTAgent]
        RE[ReasoningEngine]
    end

    subgraph "Tool Layer - ❌ MULTIPLE VIOLATIONS"
        TE[ToolExecutor<br/>❌ SRP]
        TR[ToolRegistry]
        TOOLS[Built-in Tools]
    end

    subgraph "Storage Layer - ❌ OCP VIOLATION"
        DB[Database<br/>❌ Sync/Async Mixed]
        REPO[Repositories]
    end

    subgraph "LLM Layer"
        LLM_CFG[LLMConfig<br/>❌ DIP]
        LLM_TOOL[LLMTool<br/>❌ OCP]
    end

    subgraph "Enterprise"
        RL[RateLimiter]
        CT[CostTracker]
    end

    API --> SA
    API --> CA
    SA --> RE
    CA --> RE

    RE -->|"❌ _executor._registry"| TE
    TE --> TR
    TE -.-> RL
    TE -.-> CT
    TR --> TOOLS

    TOOLS --> LLM_TOOL
    LLM_TOOL --> LLM_CFG

    REPO --> DB
    TE -.-> DB

    style TE fill:#ffcccc
    style DB fill:#ffcccc
    style LLM_TOOL fill:#ffcccc
    style LLM_CFG fill:#ffcccc
```

### Legend
- 🔴 Red Components: SOLID Violations
- Solid Lines: Direct Dependencies
- Dashed Lines: Optional Dependencies
- ❌: Specific Violation Type

---

## 8. Data Flow (Current State)

### Request Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant Agent as SimpleAutonomousAgent
    participant Engine as ReasoningEngine
    participant Executor as ToolExecutor (❌ SRP)
    participant Tool as BashTool
    participant DB as Database (❌ OCP)

    User->>API: POST /chat
    API->>Agent: run(prompt)
    Agent->>Engine: reason(task)

    loop Reasoning Loop
        Engine->>Engine: call_llm()
        Engine->>Executor: execute(tool_name, args)

        Executor->>Executor: ❌ Check rate limit<br/>❌ Validate skills<br/>❌ Record call<br/>❌ Track cost<br/>❌ Execute tool
        Executor->>Tool: execute()
        Tool-->>Executor: ToolResult

        Executor->>Executor: ❌ Record result<br/>❌ Track cost
        Executor-->>Engine: ToolResult

        Engine->>DB: ❌ session()<br/>Runtime detection!
        DB-->>Engine: Union[Session, AsyncSession]
        Note over DB: Type safety lost!
    end

    Engine-->>Agent: final_answer
    Agent-->>API: response
    API-->>User: JSON response
```

---

## Metrics Summary

### Current Architecture Issues

| Layer | Violations | Complexity | Coupling |
|-------|-----------|------------|----------|
| Tool Execution | SRP, DIP, ISP | Very High (15+) | Very High |
| Database | OCP, SRP | High (12+) | High |
| Tool Definition | ISP | Medium | High |
| LLM Tool | OCP, DIP | Medium | Medium |
| Agent Layer | DIP | Medium | High |

### Technical Debt

```mermaid
pie title SOLID Violations by Type
    "SRP Violations" : 4
    "OCP Violations" : 3
    "LSP Violations" : 2
    "ISP Violations" : 3
    "DIP Violations" : 4
```

### Cyclomatic Complexity Hot Spots

```mermaid
graph LR
    A[ToolExecutor.execute<br/>Complexity: 15+] --> B[Database.session<br/>Complexity: 12+]
    B --> C[LLMTool._setup_litellm<br/>Complexity: 10+]
    C --> D[PromptValidator.validate<br/>Complexity: 8+]

    style A fill:#ff0000,color:#fff
    style B fill:#ff6666,color:#fff
    style C fill:#ffaa00,color:#fff
    style D fill:#ffdd00
```

---

## Next Steps

See the following documents for refactoring plans:
1. `01-tool-executor-refactoring-plan.md` - Fix SRP violations in ToolExecutor
2. `02-database-refactoring-plan.md` - Fix OCP violations in Database
3. `03-proposed-architecture-diagrams.md` - See improved architecture
