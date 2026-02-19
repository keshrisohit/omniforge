"""
Skill Orchestrator Agent

This agent dynamically discovers available skills, intelligently selects the appropriate
skill(s) based on user prompts, and executes them to accomplish tasks.

Key Features:
- Automatic skill discovery and indexing
- Intelligent skill selection using LLM reasoning
- Dynamic skill loading and execution
- Multi-skill orchestration for complex tasks
- Tool restriction enforcement
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    Artifact,
    SkillInputMode,
    SkillOutputMode,
)
from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.loader import SkillLoader
from omniforge.skills.models import Skill
from omniforge.skills.storage import StorageConfig
from omniforge.skills.orchestrator import SkillOrchestrator
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.tasks.models import Task, TaskState
from omniforge.agents.helpers import extract_user_message

logger = logging.getLogger(__name__)


class SkillOrchestratorAgent(BaseAgent):
    """Agent that orchestrates skill discovery, selection, and execution.

    This agent:
    1. Discovers all available skills at initialization
    2. Analyzes user prompts to determine required skills
    3. Loads skill content dynamically
    4. Executes skills with proper tool restrictions
    5. Returns results to the user
    """

    def __init__(
        self,
        agent_id: str = "skill-orchestrator",
        skills_path: Optional[Path] = None,
        tenant_id: Optional[str] = None,
        llm_generator: Optional[LLMResponseGenerator] = None,
    ):
        """Initialize the Skill Orchestrator Agent.

        Args:
            agent_id: Unique identifier for this agent instance
            skills_path: Optional custom path to skills directory
            tenant_id: Optional tenant identifier for multi-tenancy
            llm_generator: Optional LLM generator for reasoning
        """
        self._agent_id = agent_id
        self._tenant_id = tenant_id
        self._llm_generator = llm_generator or LLMResponseGenerator(temperature=0.7, max_tokens=2000)

        # Setup skill loader
        if skills_path:
            storage_config = StorageConfig(plugin_paths=[skills_path])
        else:
            # Use default OmniForge skills path
            storage_config = StorageConfig.from_environment()

        self._skill_loader = SkillLoader(config=storage_config)

        # Initialize tool registry for skill execution
        self._tool_registry = ToolRegistry()

        # Register builtin tools
        from omniforge.tools.builtin import (
            BashTool,
            ReadTool,
            WriteTool,
            GlobTool,
            GrepTool,
        )
        from omniforge.tools.builtin.llm import LLMTool

        self._tool_registry.register(BashTool())
        self._tool_registry.register(ReadTool())
        self._tool_registry.register(WriteTool())
        self._tool_registry.register(GlobTool())
        self._tool_registry.register(GrepTool())
        self._tool_registry.register(LLMTool())
        logger.info(f"Registered {len(self._tool_registry.list_tools())} builtin tools")

        # Initialize tool executor for skill execution
        self._tool_executor = ToolExecutor(registry=self._tool_registry)

        # Initialize skill orchestrator for skill execution
        self._skill_orchestrator = SkillOrchestrator(
            skill_loader=self._skill_loader,
            tool_registry=self._tool_registry,
            tool_executor=self._tool_executor,
        )

        # Build skill index
        skill_count = self._skill_loader.build_index()
        logger.info(f"Indexed {skill_count} skills")

        # Cache available skills for quick lookup
        self._available_skills = {skill.name: skill for skill in self._skill_loader.list_skills()}
        logger.info(f"Available skills: {list(self._available_skills.keys())}")

    def get_identity(self) -> AgentIdentity:
        """Return agent identity information."""
        return AgentIdentity(
            id=self._agent_id,
            name="Skill Orchestrator",
            description=(
                "Intelligent agent that discovers, selects, and executes skills dynamically "
                "based on user requests. Capable of multi-skill orchestration for complex tasks."
            ),
            version="1.0.0",
        )

    def get_capabilities(self) -> AgentCapabilities:
        """Return agent capabilities."""
        return AgentCapabilities(
            streaming=True,
            push_notifications=False,
            multi_turn=True,
            hitl_support=False,
        )

    def get_skills(self) -> list[AgentSkill]:
        """Return agent skills (dynamically discovered)."""
        # Return a meta-skill that represents skill orchestration
        return [
            AgentSkill(
                name="skill-orchestration",
                description=(
                    "Dynamically discover, select, and execute skills based on user requests. "
                    f"Currently has access to: {', '.join(self._available_skills.keys())}"
                ),
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT, SkillOutputMode.FILE],
            )
        ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task with dynamic skill orchestration.

        Args:
            task: The task to process

        Yields:
            TaskEvent objects for status, messages, and completion
        """
        # Emit working status
        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )

        try:
            # Extract user message
            user_message = extract_user_message(task)
            logger.info(f"Processing request: {user_message}")

            # Step 1: Analyze request and select skills
            yield self._create_message_event(
                task.id, "🔍 Analyzing your request to determine required skills..."
            )

            selected_skills = await self._select_skills(user_message)

            if not selected_skills:
                yield self._create_message_event(
                    task.id,
                    "❌ I couldn't determine which skills are needed for this task. "
                    f"Available skills: {', '.join(self._available_skills.keys())}",
                )
                yield TaskDoneEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )
                return

            # Show selected skills
            skill_names = ", ".join(selected_skills)
            yield self._create_message_event(
                task.id, f"✅ Selected skill(s): **{skill_names}**\n"
            )

            # Step 2: Execute skills
            results = []
            successes = []
            for skill_name in selected_skills:
                yield self._create_message_event(
                    task.id, f"\n{'='*60}\n🔧 Executing skill: **{skill_name}**\n{'='*60}\n"
                )

                skill_result, success = await self._execute_skill(skill_name, user_message, task.id)

                if skill_result:
                    results.append(skill_result)
                    successes.append(success)
                    yield self._create_message_event(task.id, skill_result)
                else:
                    successes.append(False)
                    yield self._create_message_event(
                        task.id, f"⚠️ Skill '{skill_name}' execution failed\n"
                    )

            # Step 3: Determine final state and summarize results
            # Task succeeds if at least one skill succeeded
            any_success = any(successes)
            all_failed = not any_success

            if all_failed:
                final_state = TaskState.FAILED
                yield self._create_message_event(
                    task.id, f"\n{'='*60}\n❌ All skills failed to execute\n{'='*60}\n"
                )
            elif any_success:
                final_state = TaskState.COMPLETED
                success_count = sum(successes)
                total_count = len(successes)
                if success_count == total_count:
                    yield self._create_message_event(
                        task.id, f"\n{'='*60}\n✅ Task completed successfully!\n{'='*60}\n"
                    )
                else:
                    yield self._create_message_event(
                        task.id,
                        f"\n{'='*60}\n⚠️ Task partially completed ({success_count}/{total_count} skills succeeded)\n{'='*60}\n"
                    )
            else:
                final_state = TaskState.FAILED
                yield self._create_message_event(task.id, "\n⚠️ No results generated\n")

            # Emit done event with correct final state
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=final_state,
            )

        except Exception as e:
            logger.exception(f"Error processing task: {e}")
            yield self._create_message_event(task.id, f"\n❌ Error: {str(e)}\n")
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    async def _select_skills(self, user_message: str) -> list[str]:
        """Analyze user message and select appropriate skills.

        Args:
            user_message: The user's request

        Returns:
            List of skill names to execute
        """
        # Build skill descriptions for LLM
        skill_descriptions = []
        for name, skill_entry in self._available_skills.items():
            skill_descriptions.append(f"- **{name}**: {skill_entry.description}")

        skills_text = "\n".join(skill_descriptions)

        # Create prompt for LLM to select skills
        selection_prompt = f"""You are a skill selection system. Analyze the user's request and select the skill that best matches their intent.

AVAILABLE SKILLS:
{skills_text}

USER REQUEST:
{user_message}

Select the skill whose description best matches what the user wants to accomplish.
Respond with ONLY the skill name(s), one per line.
If no skills match, respond with "NONE".

YOUR RESPONSE:"""

        try:
            # Use LLM with low temperature for deterministic skill selection
            selection_llm = LLMResponseGenerator(temperature=0.1, max_tokens=500)

            # Use LLM to select skills (collect streaming response)
            response_parts = []
            async for chunk in selection_llm.generate_stream(selection_prompt):
                response_parts.append(chunk)
            response = "".join(response_parts)

            logger.info(f"LLM skill selection response: {response}")

            # Parse response
            lines = [line.strip() for line in response.strip().split("\n") if line.strip()]

            if not lines or lines[0].upper() == "NONE":
                return []

            # Validate skill names
            valid_skills = []
            for skill_name in lines:
                # Clean up any markdown or extra text
                skill_name = skill_name.strip("*`- ")
                if skill_name in self._available_skills:
                    valid_skills.append(skill_name)

            return valid_skills

        except Exception as e:
            logger.error(f"Error selecting skills: {e}")
            # Fallback to keyword matching
            return self._fallback_skill_selection(user_message)

    def _fallback_skill_selection(self, user_message: str) -> list[str]:
        """Fallback skill selection using keyword matching.

        Args:
            user_message: The user's request

        Returns:
            List of skill names to execute
        """
        message_lower = user_message.lower()
        selected = []

        # Check for data processing keywords
        if any(kw in message_lower for kw in ["analyze", "process", "filter", "calculate", "data"]):
            if "data-processor" in self._available_skills:
                selected.append("data-processor")

        # Check for report generation keywords
        if any(kw in message_lower for kw in ["report", "summary", "document", "generate", "write"]):
            if "report-generator" in self._available_skills:
                selected.append("report-generator")

        return selected

    async def _execute_skill(self, skill_name: str, user_message: str, task_id: str) -> tuple[Optional[str], bool]:
        """Execute a specific skill with actual tool execution.

        Args:
            skill_name: Name of the skill to execute
            user_message: The user's original request
            task_id: Task identifier

        Returns:
            Tuple of (skill execution result message, success status)
        """
        try:
            # Load full skill
            skill = self._skill_loader.load_skill(skill_name)
            if not skill:
                return (f"❌ Failed to load skill '{skill_name}'", False)

            # Show skill info
            result_parts = []
            result_parts.append(f"📋 **Skill**: {skill.metadata.name}")
            result_parts.append(f"📝 **Description**: {skill.metadata.description}")
            if skill.metadata.allowed_tools:
                result_parts.append(f"🔧 **Allowed Tools**: {', '.join(skill.metadata.allowed_tools)}")
            result_parts.append("")

            # Execute skill using SkillOrchestrator
            logger.info(f"Executing skill '{skill_name}' with tool access")
            result_parts.append("📤 **Execution**:")

            # Collect events from skill execution
            events = []
            async for event in self._skill_orchestrator.execute(
                skill_name=skill_name,
                user_request=user_message,
                task_id=task_id,
                tenant_id=self._tenant_id,
            ):
                events.append(event)

                # Stream message events
                if event.type == "message":
                    for part in event.message_parts:
                        if hasattr(part, "text"):
                            result_parts.append(part.text)

            # Check final status
            final_event = events[-1] if events else None
            success = False
            if final_event and final_event.type == "done":
                success = final_event.final_state == TaskState.COMPLETED
                status_emoji = "✅" if success else "❌"
                result_parts.append("")
                result_parts.append(f"Status: {status_emoji} {final_event.final_state.value}")

            result_parts.append("")
            return ("\n".join(result_parts), success)

        except Exception as e:
            logger.exception(f"Error executing skill '{skill_name}': {e}")
            return (f"❌ Error executing skill '{skill_name}': {str(e)}", False)

    def _create_message_event(self, task_id: str, content: str) -> TaskMessageEvent:
        """Create a task message event.

        Args:
            task_id: Task identifier
            content: Message content

        Returns:
            TaskMessageEvent
        """
        from omniforge.agents.models import TextPart

        return TaskMessageEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text=content)],
            is_partial=False,
        )


# Factory function for easy instantiation
def create_skill_orchestrator_agent(
    agent_id: str = "skill-orchestrator",
    skills_path: Optional[Path] = None,
    tenant_id: Optional[str] = None,
) -> SkillOrchestratorAgent:
    """Create a SkillOrchestratorAgent instance.

    Args:
        agent_id: Unique identifier for this agent instance
        skills_path: Optional custom path to skills directory
        tenant_id: Optional tenant identifier for multi-tenancy

    Returns:
        SkillOrchestratorAgent instance
    """
    return SkillOrchestratorAgent(
        agent_id=agent_id,
        skills_path=skills_path,
        tenant_id=tenant_id,
    )
