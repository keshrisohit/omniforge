"""Conversation state machine for Skill Creation Assistant.

This module implements the ConversationManager class that manages the finite state
machine for conversational skill creation, coordinating state transitions and
delegating to specialized components.
"""

import logging
import re
from typing import TYPE_CHECKING, Optional

from omniforge.skills.creation.models import ConversationContext, ConversationState

if TYPE_CHECKING:
    from omniforge.skills.creation.gatherer import RequirementsGatherer
    from omniforge.skills.creation.generator import SkillMdGenerator
    from omniforge.skills.loader import SkillLoader

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manage skill creation conversation state.

    This class implements the FSM for conversational skill creation, coordinating
    state transitions and delegating to RequirementsGatherer for gathering states
    and SkillMdGenerator for generation states.

    Attributes:
        gatherer: RequirementsGatherer for collecting skill requirements
        generator: SkillMdGenerator for creating SKILL.md content
    """

    def __init__(
        self,
        gatherer: "RequirementsGatherer",
        generator: "SkillMdGenerator",
        skill_loader: Optional["SkillLoader"] = None,
    ) -> None:
        """Initialize ConversationManager with dependencies.

        Args:
            gatherer: RequirementsGatherer for requirements collection
            generator: SkillMdGenerator for SKILL.md generation
            skill_loader: Optional SkillLoader for checking existing skills before creation
        """
        self.gatherer = gatherer
        self.generator = generator
        self.skill_loader = skill_loader

    async def process_message(
        self,
        message: str,
        context: ConversationContext,
    ) -> tuple[str, ConversationContext]:
        """Process user message and return response with updated context.

        This is the main entry point for conversation processing. It routes to
        appropriate state handlers, updates context, and tracks message history.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Log state transition for debugging
        logger.info(f"Processing message in state: {context.state}")

        # Store user message in history
        context.message_history.append({"role": "user", "content": message})

        try:
            # Process based on current state
            response, updated_context = await self._handle_state(message, context)

            # Store assistant response in history
            updated_context.message_history.append({"role": "assistant", "content": response})

            return response, updated_context

        except Exception as e:
            logger.error(f"Error processing message in state {context.state}: {e}", exc_info=True)
            # Transition to GATHERING_DETAILS to allow recovery instead of ERROR
            original_state = context.state
            context.state = ConversationState.GATHERING_DETAILS
            error_message = (
                f"I encountered an error while processing your request: {e}\n\n"
                "Could you provide more details or rephrase your requirements? "
                "I'll use your input to continue."
            )
            context.message_history.append({"role": "assistant", "content": error_message})
            logger.info(f"State transition: {original_state} -> GATHERING_DETAILS (error recovery)")
            return error_message, context

    async def _handle_state(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Route message to appropriate state handler.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Dispatch to state-specific handlers
        handlers = {
            ConversationState.IDLE: self._handle_idle,
            ConversationState.INTENT_DETECTION: self._handle_intent_detection,
            ConversationState.CHECKING_EXISTING: self._handle_checking_existing,
            ConversationState.GATHERING_PURPOSE: self._handle_gathering_purpose,
            ConversationState.GATHERING_DETAILS: self._handle_gathering_details,
            ConversationState.CONFIRMING_SPEC: self._handle_confirming_spec,
            ConversationState.GENERATING: self._handle_generating,
            ConversationState.VALIDATING: self._handle_validating,
            ConversationState.FIXING_ERRORS: self._handle_fixing_errors,
            ConversationState.SELECTING_STORAGE: self._handle_selecting_storage,
            ConversationState.SAVING: self._handle_saving,
            ConversationState.COMPLETED: self._handle_completed,
            ConversationState.ERROR: self._handle_error,
        }

        handler = handlers.get(context.state)
        if handler is None:
            raise ValueError(f"Unknown state: {context.state}")

        return await handler(message, context)

    async def _handle_idle(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle IDLE state — check for existing skills before creating.

        If a SkillLoader is available, searches existing skills for keyword matches
        against the user's message. If matches are found, presents them and asks
        whether to use an existing skill or create a new one.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        if self.skill_loader is not None:
            matches = self._find_matching_skills(message)
            if matches:
                context.existing_skill_suggestions = matches
                context.skill_purpose = message
                context.state = ConversationState.CHECKING_EXISTING
                logger.info(f"State transition: IDLE -> CHECKING_EXISTING ({len(matches)} match(es))")

                skills_list = "\n".join(
                    f"  • **{m['name']}** — {m['description']}" for m in matches
                )
                response = (
                    f"I found existing skill(s) that might already do what you need:\n\n"
                    f"{skills_list}\n\n"
                    "Would you like to **use one of these**, or **create a new skill**?\n"
                    "(Reply 'use it' to activate the existing skill, or 'create new' to build one from scratch)"
                )
                return response, context

        # No loader or no matches — go straight to gathering
        context.state = ConversationState.GATHERING_PURPOSE
        logger.info("State transition: IDLE -> GATHERING_PURPOSE")
        response = (
            "I'll help you create a new skill! Let's start by understanding what you need.\n\n"
            "What is the main purpose of this skill? What task should it help accomplish?"
        )
        return response, context

    def _find_matching_skills(self, message: str) -> list[dict[str, str]]:
        """Search indexed skills for keyword matches against the user message.

        Args:
            message: User's input message

        Returns:
            List of matching skill dicts with 'name' and 'description'
        """
        try:
            self.skill_loader.build_index()  # type: ignore[union-attr]
            skills = self.skill_loader.list_skills()  # type: ignore[union-attr]
        except Exception:
            return []

        # Tokenise: lowercase words only
        stopwords = {"a", "an", "the", "to", "and", "or", "for", "that", "with", "i", "want"}
        msg_words = {
            w for w in re.findall(r"[a-z]+", message.lower()) if w not in stopwords
        }

        matches = []
        for skill in skills:
            skill_text = f"{skill.name} {skill.description}".lower()
            skill_words = set(re.findall(r"[a-z]+", skill_text)) - stopwords
            overlap = msg_words & skill_words
            if len(overlap) >= 2:
                matches.append({"name": skill.name, "description": skill.description})

        return matches

    async def _handle_checking_existing(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle CHECKING_EXISTING state — user decides to use existing or create new.

        Args:
            message: User's input message ('use it' / 'create new' / etc.)
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        message_lower = message.lower().strip()

        use_keywords = ["use it", "use existing", "use that", "yes", "yep", "sure", "ok"]
        if any(kw in message_lower for kw in use_keywords):
            # User wants to use an existing skill
            context.state = ConversationState.COMPLETED
            logger.info("State transition: CHECKING_EXISTING -> COMPLETED (using existing skill)")
            if context.existing_skill_suggestions:
                skill = context.existing_skill_suggestions[0]
                response = (
                    f"Great! You can use the **{skill['name']}** skill right away.\n\n"
                    f"**Description**: {skill['description']}\n\n"
                    "This skill is already available — no creation needed."
                )
            else:
                response = "The existing skill is ready to use — no creation needed."
            return response, context

        # User wants to create a new one
        context.existing_skill_suggestions = []
        context.state = ConversationState.GATHERING_PURPOSE
        logger.info("State transition: CHECKING_EXISTING -> GATHERING_PURPOSE (creating new)")
        response = (
            "No problem! Let's create a new skill.\n\n"
            "What is the main purpose of this skill? What task should it help accomplish?"
        )
        return response, context

    async def _handle_intent_detection(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle INTENT_DETECTION state.

        Note: For MVP, this state is simplified and typically skipped.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # For MVP, transition directly to GATHERING_PURPOSE
        context.state = ConversationState.GATHERING_PURPOSE
        logger.info(f"State transition: INTENT_DETECTION -> {context.state}")
        return await self._handle_gathering_purpose(message, context)

    async def _handle_gathering_purpose(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle GATHERING_PURPOSE state - collect skill purpose.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Store purpose
        context.skill_purpose = message

        # Analyze skill requirements and capabilities
        capabilities = await self.gatherer.analyze_skill_requirements(message, context)
        context.skill_capabilities = capabilities
        logger.info(
            f"Analyzed skill capabilities - "
            f"file_ops={capabilities.needs_file_operations}, "
            f"knowledge={capabilities.needs_external_knowledge}, "
            f"scripts={capabilities.needs_script_execution}, "
            f"workflow={capabilities.needs_multi_step_workflow}, "
            f"confidence={capabilities.confidence:.2f}"
        )

        # Transition to GATHERING_DETAILS
        context.state = ConversationState.GATHERING_DETAILS
        logger.info(f"State transition: GATHERING_PURPOSE -> {context.state}")

        # Generate clarifying questions
        questions = await self.gatherer.generate_clarifying_questions(context)

        response = (
            f"Got it! I understand you want to create a skill for: {message}\n\n"
            f"To help me build this skill, I need a bit more information:\n\n"
        )
        for i, question in enumerate(questions, 1):
            response += f"{i}. {question}\n"

        return response, context

    async def _handle_gathering_details(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle GATHERING_DETAILS state - collect additional requirements.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Extract requirements from user response
        extracted = await self.gatherer.extract_requirements(message, context)

        # Update context with extracted information
        if "examples" in extracted:
            context.examples.extend(extracted["examples"])
        if "workflow_steps" in extracted:
            context.workflow_steps.extend(extracted["workflow_steps"])
        if "triggers" in extracted:
            context.triggers.extend(extracted["triggers"])
        if "references_topics" in extracted:
            context.references_topics.extend(extracted["references_topics"])
        if "scripts_needed" in extracted:
            context.scripts_needed.extend(extracted["scripts_needed"])

        # Check if we have sufficient context
        if self.gatherer.has_sufficient_context(context):
            # Generate skill name and description
            context.skill_name = await self.gatherer.generate_skill_name(context)
            context.skill_description = await self.gatherer.generate_description(context)

            # Determine required tools based on pattern and requirements
            context.allowed_tools = self.gatherer.determine_required_tools(context)

            # Transition to CONFIRMING_SPEC
            context.state = ConversationState.CONFIRMING_SPEC
            logger.info(f"State transition: GATHERING_DETAILS -> {context.state}")

            response = (
                "Great! I have enough information to create your skill.\n\n"
                f"**Skill Name**: {context.skill_name}\n"
                f"**Description**: {context.skill_description}\n\n"
                "Does this look correct? (yes/no)\n"
                "If you'd like any changes, please let me know what to adjust."
            )
        else:
            # Try to infer missing information before asking questions
            if context.can_infer():
                logger.info("Attempting to infer missing information from context")
                context.increment_inference_attempt()

                inference_result = await self.gatherer.attempt_inference_from_context(context)

                # Apply inferred information to context
                if inference_result.get("inferred", False):
                    if "examples" in inference_result and not context.examples:
                        context.examples.extend(inference_result["examples"])
                        logger.info(f"Inferred {len(inference_result['examples'])} examples")

                    if "triggers" in inference_result and not context.triggers:
                        context.triggers.extend(inference_result["triggers"])
                        logger.info(f"Inferred {len(inference_result['triggers'])} triggers")

                    if "workflow_steps" in inference_result and not context.workflow_steps:
                        context.workflow_steps.extend(inference_result["workflow_steps"])
                        logger.info(
                            f"Inferred {len(inference_result['workflow_steps'])} workflow steps"
                        )

                    # Check again if we now have sufficient context
                    if self.gatherer.has_sufficient_context(context):
                        # Generate skill name and description
                        context.skill_name = await self.gatherer.generate_skill_name(context)
                        context.skill_description = await self.gatherer.generate_description(
                            context
                        )

                        # Determine required tools based on pattern and requirements
                        context.allowed_tools = self.gatherer.determine_required_tools(context)

                        # Transition to CONFIRMING_SPEC
                        context.state = ConversationState.CONFIRMING_SPEC
                        logger.info(
                            f"State transition: GATHERING_DETAILS -> {context.state} (after inference)"
                        )

                        response = (
                            "I've analyzed our conversation and filled in some reasonable assumptions.\n\n"
                            f"**Skill Name**: {context.skill_name}\n"
                            f"**Description**: {context.skill_description}\n\n"
                            "Does this look correct? (yes/no)\n"
                            "If you'd like any changes, please let me know what to adjust."
                        )
                        return response, context

                    # Still not sufficient, decide if we should ask
                    should_ask = await self.gatherer.should_ask_clarification(
                        context, inference_result
                    )

                    if not should_ask:
                        # Proceed despite missing info (LLM says it's okay)
                        logger.info("LLM decided inference is sufficient, proceeding")
                        context.skill_name = await self.gatherer.generate_skill_name(context)
                        context.skill_description = await self.gatherer.generate_description(
                            context
                        )

                        # Determine required tools based on pattern and requirements
                        context.allowed_tools = self.gatherer.determine_required_tools(context)

                        # Transition to CONFIRMING_SPEC
                        context.state = ConversationState.CONFIRMING_SPEC
                        logger.info(
                            f"State transition: GATHERING_DETAILS -> {context.state} (LLM decision)"
                        )

                        response = (
                            "Based on our conversation, I've prepared a skill specification.\n\n"
                            f"**Skill Name**: {context.skill_name}\n"
                            f"**Description**: {context.skill_description}\n\n"
                            "Does this look correct? (yes/no)\n"
                            "If you'd like any changes, please let me know what to adjust."
                        )
                        return response, context

            # Need more information, ask clarifying questions
            questions = await self.gatherer.generate_clarifying_questions(context)
            response = "Thanks for that information! I need a bit more detail:\n\n"
            for i, question in enumerate(questions, 1):
                response += f"{i}. {question}\n"

        return response, context

    async def _handle_confirming_spec(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle CONFIRMING_SPEC state - confirm or revise specification.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        message_lower = message.lower().strip()

        # Check for confirmation
        if any(word in message_lower for word in ["yes", "correct", "looks good", "confirm"]):
            # Transition to GENERATING
            context.state = ConversationState.GENERATING
            logger.info(f"State transition: CONFIRMING_SPEC -> {context.state}")

            response = "Perfect! I'll now generate your skill. This may take a moment..."
            return response, context

        # User wants changes
        context.state = ConversationState.GATHERING_DETAILS
        logger.info(f"State transition: CONFIRMING_SPEC -> {context.state}")

        response = (
            "No problem! What would you like to change? Please provide the updated information."
        )
        return response, context

    async def _handle_generating(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle GENERATING state - generate SKILL.md content.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        print(f"\n[CONVERSATION DEBUG] _handle_generating called, about to generate content...")
        print(f"[CONVERSATION DEBUG] Context skill_name: {context.skill_name}")
        print(f"[CONVERSATION DEBUG] Context skill_description: {context.skill_description}")

        # Generate SKILL.md content
        context.generated_content = await self.generator.generate(context)
        print(f"[CONVERSATION DEBUG] Generated content length: {len(context.generated_content) if context.generated_content else 0}")
        logger.info("SKILL.md content generated")

        # Transition to VALIDATING
        context.state = ConversationState.VALIDATING
        logger.info(f"State transition: GENERATING -> {context.state}")

        response = "Skill generated successfully! Validating content..."
        return response, context

    async def _handle_validating(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle VALIDATING state - validate generated content.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Basic validation (more comprehensive validation in TASK-005)
        is_valid = self._validate_generated_content(context)

        if is_valid:
            # Transition to SELECTING_STORAGE
            context.state = ConversationState.SELECTING_STORAGE
            logger.info(f"State transition: VALIDATING -> {context.state}")

            response = "Content validated successfully! Preparing to save..."
            return response, context

        # Validation failed
        context.increment_validation_attempt()

        if context.can_retry_validation():
            # Transition to FIXING_ERRORS
            context.state = ConversationState.FIXING_ERRORS
            logger.info(f"State transition: VALIDATING -> {context.state}")
            attempt_info = (
                f"{context.validation_attempts}/{context.max_validation_retries}"
            )
            response = f"Validation failed. Attempting to fix errors (attempt {attempt_info})..."
            return response, context

        # No retries left, transition to ERROR
        context.state = ConversationState.ERROR
        logger.info(f"State transition: VALIDATING -> {context.state}")

        response = (
            "I encountered validation errors that I couldn't fix automatically. "
            "Please try creating the skill again with more specific requirements."
        )
        return response, context

    async def _handle_fixing_errors(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle FIXING_ERRORS state - attempt to fix validation errors.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Attempt to fix validation errors
        if context.generated_content and context.validation_errors:
            context.generated_content = await self.generator.fix_validation_errors(
                context.generated_content, context.validation_errors
            )
            logger.info(f"Attempted to fix {len(context.validation_errors)} validation errors")

        # Clear validation errors and re-validate
        context.validation_errors.clear()

        # Transition back to VALIDATING
        context.state = ConversationState.VALIDATING
        logger.info(f"State transition: FIXING_ERRORS -> {context.state}")

        response = "Errors fixed! Revalidating content..."
        return response, context

    async def _handle_selecting_storage(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle SELECTING_STORAGE state - select storage layer.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # For MVP, default to project layer
        context.storage_layer = "project"
        logger.info(f"Storage layer selected: {context.storage_layer}")

        # Transition to SAVING
        context.state = ConversationState.SAVING
        logger.info(f"State transition: SELECTING_STORAGE -> {context.state}")

        response = "Saving skill to project layer..."
        return response, context

    async def _handle_saving(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle SAVING state - save skill to storage.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        # Saving logic will be implemented in TASK-006 (SkillWriter)
        # For now, just transition to COMPLETED

        context.state = ConversationState.COMPLETED
        logger.info(f"State transition: SAVING -> {context.state}")

        response = (
            f"Success! Your skill '{context.skill_name}' has been created.\n\n"
            f"**Location**: {context.storage_layer} layer\n"
            f"**Description**: {context.skill_description}\n\n"
            "You can now use this skill in your conversations!"
        )
        return response, context

    async def _handle_completed(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle COMPLETED state - conversation finished.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        response = (
            "This skill creation conversation is already completed. "
            "Would you like to create another skill?"
        )
        return response, context

    async def _handle_error(
        self, message: str, context: ConversationContext
    ) -> tuple[str, ConversationContext]:
        """Handle ERROR state - allow recovery or restart.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            Tuple of (response_message, updated_context)
        """
        message_lower = message.lower().strip()

        # Check if user wants to start over
        if any(word in message_lower for word in ["start over", "restart", "new skill", "begin again"]):
            # Reset context and start fresh
            context = ConversationContext(session_id=context.session_id)
            context.state = ConversationState.IDLE
            logger.info("User requested restart, resetting context")
            response = (
                "Okay, let's start fresh! "
                "What is the main purpose of the skill you want to create?"
            )
            return response, context

        # Otherwise, treat this as additional context and transition to GATHERING_DETAILS
        # to continue the conversation
        context.state = ConversationState.GATHERING_DETAILS
        logger.info("Recovering from ERROR state, transitioning to GATHERING_DETAILS")

        # Process the message as additional context
        extracted = await self.gatherer.extract_requirements(message, context)

        # Update context with extracted information
        if "examples" in extracted:
            context.examples.extend(extracted["examples"])
        if "workflow_steps" in extracted:
            context.workflow_steps.extend(extracted["workflow_steps"])
        if "triggers" in extracted:
            context.triggers.extend(extracted["triggers"])
        if "references_topics" in extracted:
            context.references_topics.extend(extracted["references_topics"])
        if "scripts_needed" in extracted:
            context.scripts_needed.extend(extracted["scripts_needed"])

        # Reset validation tracking for fresh attempt
        context.reset_validation()

        response = (
            "Thanks for the additional context! I'll use this to improve the skill. "
            "Let me regenerate it with your input..."
        )

        # Transition to GENERATING with updated context
        context.state = ConversationState.GENERATING
        logger.info("State transition: ERROR -> GENERATING (with updated context)")

        return response, context

    def _validate_generated_content(self, context: ConversationContext) -> bool:
        """Perform basic validation on generated content.

        Args:
            context: Conversation context with generated content

        Returns:
            True if content is valid, False otherwise
        """
        if not context.generated_content:
            context.validation_errors.append("No content generated")
            return False

        content = context.generated_content

        # Check for frontmatter
        if not content.startswith("---"):
            context.validation_errors.append("Missing frontmatter")
            return False

        # Check for skill name in content
        if context.skill_name and context.skill_name not in content:
            context.validation_errors.append(f"Skill name '{context.skill_name}' not in content")
            return False

        # Check line count (under 500 lines)
        line_count = len(content.split("\n"))
        if line_count > 500:
            context.validation_errors.append(f"Content exceeds 500 lines ({line_count} lines)")
            return False

        return True

    def get_next_state(self, context: ConversationContext, user_response: str) -> ConversationState:
        """Determine next state based on current state and user input.

        This method implements the state transition logic without processing
        the message. Useful for previewing transitions or testing.

        Args:
            context: Current conversation context
            user_response: User's response message

        Returns:
            Next conversation state
        """
        current_state = context.state
        response_lower = user_response.lower().strip()

        # State transition logic
        if current_state == ConversationState.IDLE:
            return ConversationState.CHECKING_EXISTING

        if current_state == ConversationState.CHECKING_EXISTING:
            if any(kw in response_lower for kw in ["use", "yes", "existing", "it"]):
                return ConversationState.COMPLETED
            return ConversationState.GATHERING_PURPOSE

        if current_state == ConversationState.INTENT_DETECTION:
            return ConversationState.GATHERING_PURPOSE

        if current_state == ConversationState.GATHERING_PURPOSE:
            return ConversationState.GATHERING_DETAILS

        if current_state == ConversationState.GATHERING_DETAILS:
            # Check if sufficient context (simplified for preview)
            if self.gatherer.has_sufficient_context(context):
                return ConversationState.CONFIRMING_SPEC
            return ConversationState.GATHERING_DETAILS

        if current_state == ConversationState.CONFIRMING_SPEC:
            if any(word in response_lower for word in ["yes", "correct", "confirm"]):
                return ConversationState.GENERATING
            return ConversationState.GATHERING_DETAILS

        if current_state == ConversationState.GENERATING:
            return ConversationState.VALIDATING

        if current_state == ConversationState.VALIDATING:
            # Simplified validation check
            if context.generated_content:
                return ConversationState.SELECTING_STORAGE
            if context.can_retry_validation():
                return ConversationState.FIXING_ERRORS
            return ConversationState.ERROR

        if current_state == ConversationState.FIXING_ERRORS:
            return ConversationState.VALIDATING

        if current_state == ConversationState.SELECTING_STORAGE:
            return ConversationState.SAVING

        if current_state == ConversationState.SAVING:
            return ConversationState.COMPLETED

        # Terminal states stay in same state
        if current_state in [ConversationState.COMPLETED, ConversationState.ERROR]:
            return current_state

        return current_state

    def is_complete(self, context: ConversationContext) -> bool:
        """Check if conversation has reached a terminal state.

        Args:
            context: Current conversation context

        Returns:
            True if conversation is complete (COMPLETED or ERROR), False otherwise
        """
        return context.state in [ConversationState.COMPLETED, ConversationState.ERROR]
