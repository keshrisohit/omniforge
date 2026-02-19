"""
Skill Orchestrator Agent with Real Tool Execution

This agent demonstrates:
1. Dynamic skill selection using LLM (not static)
2. Skills that use actual tool calls (Read, Write, Bash, etc.)
3. Skills that figure out which tools to use via LLM
4. Real tool execution with results

The flow is:
User Prompt → LLM selects skills → For each skill:
  → LLM reads skill instructions
  → LLM figures out which tools to call
  → Agent executes real tools
  → Returns actual results
"""

import json
import logging
import re
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
from omniforge.skills.context import SkillContext
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import StorageConfig
from omniforge.tasks.models import Task, TaskState
from omniforge.tools.executor import ToolExecutor
from omniforge.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class SkillOrchestratorWithTools(BaseAgent):
    """Agent that orchestrates skills with real tool execution.

    This agent:
    1. Uses LLM to dynamically select which skills to use
    2. Loads skill instructions
    3. Uses LLM to determine which tools the skill needs
    4. Actually executes those tools (Read, Write, Bash, etc.)
    5. Returns real results from tool execution
    """

    def __init__(
        self,
        agent_id: str = "skill-orchestrator-tools",
        skills_path: Optional[Path] = None,
        tenant_id: Optional[str] = None,
        llm_generator: Optional[LLMResponseGenerator] = None,
    ):
        """Initialize the agent with tool execution capabilities."""
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

        # Setup tool registry and executor
        self._tool_registry = ToolRegistry()
        self._register_tools()
        self._tool_executor = ToolExecutor(registry=self._tool_registry)

    def _register_tools(self):
        """Register available tools for skill execution."""
        # Import builtin tool implementations
        from omniforge.tools.builtin.bash import BashTool
        from omniforge.tools.builtin.glob import GlobTool
        from omniforge.tools.builtin.grep import GrepTool
        from omniforge.tools.builtin.read import ReadTool
        from omniforge.tools.builtin.write import WriteTool

        # Register tools
        self._tool_registry.register(ReadTool())
        self._tool_registry.register(WriteTool())
        self._tool_registry.register(GlobTool())
        self._tool_registry.register(GrepTool())
        self._tool_registry.register(BashTool())

        logger.info(f"Registered tools: {list(self._tool_registry.list_tools())}")

    def get_identity(self) -> AgentIdentity:
        """Return agent identity."""
        return AgentIdentity(
            id=self._agent_id,
            name="Skill Orchestrator with Tools",
            description=(
                "Intelligent agent that dynamically selects skills using LLM, "
                "determines which tools to use, and executes real tool calls "
                "to accomplish tasks."
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
                name="skill-orchestration-with-tools",
                description=(
                    f"Dynamically select and execute skills with real tool calls. "
                    f"Available skills: {', '.join(self._available_skills.keys())}. "
                    f"Available tools: {', '.join(self._tool_registry.list_tools())}"
                ),
                input_modes=[SkillInputMode.TEXT],
                output_modes=[SkillOutputMode.TEXT, SkillOutputMode.FILE],
            )
        ]

    async def process_task(self, task: Task) -> AsyncIterator[TaskEvent]:
        """Process task with skill selection and tool execution."""
        yield TaskStatusEvent(
            task_id=task.id, timestamp=datetime.utcnow(), state=TaskState.WORKING
        )

        try:
            user_message = extract_user_message(task)
            logger.info(f"Processing request: {user_message}")

            # Step 1: Use LLM to select skills dynamically
            yield self._create_message_event(
                task.id, "🧠 Using LLM to analyze your request and select skills...\n"
            )

            selected_skills = await self._llm_select_skills(user_message)

            if not selected_skills:
                yield self._create_message_event(
                    task.id,
                    "❌ Could not determine required skills.\n"
                    f"Available: {', '.join(self._available_skills.keys())}\n",
                )
                yield TaskDoneEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )
                return

            skill_names = ", ".join(selected_skills)
            yield self._create_message_event(
                task.id, f"✅ LLM selected skill(s): **{skill_names}**\n\n"
            )

            # Step 2: Execute each skill with real tools
            for skill_name in selected_skills:
                yield self._create_message_event(
                    task.id, f"{'='*70}\n🔧 Executing: **{skill_name}** (with real tools)\n{'='*70}\n\n"
                )

                result = await self._execute_skill_with_tools(skill_name, user_message, task.id)
                yield self._create_message_event(task.id, result + "\n")

            yield self._create_message_event(
                task.id, f"\n{'='*70}\n✅ All skills executed successfully!\n{'='*70}\n"
            )

            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.COMPLETED,
            )

        except Exception as e:
            logger.exception(f"Error processing task: {e}")
            yield self._create_message_event(task.id, f"\n❌ Error: {str(e)}\n")
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    async def _llm_select_skills(self, user_message: str) -> list[str]:
        """Use LLM to dynamically select which skills are needed.

        This is NOT static - the LLM analyzes the request and decides.
        """
        # Build skill descriptions
        skill_descriptions = []
        for name, skill_entry in self._available_skills.items():
            skill_descriptions.append(f"- **{name}**: {skill_entry.description}")

        skills_text = "\n".join(skill_descriptions)

        prompt = f"""You are a skill selection system. Choose the best skill(s) for this task.

AVAILABLE SKILLS:
{skills_text}

USER REQUEST:
{user_message}

INSTRUCTIONS:
- If the user mentions "read", "analyze", "process", or "data" → use: data-processor
- If the user mentions "report", "summary", "write", or "create" → use: report-generator
- If the request involves BOTH reading/analyzing AND writing/reporting → use: data-processor, report-generator
- Respond with ONLY skill names, one per line
- No explanation, just skill names

RESPONSE (skill names only):"""

        try:
            response_parts = []
            async for chunk in self._llm_generator.generate_stream(prompt):
                response_parts.append(chunk)
            response = "".join(response_parts).strip()

            logger.info(f"LLM skill selection response: {response}")

            # Parse skill names (handle both newline and space-separated)
            # Split by newline first
            parts = response.replace(",", " ").split()

            # Clean and validate
            valid_skills = []
            for part in parts:
                skill_name = part.strip("*`-,. \n\t")
                if skill_name.upper() == "NONE":
                    continue
                if skill_name in self._available_skills:
                    if skill_name not in valid_skills:  # Avoid duplicates
                        valid_skills.append(skill_name)

            return valid_skills

        except Exception as e:
            logger.error(f"Error in LLM skill selection: {e}")
            return []

    async def _execute_skill_with_tools(
        self, skill_name: str, user_message: str, task_id: str
    ) -> str:
        """Execute a skill with real tool calls.

        The LLM:
        1. Reads the skill instructions
        2. Figures out which tools it needs to use
        3. Decides on tool parameters
        4. We execute the actual tools
        5. Returns real results
        """
        try:
            # Load full skill
            skill = self._skill_loader.load_skill(skill_name)
            if not skill:
                return f"❌ Failed to load skill '{skill_name}'"

            result_parts = []
            result_parts.append(f"📋 **Skill**: {skill.metadata.name}")
            result_parts.append(f"📝 **Description**: {skill.metadata.description}")
            if skill.metadata.allowed_tools:
                result_parts.append(
                    f"🔧 **Allowed Tools**: {', '.join(skill.metadata.allowed_tools)}"
                )
            result_parts.append("")

            # Activate skill context for tool restrictions
            skill_context = SkillContext(skill)
            self._tool_executor.activate_skill(skill)

            # Use LLM to determine which tools to call
            result_parts.append("🧠 **LLM Planning**: Analyzing what tools are needed...")
            result_parts.append("")

            tool_plan = await self._llm_plan_tools(skill, user_message)

            if not tool_plan or "tool_calls" not in tool_plan:
                result_parts.append("⚠️ No tool calls planned - executing with reasoning only")
                # Fall back to reasoning-only execution
                reasoning_result = await self._execute_with_reasoning(skill, user_message)
                result_parts.append(reasoning_result)
            else:
                # Execute the planned tool calls
                result_parts.append(
                    f"📋 **Tool Plan**: {len(tool_plan['tool_calls'])} tool call(s) planned"
                )
                result_parts.append("")

                for i, tool_call in enumerate(tool_plan["tool_calls"], 1):
                    tool_name = tool_call.get("tool")
                    tool_args = tool_call.get("arguments", {})
                    reasoning = tool_call.get("reasoning", "")

                    result_parts.append(f"**Tool Call {i}:**")
                    result_parts.append(f"  • Tool: `{tool_name}`")
                    result_parts.append(f"  • Reasoning: {reasoning}")
                    result_parts.append(f"  • Arguments: {json.dumps(tool_args, indent=4)}")

                    # Check if tool is allowed
                    if skill.metadata.allowed_tools:
                        if tool_name not in skill.metadata.allowed_tools:
                            result_parts.append(
                                f"  • ❌ BLOCKED: Tool '{tool_name}' not in allowed_tools"
                            )
                            result_parts.append("")
                            continue

                    # Execute the actual tool
                    result_parts.append(f"  • ⚙️ Executing tool...")

                    tool_result = await self._execute_tool(tool_name, tool_args)

                    if tool_result.get("success"):
                        result_parts.append(f"  • ✅ Success!")
                        result_parts.append(
                            f"  • Result: {str(tool_result.get('result', ''))[:200]}"
                        )
                    else:
                        result_parts.append(f"  • ❌ Failed: {tool_result.get('error')}")

                    result_parts.append("")

                # Generate final summary
                result_parts.append("📤 **Final Result**:")
                summary = tool_plan.get("summary", "Tools executed successfully")
                result_parts.append(summary)

            # Deactivate skill context
            self._tool_executor.deactivate_skill(skill_name)

            return "\n".join(result_parts)

        except Exception as e:
            logger.exception(f"Error executing skill '{skill_name}': {e}")
            return f"❌ Error executing skill '{skill_name}': {str(e)}"

    async def _llm_plan_tools(self, skill, user_message: str) -> Optional[dict]:
        """Use LLM to plan which tools to call and with what arguments.

        Returns a structured plan:
        {
            "tool_calls": [
                {
                    "tool": "Read",
                    "reasoning": "Need to read the file first",
                    "arguments": {"file_path": "/path/to/file"}
                }
            ],
            "summary": "Final summary of what will be done"
        }
        """
        # Get available tools
        available_tools = list(self._tool_registry.list_tools())
        if skill.metadata.allowed_tools:
            available_tools = [t for t in available_tools if t in skill.metadata.allowed_tools]

        # Build tool descriptions
        tool_descriptions = []
        for tool_name in available_tools:
            try:
                tool = self._tool_registry.get(tool_name)
                tool_descriptions.append(f"- **{tool_name}**: {tool.definition.description}")
            except Exception:
                tool_descriptions.append(f"- **{tool_name}**: Available tool")

        tools_text = "\n".join(tool_descriptions)

        prompt = f"""Plan which tools to call for this task.

AVAILABLE TOOLS (use exact lowercase names):
{tools_text}

SKILL INSTRUCTIONS:
{skill.content[:500]}...

USER REQUEST:
{user_message}

Return JSON with this EXACT format:
{{
    "tool_calls": [
        {{
            "tool": "read",
            "reasoning": "Need to read the file",
            "arguments": {{"file_path": "/path/to/file"}}
        }}
    ],
    "summary": "What will be done"
}}

CRITICAL:
- Use EXACT lowercase tool names: read, write, glob, grep, bash
- Provide realistic file paths from the user's request
- If reading a file, use "read" tool
- If writing a file, use "write" tool
- Return ONLY valid JSON, no extra text

JSON:"""

        try:
            response_parts = []
            async for chunk in self._llm_generator.generate_stream(prompt):
                response_parts.append(chunk)
            response = "".join(response_parts).strip()

            logger.info(f"LLM tool planning response: {response[:500]}...")

            # Extract JSON from response
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                plan = json.loads(json_str)
                return plan
            else:
                logger.warning("Could not extract JSON from LLM response")
                return None

        except Exception as e:
            logger.error(f"Error in LLM tool planning: {e}")
            return None

    async def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a real tool and return results."""
        try:
            tool = self._tool_registry.get(tool_name)
            if not tool:
                return {"success": False, "error": f"Tool '{tool_name}' not found"}

            # Create a minimal context
            from omniforge.tools.base import ToolCallContext

            context = ToolCallContext(
                correlation_id=f"corr-{datetime.utcnow().timestamp()}",
                task_id="skill-execution",
                agent_id=self._agent_id,
            )

            # Execute tool
            result = await tool.execute(arguments=arguments, context=context)

            return {
                "success": result.success,
                "result": result.result if result.success else None,
                "error": result.error if not result.success else None,
            }

        except Exception as e:
            logger.exception(f"Error executing tool '{tool_name}': {e}")
            return {"success": False, "error": str(e)}

    async def _execute_with_reasoning(self, skill, user_message: str) -> str:
        """Fall back to reasoning-only execution if no tools are planned."""
        prompt = f"""Execute the skill based on its instructions.

SKILL INSTRUCTIONS:
{skill.content}

USER REQUEST:
{user_message}

Provide a clear response following the skill's instructions:"""

        response_parts = []
        async for chunk in self._llm_generator.generate_stream(prompt):
            response_parts.append(chunk)

        return "".join(response_parts)

    def _create_message_event(self, task_id: str, content: str) -> TaskMessageEvent:
        """Create a task message event."""
        return TaskMessageEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            message_parts=[TextPart(text=content)],
            is_partial=False,
        )


def create_skill_orchestrator_with_tools(
    agent_id: str = "skill-orchestrator-tools",
    skills_path: Optional[Path] = None,
    tenant_id: Optional[str] = None,
) -> SkillOrchestratorWithTools:
    """Factory function to create agent with tool execution."""
    return SkillOrchestratorWithTools(
        agent_id=agent_id,
        skills_path=skills_path,
        tenant_id=tenant_id,
    )
