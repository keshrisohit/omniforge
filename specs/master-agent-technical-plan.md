# Master Agent Technical Implementation Plan

**Created**: 2026-01-26
**Author**: Technical Architect
**Status**: Draft
**Version**: 1.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Analysis](#requirements-analysis)
3. [Constraints and Assumptions](#constraints-and-assumptions)
4. [System Architecture](#system-architecture)
5. [Technology Stack](#technology-stack)
6. [Component Specifications](#component-specifications)
7. [Data Models](#data-models)
8. [Integration Architecture](#integration-architecture)
9. [Query Handler System](#query-handler-system)
10. [Error Handling Strategy](#error-handling-strategy)
11. [Performance and Scalability](#performance-and-scalability)
12. [Testing Strategy](#testing-strategy)
13. [Implementation Phases](#implementation-phases)
14. [Risk Assessment](#risk-assessment)
15. [Alternative Approaches](#alternative-approaches)

---

## Executive Summary

The Master Agent is the intelligent routing layer for OmniForge, serving as the central entry point for all user chat interactions. It analyzes user intent, discovers appropriate agents, asks clarifying questions when needed, and routes requests to the correct handler.

**Key Architectural Decisions:**

1. **Extends BaseAgent** - Lightweight agent with custom routing events for transparency
2. **Uses existing AgentRegistry** - Integrates with platform's agent discovery infrastructure
3. **LLM-based Intent Analysis** - Uses structured output for reliable intent classification
4. **Extensible Query Handler Pattern** - Plugin-based system for handling different query types
5. **Streaming-First Design** - All responses stream through SSE for responsive UX

**Core Technologies:**
- Python 3.9+ with async/await
- LiteLLM for multi-provider LLM access
- Pydantic for data validation and structured outputs
- Existing OmniForge infrastructure (AgentRegistry, Skills, Tools)

---

## Requirements Analysis

### Functional Requirements (from Product Spec)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Detect action type (CREATE/UPDATE/EXECUTE/QUERY) | P0 |
| FR-02 | Route CREATE/UPDATE intents to Platform Agent Builder | P0 |
| FR-03 | Discover and route EXECUTE intents to customer agents | P0 |
| FR-04 | Handle QUERY intents via extensible handler system | P0 |
| FR-05 | Generate clarifying questions when intent is ambiguous | P0 |
| FR-06 | Support power user override (@agent-name syntax) | P1 |
| FR-07 | Stream responses back to user via SSE | P0 |
| FR-08 | Maintain conversation context for follow-ups | P1 |
| FR-09 | Support multi-turn clarification flows | P1 |
| FR-10 | Provide debug/transparency mode for power users | P2 |

### Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Intent analysis latency | <200ms |
| NFR-02 | Agent discovery latency | <100ms |
| NFR-03 | End-to-end routing latency | <500ms |
| NFR-04 | Routing accuracy | >85% |
| NFR-05 | Availability | 99.9% |
| NFR-06 | Tenant isolation | 100% |

### Extracted Technical Needs

1. **LLM Integration** - Structured output support for intent classification
2. **Async Processing** - All I/O operations must be non-blocking
3. **Streaming Support** - SSE event streaming for real-time responses
4. **Multi-tenancy** - Strict tenant isolation in agent discovery
5. **Extensibility** - Plugin architecture for query handlers
6. **Observability** - Logging, metrics, and tracing for routing decisions

---

## Constraints and Assumptions

### Constraints

1. **Must be a BaseAgent implementation** - Inherits from existing agent hierarchy
2. **Must use AgentRegistry** - No parallel agent discovery mechanism
3. **Must integrate with existing ChatService** - Uses established chat patterns
4. **Must support existing Skills system** - Skills drive agent capabilities
5. **Python 3.9+ compatibility** - No features beyond this version
6. **100 character line length** - Black/ruff enforced

### Assumptions

1. **Platform Agent Builder exists** - Or will be built to handle CREATE/UPDATE
2. **Customer agents are registered** - Via AgentRegistry with tenant scoping
3. **LLM API available** - Via LiteLLM with configured providers
4. **Conversation context persisted** - By calling service (not Master Agent)
5. **Single tenant per request** - tenant_id always available in context

### Design Tradeoffs

| Decision | Tradeoff | Rationale |
|----------|----------|-----------|
| Extend CoTAgent vs BaseAgent | More overhead, but visible reasoning | Debugging and transparency critical for routing |
| LLM for intent analysis vs Rules | Higher latency/cost, but more flexible | Natural language understanding requires LLM |
| Sync clarification vs Async | Simpler flow, blocks on user input | User experience requires synchronous Q&A |
| Single agent routing vs Multi-agent | Limited capability, simpler design | Spec explicitly excludes multi-agent orchestration |

---

## System Architecture

### High-Level Architecture

```
                                    +------------------+
                                    |   Chat Service   |
                                    +--------+---------+
                                             |
                                             v
+--------------------------------------------------------------------+
|                         MASTER AGENT                                |
|                                                                     |
|  +----------------+    +------------------+    +----------------+   |
|  | Intent         |    | Routing          |    | Response       |   |
|  | Analyzer       |--->| Decision         |--->| Streamer       |   |
|  | (LLM-based)    |    | Engine           |    |                |   |
|  +----------------+    +--------+---------+    +----------------+   |
|          |                      |                                   |
|          v                      v                                   |
|  +----------------+    +------------------+                         |
|  | Clarification  |    | Agent            |                         |
|  | Manager        |    | Discovery        |                         |
|  |                |    | Service          |                         |
|  +----------------+    +------------------+                         |
|                                 |                                   |
+--------------------------------------------------------------------+
                                  |
          +-----------------------+------------------------+
          |                       |                        |
          v                       v                        v
+------------------+    +------------------+    +------------------+
| Platform Agent   |    | Customer Agents  |    | Query Handlers   |
| Builder          |    | (via Registry)   |    | (Extensible)     |
+------------------+    +------------------+    +------------------+
```

### Component Interaction Flow

```
User Request
    |
    v
+-------------------+
| 1. Parse Request  |
|    - Extract @agent override
|    - Get conversation context
+-------------------+
    |
    v
+-------------------+
| 2. Analyze Intent |  <-- LLM Call with structured output
|    - Detect action_type
|    - Extract entities
|    - Calculate confidence
+-------------------+
    |
    v
+-------------------+
| 3. Route Decision |
|    - Check confidence threshold
|    - Check for explicit override
|    - Determine routing target
+-------------------+
    |
    +---> High Confidence (>85%)
    |         |
    |         v
    |    +-------------------+
    |    | Route to Handler  |
    |    +-------------------+
    |
    +---> Low Confidence (<60%)
    |         |
    |         v
    |    +-------------------+
    |    | Generate Question |
    |    +-------------------+
    |
    +---> Multiple Matches
              |
              v
         +-------------------+
         | Multiple Choice   |
         | Question          |
         +-------------------+
```

### Module Structure

```
src/omniforge/master_agent/
├── __init__.py
├── agent.py                 # MasterAgent class (CoTAgent subclass)
├── intent/
│   ├── __init__.py
│   ├── analyzer.py          # IntentAnalyzer (LLM-based)
│   ├── models.py            # IntentAnalysis, ActionType, etc.
│   └── prompts.py           # Intent analysis prompt templates
├── routing/
│   ├── __init__.py
│   ├── router.py            # MasterAgentRouter
│   ├── decision.py          # RoutingDecision models
│   └── scoring.py           # Agent scoring utilities
├── discovery/
│   ├── __init__.py
│   └── service.py           # AgentDiscoveryWrapper (extends existing)
├── clarification/
│   ├── __init__.py
│   ├── manager.py           # ClarificationManager
│   └── questions.py         # Question generation strategies
├── query_handlers/
│   ├── __init__.py
│   ├── base.py              # QueryHandler ABC
│   ├── registry.py          # QueryHandlerRegistry
│   ├── llm_handler.py       # LLMQueryHandler (default fallback)
│   └── agent_list.py        # AgentListQueryHandler
├── context/
│   ├── __init__.py
│   └── manager.py           # ConversationContextManager
└── errors.py                # Master agent specific errors
```

---

## Technology Stack

### Core Dependencies (Existing)

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Agent Framework | omniforge.agents | - | BaseAgent, CoTAgent |
| Registry | omniforge.agents.registry | - | AgentRegistry |
| Tools | omniforge.tools | - | LLMTool, ToolExecutor |
| Tasks | omniforge.tasks | - | Task, TaskEvent models |
| Chat | omniforge.chat | - | ChatService, streaming |
| Discovery | omniforge.orchestration.discovery | - | AgentDiscoveryService |

### New Dependencies

| Component | Package | Version | Purpose |
|-----------|---------|---------|---------|
| Structured Output | pydantic | existing | JSON schema for LLM output |

### LLM Configuration

```python
# Intent analysis requires structured output support
INTENT_ANALYSIS_CONFIG = {
    "model": "gpt-4o-mini",  # Supports response_format
    "temperature": 0.0,      # Deterministic for routing
    "max_tokens": 1024,
    "response_format": {"type": "json_object"}
}

# Clarification question generation
CLARIFICATION_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.7,      # More creative for questions
    "max_tokens": 512
}
```

---

## SKILL.md Files (Claude Code Convention)

Master Agent capabilities are defined in SKILL.md files following Claude Code skill convention with YAML frontmatter.

### Skill Directory Structure

```
src/omniforge/master_agent/skills/
├── intent-analysis/
│   └── SKILL.md
├── agent-discovery/
│   └── SKILL.md
└── smart-routing/
    └── SKILL.md
```

### 1. Intent Analysis Skill

**File**: `src/omniforge/master_agent/skills/intent-analysis/SKILL.md`

```markdown
---
name: intent-analysis
description: Analyzes user intent to determine action type (CREATE/UPDATE/EXECUTE/QUERY) and extract entities
allowed-tools:
  - LLM
model: gpt-4o-mini
context: inherit
user-invocable: false
disable-model-invocation: true
priority: 0
tags:
  - intent
  - nlp
  - classification
---

# Intent Analysis Skill

Analyzes user messages to understand intent and classify into action types.

## Capabilities

- Detect action type: CREATE, UPDATE, EXECUTE, QUERY, or AMBIGUOUS
- Extract entities (agent names, data sources, targets)
- Calculate confidence score (0.0 to 1.0)
- Identify ambiguous requests requiring clarification

## How It Works

Uses LLM with structured JSON output (temperature=0.0 for determinism).

Returns IntentAnalysis with:
- `action_type`: CREATE | UPDATE | EXECUTE | QUERY | AMBIGUOUS
- `primary_intent`: Detailed description
- `entities`: Extracted key-value pairs
- `confidence`: 0.0 to 1.0
- `ambiguous`: Boolean flag
```

### 2. Agent Discovery Skill

**File**: `src/omniforge/master_agent/skills/agent-discovery/SKILL.md`

```markdown
---
name: agent-discovery
description: Discovers and scores customer agents that match user intent
allowed-tools: []
context: inherit
user-invocable: false
disable-model-invocation: true
priority: 0
tags:
  - discovery
  - matching
  - scoring
---

# Agent Discovery Skill

Discovers registered customer agents and scores based on intent match.

## Capabilities

- Query AgentRegistry (tenant-scoped)
- Match agent skills to required capabilities
- Score using composite algorithm
- Return ranked candidates

## Scoring Algorithm

- **Skill matching (60%)**: Capability overlap
- **Domain alignment (20%)**: Domain relevance
- **Performance (10%)**: Historical success rate
- **Recency (10%)**: Last successful use

Returns list of ScoredAgent objects sorted by score.
```

### 3. Smart Routing Skill

**File**: `src/omniforge/master_agent/skills/smart-routing/SKILL.md`

```markdown
---
name: smart-routing
description: Routes user requests to appropriate handlers based on intent and confidence
allowed-tools:
  - Subagent
context: inherit
user-invocable: false
disable-model-invocation: true
priority: 0
tags:
  - routing
  - orchestration
---

# Smart Routing Skill

Makes routing decisions based on intent analysis and agent discovery.

## Routing Decision Tree

1. **@agent override**: Route directly if found
2. **Action type routing**:
   - CREATE → Platform Agent Builder
   - UPDATE → Platform Agent Builder (with context)
   - QUERY → Query Handler Registry
   - EXECUTE → Agent discovery + routing
   - AMBIGUOUS → Clarifying question

3. **EXECUTE confidence evaluation**:
   - High (>85%) + high score (>85%) → route immediately
   - Multiple similar scores → clarify
   - No matches → offer to create or suggest alternatives

Returns routing decision with target and context.
```

---

## Component Specifications

### 1. MasterAgent Class

**File**: `src/omniforge/master_agent/agent.py`

```python
"""Master Agent - Intelligent router for all platform interactions."""

from typing import AsyncIterator, Optional
from uuid import UUID

from omniforge.agents.cot.agent import CoTAgent
from omniforge.agents.cot.engine import ReasoningEngine
from omniforge.agents.events import TaskEvent, TaskMessageEvent, TaskDoneEvent
from omniforge.agents.models import (
    AgentIdentity,
    AgentCapabilities,
    TextPart,
)
from omniforge.skills.loader import SkillLoader
from omniforge.agents.registry import AgentRegistry
from omniforge.tasks.models import Task, TaskState

from omniforge.master_agent.intent.analyzer import IntentAnalyzer
from omniforge.master_agent.intent.models import IntentAnalysis, ActionType
from omniforge.master_agent.routing.router import MasterAgentRouter
from omniforge.master_agent.clarification.manager import ClarificationManager
from omniforge.master_agent.context.manager import ConversationContextManager
from omniforge.master_agent.query_handlers.registry import QueryHandlerRegistry


class MasterAgent(CoTAgent):
    """Smart router that directs requests to appropriate agents or handlers.

    The Master Agent serves as the central entry point for all user chat
    interactions on the OmniForge platform. It:

    1. Analyzes user intent (CREATE/UPDATE/EXECUTE/QUERY)
    2. Routes to appropriate handler based on intent
    3. Asks clarifying questions when ambiguous
    4. Streams responses back to user

    Attributes:
        identity: Agent identity (id, name, description, version)
        capabilities: Agent capabilities configuration
        skills: List of skills this agent provides
    """

    identity = AgentIdentity(
        id="master-agent",
        name="Master Agent",
        description="Intelligent router for all platform interactions",
        version="1.0.0"
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=False
    )

    # Skills loaded dynamically from SKILL.md files
    # Located in: src/omniforge/master_agent/skills/
    # Files: intent-analysis/SKILL.md, agent-discovery/SKILL.md, smart-routing/SKILL.md
    skills = []

    # Configuration constants
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60
    SIMILAR_SCORE_THRESHOLD = 0.15  # 15% difference
    MAX_CLARIFICATION_ROUNDS = 3

    def __init__(
        self,
        agent_id: Optional[UUID] = None,
        tenant_id: Optional[str] = None,
        agent_registry: Optional[AgentRegistry] = None,
        query_handler_registry: Optional[QueryHandlerRegistry] = None,
        skill_loader: Optional[SkillLoader] = None,
        **kwargs
    ) -> None:
        """Initialize Master Agent with dependencies.

        Args:
            agent_id: Optional explicit UUID for the agent instance
            tenant_id: Optional tenant identifier for multi-tenancy
            agent_registry: Registry for agent discovery
            query_handler_registry: Registry for query handlers
            skill_loader: Loader for SKILL.md files (uses default if not provided)
            **kwargs: Additional arguments passed to CoTAgent
        """
        super().__init__(agent_id=agent_id, tenant_id=tenant_id, **kwargs)

        # Initialize components (lazy load if not provided)
        self._agent_registry = agent_registry
        self._query_handler_registry = query_handler_registry or QueryHandlerRegistry()
        self._skill_loader = skill_loader or SkillLoader()

        # Load skills from SKILL.md files
        self._load_skills()

        # Create sub-components
        self._intent_analyzer = IntentAnalyzer()
        self._router = MasterAgentRouter()
        self._clarification_manager = ClarificationManager()
        self._context_manager = ConversationContextManager()

    def _load_skills(self) -> None:
        """Load Master Agent skills from SKILL.md files.

        Skills are loaded from src/omniforge/master_agent/skills/ directory.
        Each subdirectory contains a SKILL.md file:
        - intent-analysis/SKILL.md - Intent analysis capability
        - agent-discovery/SKILL.md - Agent discovery capability
        - smart-routing/SKILL.md - Smart routing capability

        This follows the Claude Code skill convention with YAML frontmatter.
        """
        # Skills will be loaded automatically by SkillLoader from master_agent/skills/
        # The loader will parse SKILL.md files and make them available to the agent
        pass

    async def reason(self, task: Task, engine: ReasoningEngine) -> str:
        """Perform routing reasoning to handle user request.

        This method implements the core routing logic:
        1. Check for explicit @agent override
        2. Analyze intent using LLM
        3. Route based on action type and confidence
        4. Generate clarifying questions if needed

        Args:
            task: The task containing user request
            engine: ReasoningEngine for visible reasoning steps

        Returns:
            Final response string to return to user
        """
        # Extract user message from task
        user_message = self._extract_user_message(task)
        context = self._context_manager.get_context(task.id)

        # Step 1: Check for explicit @agent override
        engine.add_thinking("Checking for explicit @agent override in request...")
        override_agent = self._parse_agent_override(user_message)

        if override_agent:
            engine.add_thinking(f"Found explicit override: routing to @{override_agent}")
            return await self._route_to_explicit_agent(
                override_agent, user_message, task, engine
            )

        # Step 2: Analyze intent
        engine.add_thinking("Analyzing user intent using LLM...")
        intent = await self._intent_analyzer.analyze(user_message, context)

        engine.add_thinking(
            f"Intent analysis complete: action_type={intent.action_type.value}, "
            f"confidence={intent.confidence:.2f}, ambiguous={intent.ambiguous}"
        )

        # Step 3: Route based on action type
        if intent.action_type == ActionType.CREATE:
            engine.add_thinking("Routing to Platform Agent Builder for CREATE...")
            return await self._route_to_builder(task, engine, update=False)

        elif intent.action_type == ActionType.UPDATE:
            engine.add_thinking("Routing to Platform Agent Builder for UPDATE...")
            agent_to_update = intent.entities.get("agent_name")
            return await self._route_to_builder(
                task, engine, update=True, agent_name=agent_to_update
            )

        elif intent.action_type == ActionType.QUERY:
            engine.add_thinking("Routing to Query Handler system...")
            return await self._route_to_query_handler(task, intent, engine)

        elif intent.action_type == ActionType.EXECUTE:
            engine.add_thinking("Processing EXECUTE intent - discovering agents...")
            return await self._handle_execute_intent(task, intent, engine)

        else:
            # Ambiguous - ask clarifying question
            engine.add_thinking("Intent unclear - generating clarifying question...")
            return await self._generate_clarification(task, intent, engine)

    async def _handle_execute_intent(
        self,
        task: Task,
        intent: IntentAnalysis,
        engine: ReasoningEngine
    ) -> str:
        """Handle EXECUTE intent with agent discovery and routing.

        Args:
            task: The task to process
            intent: Analyzed intent information
            engine: ReasoningEngine for reasoning steps

        Returns:
            Response from routed agent or clarification question
        """
        # Discover matching agents
        candidates = await self._discover_agents(task.tenant_id, intent)

        if not candidates:
            engine.add_thinking("No matching agents found - offering alternatives...")
            return await self._handle_no_match(task, intent, engine)

        engine.add_thinking(f"Found {len(candidates)} candidate agents")

        # Check confidence and candidate scores
        top_score = candidates[0].score

        if intent.confidence >= self.HIGH_CONFIDENCE_THRESHOLD and top_score >= 0.85:
            # High confidence - route immediately
            engine.add_thinking(f"High confidence match - routing to {candidates[0].agent_id}")
            return await self._route_to_agent(candidates[0], task, engine)

        # Check for multiple similar-scoring candidates
        similar_candidates = [
            c for c in candidates
            if abs(c.score - top_score) <= self.SIMILAR_SCORE_THRESHOLD
        ]

        if len(similar_candidates) > 1:
            engine.add_thinking(
                f"Multiple similar candidates ({len(similar_candidates)}) - "
                "asking for clarification..."
            )
            return await self._generate_multiple_choice(task, similar_candidates, engine)

        if intent.confidence < self.MEDIUM_CONFIDENCE_THRESHOLD:
            engine.add_thinking("Low confidence - asking open-ended question...")
            return await self._generate_clarification(task, intent, engine)

        # Medium confidence with single top candidate - route
        engine.add_thinking(f"Medium confidence - routing to best match: {candidates[0].agent_id}")
        return await self._route_to_agent(candidates[0], task, engine)

    # ... additional helper methods ...
```

### 2. IntentAnalyzer Class

**File**: `src/omniforge/master_agent/intent/analyzer.py`

```python
"""Intent analyzer using LLM with structured output."""

import json
from typing import Optional

from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.base import ToolCallContext

from omniforge.master_agent.intent.models import (
    IntentAnalysis,
    ActionType,
    IntentEntities,
)
from omniforge.master_agent.intent.prompts import INTENT_ANALYSIS_PROMPT
from omniforge.master_agent.context.manager import ConversationContext


class IntentAnalyzer:
    """Analyzes user messages to extract intent and entities using LLM.

    Uses structured output (JSON mode) to reliably extract:
    - Action type (CREATE/UPDATE/EXECUTE/QUERY/AMBIGUOUS)
    - Primary intent classification
    - Relevant entities (agent names, data sources, etc.)
    - Confidence score
    - Ambiguity flag

    Example:
        >>> analyzer = IntentAnalyzer()
        >>> intent = await analyzer.analyze("Generate my weekly Notion report")
        >>> print(intent.action_type)
        ActionType.EXECUTE
        >>> print(intent.confidence)
        0.92
    """

    def __init__(self, llm_tool: Optional[LLMTool] = None) -> None:
        """Initialize intent analyzer.

        Args:
            llm_tool: Optional LLMTool instance. Creates default if not provided.
        """
        self._llm = llm_tool or LLMTool()

    async def analyze(
        self,
        message: str,
        context: Optional[ConversationContext] = None
    ) -> IntentAnalysis:
        """Analyze user message to extract intent.

        Args:
            message: User's raw message text
            context: Optional conversation context for follow-ups

        Returns:
            IntentAnalysis with action_type, entities, confidence

        Raises:
            IntentAnalysisError: If LLM call fails or response is invalid
        """
        # Build prompt with context
        prompt = self._build_prompt(message, context)

        # Create execution context
        tool_context = ToolCallContext(
            correlation_id=f"intent-{id(message)}",
            task_id="intent-analysis",
            agent_id="master-agent"
        )

        # Call LLM with JSON mode
        result = await self._llm.execute(
            context=tool_context,
            arguments={
                "prompt": prompt,
                "system": self._get_system_prompt(),
                "model": "gpt-4o-mini",
                "temperature": 0.0,
                "max_tokens": 1024,
                "response_format": {"type": "json_object"}
            }
        )

        if not result.success:
            raise IntentAnalysisError(f"LLM call failed: {result.error}")

        # Parse structured response
        return self._parse_response(result.result["content"])

    def _build_prompt(
        self,
        message: str,
        context: Optional[ConversationContext]
    ) -> str:
        """Build analysis prompt with message and context.

        Args:
            message: User message to analyze
            context: Optional conversation context

        Returns:
            Formatted prompt string
        """
        context_str = ""
        if context and context.recent_messages:
            context_str = "\n\nRecent conversation:\n"
            for msg in context.recent_messages[-5:]:
                context_str += f"- {msg.role}: {msg.content[:100]}...\n"

        return INTENT_ANALYSIS_PROMPT.format(
            user_message=message,
            context=context_str
        )

    def _get_system_prompt(self) -> str:
        """Get system prompt for intent analysis."""
        return """You are an intent analysis system for OmniForge platform.

Analyze user messages and extract:
1. action_type: CREATE, UPDATE, EXECUTE, QUERY, or AMBIGUOUS
2. primary_intent: Brief description of what user wants
3. entities: Relevant extracted entities (agent names, data sources, etc.)
4. confidence: 0.0-1.0 score of how certain you are
5. ambiguous: true if multiple valid interpretations exist

ACTION TYPE DETECTION:
- CREATE: User wants to create a NEW agent ("I need an agent", "build", "create", "set up automation")
- UPDATE: User wants to modify EXISTING agent ("update my", "modify", "change", "add to my agent")
- EXECUTE: User wants to RUN an existing agent ("generate", "run", "send", "analyze", "show me")
- QUERY: User asking questions ("what", "how", "list", "show me stats", "explain")
- AMBIGUOUS: Cannot determine with confidence

Respond ONLY with valid JSON matching this schema:
{
    "action_type": "CREATE|UPDATE|EXECUTE|QUERY|AMBIGUOUS",
    "primary_intent": "string",
    "entities": {
        "agent_name": "string or null",
        "data_source": "string or null",
        "target": "string or null",
        "topic": "string or null"
    },
    "confidence": 0.0-1.0,
    "ambiguous": true|false,
    "ambiguity_reason": "string or null"
}"""

    def _parse_response(self, content: str) -> IntentAnalysis:
        """Parse LLM JSON response into IntentAnalysis.

        Args:
            content: Raw JSON string from LLM

        Returns:
            IntentAnalysis model instance

        Raises:
            IntentAnalysisError: If parsing fails
        """
        try:
            data = json.loads(content)

            return IntentAnalysis(
                action_type=ActionType(data["action_type"]),
                primary_intent=data["primary_intent"],
                entities=IntentEntities(
                    agent_name=data["entities"].get("agent_name"),
                    data_source=data["entities"].get("data_source"),
                    target=data["entities"].get("target"),
                    topic=data["entities"].get("topic")
                ),
                confidence=float(data["confidence"]),
                ambiguous=bool(data["ambiguous"]),
                ambiguity_reason=data.get("ambiguity_reason")
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise IntentAnalysisError(f"Failed to parse intent response: {e}")
```

### 3. AgentDiscoveryWrapper

**File**: `src/omniforge/master_agent/discovery/service.py`

```python
"""Agent discovery service wrapper with scoring."""

from dataclasses import dataclass
from typing import Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.registry import AgentRegistry
from omniforge.orchestration.discovery import AgentDiscoveryService

from omniforge.master_agent.intent.models import IntentAnalysis


@dataclass
class ScoredAgent:
    """Agent with discovery score.

    Attributes:
        agent: The discovered agent
        agent_id: Agent's identity ID
        score: Match score (0.0-1.0)
        match_reasons: List of reasons for the match
    """
    agent: BaseAgent
    agent_id: str
    score: float
    match_reasons: list[str]


class MasterAgentDiscoveryService:
    """Discovery service wrapper for Master Agent with scoring.

    Extends the platform's AgentDiscoveryService with:
    - Skill-based matching against intent
    - Composite scoring formula
    - Tenant isolation enforcement
    - Health filtering (future)

    Scoring formula:
        score = (skill_match * 0.6) + (domain_match * 0.2) +
                (performance * 0.1) + (recency * 0.1)
    """

    # Scoring weights
    SKILL_WEIGHT = 0.6
    DOMAIN_WEIGHT = 0.2
    PERFORMANCE_WEIGHT = 0.1
    RECENCY_WEIGHT = 0.1

    def __init__(self, registry: AgentRegistry) -> None:
        """Initialize discovery service.

        Args:
            registry: AgentRegistry for agent lookup
        """
        self._registry = registry
        self._discovery = AgentDiscoveryService(registry=registry)

    async def discover_agents(
        self,
        tenant_id: str,
        intent: IntentAnalysis,
        limit: int = 10
    ) -> list[ScoredAgent]:
        """Discover and score agents matching intent.

        Args:
            tenant_id: Tenant ID for isolation
            intent: Analyzed user intent
            limit: Maximum agents to return

        Returns:
            List of ScoredAgent sorted by score descending
        """
        # Get all customer agents for tenant
        all_agents = await self._registry.list_all()

        # Filter by tenant
        tenant_agents = [
            agent for agent in all_agents
            if agent.tenant_id == tenant_id
        ]

        # Score each agent
        scored = []
        for agent in tenant_agents:
            score, reasons = self._calculate_score(agent, intent)
            if score > 0:
                scored.append(ScoredAgent(
                    agent=agent,
                    agent_id=agent.identity.id,
                    score=score,
                    match_reasons=reasons
                ))

        # Sort by score descending and limit
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:limit]

    def _calculate_score(
        self,
        agent: BaseAgent,
        intent: IntentAnalysis
    ) -> tuple[float, list[str]]:
        """Calculate match score for agent against intent.

        Args:
            agent: Agent to score
            intent: User intent to match

        Returns:
            Tuple of (score, reasons)
        """
        reasons = []

        # Skill matching (60% weight)
        skill_score = self._calculate_skill_score(agent, intent)
        if skill_score > 0:
            reasons.append(f"skill_match={skill_score:.2f}")

        # Domain matching (20% weight)
        domain_score = self._calculate_domain_score(agent, intent)
        if domain_score > 0:
            reasons.append(f"domain_match={domain_score:.2f}")

        # Performance (10% weight) - placeholder for future
        performance_score = 1.0  # Default to perfect

        # Recency (10% weight) - placeholder for future
        recency_score = 1.0  # Default to perfect

        # Composite score
        total_score = (
            skill_score * self.SKILL_WEIGHT +
            domain_score * self.DOMAIN_WEIGHT +
            performance_score * self.PERFORMANCE_WEIGHT +
            recency_score * self.RECENCY_WEIGHT
        )

        return total_score, reasons

    def _calculate_skill_score(
        self,
        agent: BaseAgent,
        intent: IntentAnalysis
    ) -> float:
        """Calculate skill match score.

        Args:
            agent: Agent to evaluate
            intent: Intent with required skills/keywords

        Returns:
            Score 0.0-1.0
        """
        # Extract keywords from intent
        keywords = set()
        if intent.primary_intent:
            keywords.update(intent.primary_intent.lower().split())
        if intent.entities.data_source:
            keywords.add(intent.entities.data_source.lower())
        if intent.entities.topic:
            keywords.update(intent.entities.topic.lower().split())

        # Match against agent skills
        agent_keywords = set()
        for skill in agent.skills:
            agent_keywords.add(skill.id.lower())
            agent_keywords.add(skill.name.lower())
            agent_keywords.update(skill.description.lower().split())
            if skill.tags:
                agent_keywords.update(tag.lower() for tag in skill.tags)

        # Calculate overlap
        if not keywords:
            return 0.0

        matches = keywords.intersection(agent_keywords)
        return len(matches) / len(keywords)

    def _calculate_domain_score(
        self,
        agent: BaseAgent,
        intent: IntentAnalysis
    ) -> float:
        """Calculate domain alignment score.

        Args:
            agent: Agent to evaluate
            intent: Intent with domain hints

        Returns:
            Score 0.0-1.0
        """
        # Simple domain matching based on agent description
        if not intent.primary_intent:
            return 0.0

        intent_words = set(intent.primary_intent.lower().split())
        desc_words = set(agent.identity.description.lower().split())

        if not intent_words:
            return 0.0

        matches = intent_words.intersection(desc_words)
        return min(1.0, len(matches) / max(1, len(intent_words) * 0.3))
```

### 4. ClarificationManager

**File**: `src/omniforge/master_agent/clarification/manager.py`

```python
"""Clarification question generation and management."""

from typing import Optional

from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.base import ToolCallContext

from omniforge.master_agent.intent.models import IntentAnalysis
from omniforge.master_agent.discovery.service import ScoredAgent


class ClarificationManager:
    """Generates and manages clarifying questions.

    Supports three question strategies:
    1. Multiple Choice - When several agents match with similar scores
    2. Entity Clarification - When missing key information
    3. Open-Ended - When very uncertain about intent

    Example:
        >>> manager = ClarificationManager()
        >>> question = await manager.generate_multiple_choice(candidates)
        >>> print(question.text)
        "I can help with that! Which type would you like?
         1. **Notion Project Status** - Summary of your Notion projects
         2. **Financial Report** - Revenue and expenses analysis"
    """

    def __init__(self, llm_tool: Optional[LLMTool] = None) -> None:
        """Initialize clarification manager.

        Args:
            llm_tool: Optional LLMTool instance
        """
        self._llm = llm_tool or LLMTool()

    async def generate_multiple_choice(
        self,
        candidates: list[ScoredAgent],
        max_options: int = 4
    ) -> str:
        """Generate multiple choice question for ambiguous routing.

        Args:
            candidates: List of matching agents
            max_options: Maximum options to show (default 4)

        Returns:
            Formatted question string with numbered options
        """
        options = candidates[:max_options]

        # Build option list
        option_lines = []
        for i, candidate in enumerate(options, 1):
            name = candidate.agent.identity.name
            desc = candidate.agent.identity.description[:80]
            option_lines.append(f"{i}. **{name}** - {desc}")

        question = (
            "I can help with that! Which type would you like?\n\n"
            + "\n".join(option_lines)
            + "\n\nJust let me know which one!"
        )

        return question

    async def generate_entity_clarification(
        self,
        intent: IntentAnalysis,
        missing_entity: str
    ) -> str:
        """Generate question for missing entity.

        Args:
            intent: Current intent analysis
            missing_entity: Name of missing entity

        Returns:
            Question asking for specific entity
        """
        entity_questions = {
            "data_source": "Where is the data you want me to work with?\n- Notion\n- Google Sheets\n- Database",
            "target": "Where should I send the result?\n- Slack\n- Email\n- Notion",
            "agent_name": "Which agent would you like me to update?",
            "timeframe": "What time period should I cover?\n- This week\n- This month\n- Custom range"
        }

        return entity_questions.get(
            missing_entity,
            f"Could you tell me more about the {missing_entity}?"
        )

    async def generate_open_ended(
        self,
        intent: IntentAnalysis
    ) -> str:
        """Generate open-ended clarifying question.

        Args:
            intent: Current (unclear) intent analysis

        Returns:
            Open-ended question for more context
        """
        if intent.ambiguity_reason:
            return f"I want to make sure I understand correctly. {intent.ambiguity_reason} Could you tell me a bit more about what you're trying to accomplish?"

        return "Could you tell me a bit more about what you're trying to accomplish? For example:\n- What kind of result are you looking for?\n- Which data or system should I work with?"

    async def generate_create_vs_execute(
        self,
        intent: IntentAnalysis,
        matching_agent: Optional[ScoredAgent] = None
    ) -> str:
        """Generate question for CREATE vs EXECUTE ambiguity.

        Args:
            intent: Ambiguous intent
            matching_agent: Optional existing agent that might match

        Returns:
            Question distinguishing create from execute
        """
        if matching_agent:
            agent_name = matching_agent.agent.identity.name
            return (
                f"I can help with that! Did you mean:\n\n"
                f"1. **Run your existing {agent_name}** - Execute it now\n"
                f"2. **Create a new automated agent** - Set up something new\n\n"
                f"Which one?"
            )

        return (
            "I can help with that! Did you mean:\n\n"
            "1. **Run an existing agent** - Use an agent you've already set up\n"
            "2. **Create a new agent** - Build a new automation\n\n"
            "Which one?"
        )
```

---

## Data Models

### Intent Models

**File**: `src/omniforge/master_agent/intent/models.py`

```python
"""Data models for intent analysis."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Primary action type classification."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    EXECUTE = "EXECUTE"
    QUERY = "QUERY"
    AMBIGUOUS = "AMBIGUOUS"


class IntentEntities(BaseModel):
    """Extracted entities from user message.

    Attributes:
        agent_name: Referenced agent name (for UPDATE/EXECUTE)
        data_source: Data source mentioned (notion, sheets, etc.)
        target: Output destination (slack, email, etc.)
        topic: Subject/topic of request
    """

    agent_name: Optional[str] = None
    data_source: Optional[str] = None
    target: Optional[str] = None
    topic: Optional[str] = None


class IntentAnalysis(BaseModel):
    """Complete intent analysis result.

    Attributes:
        action_type: Primary action classification
        primary_intent: Brief description of intent
        entities: Extracted entities
        confidence: Confidence score (0.0-1.0)
        ambiguous: Whether multiple interpretations exist
        ambiguity_reason: Explanation of ambiguity
        required_skills: Skills needed to fulfill intent
    """

    action_type: ActionType
    primary_intent: str
    entities: IntentEntities
    confidence: float = Field(ge=0.0, le=1.0)
    ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
```

### Routing Models

**File**: `src/omniforge/master_agent/routing/decision.py`

```python
"""Routing decision models."""

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel

from omniforge.master_agent.discovery.service import ScoredAgent


class RoutingTarget(str, Enum):
    """Target for routing decision."""

    AGENT_BUILDER = "agent_builder"
    CUSTOMER_AGENT = "customer_agent"
    QUERY_HANDLER = "query_handler"
    CLARIFICATION = "clarification"
    ERROR = "error"


class RoutingDecision(BaseModel):
    """Routing decision with target and context.

    Attributes:
        target: Where to route the request
        agent: Target agent (if routing to customer agent)
        query_handler_id: Handler ID (if routing to query handler)
        clarification_question: Question (if requesting clarification)
        context: Additional context to pass to target
        reasoning: Explanation of routing decision
    """

    target: RoutingTarget
    agent: Optional[ScoredAgent] = None
    query_handler_id: Optional[str] = None
    clarification_question: Optional[str] = None
    context: dict = {}
    reasoning: str = ""

    class Config:
        arbitrary_types_allowed = True
```

### Context Models

**File**: `src/omniforge/master_agent/context/manager.py`

```python
"""Conversation context management."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ContextMessage:
    """Single message in conversation context."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConversationContext:
    """Conversation context for multi-turn interactions.

    Attributes:
        conversation_id: Unique conversation identifier
        recent_messages: Last N messages in conversation
        clarification_history: Questions asked and responses
        extracted_entities: Accumulated extracted entities
        routing_history: Previous routing decisions
    """

    conversation_id: str
    recent_messages: list[ContextMessage] = field(default_factory=list)
    clarification_history: list[tuple[str, str]] = field(default_factory=list)
    extracted_entities: dict[str, str] = field(default_factory=dict)
    routing_history: list[str] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """Add message to context, keeping last 10."""
        self.recent_messages.append(ContextMessage(role=role, content=content))
        if len(self.recent_messages) > 10:
            self.recent_messages = self.recent_messages[-10:]

    def add_clarification(self, question: str, response: str) -> None:
        """Record clarification Q&A."""
        self.clarification_history.append((question, response))

    def merge_entities(self, entities: dict[str, Optional[str]]) -> None:
        """Merge new entities into context."""
        for key, value in entities.items():
            if value is not None:
                self.extracted_entities[key] = value


class ConversationContextManager:
    """Manages conversation contexts with TTL."""

    CONTEXT_TTL_SECONDS = 3600  # 1 hour

    def __init__(self) -> None:
        """Initialize context manager."""
        self._contexts: dict[str, tuple[ConversationContext, datetime]] = {}

    def get_context(self, conversation_id: str) -> ConversationContext:
        """Get or create conversation context.

        Args:
            conversation_id: Unique conversation ID

        Returns:
            ConversationContext for the conversation
        """
        now = datetime.utcnow()

        if conversation_id in self._contexts:
            context, created = self._contexts[conversation_id]
            age = (now - created).total_seconds()
            if age < self.CONTEXT_TTL_SECONDS:
                return context

        # Create new context
        context = ConversationContext(conversation_id=conversation_id)
        self._contexts[conversation_id] = (context, now)
        return context

    def update_context(
        self,
        conversation_id: str,
        context: ConversationContext
    ) -> None:
        """Update stored context."""
        self._contexts[conversation_id] = (context, datetime.utcnow())
```

---

## Integration Architecture

### Integration with Chat Service

The Master Agent integrates with the existing ChatService as the primary response generator.

```python
# src/omniforge/chat/master_agent_integration.py

from typing import AsyncIterator

from omniforge.chat.models import ChatRequest
from omniforge.chat.streaming import format_chunk_event, format_done_event
from omniforge.master_agent.agent import MasterAgent
from omniforge.agents.models import TextPart
from omniforge.tasks.models import Task, TaskState, TaskMessage


class MasterAgentChatAdapter:
    """Adapts MasterAgent for ChatService integration.

    Converts chat requests to tasks and streams task events
    as SSE-formatted responses.
    """

    def __init__(self, master_agent: MasterAgent) -> None:
        """Initialize adapter.

        Args:
            master_agent: MasterAgent instance to use
        """
        self._agent = master_agent

    async def process_chat(
        self,
        request: ChatRequest,
        tenant_id: str,
        user_id: str
    ) -> AsyncIterator[str]:
        """Process chat request through Master Agent.

        Args:
            request: Chat request from user
            tenant_id: Tenant identifier
            user_id: User identifier

        Yields:
            SSE-formatted event strings
        """
        # Create task from chat request
        task = self._create_task(request, tenant_id, user_id)

        # Process through Master Agent
        async for event in self._agent.process_task(task):
            # Convert task events to SSE chunks
            if hasattr(event, 'message_parts'):
                for part in event.message_parts:
                    if hasattr(part, 'text'):
                        yield format_chunk_event(part.text)

            if event.type == "done":
                # Yield completion event
                yield format_done_event(...)

    def _create_task(
        self,
        request: ChatRequest,
        tenant_id: str,
        user_id: str
    ) -> Task:
        """Create Task from ChatRequest."""
        from datetime import datetime
        from uuid import uuid4

        return Task(
            id=str(uuid4()),
            agent_id="master-agent",
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text=request.message)],
                    created_at=datetime.utcnow()
                )
            ],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id=tenant_id,
            user_id=user_id
        )
```

### Integration with Agent Registry

```python
# Integration pattern for agent discovery

from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository


def create_master_agent_with_registry() -> MasterAgent:
    """Create Master Agent with configured registry.

    Returns:
        Configured MasterAgent instance
    """
    # Create repository and registry
    repository = InMemoryAgentRepository()
    registry = AgentRegistry(repository=repository)

    # Create Master Agent with registry
    return MasterAgent(agent_registry=registry)
```

### Integration with Platform Agent Builder

```python
# Routing to Agent Builder (stubbed for future implementation)

async def _route_to_builder(
    self,
    task: Task,
    engine: ReasoningEngine,
    update: bool = False,
    agent_name: Optional[str] = None
) -> str:
    """Route request to Platform Agent Builder.

    Args:
        task: Task to route
        engine: ReasoningEngine for logging
        update: True if updating existing agent
        agent_name: Agent to update (for UPDATE intent)

    Returns:
        Response from Agent Builder
    """
    engine.add_thinking(
        f"Routing to Agent Builder ({'UPDATE' if update else 'CREATE'})..."
    )

    # Build context for Agent Builder
    context = {
        "action": "UPDATE" if update else "CREATE",
        "original_request": self._extract_user_message(task),
        "tenant_id": task.tenant_id,
        "user_id": task.user_id
    }

    if update and agent_name:
        context["agent_to_update"] = agent_name

    # TODO: Route to actual Agent Builder agent
    # For now, return informative message
    if update:
        return (
            f"I can help you update your '{agent_name}' agent! "
            "Let me connect you with the Agent Builder...\n\n"
            "(Agent Builder integration coming soon)"
        )
    else:
        return (
            "I can help you create that agent! "
            "Let me connect you with the Agent Builder...\n\n"
            "(Agent Builder integration coming soon)"
        )
```

---

## Query Handler System

### QueryHandler Abstract Base Class

**File**: `src/omniforge/master_agent/query_handlers/base.py`

```python
"""Base class for query handlers."""

from abc import ABC, abstractmethod
from typing import Optional

from omniforge.master_agent.context.manager import ConversationContext


class QueryHandler(ABC):
    """Abstract base class for query handlers.

    Query handlers process informational queries that don't require
    agent execution. Examples:
    - "What agents do I have?"
    - "How does this platform work?"
    - "Show me agent stats"

    Handlers are registered with QueryHandlerRegistry and tried
    in priority order. The first handler that can_handle() returns
    True will process the query.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Unique identifier for this handler."""
        pass

    @property
    @abstractmethod
    def priority(self) -> int:
        """Priority for handler ordering (higher = tried first)."""
        pass

    @abstractmethod
    async def can_handle(self, query: str, context: ConversationContext) -> bool:
        """Check if this handler can process the query.

        Args:
            query: User's query string
            context: Conversation context

        Returns:
            True if handler can process, False otherwise
        """
        pass

    @abstractmethod
    async def handle(
        self,
        query: str,
        context: ConversationContext,
        tenant_id: str
    ) -> str:
        """Handle the query and return response.

        Args:
            query: User's query string
            context: Conversation context
            tenant_id: Tenant identifier

        Returns:
            Response string
        """
        pass
```

### QueryHandlerRegistry

**File**: `src/omniforge/master_agent/query_handlers/registry.py`

```python
"""Registry for query handlers."""

from typing import Optional

from omniforge.master_agent.query_handlers.base import QueryHandler
from omniforge.master_agent.query_handlers.llm_handler import LLMQueryHandler
from omniforge.master_agent.context.manager import ConversationContext


class QueryHandlerRegistry:
    """Registry managing query handlers with priority ordering.

    Handlers are tried in priority order (highest first).
    LLMQueryHandler is always registered as the fallback with
    lowest priority.

    Example:
        >>> registry = QueryHandlerRegistry()
        >>> registry.register(AgentListQueryHandler())
        >>> handler = await registry.find_handler("list my agents", context)
        >>> response = await handler.handle("list my agents", context, "tenant-1")
    """

    def __init__(self) -> None:
        """Initialize registry with default handlers."""
        self._handlers: list[QueryHandler] = []

        # Always register LLM handler as fallback
        self.register(LLMQueryHandler())

    def register(self, handler: QueryHandler) -> None:
        """Register a query handler.

        Args:
            handler: Handler to register
        """
        self._handlers.append(handler)
        # Sort by priority descending
        self._handlers.sort(key=lambda h: h.priority, reverse=True)

    async def find_handler(
        self,
        query: str,
        context: ConversationContext
    ) -> Optional[QueryHandler]:
        """Find appropriate handler for query.

        Args:
            query: User's query
            context: Conversation context

        Returns:
            First handler that can_handle, or None
        """
        for handler in self._handlers:
            if await handler.can_handle(query, context):
                return handler
        return None

    async def handle_query(
        self,
        query: str,
        context: ConversationContext,
        tenant_id: str
    ) -> str:
        """Find handler and process query.

        Args:
            query: User's query
            context: Conversation context
            tenant_id: Tenant identifier

        Returns:
            Response from handler

        Raises:
            ValueError: If no handler found (shouldn't happen with LLM fallback)
        """
        handler = await self.find_handler(query, context)
        if handler is None:
            raise ValueError("No handler found for query")

        return await handler.handle(query, context, tenant_id)
```

### LLMQueryHandler (Fallback)

**File**: `src/omniforge/master_agent/query_handlers/llm_handler.py`

```python
"""LLM-based query handler (default fallback)."""

from omniforge.tools.builtin.llm import LLMTool
from omniforge.tools.base import ToolCallContext

from omniforge.master_agent.query_handlers.base import QueryHandler
from omniforge.master_agent.context.manager import ConversationContext


class LLMQueryHandler(QueryHandler):
    """Default query handler using LLM for general questions.

    This handler serves as the fallback for queries that don't match
    any specialized handler. It uses the LLM to generate helpful
    responses about the platform.
    """

    @property
    def id(self) -> str:
        return "llm-query-handler"

    @property
    def priority(self) -> int:
        return 0  # Lowest priority - fallback

    def __init__(self) -> None:
        """Initialize LLM query handler."""
        self._llm = LLMTool()

    async def can_handle(
        self,
        query: str,
        context: ConversationContext
    ) -> bool:
        """LLM handler can always handle queries (fallback)."""
        return True

    async def handle(
        self,
        query: str,
        context: ConversationContext,
        tenant_id: str
    ) -> str:
        """Handle query using LLM.

        Args:
            query: User's query
            context: Conversation context
            tenant_id: Tenant identifier

        Returns:
            LLM-generated response
        """
        tool_context = ToolCallContext(
            correlation_id=f"query-{id(query)}",
            task_id="query-handling",
            agent_id="master-agent",
            tenant_id=tenant_id
        )

        system_prompt = """You are the OmniForge platform assistant.

You help users understand:
- How the platform works
- What they can do with agents
- How to create and manage agents
- General platform capabilities

Be helpful, concise, and friendly. If you don't know something specific
about their account or agents, suggest they ask about specific agents
or use platform commands.

Important: You cannot access user-specific data like their agent list
or usage stats. For those queries, suggest they ask "list my agents"
or similar specific commands."""

        result = await self._llm.execute(
            context=tool_context,
            arguments={
                "prompt": query,
                "system": system_prompt,
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 1024
            }
        )

        if result.success:
            return result.result["content"]
        else:
            return (
                "I apologize, but I'm having trouble processing your question "
                "right now. Could you try rephrasing it or ask something more specific?"
            )
```

### AgentListQueryHandler (Example Specialized Handler)

**File**: `src/omniforge/master_agent/query_handlers/agent_list.py`

```python
"""Handler for agent listing queries."""

import re

from omniforge.agents.registry import AgentRegistry

from omniforge.master_agent.query_handlers.base import QueryHandler
from omniforge.master_agent.context.manager import ConversationContext


class AgentListQueryHandler(QueryHandler):
    """Handler for "list my agents" and similar queries."""

    # Patterns that indicate agent listing intent
    PATTERNS = [
        r"list\s+(my\s+)?agents?",
        r"what\s+agents?\s+(do\s+i\s+have|are\s+available)",
        r"show\s+(me\s+)?(my\s+)?agents?",
        r"which\s+agents?\s+(do\s+i\s+have|exist)"
    ]

    @property
    def id(self) -> str:
        return "agent-list-handler"

    @property
    def priority(self) -> int:
        return 100  # High priority

    def __init__(self, registry: AgentRegistry) -> None:
        """Initialize with agent registry.

        Args:
            registry: AgentRegistry for agent lookup
        """
        self._registry = registry

    async def can_handle(
        self,
        query: str,
        context: ConversationContext
    ) -> bool:
        """Check if query is about listing agents."""
        query_lower = query.lower()
        return any(
            re.search(pattern, query_lower)
            for pattern in self.PATTERNS
        )

    async def handle(
        self,
        query: str,
        context: ConversationContext,
        tenant_id: str
    ) -> str:
        """List agents for tenant.

        Args:
            query: User's query
            context: Conversation context
            tenant_id: Tenant identifier

        Returns:
            Formatted agent list
        """
        # Get agents for tenant
        registry = AgentRegistry(
            repository=self._registry._repository,
            tenant_id=tenant_id
        )
        agents = await registry.list_all()

        if not agents:
            return (
                "You don't have any agents set up yet.\n\n"
                "Would you like me to help you create one? Just tell me what "
                "kind of automation you need!"
            )

        # Format agent list
        lines = ["Here are your agents:\n"]
        for agent in agents:
            skill_count = len(agent.skills)
            lines.append(
                f"- **{agent.identity.name}** ({agent.identity.id})\n"
                f"  {agent.identity.description[:60]}... | "
                f"{skill_count} skill{'s' if skill_count != 1 else ''}"
            )

        lines.append(
            "\n\nTo run an agent, just describe what you want to do "
            "(e.g., 'generate my Notion report')."
        )

        return "\n".join(lines)
```

---

## Error Handling Strategy

### Error Hierarchy

**File**: `src/omniforge/master_agent/errors.py`

```python
"""Master Agent error definitions."""


class MasterAgentError(Exception):
    """Base exception for Master Agent errors."""
    pass


class IntentAnalysisError(MasterAgentError):
    """Raised when intent analysis fails."""

    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error


class AgentDiscoveryError(MasterAgentError):
    """Raised when agent discovery fails."""
    pass


class RoutingError(MasterAgentError):
    """Raised when routing decision cannot be made."""
    pass


class ClarificationError(MasterAgentError):
    """Raised when clarification generation fails."""
    pass


class QueryHandlerError(MasterAgentError):
    """Raised when query handling fails."""
    pass


class CircularRoutingError(MasterAgentError):
    """Raised when circular routing is detected."""

    def __init__(self, depth: int, max_depth: int):
        super().__init__(
            f"Circular routing detected at depth {depth} (max: {max_depth})"
        )
        self.depth = depth
        self.max_depth = max_depth
```

### Error Handling Patterns

```python
# In MasterAgent.reason()

async def reason(self, task: Task, engine: ReasoningEngine) -> str:
    """Process with comprehensive error handling."""
    try:
        # ... main routing logic ...
        pass

    except IntentAnalysisError as e:
        engine.add_thinking(f"Intent analysis failed: {e}")
        return self._handle_analysis_error(e)

    except AgentDiscoveryError as e:
        engine.add_thinking(f"Agent discovery failed: {e}")
        return self._handle_discovery_error(e)

    except CircularRoutingError as e:
        engine.add_thinking(f"Circular routing detected: {e}")
        return self._handle_circular_error(e)

    except Exception as e:
        # Unexpected error - log and return graceful message
        import logging
        logging.exception(f"Unexpected error in Master Agent: {e}")
        return self._handle_unexpected_error(e)

def _handle_analysis_error(self, error: IntentAnalysisError) -> str:
    """Handle intent analysis failures gracefully."""
    return (
        "I'm having trouble understanding your request right now. "
        "Could you try rephrasing it? For example:\n"
        "- 'Generate my weekly report'\n"
        "- 'Create an agent that sends Slack messages'\n"
        "- 'What agents do I have?'"
    )

def _handle_discovery_error(self, error: AgentDiscoveryError) -> str:
    """Handle agent discovery failures."""
    return (
        "I'm experiencing issues finding available agents. "
        "This is likely a temporary problem. Please try again in a moment."
    )

def _handle_circular_error(self, error: CircularRoutingError) -> str:
    """Handle circular routing detection."""
    return (
        "I detected a routing loop and stopped to prevent issues. "
        "Please try a more specific request."
    )

def _handle_unexpected_error(self, error: Exception) -> str:
    """Handle unexpected errors gracefully."""
    return (
        "I encountered an unexpected issue processing your request. "
        "Our team has been notified. Please try again or contact support "
        "if the problem persists."
    )
```

---

## Performance and Scalability

### Latency Budget

| Component | Budget | Strategy |
|-----------|--------|----------|
| Intent Analysis | 200ms | Fast model, structured output |
| Agent Discovery | 100ms | In-memory registry, efficient filtering |
| Clarification Gen | 100ms | Cached templates, fast model |
| Agent Routing | 50ms | Direct call, no additional processing |
| **Total E2E** | **500ms** | Parallel where possible |

### Caching Strategy

```python
# Cache configuration
CACHE_CONFIG = {
    # Intent analysis cache (same message = same intent)
    "intent_cache": {
        "enabled": True,
        "ttl_seconds": 60,
        "max_size": 1000
    },

    # Agent list cache (per tenant)
    "agent_cache": {
        "enabled": True,
        "ttl_seconds": 30,
        "max_size": 100
    },

    # Clarification templates (static)
    "template_cache": {
        "enabled": True,
        "ttl_seconds": 3600,
        "max_size": 50
    }
}
```

### Scalability Considerations

1. **Stateless Design** - Master Agent is stateless; context managed externally
2. **Horizontal Scaling** - Multiple instances can run in parallel
3. **Registry Efficiency** - Use indexed lookups for large agent counts
4. **LLM Rate Limiting** - Built-in rate limiting via existing tools
5. **Connection Pooling** - Reuse LLM connections across requests

---

## Testing Strategy

### Unit Tests

```python
# tests/test_master_agent/test_intent_analyzer.py

import pytest
from unittest.mock import AsyncMock, MagicMock

from omniforge.master_agent.intent.analyzer import IntentAnalyzer
from omniforge.master_agent.intent.models import ActionType


class TestIntentAnalyzer:
    """Tests for IntentAnalyzer."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM tool."""
        llm = MagicMock()
        llm.execute = AsyncMock()
        return llm

    @pytest.fixture
    def analyzer(self, mock_llm):
        """Create analyzer with mock LLM."""
        return IntentAnalyzer(llm_tool=mock_llm)

    @pytest.mark.asyncio
    async def test_analyze_create_intent(self, analyzer, mock_llm):
        """Should detect CREATE intent correctly."""
        mock_llm.execute.return_value = MagicMock(
            success=True,
            result={
                "content": '{"action_type": "CREATE", "primary_intent": "create agent", '
                          '"entities": {}, "confidence": 0.95, "ambiguous": false}'
            }
        )

        result = await analyzer.analyze("I need an agent that sends Slack messages")

        assert result.action_type == ActionType.CREATE
        assert result.confidence >= 0.9
        assert not result.ambiguous

    @pytest.mark.asyncio
    async def test_analyze_execute_intent(self, analyzer, mock_llm):
        """Should detect EXECUTE intent correctly."""
        mock_llm.execute.return_value = MagicMock(
            success=True,
            result={
                "content": '{"action_type": "EXECUTE", "primary_intent": "generate report", '
                          '"entities": {"data_source": "notion"}, "confidence": 0.92, '
                          '"ambiguous": false}'
            }
        )

        result = await analyzer.analyze("Generate my weekly Notion report")

        assert result.action_type == ActionType.EXECUTE
        assert result.entities.data_source == "notion"
```

### Integration Tests

```python
# tests/test_master_agent/test_integration.py

import pytest
from omniforge.master_agent.agent import MasterAgent
from omniforge.agents.registry import AgentRegistry
from omniforge.storage.memory import InMemoryAgentRepository


class TestMasterAgentIntegration:
    """Integration tests for Master Agent."""

    @pytest.fixture
    def registry(self):
        """Create test registry."""
        repo = InMemoryAgentRepository()
        return AgentRegistry(repository=repo)

    @pytest.fixture
    def master_agent(self, registry):
        """Create Master Agent for testing."""
        return MasterAgent(agent_registry=registry)

    @pytest.mark.asyncio
    async def test_full_routing_flow(self, master_agent):
        """Test complete routing flow from request to response."""
        # Create test task
        task = create_test_task("Generate my weekly report")

        # Process through Master Agent
        events = []
        async for event in master_agent.process_task(task):
            events.append(event)

        # Verify events
        assert len(events) > 0
        assert events[-1].type == "done"
```

### Test Coverage Requirements

| Component | Required Coverage |
|-----------|------------------|
| IntentAnalyzer | 90% |
| MasterAgentRouter | 90% |
| ClarificationManager | 85% |
| QueryHandlerRegistry | 85% |
| MasterAgent (overall) | 80% |

---

## Implementation Phases

### Phase 1: Basic Routing (MVP) - 2 weeks

**Scope:**
- MasterAgent class extending CoTAgent
- IntentAnalyzer with LLM-based analysis
- Basic agent discovery (skill matching)
- Single-choice routing (pick best agent)
- Basic error handling

**Deliverables:**
1. `src/omniforge/master_agent/agent.py`
2. `src/omniforge/master_agent/intent/` module
3. `src/omniforge/master_agent/routing/` module
4. `src/omniforge/master_agent/discovery/` module
5. Unit tests for all components

**Success Criteria:**
- Can route clear EXECUTE requests to correct agents
- Can detect CREATE/UPDATE/QUERY intents
- >80% accuracy on test set

### Phase 2: Clarification System - 1 week

**Scope:**
- ClarificationManager implementation
- Multiple choice question generation
- Entity clarification questions
- Open-ended questions
- Multi-turn clarification flow

**Deliverables:**
1. `src/omniforge/master_agent/clarification/` module
2. `src/omniforge/master_agent/context/` module
3. Integration with MasterAgent
4. Tests for clarification flows

**Success Criteria:**
- Can handle ambiguous requests gracefully
- Multi-turn clarification works correctly
- <30% of requests require clarification

### Phase 3: Query Handler System - 1 week

**Scope:**
- QueryHandler base class
- QueryHandlerRegistry
- LLMQueryHandler (fallback)
- AgentListQueryHandler
- Integration with MasterAgent

**Deliverables:**
1. `src/omniforge/master_agent/query_handlers/` module
2. At least 2 specialized handlers
3. Tests for query handling

**Success Criteria:**
- Extensible handler system works
- Can answer "list my agents" queries
- LLM fallback handles general questions

### Phase 4: Polish and Optimization - 1 week

**Scope:**
- Power user overrides (@agent syntax)
- Debug/transparency mode
- Performance optimization
- Caching implementation
- Documentation

**Deliverables:**
1. @agent override implementation
2. Debug mode for routing visibility
3. Caching for intent analysis
4. User documentation
5. API documentation

**Success Criteria:**
- E2E latency <500ms
- >85% routing accuracy
- Production-ready code quality

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM latency spikes | High | Medium | Caching, timeout handling, fallback |
| Intent misclassification | High | Medium | Confidence thresholds, clarification |
| Agent Builder not ready | Medium | High | Stub implementation, graceful messaging |
| Circular routing loops | High | Low | Depth tracking, circuit breaker |
| Rate limit exhaustion | Medium | Low | Request queuing, LiteLLM retry |

### Dependency Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| AgentRegistry API changes | High | Low | Interface wrapper, abstraction layer |
| LLM model deprecation | Medium | Low | LiteLLM abstraction, model config |
| Chat service changes | Medium | Low | Adapter pattern, loose coupling |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Poor routing decisions | High | Medium | Logging, monitoring, feedback loop |
| User frustration with clarifications | Medium | Medium | Limit clarification rounds, smart defaults |
| Tenant data leakage | Critical | Low | Strict tenant filtering, tests |

---

## Alternative Approaches

### Alternative 1: Rules-Based Intent Detection

**Description:** Use keyword matching and regex patterns instead of LLM for intent detection.

**Pros:**
- Faster (<10ms vs 200ms)
- Deterministic behavior
- No LLM costs
- Simpler debugging

**Cons:**
- Less flexible to natural language
- Requires manual rule maintenance
- Poor handling of edge cases
- Cannot extract complex entities

**Recommendation:** Not recommended. Natural language understanding requires LLM.

### Alternative 2: Extend BaseAgent Instead of CoTAgent

**Description:** Have MasterAgent extend BaseAgent directly instead of CoTAgent.

**Pros:**
- Simpler implementation
- Less overhead
- Faster execution

**Cons:**
- No visible reasoning chain
- Harder to debug routing decisions
- Cannot leverage ReasoningEngine

**Recommendation:** Not recommended. Transparency is critical for routing debugging.

### Alternative 3: Synchronous Query Handler Resolution

**Description:** Resolve query handlers synchronously at registration time instead of per-request.

**Pros:**
- Faster per-request handling
- Simpler flow

**Cons:**
- Cannot consider request context in handler selection
- Less flexible matching

**Recommendation:** Async resolution preferred for context-aware handler selection.

### Alternative 4: Multi-Agent Routing (Future)

**Description:** Support routing to multiple agents in parallel or sequence.

**Pros:**
- More powerful workflows
- Can combine agent capabilities

**Cons:**
- Significantly more complex
- Out of Phase 1 scope
- Orchestration challenges

**Recommendation:** Defer to Phase 2+ per product spec.

---

## Appendix

### A. Intent Analysis Prompt Template

```python
INTENT_ANALYSIS_PROMPT = """Analyze the following user message and extract intent information.

User Message: {user_message}
{context}

Determine:
1. What type of action does the user want? (CREATE/UPDATE/EXECUTE/QUERY/AMBIGUOUS)
2. What specifically do they want to accomplish?
3. What entities (agents, data sources, targets) are mentioned?
4. How confident are you in this interpretation? (0.0-1.0)
5. Are there multiple valid interpretations?

Remember:
- CREATE = User wants to build a NEW agent
- UPDATE = User wants to MODIFY an existing agent
- EXECUTE = User wants to RUN an existing agent
- QUERY = User is asking questions/seeking information
- AMBIGUOUS = Cannot determine with confidence

Respond with JSON only."""
```

### B. Configuration Constants

```python
# src/omniforge/master_agent/config.py

class MasterAgentConfig:
    """Configuration constants for Master Agent."""

    # Confidence thresholds
    HIGH_CONFIDENCE_THRESHOLD = 0.85
    MEDIUM_CONFIDENCE_THRESHOLD = 0.60

    # Agent scoring
    SIMILAR_SCORE_THRESHOLD = 0.15  # 15% difference
    SKILL_WEIGHT = 0.6
    DOMAIN_WEIGHT = 0.2
    PERFORMANCE_WEIGHT = 0.1
    RECENCY_WEIGHT = 0.1

    # Clarification limits
    MAX_CLARIFICATION_ROUNDS = 3
    MAX_MULTIPLE_CHOICE_OPTIONS = 4

    # Routing safety
    MAX_ROUTING_DEPTH = 2

    # Context management
    MAX_CONTEXT_MESSAGES = 10
    CONTEXT_TTL_SECONDS = 3600

    # Cache settings
    INTENT_CACHE_TTL_SECONDS = 60
    AGENT_CACHE_TTL_SECONDS = 30

    # LLM settings
    INTENT_ANALYSIS_MODEL = "gpt-4o-mini"
    INTENT_ANALYSIS_TEMPERATURE = 0.0
    CLARIFICATION_MODEL = "gpt-4o-mini"
    CLARIFICATION_TEMPERATURE = 0.7
```

### C. Sequence Diagrams

**CREATE Intent Flow:**
```
User -> MasterAgent: "I need an agent that sends Slack messages"
MasterAgent -> IntentAnalyzer: analyze(message)
IntentAnalyzer -> LLM: structured prompt
LLM -> IntentAnalyzer: {action_type: CREATE, confidence: 0.92}
IntentAnalyzer -> MasterAgent: IntentAnalysis
MasterAgent -> MasterAgent: route_to_builder()
MasterAgent -> AgentBuilder: CREATE context
AgentBuilder -> User: "I can help you create that agent..."
```

**EXECUTE Intent Flow:**
```
User -> MasterAgent: "Generate my weekly report"
MasterAgent -> IntentAnalyzer: analyze(message)
IntentAnalyzer -> LLM: structured prompt
LLM -> IntentAnalyzer: {action_type: EXECUTE, confidence: 0.95}
IntentAnalyzer -> MasterAgent: IntentAnalysis
MasterAgent -> DiscoveryService: discover_agents(tenant, intent)
DiscoveryService -> AgentRegistry: list_all(tenant)
AgentRegistry -> DiscoveryService: [agents]
DiscoveryService -> MasterAgent: [ScoredAgent(score=0.92)]
MasterAgent -> CustomerAgent: route_to_agent(task)
CustomerAgent -> User: "Here's your weekly report..."
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | Technical Architect | Initial version |

---

**Next Steps:**
1. Review and approve technical plan
2. Create task breakdown for Phase 1
3. Begin implementation of MasterAgent class
4. Set up test infrastructure
