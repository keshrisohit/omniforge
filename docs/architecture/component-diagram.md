# OmniForge System Component Diagram

This diagram represents the current state of the OmniForge architecture as of February 2026.

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        CLI[CLI Interface]
        Frontend[Frontend<br/>React/Next.js<br/><i>Pre-Alpha</i>]
        APIClient[External API Clients]
    end

    subgraph "API Gateway Layer"
        FastAPI[FastAPI Application]

        subgraph "Middleware Stack"
            CORS[CORS Middleware]
            Tenant[Tenant Middleware]
            CorrelationID[Correlation ID Middleware]
            ErrorHandler[Error Handler Middleware]
        end
    end

    subgraph "API Routes Layer"
        ChatRoute[/api/v1/chat]
        AgentsRoute[/api/v1/agents]
        BuilderRoute[/api/v1/builder-agents]
        ConvoRoute[/api/v1/conversation]
        TasksRoute[/api/v1/tasks]
        PromptsRoute[/api/v1/prompts]
        ChainsRoute[/api/v1/chains]
        OAuthRoute[/api/v1/oauth]
        HealthRoute[/health]
    end

    subgraph "Core Domain Layer"
        subgraph "Agent Domain"
            MasterAgent[Master Agent<br/>Orchestrator]
            AgentRegistry[Agent Registry]
            A2AProtocol[A2A Protocol<br/>Agent-to-Agent Comm]
            BaseAgent[Base Agent Interface]
        end

        subgraph "Skills Domain"
            SkillCreation[Skill Creation System<br/>11-State FSM]
            SkillLibrary[40+ Pre-built Skills]
            SkillValidator[Skill Validator]
            SkillGenerator[Skill Generator]
            PatternDetector[Pattern Detector]
        end

        subgraph "Orchestration Domain"
            OrchClient[Orchestration Client]
            Discovery[Service Discovery]
            Router[Request Router]
            Execution[Execution Engine<br/>Task Scheduler]
        end

        subgraph "Chat Domain"
            ChatManager[Chat Manager]
            ConvoManager[Conversation Manager]
            LLMGenerator[LLM Response Generator]
            StreamHandler[Stream Handler]
        end

        subgraph "Tools Domain"
            ToolExecutor[Tool Executor]
            ToolRegistry[Tool Registry]
            BuiltinTools[Built-in Tools]
        end

        subgraph "Builder Domain"
            BuilderOrch[Builder Orchestrator]
            SkillBuilder[Skill Builder]
            RepoBuilder[Repository Builder]
        end
    end

    subgraph "Infrastructure Layer"
        subgraph "LLM Abstraction"
            LLMLayer[LLM Abstraction Layer]
            LiteLLM[LiteLLM Provider]
            CostTracker[Cost Tracker]
            FallbackChain[Fallback Chain]
        end

        subgraph "Storage Layer"
            Database[Database Layer<br/>SQLAlchemy]
            RepoPattern[Repository Pattern]
            AsyncEngine[Async/Sync Engine]
        end

        subgraph "Security & Enterprise"
            RBAC[RBAC System]
            TenantIsolation[Tenant Isolation]
            Auth[Authentication]
            Governance[Governance]
            Auditing[Auditing]
            RateLimiter[Rate Limiter]
        end

        subgraph "Observability"
            Logging[Structured Logging]
            Metrics[Metrics Collector]
            Monitoring[Monitoring]
        end

        subgraph "Prompts & Routing"
            PromptMgmt[Prompt Management]
            PromptRegistry[Prompt Registry]
            RoutingEngine[Routing Engine]
        end
    end

    subgraph "External Systems"
        LLMProviders[LLM Providers<br/>OpenAI, Anthropic, etc.]
        DB[(Database<br/>SQLite/PostgreSQL)]
        OAuth[OAuth Providers]
    end

    %% Client connections
    CLI --> FastAPI
    Frontend -.-> FastAPI
    APIClient --> FastAPI

    %% Middleware flow
    FastAPI --> CORS
    CORS --> Tenant
    Tenant --> CorrelationID
    CorrelationID --> ErrorHandler

    %% Routes to domains
    ChatRoute --> ChatManager
    AgentsRoute --> MasterAgent
    BuilderRoute --> BuilderOrch
    ConvoRoute --> ConvoManager
    TasksRoute --> Execution
    PromptsRoute --> PromptMgmt
    ChainsRoute --> OrchClient
    OAuthRoute --> Auth

    %% Agent domain connections
    MasterAgent --> AgentRegistry
    MasterAgent --> A2AProtocol
    AgentRegistry --> BaseAgent
    MasterAgent --> Execution

    %% Skills connections
    SkillCreation --> PatternDetector
    SkillCreation --> SkillGenerator
    SkillCreation --> SkillValidator
    SkillCreation --> LLMGenerator
    AgentRegistry --> SkillLibrary

    %% Orchestration connections
    OrchClient --> Discovery
    OrchClient --> Router
    Router --> Execution

    %% Chat connections
    ChatManager --> LLMGenerator
    ChatManager --> StreamHandler
    ConvoManager --> ChatManager
    LLMGenerator --> LLMLayer

    %% Tools connections
    ToolExecutor --> ToolRegistry
    ToolRegistry --> BuiltinTools
    MasterAgent --> ToolExecutor

    %% Builder connections
    BuilderOrch --> SkillBuilder
    BuilderOrch --> RepoBuilder
    SkillBuilder --> SkillCreation

    %% LLM layer connections
    LLMLayer --> LiteLLM
    LLMLayer --> CostTracker
    LLMLayer --> FallbackChain
    LiteLLM --> LLMProviders

    %% Storage connections
    Database --> AsyncEngine
    Database --> RepoPattern
    RepoPattern --> DB

    %% Security connections
    Tenant --> TenantIsolation
    Auth --> OAuth
    RBAC --> TenantIsolation

    %% All domains use storage
    MasterAgent --> RepoPattern
    SkillLibrary --> RepoPattern
    ChatManager --> RepoPattern
    PromptMgmt --> RepoPattern

    %% All domains use observability
    MasterAgent -.-> Logging
    ChatManager -.-> Logging
    LLMLayer -.-> Metrics
    Execution -.-> Metrics

    %% Styling
    classDef prealpha fill:#ffcccc,stroke:#cc0000
    classDef mvp fill:#ffffcc,stroke:#cccc00
    classDef production fill:#ccffcc,stroke:#00cc00
    classDef external fill:#e6f3ff,stroke:#0066cc

    class Frontend prealpha
    class SkillCreation,BuilderOrch mvp
    class FastAPI,MasterAgent,Database,RBAC,LLMLayer production
    class LLMProviders,DB,OAuth external
