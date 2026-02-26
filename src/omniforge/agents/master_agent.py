"""Master Agent - Central orchestrator for all platform operations.

The Master Agent is a ReAct-based autonomous agent that uses platform
management tools to orchestrate all OmniForge operations. Rather than
relying on keyword matching or hardcoded routing, it reasons about user
requests and calls the appropriate tools (create_agent, list_agents, etc.)
to fulfill them — embodying the "agents build agents" philosophy.

Session state: MasterAgent is stateful. When delegate_to_agent fires, it
stores the sub-agent reference and forwards all subsequent messages to it
until that sub-agent signals completion or the user cancels.
"""

import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

from omniforge.agents.autonomous_simple import SimpleAutonomousAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskErrorEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.helpers import get_latest_user_message
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.agents.registry import AgentRegistry
from omniforge.tasks.models import Task, TaskMessage, TaskState
from omniforge.tools.registry import ToolRegistry

_CANCEL_WORDS = frozenset({"cancel", "exit", "quit", "stop", "start over", "reset", "done"})

_RETURN_CLASSIFICATION_PROMPT = """\
The user is currently talking to a sub-agent. Does the following message indicate that \
the user wants to stop the sub-agent and return to the main/master assistant?

Message: "{message}"

Reply with ONLY the single word YES or NO."""


