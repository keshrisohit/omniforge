"""Conversation state machine for agent creation with multi-skill support.

Manages the multi-turn conversation flow for creating agents through natural language,
including multi-skill detection and public skill suggestions.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from omniforge.builder.conversation import prompts
from omniforge.builder.conversation.skill_suggestion import SkillSuggestionManager
from omniforge.builder.generation.agent_generator import (
    AgentGenerator,
    SkillNeedsAnalysis,
)
from omniforge.builder.models import AgentConfig, SkillReference, TriggerType
from omniforge.builder.skill_generator import SkillGenerationRequest


class ConversationState(str, Enum):
    """States in agent creation conversation flow."""

    INITIAL = "initial"
    UNDERSTANDING_GOAL = "understanding_goal"
    INTEGRATION_SETUP = "integration_setup"
    REQUIREMENTS_GATHERING = "requirements_gathering"
    SKILL_SUGGESTION = "skill_suggestion"
    SKILL_SELECTION = "skill_selection"
    SKILL_DESIGN = "skill_design"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    COMPLETE = "complete"


class ConversationContext(BaseModel):
    """Context maintained throughout conversation.

    Attributes:
        conversation_id: Unique conversation identifier
        tenant_id: Tenant this conversation belongs to
        user_id: User creating the agent
        state: Current conversation state
        agent_goal: What the agent should accomplish
        integration_type: Integration being used (notion, slack, etc.)
        integration_id: ID of connected integration
        requirements: Gathered requirements as key-value pairs
        skill_needs_analysis: Multi-skill detection results
        suggested_public_skills: Suggested public skills by order
        selected_public_skill_ids: User-selected public skill IDs
        skill_requests: Skills to be created
        agent_config: Partially built agent configuration
        messages: Conversation message history
    """

    conversation_id: str
    tenant_id: str
    user_id: str
    state: ConversationState = Field(default=ConversationState.INITIAL)
    agent_goal: Optional[str] = None
    integration_type: Optional[str] = None
    integration_id: Optional[str] = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    skill_needs_analysis: Optional[SkillNeedsAnalysis] = None
    suggested_public_skills: dict[int, list[dict[str, str]]] = Field(default_factory=dict)
    selected_public_skill_ids: list[str] = Field(default_factory=list)
    skill_requests: list[SkillGenerationRequest] = Field(default_factory=list)
    agent_config: Optional[AgentConfig] = None
    messages: list[dict[str, str]] = Field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history.

        Args:
            role: Message role (user/assistant)
            content: Message content
        """
        self.messages.append({"role": role, "content": content})

    def update_requirements(self, **kwargs: Any) -> None:
        """Update requirements from conversation.

        Args:
            **kwargs: Requirements as key-value pairs
        """
        self.requirements.update(kwargs)