```

## Component Details

### Client Layer
- **CLI Interface**: Command-line interface for developer interaction (Production)
- **Frontend**: React/Next.js web interface (Pre-Alpha - minimal scaffolding only)
- **External API Clients**: Third-party integrations via REST API

### API Gateway Layer
- **FastAPI Application**: Main web framework with lifecycle management
- **Middleware Stack**:
  - CORS: Cross-origin resource sharing
  - Tenant: Multi-tenancy isolation
  - Correlation ID: Request tracing
  - Error Handler: Consistent error responses

### API Routes
- 9 route modules providing REST endpoints
- All routes prefixed with `/api/v1` except `/health`
- Streaming support for chat endpoints

### Core Domain Layer

#### Agent Domain (Production)
- **Master Agent**: Central orchestrator (957 LOC)
- **Agent Registry**: Service discovery for agents
- **A2A Protocol**: Agent-to-Agent communication protocol
- **Base Agent Interface**: Common interface for all agents

#### Skills Domain (MVP)
- **Skill Creation System**: 11-state FSM for conversational skill building (4,656 LOC)
- **Skill Library**: 40+ pre-built skills across multiple domains
- **Pattern Detector**: Identifies 4 skill patterns (SIMPLE, WORKFLOW, REFERENCE_HEAVY, SCRIPT_BASED)
- **Skill Generator**: LLM-powered SKILL.md generation
- **Skill Validator**: Anthropic specification compliance

#### Orchestration Domain (Production)
- **Orchestration Client**: Request coordination
- **Service Discovery**: Dynamic service location
- **Request Router**: Intelligent routing
- **Execution Engine**: Task scheduling and lifecycle management

#### Chat Domain (Production)
- **Chat Manager**: Conversation orchestration
- **Conversation Manager**: Multi-turn conversation state
- **LLM Response Generator**: Response generation with multiple providers
- **Stream Handler**: Server-sent events for streaming

#### Tools Domain (Production)
- **Tool Executor**: Executes registered tools
- **Tool Registry**: Central tool registration
- **Built-in Tools**: Pre-built tool implementations

#### Builder Domain (MVP)
- **Builder Orchestrator**: Coordinates building tasks
- **Skill Builder**: Builds new skills
- **Repository Builder**: Creates skill repositories

### Infrastructure Layer

#### LLM Abstraction (Production)
- **LLM Layer**: Provider-agnostic abstraction
- **LiteLLM**: Multi-provider integration (OpenAI, Anthropic, etc.)
- **Cost Tracker**: Token usage and cost monitoring
- **Fallback Chain**: Provider failover support

#### Storage Layer (Production)
- **Database Layer**: Dual sync/async SQLAlchemy
- **Repository Pattern**: Domain-driven design
- **Async/Sync Engine**: Supports aiosqlite, asyncpg, sqlite

#### Security & Enterprise (Production)
- **RBAC**: Role-based access control
- **Tenant Isolation**: Multi-tenancy security
- **Authentication**: User authentication with OAuth support
- **Governance**: Enterprise governance policies
- **Auditing**: Audit trail for compliance
- **Rate Limiter**: API rate limiting

#### Observability (Production)
- **Structured Logging**: JSON logging with correlation IDs
- **Metrics Collector**: Performance and usage metrics
- **Monitoring**: Application health monitoring

#### Prompts & Routing (Production)
- **Prompt Management**: Centralized prompt management
- **Prompt Registry**: Prompt template storage
- **Routing Engine**: Request routing logic

### External Systems
- **LLM Providers**: OpenAI, Anthropic, and other providers via LiteLLM
- **Database**: SQLite (dev) or PostgreSQL (production)
- **OAuth Providers**: External authentication providers

## Key Architecture Patterns

1. **Repository Pattern**: Clean separation of data access
2. **Factory Pattern**: Application and service creation
3. **Observer Pattern**: Event streaming and monitoring
4. **Strategy Pattern**: Pluggable LLM providers and tools
5. **FSM Pattern**: Skill creation workflow management
6. **Middleware Pattern**: Request processing pipeline
7. **Registry Pattern**: Tool and agent discovery
8. **Dependency Injection**: Loose coupling and testability

## Technology Stack

### Backend
- **Framework**: FastAPI 0.100+
- **Language**: Python 3.9+
- **ORM**: SQLAlchemy (async/sync)
- **LLM Integration**: LiteLLM
- **Testing**: pytest with 219 test files
- **Code Quality**: black, ruff, mypy

### Frontend
- **Framework**: Next.js 14+ (planned)
- **Language**: TypeScript (planned)
- **Styling**: Tailwind CSS (planned)
- **Status**: Pre-alpha (scaffolding only)

### Database
- **Development**: SQLite with aiosqlite
- **Production**: PostgreSQL with asyncpg

### External Services
- **LLM Providers**: Multi-provider via LiteLLM
- **Authentication**: OAuth 2.0

## Maturity Levels

- 🟢 **Production**: Core infrastructure, API, agents, orchestration, storage, security
- 🟡 **MVP**: Skill creation system, builder domain (February 2026)
- 🔴 **Pre-Alpha**: Frontend (scaffolding only)

## Recent Developments (Feb 2026)

1. **Skill Creation System**: FSM-based conversational skill builder with LLM integration
2. **Path Normalization**: {baseDir} placeholder for portable skill generation
3. **Enhanced Validation**: Anthropic specification compliance
4. **Pattern Detection**: Automatic skill pattern recognition
5. **Resource Generation**: Automated script, reference, and asset generation

## Known Gaps

1. **Tool Permissions**: `determine_required_tools()` stub - not automatically setting based on patterns
2. **Reference Generation**: Missing references/ directory creation
3. **Asset Generation**: Missing assets/ directory creation
4. **Frontend**: Minimal implementation, requires substantial development