class MasterAgent(SimpleAutonomousAgent):
    """Master Agent - Central orchestrator for the OmniForge platform.

    Extends SimpleAutonomousAgent with platform management tools, enabling
    the agent to create agents, manage skills, and answer platform queries
    entirely through the ReAct reasoning loop — no keyword matching required.

    Stateful delegation: when the LLM calls delegate_to_agent, subsequent
    messages are forwarded directly to the selected sub-agent until it
    completes or the user cancels.

    The agent has access to:
    - ``list_agents``: Discover registered agents
    - ``list_skills``: Browse the skills library
    - ``create_agent``: Build and register a new agent (auto-loads all skills)
    - ``add_skill_to_agent``: Explicitly assign a skill to an existing agent
    - ``delegate_to_agent``: Delegate conversation to a specific agent

    Attributes:
        identity: Master Agent identity
        capabilities: Streaming + multi-turn support
        skills: Platform orchestration skill
    """

    identity = AgentIdentity(
        id="master-agent",
        name="Master Agent",
        description="Central orchestrator for all platform operations",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        hitl_support=False,
    )

    skills = [
        AgentSkill(
            id="platform-orchestration",
            name="Platform Orchestration",
            description=("Create and manage agents and skills on the OmniForge platform"),
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    _SYSTEM_PROMPT = """\
You are the OmniForge Master Agent — the central orchestrator for an \
enterprise AI agent platform where agents build agents.

## Your Capabilities
You help users manage their AI agent platform through these tools:
- `list_agents` — show all registered agents (id, name, skill count)
- `list_skills` — browse the full skills library
- `create_agent` — build and register a new agent (auto-loads ALL library skills)
- `add_skill_to_agent` — explicitly tag an existing agent with a specific skill
- `delegate_to_agent` — hand off the conversation to a specific agent
- `store_artifact` — persist skill output as a named, typed artifact (when available)
- `fetch_artifact` — retrieve a previously stored artifact by ID (when available)

## Intent Disambiguation — Read This First

Before deciding which rule to apply, identify what the user actually wants:

| User intent | Correct action |
|---|---|
| "create / build / make an agent" | → create_agent rule |
| "list / show my agents" | → list_agents rule |
| "list / show skills" | → list_skills rule |
| "add / assign / attach a skill to my agent" | → add_skill_to_agent rule |
| "talk to / use / switch to agent X" | → delegate_to_agent rule |
| "write / author / build a new custom skill from scratch" | → skill-author rule |
| anything about what OmniForge can do | → explain platform |

CRITICAL: Do NOT route to the skill-creation-assistant just because the user \
mentions the word "skill". Only delegate there when the user explicitly wants to \
author brand-new SKILL.md code that does not yet exist in the library.

## Decision Rules — Follow These Exactly

### When user wants to LIST agents:
- Call `list_agents` and present results in a readable format.
- If no agents exist, suggest creating one.

### When user wants to LIST or FIND skills:
- Call `list_skills` and present the results.
- If user is looking for a specific skill type, filter the output by relevance.

### When user wants to ADD a skill to an existing agent:
1. If agent ID is unknown, call `list_agents` to find it.
2. Call `list_skills` to confirm the skill ID exists.
3. Call `add_skill_to_agent` with both IDs.
4. Confirm the assignment was successful.

### When user wants to CREATE an agent:
1. Call `list_agents` first to check for duplicates by name or purpose.
2. If a similar agent already exists, tell the user and ask if they want to proceed anyway.
3. If no duplicate, call `create_agent` with:
   - `name`: Clear, descriptive name (e.g. "Customer Outreach Agent", not "agent1")
   - `purpose`: One-sentence description of what this agent does
   - `capabilities`: Comma-separated list of skills/features the user mentioned
4. Report the created agent's ID and confirm how many skills were loaded.

### When user wants to TALK TO or USE a specific agent:
- Call `list_agents` to find the agent's ID.
- Call `delegate_to_agent` with that agent's ID.
- IMMEDIATELY after calling delegate_to_agent, respond with is_final=true and a \
brief message like "You are now connected to [agent name]. Your message will be \
handled by them."
- Do NOT call any other tools after delegate_to_agent. Stop immediately.

### When you receive context that a delegation completed successfully:
- Acknowledge what was accomplished in one sentence.
- Ask the user "What would you like to do next?"
- Do NOT re-delegate to the same agent unless the user explicitly asks again.

### When user wants to AUTHOR a brand-new custom skill (new SKILL.md code):
Only apply this rule when the user explicitly wants to write/create new skill code \
that does not exist yet — NOT when they want to add an existing skill to an agent.
1. Call `list_skills` first to check if a similar skill already exists.
2. If a matching skill exists, tell the user and ask if they want it added to an agent instead.
3. Only if no existing skill covers the use case, call `delegate_to_agent` \
with `agent_id="skill-creation-assistant"`.
4. Do NOT try to create the skill yourself — the Skill Creation Assistant will \
guide the user through a multi-step process.

### After a skill returns data worth keeping:
- If the result should be saved for future retrieval, call `store_artifact` with:
  - `type`: one of document, dataset, code, image, structured
  - `title`: a clear descriptive name
  - `content`: the skill's output (JSON string for structured data, plain text otherwise)
- Report the returned `artifact_id` to the user so they can retrieve it later.
- Use `fetch_artifact` when the user asks to retrieve or view a previously stored result.

### When user asks about OmniForge or what they can do:
- Explain the platform briefly: agents can be created via chat, auto-load skills, \
and can be used for any automation task.
- List the things you can do (create/list agents, list skills, delegate, author skills, \
store/fetch artifacts).

### When user request is vague or ambiguous:
- Ask one clarifying question to determine their intent before calling any tool.
- If unclear whether they want to "add an existing skill" vs "author a new skill", \
ask explicitly: "Do you want to add an existing skill from the library, or create a \
brand-new custom skill?"

### When a tool call fails:
- Read the error message carefully.
- If the agent doesn't exist, call `list_agents` to show what does exist.
- If the skill doesn't exist, call `list_skills` to show available options.
- Never retry the same failing call with the same arguments.

## Response Style
- Be concise — one short paragraph or a brief bullet list is enough.
- Always confirm what action was taken and its outcome.
- Never fabricate agent IDs or skill names — always verify with tools first.
- Format agent/skill IDs as `code` when mentioning them.
"""

    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        tenant_id: Optional[str] = None,
        artifact_store: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the Master Agent with platform management tools.

        Args:
            agent_registry: Registry for agent discovery and management.
                           Platform tools are only registered when provided.
            tenant_id: Tenant identifier for multi-tenant isolation
            artifact_store: Optional ArtifactStore for persistent artifact storage.
                           When provided, store_artifact and fetch_artifact tools
                           are registered in the tool registry.
            **kwargs: Additional arguments passed to SimpleAutonomousAgent
        """
        # Delegation state — set before tool registration so callback is valid
        self._delegated_agent: Optional[Any] = None
        # Failure context from the last delegation — injected into the next ReAct turn
        self._last_delegation_error: Optional[str] = None
        # Success context from the last delegation — injected into the next ReAct turn
        self._last_delegation_success: Optional[str] = None
        # MCP lazy-init state
        self._mcp_initialized: bool = False
        self._mcp_manager: Optional[Any] = None

        # Build registry: default tools (includes llm) + platform tools
        from omniforge.llm.config import load_config_from_env
        from omniforge.tools.setup import setup_default_tools

        platform_registry = ToolRegistry()
        setup_default_tools(platform_registry)

        if agent_registry is not None:
            from omniforge.skills.creation.agent import SkillCreationAgent
            from omniforge.tools.builtin.platform import register_platform_tools

            # Built-in sub-agent available for delegation without registry lookup
            self._skill_creation_agent = SkillCreationAgent()

            register_platform_tools(
                platform_registry,
                agent_registry,
                tenant_id,
                on_delegate=self._set_delegated_agent,
                local_agents={self._skill_creation_agent.identity.id: self._skill_creation_agent},
            )
        else:
            self._skill_creation_agent = None

        if artifact_store is not None:
            from omniforge.tools.builtin.artifact import register_artifact_tools

            register_artifact_tools(platform_registry, artifact_store)

        # Use the env-configured default model instead of the hardcoded fallback
        llm_config = load_config_from_env()
        kwargs.setdefault("model", llm_config.default_model)

        super().__init__(
            system_prompt=self._SYSTEM_PROMPT,
            tool_registry=platform_registry,
            tenant_id=tenant_id,
            **kwargs,
        )

        # Expose registry for MasterResponseGenerator compatibility
        self._agent_registry = agent_registry

    async def _wants_to_return_to_master(self, user_message: str) -> bool:
        """Determine if the user wants to return to the master agent.

        Uses a two-stage approach:
        1. Fast path: exact keyword match (zero latency)
        2. LLM fallback: classifies natural-language intent when no keyword matches

        Args:
            user_message: The raw user message text

        Returns:
            True if the user wants to return to the master agent, False otherwise
        """
        # Fast path — unambiguous keywords
        if user_message.lower().strip() in _CANCEL_WORDS:
            return True

        # LLM fallback — handle natural language like "take me back", "I'm done here", etc.
        try:
            import litellm

            prompt = _RETURN_CLASSIFICATION_PROMPT.format(message=user_message)
            response = await litellm.acompletion(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=5,
                temperature=0.0,
            )
            answer = response.choices[0].message.content.strip().upper()
            return answer.startswith("YES")
        except Exception as exc:
            logger.debug("Return-to-master classification failed, forwarding to sub-agent: %s", exc)
            return False

    def _set_delegated_agent(self, agent: Any) -> None:
        """Callback invoked by DelegateToAgentTool to set the active sub-agent.

        Args:
            agent: The agent instance to delegate subsequent messages to
        """
        self._delegated_agent = agent

    async def _ensure_mcp_initialized(self) -> None:
        """Lazily connect to MCP servers on the first task.

        Reads OMNIFORGE_MCP_CONFIG and registers any configured server tools
        into this agent's tool registry. Failed servers are logged and skipped.
        """
        if self._mcp_initialized:
            return
        self._mcp_initialized = True  # set before await to prevent concurrent double-init
        try:
            from omniforge.tools.setup import setup_mcp_tools

            self._mcp_manager = await setup_mcp_tools(self._tool_registry)
            if self._mcp_manager:
                logger.info("MCP servers connected: %s", self._mcp_manager.connected_servers)
        except Exception as exc:
            logger.warning("MCP initialization failed (continuing without MCP): %s", exc)

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:  # type: ignore[override]
        """Process a task with stateful delegation support.

        Decision order:
        1. Cancel word + active delegation → clear delegation, confirm
        2. Active delegation → forward task to delegated agent
        3. No delegation → normal ReAct loop via super().process_task()

        Args:
            task: The task to process

        Yields:
            TaskEvent objects
        """
        user_message = get_latest_user_message(task)

        # ── Handle cancellation of active delegation ──────────────────────
        if self._delegated_agent is not None and await self._wants_to_return_to_master(user_message):
            self._delegated_agent = None
            now = datetime.utcnow()
            yield TaskStatusEvent(task_id=task.id, timestamp=now, state=TaskState.WORKING)
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=now,
                message_parts=[TextPart(text="Delegation cancelled. How else can I help you?")],
                is_partial=False,
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=now,
                final_state=TaskState.COMPLETED,
            )
            return

        # ── Forward to delegated agent ────────────────────────────────────
        if self._delegated_agent is not None:
            async for event in self._handle_delegation(task):
                yield event
            return

        # ── Normal ReAct loop ─────────────────────────────────────────────
        # Connect to MCP servers on first task (no-op on subsequent calls)
        await self._ensure_mcp_initialized()

        # Set root trace_id on first entry (when not already set by a parent)
        if task.trace_id is None:
            task = task.model_copy(update={"trace_id": task.id})

        # Inject prior delegation outcome into the task history so the LLM
        # can reason about what happened and course-correct or acknowledge
        if self._last_delegation_success is not None:
            success_context = self._last_delegation_success
            self._last_delegation_success = None
            task = self._inject_context_message(task, success_context)

        if self._last_delegation_error is not None:
            error_context = self._last_delegation_error
            self._last_delegation_error = None
            task = self._inject_context_message(task, error_context)

        # Track whether delegate_to_agent was called during this ReAct turn
        delegation_set_during_react = False
        async for event in super().process_task(task):
            # When delegation was set mid-loop, suppress the master's own COMPLETED
            # event — the subagent will emit its own terminal event below
            if (
                self._delegated_agent is not None
                and isinstance(event, TaskDoneEvent)
                and event.final_state == TaskState.COMPLETED
            ):
                delegation_set_during_react = True
                continue
            yield event

        # If delegation was triggered during this turn, immediately run the
        # subagent with the SAME user message so the original request is forwarded
        if delegation_set_during_react and self._delegated_agent is not None:
            async for event in self._handle_delegation(task):
                yield event

    async def _handle_delegation(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Run the currently delegated sub-agent for one task turn.

        Remaps task IDs, captures errors, stores outcome context for the next
        ReAct turn, and auto-clears _delegated_agent on any terminal state.

        Args:
            task: The parent task (used for task_id remapping and subtask creation)

        Yields:
            TaskEvent objects from the delegated agent
        """
        delegated_id = (
            self._delegated_agent.identity.id
            if hasattr(self._delegated_agent, "identity")
            else "agent"
        )
        now = datetime.utcnow()
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=now,
            state=TaskState.WORKING,
            message=f"Delegating to '{delegated_id}'...",
        )
        subtask = self._make_subtask(task)
        last_error_message: Optional[str] = None
        last_agent_message: Optional[str] = None  # captures subagent's final response text
        async for event in self._delegated_agent.process_task(subtask):
            # Remap task_id so caller sees consistent IDs
            if hasattr(event, "task_id"):
                event = event.model_copy(update={"task_id": task.id})

            # Capture the subagent's last complete (non-partial) message text
            if isinstance(event, TaskMessageEvent) and not event.is_partial:
                parts_text = " ".join(
                    p.text for p in event.message_parts if hasattr(p, "text") and p.text
                ).strip()
                if parts_text:
                    last_agent_message = parts_text

            # Capture error reason so we can surface it if the task fails
            if isinstance(event, TaskErrorEvent):
                last_error_message = event.error_message

            # Auto-clear delegation on any terminal state and store outcome context
            if isinstance(event, TaskDoneEvent) and event.final_state in (
                TaskState.COMPLETED,
                TaskState.FAILED,
                TaskState.CANCELLED,
            ):
                self._delegated_agent = None
                if event.final_state == TaskState.COMPLETED:
                    # Inject success context including the subagent's actual result
                    result_summary = (
                        f' The agent\'s final response was: "{last_agent_message}"'
                        if last_agent_message
                        else ""
                    )
                    self._last_delegation_success = (
                        f"[Delegation to '{delegated_id}' completed successfully.{result_summary} "
                        "The user is now back with you (Master Agent). "
                        "Acknowledge what was done and ask what they'd like to do next.]"
                    )
                else:
                    agent_id = subtask.agent_id
                    reason = (
                        last_error_message or f"task ended with state: {event.final_state.value}"
                    )
                    user_error_text = (
                        f"I wasn't able to complete that with '{delegated_id}'. "
                        f"{reason}. What would you like to do instead?"
                    )
                    self._last_delegation_error = (
                        f"[Delegation to '{delegated_id}' ended with "
                        f"{event.final_state.value}. Reason: {reason}. "
                        "Tell the user what failed and ask what to do next.]"
                    )
                    now = datetime.utcnow()
                    yield TaskMessageEvent(
                        task_id=task.id,
                        timestamp=now,
                        message_parts=[TextPart(text=user_error_text)],
                        is_partial=False,
                    )

            yield event

    def _inject_context_message(self, task: Task, context_text: str) -> Task:
        """Return a copy of *task* with an assistant context message prepended.

        This is used to surface delegation failure details to the LLM on the
        next ReAct turn so it can course-correct without relying on the client
        to relay the failure back via conversation_history.

        Args:
            task: The incoming task
            context_text: Context string to prepend as an agent (assistant) message

        Returns:
            New Task with the context message inserted before the last user message
        """
        now = datetime.utcnow()
        context_msg = TaskMessage(
            id=str(uuid4()),
            role="agent",
            parts=[TextPart(text=context_text)],
            created_at=now,
        )
        # Insert just before the final user message so the LLM sees:
        # [history...] [error context] [current user message]
        new_messages = list(task.messages[:-1]) + [context_msg] + list(task.messages[-1:])
        return task.model_copy(update={"messages": new_messages})

    def _make_subtask(self, parent_task: Task) -> Task:
        """Create a sub-task for the delegated agent from the parent task.

        Includes up to 5 prior messages from the parent task as context,
        plus the latest user message. Inherits conversation_id so the
        sub-agent can use the same HITL session key.

        Args:
            parent_task: The parent task from MasterAgent

        Returns:
            A new Task with parent_task_id and conversation_id set
        """
        now = datetime.utcnow()
        agent_id = (
            self._delegated_agent.identity.id if self._delegated_agent is not None else "unknown"
        )
        # Include up to 5 prior messages for context (all except the last user message)
        prior_messages = list(parent_task.messages[:-1])[-5:]
        # Preserve the full last user message (all parts: text, images, files)
        last_user_msg = next(
            (msg for msg in reversed(parent_task.messages) if msg.role == "user"),
            None,
        )
        if last_user_msg is not None:
            forwarded_msg = TaskMessage(
                id=str(uuid4()),
                role="user",
                parts=last_user_msg.parts,
                created_at=now,
            )
        else:
            forwarded_msg = TaskMessage(
                id=str(uuid4()),
                role="user",
                parts=[TextPart(text="")],
                created_at=now,
            )
        messages = prior_messages + [forwarded_msg]
        return Task(
            id=str(uuid4()),
            agent_id=agent_id,
            state=TaskState.SUBMITTED,
            messages=messages,
            parent_task_id=parent_task.id,
            created_at=now,
            updated_at=now,
            user_id=parent_task.user_id,
            tenant_id=parent_task.tenant_id,
            conversation_id=parent_task.conversation_id,
            trace_id=parent_task.trace_id,
        )