class ConversationManager:
    """Manages conversation flow for agent creation with multi-skill support."""

    def __init__(
        self,
        agent_generator: Optional[AgentGenerator] = None,
        skill_suggestion_manager: Optional[SkillSuggestionManager] = None,
    ) -> None:
        """Initialize conversation manager.

        Args:
            agent_generator: AgentGenerator for multi-skill detection
            skill_suggestion_manager: SkillSuggestionManager for public skill suggestions
        """
        self.contexts: dict[str, ConversationContext] = {}
        self._agent_generator = agent_generator or AgentGenerator()
        self._skill_suggestions = skill_suggestion_manager

    def start_conversation(
        self, conversation_id: str, tenant_id: str, user_id: str
    ) -> ConversationContext:
        """Start a new agent creation conversation.

        Args:
            conversation_id: Unique conversation ID
            tenant_id: Tenant ID
            user_id: User ID

        Returns:
            Initial conversation context
        """
        context = ConversationContext(
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            user_id=user_id,
            state=ConversationState.INITIAL,
        )

        self.contexts[conversation_id] = context
        return context

    def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """Get conversation context by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation context if found, None otherwise
        """
        return self.contexts.get(conversation_id)

    async def process_user_input(
        self, conversation_id: str, user_input: str
    ) -> tuple[ConversationContext, str]:
        """Process user input and generate response.

        Args:
            conversation_id: Conversation ID
            user_input: User's message

        Returns:
            Tuple of (updated context, assistant response)

        Raises:
            ValueError: If conversation not found
        """
        context = self.contexts.get(conversation_id)
        if not context:
            raise ValueError(f"Conversation {conversation_id} not found")

        # Add user message to history
        context.add_message("user", user_input)

        # Process based on current state
        if context.state == ConversationState.INITIAL:
            response = await self._handle_initial(context, user_input)
        elif context.state == ConversationState.UNDERSTANDING_GOAL:
            response = self._handle_understanding_goal(context, user_input)
        elif context.state == ConversationState.INTEGRATION_SETUP:
            response = self._handle_integration_setup(context, user_input)
        elif context.state == ConversationState.REQUIREMENTS_GATHERING:
            response = await self._handle_requirements_gathering(context, user_input)
        elif context.state == ConversationState.SKILL_SUGGESTION:
            response = await self._handle_skill_suggestion(context, user_input)
        elif context.state == ConversationState.SKILL_SELECTION:
            response = await self._handle_skill_selection(context, user_input)
        elif context.state == ConversationState.SKILL_DESIGN:
            response = self._handle_skill_design(context, user_input)
        elif context.state == ConversationState.TESTING:
            response = self._handle_testing(context, user_input)
        elif context.state == ConversationState.DEPLOYMENT:
            response = self._handle_deployment(context, user_input)
        else:
            response = "I'm not sure how to help with that. Can you rephrase?"

        # Add assistant response to history
        context.add_message("assistant", response)

        return context, response

    async def _handle_initial(self, context: ConversationContext, user_input: str) -> str:
        """Handle initial state - understand what user wants.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        # Extract goal from user input
        context.agent_goal = user_input
        context.state = ConversationState.UNDERSTANDING_GOAL

        return prompts.understanding_goal_prompt(user_input)

    def _handle_understanding_goal(self, context: ConversationContext, user_input: str) -> str:
        """Handle understanding goal - identify integration needed.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        # Extract integration type
        integration = user_input.lower().strip()
        context.integration_type = integration
        context.state = ConversationState.INTEGRATION_SETUP

        return prompts.integration_setup_prompt(integration)

    def _handle_integration_setup(self, context: ConversationContext, user_input: str) -> str:
        """Handle integration setup - guide OAuth flow.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        if "yes" in user_input.lower() or "ready" in user_input.lower():
            context.state = ConversationState.REQUIREMENTS_GATHERING
            return prompts.integration_connected_prompt(context.integration_type or "integration")
        else:
            return prompts.wait_for_connection_prompt()

    async def _handle_requirements_gathering(
        self, context: ConversationContext, user_input: str
    ) -> str:
        """Handle requirements gathering - collect details and analyze skills.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        # Store user description
        context.update_requirements(user_description=user_input)

        # Extract trigger info
        if "monday" in user_input.lower() or "weekly" in user_input.lower():
            context.requirements["trigger"] = "scheduled"
            context.requirements["schedule"] = "0 8 * * MON"
        else:
            context.requirements["trigger"] = "on_demand"

        # Analyze skill needs using AgentGenerator
        analysis = self._agent_generator.determine_skills_needed(user_input)
        context.skill_needs_analysis = analysis

        # If multi-skill and skill suggestion manager available, suggest public skills
        if analysis.is_multi_skill and self._skill_suggestions:
            # Get suggestions for each skill need
            suggestions = await self._skill_suggestions.suggest_skills_for_all_needs(
                skill_needs=analysis.skills_needed,
                limit_per_need=2,
            )

            # Format for display
            for order, recommendations in suggestions.items():
                context.suggested_public_skills[order] = (
                    self._skill_suggestions.format_recommendations_for_display(recommendations)
                )

            # Build all suggested skills for display
            all_suggestions = []
            for order in sorted(context.suggested_public_skills.keys()):
                all_suggestions.extend(context.suggested_public_skills[order])

            context.state = ConversationState.SKILL_SUGGESTION

            return prompts.multi_skill_suggestion_prompt(
                suggested_flow=analysis.suggested_flow,
                public_skills=all_suggestions if all_suggestions else None,
            )

        # Single skill or no suggestion manager - proceed to skill design
        context.state = ConversationState.SKILL_DESIGN

        num_skills = len(analysis.skills_needed)
        return prompts.skill_design_summary_prompt(
            goal=context.agent_goal or "automation",
            integration=context.integration_type or "integration",
            trigger=context.requirements.get("trigger", "on_demand"),
            num_skills=num_skills,
        )

    async def _handle_skill_suggestion(self, context: ConversationContext, user_input: str) -> str:
        """Handle skill suggestion - let user choose public or custom.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        input_lower = user_input.lower()

        # Check if user wants to use suggested skills
        if "use" in input_lower and ("these" in input_lower or "existing" in input_lower):
            # User wants to use public skills - show selection
            all_suggestions = []
            for order in sorted(context.suggested_public_skills.keys()):
                all_suggestions.extend(context.suggested_public_skills[order])

            context.state = ConversationState.SKILL_SELECTION
            return prompts.public_skill_options_prompt(all_suggestions)

        elif "custom" in input_lower or "create" in input_lower:
            # User wants custom skills - proceed to skill design
            context.state = ConversationState.SKILL_DESIGN

            assert context.skill_needs_analysis is not None
            num_skills = len(context.skill_needs_analysis.skills_needed)

            return prompts.skill_design_summary_prompt(
                goal=context.agent_goal or "automation",
                integration=context.integration_type or "integration",
                trigger=context.requirements.get("trigger", "on_demand"),
                num_skills=num_skills,
            )

        elif "yes" in input_lower:
            # Ambiguous - clarify
            return (
                "Would you like to:\n"
                "1. Use the existing skills I suggested\n"
                "2. Create custom skills instead\n\n"
                "Please choose 1 or 2."
            )

        else:
            # Default to proceeding with custom
            context.state = ConversationState.SKILL_DESIGN

            assert context.skill_needs_analysis is not None
            num_skills = len(context.skill_needs_analysis.skills_needed)

            return prompts.skill_design_summary_prompt(
                goal=context.agent_goal or "automation",
                integration=context.integration_type or "integration",
                trigger=context.requirements.get("trigger", "on_demand"),
                num_skills=num_skills,
            )

    async def _handle_skill_selection(self, context: ConversationContext, user_input: str) -> str:
        """Handle skill selection - parse user's choices.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        # Get all available skills
        all_suggestions = []
        for order in sorted(context.suggested_public_skills.keys()):
            all_suggestions.extend(context.suggested_public_skills[order])

        # Parse user selection
        assert self._skill_suggestions is not None
        selected_ids = self._skill_suggestions.match_user_selection(
            user_input=user_input,
            available_skills=all_suggestions,
        )

        context.selected_public_skill_ids = selected_ids

        # Determine remaining custom skills needed
        assert context.skill_needs_analysis is not None
        total_needs = len(context.skill_needs_analysis.skills_needed)
        num_selected = len(selected_ids)

        if num_selected == 0:
            # User selected none - create all custom
            context.state = ConversationState.SKILL_DESIGN
            return prompts.skill_design_summary_prompt(
                goal=context.agent_goal or "automation",
                integration=context.integration_type or "integration",
                trigger=context.requirements.get("trigger", "on_demand"),
                num_skills=total_needs,
            )

        elif num_selected == total_needs:
            # User selected all public skills - no custom needed
            context.state = ConversationState.TESTING
            return prompts.testing_prompt()

        else:
            # Mixed public and custom - confirm
            # Get public skill details
            public_skills = []
            for skill_id in selected_ids:
                skill = await self._skill_suggestions.get_skill_by_id(skill_id)
                if skill:
                    public_skills.append(skill.name)

            # Get remaining custom needs
            custom_needs = [
                need
                for i, need in enumerate(context.skill_needs_analysis.skills_needed)
                if i >= num_selected
            ]
            custom_descriptions = [need.description for need in custom_needs]

            context.state = ConversationState.SKILL_DESIGN

            return prompts.mixed_skills_confirmation_prompt(
                public_skills=public_skills,
                custom_skills=custom_descriptions,
            )

    def _handle_skill_design(self, context: ConversationContext, user_input: str) -> str:
        """Handle skill design - create skill specification.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        if "yes" in user_input.lower():
            # Create skill requests based on analysis
            if context.skill_needs_analysis:
                for need in context.skill_needs_analysis.skills_needed:
                    skill_id = f"{context.integration_type}-{need.action[:20].replace(' ', '-')}"
                    skill_request = SkillGenerationRequest(
                        skill_id=skill_id,
                        name=f"{need.action.capitalize()}",
                        description=need.description[:80],
                        integration_type=need.integration or context.integration_type,
                        purpose=need.description,
                        allowed_tools=["ExternalAPI", "Read", "Write"],
                        steps=[need.description],
                    )
                    context.skill_requests.append(skill_request)
            else:
                # Fallback to single skill
                skill_id = f"{context.integration_type}-automation"
                skill_request = SkillGenerationRequest(
                    skill_id=skill_id,
                    name=f"{context.integration_type.capitalize()} Automation",  # type: ignore
                    description=context.agent_goal[:80] if context.agent_goal else "Automation",  # type: ignore
                    integration_type=context.integration_type,
                    purpose=context.agent_goal or "Automate tasks",
                    allowed_tools=["ExternalAPI", "Read", "Write"],
                    steps=[
                        f"Connect to {context.integration_type}",
                        "Fetch required data",
                        "Process and format output",
                    ],
                )
                context.skill_requests.append(skill_request)

            context.state = ConversationState.TESTING
            return prompts.testing_prompt()
        else:
            context.state = ConversationState.REQUIREMENTS_GATHERING
            return prompts.modification_prompt()

    def _handle_testing(self, context: ConversationContext, user_input: str) -> str:
        """Handle testing phase.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        if "yes" in user_input.lower():
            context.state = ConversationState.DEPLOYMENT
            return prompts.test_success_prompt()
        else:
            return prompts.wait_for_test_prompt()

    def _handle_deployment(self, context: ConversationContext, user_input: str) -> str:
        """Handle deployment phase.

        Args:
            context: Conversation context
            user_input: User input

        Returns:
            Assistant response
        """
        if "yes" in user_input.lower():
            # Create agent config
            trigger_type = (
                TriggerType.SCHEDULED
                if context.requirements.get("trigger") == "scheduled"
                else TriggerType.ON_DEMAND
            )

            # Build skills list - mix of public and custom
            skills: list[SkillReference] = []

            # Add selected public skills
            for i, skill_id in enumerate(context.selected_public_skill_ids, 1):
                skills.append(
                    SkillReference(
                        skill_id=skill_id,
                        name=skill_id,
                        source="public",
                        order=i,
                    )
                )

            # Add custom skills
            start_order = len(skills) + 1
            for i, skill in enumerate(context.skill_requests, start_order):
                skills.append(
                    SkillReference(
                        skill_id=skill.skill_id,
                        name=skill.name,
                        source="custom",
                        order=i,
                    )
                )

            context.agent_config = AgentConfig(
                tenant_id=context.tenant_id,
                name=f"{context.integration_type.capitalize()} Agent",  # type: ignore
                description=context.agent_goal or "Automation agent",
                trigger=trigger_type,
                schedule=context.requirements.get("schedule"),
                skills=skills,
                integrations=[context.integration_id] if context.integration_id else [],
                created_by=context.user_id,
            )

            context.state = ConversationState.COMPLETE

            return prompts.deployment_success_prompt(
                agent_name=context.agent_config.name,
                trigger=context.agent_config.trigger.value,
                schedule=context.agent_config.schedule,
            )
        else:
            return prompts.draft_saved_prompt()
