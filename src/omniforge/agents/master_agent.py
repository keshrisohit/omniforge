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

from datetime import datetime
from typing import Any, AsyncIterator, Optional
from uuid import uuid4

from omniforge.agents.autonomous_simple import SimpleAutonomousAgent
from omniforge.agents.events import TaskDoneEvent, TaskEvent, TaskMessageEvent, TaskStatusEvent
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

## Decision Rules — Follow These Exactly

### When user wants to CREATE an agent:
1. Call `list_agents` first to check for duplicates by name or purpose.
2. If a similar agent already exists, tell the user and ask if they want to proceed anyway.
3. If no duplicate, call `create_agent` with:
   - `name`: Clear, descriptive name (e.g. "Customer Outreach Agent", not "agent1")
   - `purpose`: One-sentence description of what this agent does
   - `capabilities`: Comma-separated list of skills/features the user mentioned
4. Report the created agent's ID and confirm how many skills were loaded.

### When user wants to CREATE a SKILL (new code/behaviour):
- Call `delegate_to_agent` with `agent_id="skill-creation-assistant"`.
- Do NOT try to create the skill yourself — the Skill Creation Assistant will \
guide the user through a multi-step process.

### When user wants to TALK TO or USE a specific agent:
- Call `list_agents` to find the agent's ID.
- Call `delegate_to_agent` with that agent's ID.
- The user's subsequent messages will be handled by that agent.

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

### When user asks about OmniForge or what they can do:
- Explain the platform briefly: agents can be created via chat, auto-load skills, \
and can be used for any automation task.
- List the things you can do (create/list agents, list skills, delegate, create skills).

### When user request is vague or ambiguous:
- Ask one clarifying question to determine their intent before calling any tool.

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
        **kwargs: Any,
    ) -> None:
        """Initialize the Master Agent with platform management tools.

        Args:
            agent_registry: Registry for agent discovery and management.
                           Platform tools are only registered when provided.
            tenant_id: Tenant identifier for multi-tenant isolation
            **kwargs: Additional arguments passed to SimpleAutonomousAgent
        """
        # Delegation state — set before tool registration so callback is valid
        self._delegated_agent: Optional[Any] = None

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
                local_agents={
                    self._skill_creation_agent.identity.id: self._skill_creation_agent
                },
            )
        else:
            self._skill_creation_agent = None

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

    def _set_delegated_agent(self, agent: Any) -> None:
        """Callback invoked by DelegateToAgentTool to set the active sub-agent.

        Args:
            agent: The agent instance to delegate subsequent messages to
        """
        self._delegated_agent = agent

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
        if self._delegated_agent is not None and user_message.lower().strip() in _CANCEL_WORDS:
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
            subtask = self._make_subtask(task)
            async for event in self._delegated_agent.process_task(subtask):
                # Remap task_id to parent task so caller sees consistent IDs
                if hasattr(event, "task_id"):
                    object.__setattr__(event, "task_id", task.id)
                # Auto-clear delegation when sub-agent completes
                if isinstance(event, TaskDoneEvent) and event.final_state == TaskState.COMPLETED:
                    self._delegated_agent = None
                yield event
            return

        # ── Normal ReAct loop ─────────────────────────────────────────────
        async for event in super().process_task(task):
            yield event

    def _make_subtask(self, parent_task: Task) -> Task:
        """Create a sub-task for the delegated agent from the parent task.

        Only the latest user message is forwarded; the delegated agent
        manages its own session history internally.

        Args:
            parent_task: The parent task from MasterAgent

        Returns:
            A new Task with parent_task_id set
        """
        now = datetime.utcnow()
        user_message = get_latest_user_message(parent_task)
        agent_id = (
            self._delegated_agent.identity.id
            if self._delegated_agent is not None
            else "unknown"
        )
        return Task(
            id=str(uuid4()),
            agent_id=agent_id,
            state=TaskState.SUBMITTED,
            messages=[
                TaskMessage(
                    id=str(uuid4()),
                    role="user",
                    parts=[TextPart(text=user_message)],
                    created_at=now,
                )
            ],
            parent_task_id=parent_task.id,
            created_at=now,
            updated_at=now,
            user_id=parent_task.user_id,
            tenant_id=parent_task.tenant_id,
        )
