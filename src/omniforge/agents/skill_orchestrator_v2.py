"""
Skill Orchestrator V2 - Agent that orchestrates self-executing skills

This version uses AutonomousSkillExecutor where each skill:
1. Knows how to execute itself
2. Figures out which tools to use
3. Executes those tools
4. Returns results

The agent just:
1. Selects which skill to use (via LLM)
2. Loads the skill
3. Executes via SkillOrchestrator
4. Returns results

This is cleaner architecture - skills are self-contained modules.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import (
    TaskDoneEvent,
    TaskEvent,
    TaskMessageEvent,
    TaskStatusEvent,
)
from omniforge.agents.helpers import extract_user_message
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.skills.orchestrator import SkillOrchestrator
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.tasks.models import Task, TaskState
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.executor import ToolExecutor

logger = logging.getLogger(__name__)


class SkillOrchestratorV2(BaseAgent):
    """Agent that orchestrates self-executing skills.

    This agent:
    1. Uses LLM to select which skills are needed
    2. Loads each skill
    3. Lets the skill execute itself (skill.execute())
    4. Returns results

    The skills handle their own tool selection and execution.
    """

    def __init__(
        self,
        agent_id: str = "skill-orchestrator-v2",
        skills_path: Optional[Path] = None,
        tenant_id: Optional[str] = None,
        llm_generator: Optional[LLMResponseGenerator] = None,
    ):
        """Initialize the orchestrator."""
        self._agent_id = agent_id
        self._tenant_id = tenant_id
        self._llm_generator = llm_generator or LLMResponseGenerator(
            temperature=0.7, max_tokens=2000
        )

        # Setup skill loader
        if skills_path:
            storage_config = StorageConfig(plugin_paths=[skills_path])
        else:
            storage_config = StorageConfig.from_environment()

        self._skill_loader = SkillLoader(config=storage_config)
        skill_count = self._skill_loader.build_index()
        logger.info(f"Indexed {skill_count} skills")

        # Cache available skills
        self._available_skills = {
            skill.name: skill for skill in self._skill_loader.list_skills()
        }
        logger.info(f"Available skills: {list(self._available_skills.keys())}")

        # Setup tool registry
        self._tool_registry = ToolRegistry()
        self._register_tools()

        # Initialize tool executor and skill orchestrator
        self._tool_executor = ToolExecutor(registry=self._tool_registry)
        self._skill_orchestrator = SkillOrchestrator(
            skill_loader=self._skill_loader,
            tool_registry=self._tool_registry,
            tool_executor=self._tool_executor,
        )

    def _register_tools(self):
        """Register available tools."""
        from omniforge.tools.builtin.bash import BashTool
        from omniforge.tools.builtin.glob import GlobTool
        from omniforge.tools.builtin.grep import GrepTool
        from omniforge.tools.builtin.read import ReadTool
        from omniforge.tools.builtin.write import WriteTool
        from omniforge.tools.builtin.llm import LLMTool

        self._tool_registry.register(ReadTool())
        self._tool_registry.register(WriteTool())
        self._tool_registry.register(GlobTool())
        self._tool_registry.register(GrepTool())
        self._tool_registry.register(BashTool())
        self._tool_registry.register(LLMTool())

        logger.info(f"Registered tools: {list(self._tool_registry.list_tools())}")

    def get_identity(self) -> AgentIdentity:
        """Return agent identity."""
        return AgentIdentity(
            id=self._agent_id,
            name="Skill Orchestrator V2",
            description=(
                "Agent that orchestrates self-executing skills. "
                "Each skill knows how to execute itself with tools."
            ),
            version="2.0.0",
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
        """Return agent skills."""
        return [
            AgentSkill(
                name="skill-orchestration-v2",
                description=(
                    f"Orchestrates self-executing skills. "
                    f"Available: {', '.join(self._available_skills.keys())}"
                ),
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT, SkillOutputMode.FILE],
            )
        ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task by orchestrating skills."""
        yield TaskStatusEvent(
            task_id=task.id, timestamp=datetime.utcnow(), state=TaskState.WORKING
        )

        try:
            user_message = extract_user_message(task)
            logger.info(f"Processing: {user_message}")

            # Step 1: LLM selects which skills to use
            yield self._message(task.id, "🧠 Analyzing request and selecting skills...\n")

            selected_skills = await self._select_skills(user_message)

            if not selected_skills:
                yield self._message(
                    task.id,
                    f"❌ Could not determine skills.\n"
                    f"Available: {', '.join(self._available_skills.keys())}\n",
                )
                yield self._done(task.id, TaskState.COMPLETED)
                return

            yield self._message(
                task.id, f"✅ Selected: **{', '.join(selected_skills)}**\n\n"
            )

            # Step 2: Execute each skill (skill executes itself!)
            for skill_name in selected_skills:
                yield self._message(
                    task.id,
                    f"{'='*70}\n"
                    f"🔧 **Skill: {skill_name}**\n"
                    f"{'='*70}\n\n",
                )

                # Load skill metadata for display
                skill = self._skill_loader.load_skill(skill_name)
                if not skill:
                    yield self._message(task.id, f"❌ Failed to load skill\n\n")
                    continue

                # Display skill info
                yield self._message(
                    task.id,
                    f"📋 Description: {skill.metadata.description}\n"
                    f"🔧 Allowed tools: {', '.join(skill.metadata.allowed_tools or ['all'])}\n\n"
                    f"▶️  Skill executing...\n\n",
                )

                # Execute skill via orchestrator (forwards events)
                async for event in self._skill_orchestrator.execute(
                    skill_name=skill_name,
                    user_request=user_message,
                    task_id=task.id,
                    tenant_id=self._tenant_id,
                ):
                    # Forward all events
                    yield event
                    if result["errors"]:
                        yield self._message(task.id, f"**Errors:**\n")
                        for error in result["errors"]:
                            yield self._message(task.id, f"  • {error}\n")
                        yield self._message(task.id, "\n")

            yield self._message(
                task.id, f"{'='*70}\n✅ All skills completed!\n{'='*70}\n"
            )
            yield self._done(task.id, TaskState.COMPLETED)

        except Exception as e:
            logger.exception(f"Error: {e}")
            yield self._message(task.id, f"\n❌ Error: {e}\n")
            yield self._done(task.id, TaskState.FAILED)

    async def _select_skills(self, user_message: str) -> list[str]:
        """Use LLM to select skills."""
        skill_descriptions = []
        for name, skill_entry in self._available_skills.items():
            skill_descriptions.append(f"- **{name}**: {skill_entry.description}")

        skills_text = "\n".join(skill_descriptions)

        prompt = f"""Select which skill(s) to use for this request.

AVAILABLE SKILLS:
{skills_text}

USER REQUEST:
{user_message}

INSTRUCTIONS:
- Analyze what the user needs
- Select appropriate skill(s)
- If reading/analyzing data → use: data-processor
- If creating reports/documents → use: report-generator
- If both → use both skills
- Output ONLY skill names, one per line

SKILL NAMES:"""

        try:
            response_parts = []
            async for chunk in self._llm_generator.generate_stream(prompt):
                response_parts.append(chunk)
            response = "".join(response_parts).strip()

            logger.info(f"LLM selected: {response}")

            # Parse and validate
            parts = response.replace(",", " ").split()
            valid_skills = []
            for part in parts:
                skill_name = part.strip("*`-,. \n\t")
                if skill_name in self._available_skills:
                    if skill_name not in valid_skills:
                        valid_skills.append(skill_name)

            return valid_skills

        except Exception as e:
            logger.error(f"Error selecting skills: {e}")
            return []

    def _message(self, task_id: str, content: str) -> TaskMessageEvent:
        """Create message event."""
        return TaskMessageEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text=content)],
            is_partial=False,
        )

    def _done(self, task_id: str, state: TaskState) -> TaskDoneEvent:
        """Create done event."""
        return TaskDoneEvent(task_id=task_id, timestamp=datetime.utcnow(), final_state=state)


def create_skill_orchestrator_v2(
    agent_id: str = "skill-orchestrator-v2",
    skills_path: Optional[Path] = None,
    tenant_id: Optional[str] = None,
) -> SkillOrchestratorV2:
    """Factory function."""
    return SkillOrchestratorV2(agent_id=agent_id, skills_path=skills_path, tenant_id=tenant_id)
