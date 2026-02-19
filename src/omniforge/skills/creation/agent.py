"""Skill Creation Assistant agent.

This module implements the main SkillCreationAgent class that orchestrates all components
to provide conversational skill creation following Anthropic Agent Skills guidelines.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional
from uuid import UUID

from omniforge.agents.base import BaseAgent
from omniforge.agents.events import TaskDoneEvent, TaskMessageEvent, TaskStatusEvent
from omniforge.agents.models import (
    AgentCapabilities,
    AgentIdentity,
    AgentSkill,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)
from omniforge.chat.llm_generator import LLMResponseGenerator
from omniforge.conversation.models import ConversationType, MessageRole
from omniforge.conversation.sqlite_repository import SQLiteConversationRepository
from omniforge.skills.creation.conversation import ConversationManager
from omniforge.skills.creation.gatherer import RequirementsGatherer
from omniforge.skills.creation.generator import SkillMdGenerator
from omniforge.skills.creation.models import ConversationContext, ConversationState
from omniforge.skills.creation.validator import SkillValidator
from omniforge.skills.creation.writer import SkillWriter
from omniforge.skills.loader import SkillLoader
from omniforge.skills.storage import SkillStorageManager, StorageConfig
from omniforge.tasks.models import Task, TaskState

logger = logging.getLogger(__name__)


class SkillCreationAgent(BaseAgent):
    """Conversational agent for skill creation following Anthropic guidelines.

    This agent orchestrates the full skill creation workflow from requirements
    gathering through validation and file writing, providing a conversational
    interface that guides users through creating compliant agent skills.

    Implements the A2A BaseAgent interface via process_task(), wrapping the
    existing multi-turn FSM (handle_message) for delegation from MasterAgent.

    Attributes:
        identity: Agent identity information
        capabilities: A2A capabilities declaration
        skills: Skills this agent provides
        llm_generator: LLM generator for intelligent responses
        conversation_manager: FSM-based conversation state management
        requirements_gatherer: Intelligent requirements collection
        skill_md_generator: SKILL.md content generation
        skill_validator: Compliance validation
        skill_writer: Filesystem operations
        conversation_repository: Optional repository for conversation persistence
        sessions: In-memory session storage (cache + fallback)
    """

    identity = AgentIdentity(
        id="skill-creation-assistant",
        name="Skill Creation Assistant",
        description="Create OmniForge skills through natural conversation",
        version="1.0.0",
    )

    capabilities = AgentCapabilities(
        streaming=True,
        multi_turn=True,
        push_notifications=False,
        hitl_support=False,
    )

    skills = [
        AgentSkill(
            id="skill-creation",
            name="Skill Creation",
            description="Guide users through creating OmniForge SKILL.md files via conversation",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
    ]

    def __init__(
        self,
        llm_generator: Optional[LLMResponseGenerator] = None,
        storage_config: Optional[StorageConfig] = None,
        conversation_repository: Optional[SQLiteConversationRepository] = None,
    ) -> None:
        """Initialize agent with dependencies (or create defaults).

        Args:
            llm_generator: Optional LLM generator for responses (creates default if None)
            storage_config: Optional storage configuration (creates default if None)
            conversation_repository: Optional repository for conversation persistence (None = in-memory only)
        """
        super().__init__()

        # Initialize LLM generator
        self.llm_generator = llm_generator or LLMResponseGenerator()

        # Initialize storage configuration with project root
        if storage_config is None:
            # Use src/omniforge/skills as the default project path
            from pathlib import Path

            project_root = Path.cwd()
            # Try to find src/omniforge/skills directory
            if (project_root / "src" / "omniforge" / "skills").exists():
                storage_config = StorageConfig(
                    project_path=project_root / "src" / "omniforge" / "skills"
                )
            else:
                storage_config = StorageConfig.from_environment(project_root=project_root)

        storage_manager = SkillStorageManager(storage_config)

        # Initialize components
        self.requirements_gatherer = RequirementsGatherer(self.llm_generator)
        self.skill_md_generator = SkillMdGenerator(self.llm_generator)
        self.skill_validator = SkillValidator()
        self.skill_writer = SkillWriter(storage_manager)

        # SkillLoader for checking existing skills before creating new ones
        self.skill_loader = SkillLoader(storage_config)

        # Initialize conversation manager
        self.conversation_manager = ConversationManager(
            gatherer=self.requirements_gatherer,
            generator=self.skill_md_generator,
            skill_loader=self.skill_loader,
        )

        # Conversation persistence using unified repository
        self.conversation_repository = conversation_repository

        # Session storage (in-memory cache + fallback when no DB)
        self.sessions: dict[str, ConversationContext] = {}

        # Track how many messages have been persisted per session (to avoid duplicates)
        self._persisted_msg_counts: dict[str, int] = {}

        logger.info(
            f"Initialized {self.identity.name} v{self.identity.version} "
            f"(persistence: {'enabled' if conversation_repository else 'disabled'})"
        )

    async def process_task(self, task: Task) -> AsyncIterator:  # type: ignore[override]
        """A2A-compliant task processor that wraps the FSM handle_message().

        Uses task.user_id as session_id so multi-turn continuity is preserved
        across successive process_task() calls from MasterAgent delegation.

        Yields:
            TaskStatusEvent(WORKING) at start
            TaskMessageEvent for each chunk from the FSM
            TaskStatusEvent(INPUT_REQUIRED) if FSM awaits next turn
            TaskDoneEvent(COMPLETED) if FSM completed (session cleared)
            TaskDoneEvent(FAILED) on unexpected error
        """
        # Extract latest user message from task
        user_message = ""
        for msg in reversed(task.messages):
            if msg.role == "user":
                for part in msg.parts:
                    if hasattr(part, "text"):
                        user_message = part.text
                        break
                break

        session_id = task.user_id
        tenant_id = task.tenant_id or "local"

        yield TaskStatusEvent(
            task_id=task.id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
        )

        try:
            async for chunk in self.handle_message(user_message, session_id, tenant_id):
                yield TaskMessageEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=chunk)],
                    is_partial=True,
                )

            # After handle_message completes, check if FSM session is still active
            if session_id in self.sessions:
                # FSM still active — awaiting user's next turn
                yield TaskStatusEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    state=TaskState.INPUT_REQUIRED,
                )
            else:
                # FSM completed (session cleared by _clear_session)
                yield TaskDoneEvent(
                    task_id=task.id,
                    timestamp=datetime.utcnow(),
                    final_state=TaskState.COMPLETED,
                )

        except Exception as e:
            logger.error(f"SkillCreationAgent.process_task error: {e}", exc_info=True)
            yield TaskMessageEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=f"Skill creation error: {e}")],
                is_partial=False,
            )
            yield TaskDoneEvent(
                task_id=task.id,
                timestamp=datetime.utcnow(),
                final_state=TaskState.FAILED,
            )

    async def handle_message(
        self,
        message: str,
        session_id: str,
        tenant_id: str,  # BREAKING CHANGE: tenant_id is now required for multi-tenancy
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> AsyncIterator[str]:
        """Handle conversational message for skill creation.

        Processes the user's message through the conversation state machine,
        updating context and yielding response chunks for streaming to the user.

        Args:
            message: User's input message
            session_id: Unique session identifier
            tenant_id: Tenant identifier for multi-tenancy isolation (required)
            conversation_history: Optional conversation history for context

        Yields:
            Response chunks for streaming to user

        Example:
            >>> agent = SkillCreationAgent()
            >>> async for chunk in agent.handle_message(
            ...     "Create a skill to format product names",
            ...     session_id="session-123",
            ...     tenant_id="tenant-456"
            ... ):
            ...     print(chunk, end="")
        """
        try:
            # Get or create conversation context (with DB restoration if available)
            context = await self.get_session_context(session_id, tenant_id)

            # Restore conversation history if provided
            if conversation_history and not context.message_history:
                context.message_history = conversation_history

            # Process message through conversation manager
            response, updated_context = await self.conversation_manager.process_message(
                message, context
            )

            # Update session context in memory
            self.sessions[session_id] = updated_context

            # Persist context after processing (non-blocking)
            await self._persist_context(updated_context, tenant_id)

            # Persist new messages to the DB (conversation must exist first)
            await self._persist_new_messages(updated_context, tenant_id)

            # Check if we need to trigger generation (state machine moved to GENERATING)
            if updated_context.state == ConversationState.GENERATING:
                # Yield initial response
                yield response + "\n\n"

                # Trigger generation workflow
                async for chunk in self._handle_generation_workflow(session_id, tenant_id):
                    yield chunk

            # Check if we need to trigger validation (state machine moved to VALIDATING)
            elif updated_context.state == ConversationState.VALIDATING:
                yield response + "\n\n"
                async for chunk in self._handle_validation_workflow(session_id, tenant_id):
                    yield chunk

            # Check if we need to save (state machine moved to SAVING)
            elif updated_context.state == ConversationState.SAVING:
                yield response + "\n\n"
                async for chunk in self._handle_saving_workflow(session_id, tenant_id):
                    yield chunk

            # Otherwise, just yield the response
            else:
                yield response

            # Clear session if conversation is complete
            if self.conversation_manager.is_complete(updated_context):
                await self._clear_session(session_id, tenant_id)

        except Exception as e:
            logger.error(f"Error handling message in session {session_id}: {e}", exc_info=True)
            # Transition to GATHERING_DETAILS to allow recovery
            context = await self.get_session_context(session_id, tenant_id)
            if context.state not in [ConversationState.COMPLETED, ConversationState.ERROR]:
                context.state = ConversationState.GATHERING_DETAILS
                self.sessions[session_id] = context
                # Persist error state (with ignore_errors to prevent cascading failures)
                await self._persist_context(context, tenant_id, ignore_errors=True)
            yield (
                f"I encountered an error: {e}\n\n"
                "Could you provide more context or clarify your requirements? "
                "I'll use your input to continue creating the skill.\n"
            )

    async def _handle_generation_workflow(
        self, session_id: str, tenant_id: str
    ) -> AsyncIterator[str]:
        """Handle the generation workflow state transitions.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier

        Yields:
            Status messages for user feedback
        """
        context = self.sessions[session_id]

        try:
            yield "Generating SKILL.md content...\n"

            # Actually generate the content (call conversation manager's handler)
            _, updated_context = await self.conversation_manager._handle_generating("", context)
            self.sessions[session_id] = updated_context

            # Persist after generation
            await self._persist_context(updated_context, tenant_id)

            yield "Generation complete! Validating content...\n\n"

            # Trigger validation workflow
            async for chunk in self._handle_validation_workflow(session_id, tenant_id):
                yield chunk

        except Exception as e:
            logger.error(f"Generation workflow error: {e}", exc_info=True)
            context.state = ConversationState.GATHERING_DETAILS
            self.sessions[session_id] = context
            # Persist error state
            await self._persist_context(context, tenant_id, ignore_errors=True)
            yield (
                f"I encountered an issue during generation: {e}\n\n"
                "Could you provide more specific requirements? "
                "Additional examples or details would help me create the skill.\n"
            )

    async def _handle_validation_workflow(
        self, session_id: str, tenant_id: str
    ) -> AsyncIterator[str]:
        """Handle the validation workflow state transitions (iterative, not recursive).

        This method uses an iterative approach with progress tracking instead of
        recursion to avoid stack buildup and detect when fixes aren't improving.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier

        Yields:
            Validation status messages
        """
        context = self.sessions[session_id]

        if not context.generated_content or not context.skill_name:
            context.state = ConversationState.ERROR
            self.sessions[session_id] = context
            await self._persist_context(context, tenant_id, ignore_errors=True)
            yield "Error: No generated content to validate.\n"
            return

        try:
            # Iterative validation loop (not recursive)
            while True:
                # Validate the generated content
                validation_result = self.skill_validator.validate(
                    context.generated_content,
                    context.skill_name,
                )

                if validation_result.is_valid:
                    # Validation passed
                    yield "Validation successful! ✓\n\n"

                    # Transition to SELECTING_STORAGE
                    context.state = ConversationState.SELECTING_STORAGE
                    context.reset_validation()
                    self.sessions[session_id] = context
                    await self._persist_context(context, tenant_id)

                    # For MVP, automatically select project layer
                    yield "Selecting storage location...\n"
                    context.storage_layer = "project"
                    context.state = ConversationState.SAVING
                    self.sessions[session_id] = context
                    await self._persist_context(context, tenant_id)

                    # Trigger saving workflow
                    async for chunk in self._handle_saving_workflow(session_id, tenant_id):
                        yield chunk
                    break  # Exit validation loop

                else:
                    # Validation failed - track progress
                    error_count = len(validation_result.errors)
                    making_progress = context.track_validation_progress(error_count)

                    context.validation_errors = validation_result.errors
                    context.increment_validation_attempt()

                    yield f"Validation found {error_count} issue(s):\n"
                    for i, error in enumerate(validation_result.errors, 1):
                        yield f"{i}. {error}\n"

                    # Check if we can retry and if we're making progress
                    if context.can_retry_validation():
                        if not making_progress and context.validation_attempts > 1:
                            # Not making progress, transition to GATHERING_DETAILS for user input
                            logger.warning("Validation errors not decreasing, asking user for help")
                            context.state = ConversationState.GATHERING_DETAILS
                            self.sessions[session_id] = context
                            await self._persist_context(context, tenant_id)
                            yield (
                                "\nAutomatic fixes aren't resolving these issues. "
                                "Could you provide more specific requirements or clarify:\n"
                                "- What specific behavior should this skill have?\n"
                                "- Are there any examples or details that would help?\n\n"
                                "I'll use your input to regenerate the skill "
                                "with better accuracy.\n"
                            )
                            break  # Exit validation loop

                        # Attempt to fix errors
                        attempt_msg = (
                            f"\nAttempting to fix errors "
                            f"(attempt {context.validation_attempts}/"
                            f"{context.max_validation_retries})...\n"
                        )
                        yield attempt_msg
                        context.state = ConversationState.FIXING_ERRORS

                        # Fix errors using generator
                        fixed_content = await self.skill_md_generator.fix_validation_errors(
                            context.generated_content,
                            context.validation_errors,
                        )

                        # Check if content actually changed
                        if fixed_content == context.generated_content:
                            logger.warning("LLM fix didn't change content, asking user for input")
                            context.state = ConversationState.GATHERING_DETAILS
                            self.sessions[session_id] = context
                            await self._persist_context(context, tenant_id)
                            yield (
                                "\nI'm having trouble fixing these issues automatically. "
                                "Could you provide more details or clarify your requirements? "
                                "Your input will help me generate a better skill.\n"
                            )
                            break  # Exit validation loop

                        context.generated_content = fixed_content
                        context.validation_errors.clear()
                        context.state = ConversationState.VALIDATING
                        self.sessions[session_id] = context
                        await self._persist_context(context, tenant_id)

                        # Continue to next iteration (not recursive call)
                        yield "Errors fixed! Revalidating...\n\n"

                    else:
                        # Max retries exceeded, transition to GATHERING_DETAILS for user input
                        context.state = ConversationState.GATHERING_DETAILS
                        self.sessions[session_id] = context
                        await self._persist_context(context, tenant_id)
                        yield (
                            "\nI've tried several times but couldn't resolve "
                            "all validation issues. "
                            "Could you help by providing more specific requirements? "
                            "What additional details or examples can you share "
                            "to help me create this skill?\n"
                        )
                        break  # Exit validation loop

        except Exception as e:
            logger.error(f"Validation workflow error: {e}", exc_info=True)
            context.state = ConversationState.GATHERING_DETAILS
            self.sessions[session_id] = context
            await self._persist_context(context, tenant_id, ignore_errors=True)
            yield (
                f"I encountered an issue during validation: {e}\n\n"
                "Could you provide more details or clarify your requirements? "
                "This will help me generate a better skill.\n"
            )

    async def _handle_saving_workflow(self, session_id: str, tenant_id: str) -> AsyncIterator[str]:
        """Handle the saving workflow.

        Args:
            session_id: Session identifier
            tenant_id: Tenant identifier

        Yields:
            Save status messages
        """
        context = self.sessions[session_id]

        if not context.generated_content or not context.skill_name or not context.storage_layer:
            context.state = ConversationState.ERROR
            self.sessions[session_id] = context
            await self._persist_context(context, tenant_id, ignore_errors=True)
            yield "Error: Missing required information for saving.\n"
            return

        try:
            # Write skill to filesystem
            yield f"Saving skill to {context.storage_layer} layer...\n"

            skill_path = await self.skill_writer.write_skill(
                skill_name=context.skill_name,
                content=context.generated_content,
                storage_layer=context.storage_layer,
                resources=context.generated_resources if context.generated_resources else None,
            )

            # Success!
            context.state = ConversationState.COMPLETED
            self.sessions[session_id] = context
            await self._persist_context(context, tenant_id)

            yield f"\n✓ Success! Your skill '{context.skill_name}' has been created!\n\n"
            yield f"**Location**: {skill_path.parent}\n"
            yield f"**File**: {skill_path.name}\n"
            yield f"**Description**: {context.skill_description}\n\n"
            yield (
                "You can now use this skill in your conversations. "
                "Agents will automatically apply it when relevant.\n"
            )

        except Exception as e:
            logger.error(f"Saving workflow error: {e}", exc_info=True)
            # For saving errors, we should stay in ERROR state as this is likely
            # a filesystem issue, not a content issue
            context.state = ConversationState.ERROR
            self.sessions[session_id] = context
            await self._persist_context(context, tenant_id, ignore_errors=True)
            yield (
                f"Failed to save skill: {e}\n\n"
                "This appears to be a storage issue. Would you like to:\n"
                "1. Try again (I'll reattempt saving)\n"
                "2. Start over with a new skill\n"
            )

    async def create_skill(
        self,
        purpose: str,
        examples: list[dict[str, str]],
        triggers: list[str],
        storage_layer: str = "project",
    ) -> Path:
        """Programmatic skill creation (non-conversational).

        Creates a skill directly without conversational interaction, useful
        for automated skill generation or batch creation.

        Args:
            purpose: Main purpose/goal of the skill
            examples: List of example dicts with input/output
            triggers: List of triggering conditions/scenarios
            storage_layer: Target storage layer (default: "project")

        Returns:
            Path to created SKILL.md file

        Raises:
            ValueError: If required parameters are invalid
            SkillWriterError: If skill creation fails

        Example:
            >>> agent = SkillCreationAgent()
            >>> path = await agent.create_skill(
            ...     purpose="Format product names",
            ...     examples=[{"input": "PA", "output": "Pro Analytics"}],
            ...     triggers=["writing documentation"],
            ...     storage_layer="project"
            ... )
            >>> print(f"Created skill at {path}")
        """
        # Create a temporary context
        context = ConversationContext()
        context.skill_purpose = purpose
        context.examples = [
            f"Input: {ex.get('input', '')}, Output: {ex.get('output', '')}" for ex in examples
        ]
        context.triggers = triggers
        context.storage_layer = storage_layer

        # Analyze skill requirements and capabilities
        context.skill_capabilities = await self.requirements_gatherer.analyze_skill_requirements(
            purpose, context
        )

        # Generate skill name and description
        context.skill_name = await self.requirements_gatherer.generate_skill_name(context)
        context.skill_description = await self.requirements_gatherer.generate_description(context)

        # Generate SKILL.md content
        context.generated_content = await self.skill_md_generator.generate(context)

        # Validate
        validation_result = self.skill_validator.validate(
            context.generated_content,
            context.skill_name,
        )

        if not validation_result.is_valid:
            # Try to fix once
            context.generated_content = await self.skill_md_generator.fix_validation_errors(
                context.generated_content,
                validation_result.errors,
            )

            # Re-validate
            validation_result = self.skill_validator.validate(
                context.generated_content,
                context.skill_name,
            )

            if not validation_result.is_valid:
                error_msg = "; ".join(validation_result.errors)
                raise ValueError(f"Skill validation failed: {error_msg}")

        # Write to filesystem
        skill_path = await self.skill_writer.write_skill(
            skill_name=context.skill_name,
            content=context.generated_content,
            storage_layer=storage_layer,
            resources=context.generated_resources if context.generated_resources else None,
        )

        logger.info(f"Successfully created skill '{context.skill_name}' at {skill_path}")
        return skill_path

    async def get_session_context(self, session_id: str, tenant_id: str) -> ConversationContext:
        """Get or create conversation context for session.

        Checks in-memory cache first (fast path), then falls back to database
        if repository is configured. Creates new context if not found anywhere.

        Args:
            session_id: Unique session identifier (UUID string or UUID)
            tenant_id: Tenant identifier for multi-tenancy isolation

        Returns:
            ConversationContext for the session

        Example:
            >>> agent = SkillCreationAgent()
            >>> context = await agent.get_session_context("session-123", "tenant-456")
            >>> assert context.session_id == "session-123"
            >>> assert context.state == ConversationState.IDLE
        """
        # Check in-memory cache first (fast path)
        if session_id in self.sessions:
            return self.sessions[session_id]

        # Fall back to database if repository exists
        if self.conversation_repository:
            try:
                # Convert session_id to UUID (generate if not valid UUID)
                conversation_id = self._session_id_to_uuid(session_id, tenant_id)
                conversation = await self.conversation_repository.get_conversation(
                    conversation_id, tenant_id
                )

                if conversation:
                    # Extract ConversationContext from state_metadata
                    loaded_context = self._deserialize_context(conversation.state_metadata or {})
                    loaded_context.session_id = session_id

                    # Restore FSM state from conversation
                    if conversation.state:
                        loaded_context.state = ConversationState(conversation.state)

                    # Load messages from conversation_messages table
                    messages = await self.conversation_repository.get_messages(
                        conversation_id, tenant_id
                    )
                    loaded_context.message_history = [
                        {"role": msg.role, "content": msg.content} for msg in messages
                    ]

                    # Track how many messages are already persisted
                    self._persisted_msg_counts[session_id] = len(loaded_context.message_history)

                    # Restore to memory cache
                    self.sessions[session_id] = loaded_context
                    logger.info(
                        f"Restored session {session_id} from database for tenant {tenant_id}"
                    )
                    return loaded_context
            except Exception as e:
                logger.warning(
                    f"Failed to load session {session_id} from database: {e}. "
                    "Creating new session."
                )

        # Create new context if not found anywhere
        context = ConversationContext(session_id=session_id)
        self.sessions[session_id] = context
        logger.debug(f"Created new session context: {session_id}")
        return context

    async def _persist_context(
        self,
        context: ConversationContext,
        tenant_id: str,
        ignore_errors: bool = False,
    ) -> None:
        """Persist conversation context to database (non-blocking).

        Args:
            context: ConversationContext to persist
            tenant_id: Tenant identifier
            ignore_errors: If True, log errors but don't raise (for error path persistence)

        Note:
            This method is non-blocking - persistence errors won't crash the agent.
            Errors are logged and optionally suppressed based on ignore_errors flag.
        """
        if not self.conversation_repository:
            return  # No repository configured, skip persistence

        try:
            import time

            start_time = time.perf_counter()

            # Convert session_id to UUID (generate if not valid UUID)
            conversation_id = self._session_id_to_uuid(context.session_id, tenant_id)

            # Check if conversation exists
            existing_conversation = await self.conversation_repository.get_conversation(
                conversation_id, tenant_id
            )

            if existing_conversation:
                # Update existing conversation
                await self.conversation_repository.update_state(
                    conversation_id,
                    tenant_id,
                    state=context.state.value,
                    state_metadata=self._serialize_context(context),
                )
            else:
                # Create new conversation with specific ID
                await self.conversation_repository.create_conversation(
                    tenant_id=tenant_id,
                    user_id=tenant_id,  # For now, use tenant_id as user_id
                    title=context.skill_name or "Skill Creation Session",
                    conversation_type=ConversationType.SKILL_CREATION,
                    state=context.state.value,
                    state_metadata=self._serialize_context(context),
                    conversation_id=conversation_id,
                )

            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.debug(
                f"Persisted session {context.session_id} for tenant {tenant_id} "
                f"in {latency_ms:.2f}ms"
            )
        except Exception as e:
            logger.error(
                f"Failed to persist session {context.session_id} for tenant {tenant_id}: {e}",
                exc_info=not ignore_errors,
            )
            if not ignore_errors:
                raise

    async def _persist_new_messages(self, context: ConversationContext, tenant_id: str) -> None:
        """Persist any new messages from context.message_history to the database.

        Only persists messages that haven't been saved yet (tracked via _persisted_msg_counts).
        The conversation must already exist in DB before calling this method.

        Args:
            context: ConversationContext with message_history
            tenant_id: Tenant identifier
        """
        if not self.conversation_repository:
            return

        session_id = context.session_id
        persisted_count = self._persisted_msg_counts.get(session_id, 0)
        new_messages = context.message_history[persisted_count:]

        if not new_messages:
            return

        conversation_id = self._session_id_to_uuid(session_id, tenant_id)
        saved = 0
        for msg in new_messages:
            content = msg.get("content", "")
            if not content.strip():
                continue
            try:
                role = MessageRole(msg["role"])
                await self.conversation_repository.add_message(
                    conversation_id, tenant_id, role, content
                )
                saved += 1
            except Exception as e:
                logger.warning(f"Failed to persist message for session {session_id}: {e}")
                break  # Stop saving if we hit an error to avoid partial writes

        self._persisted_msg_counts[session_id] = persisted_count + saved

    async def _clear_session(self, session_id: str, tenant_id: str) -> None:
        """Clear session context after completion.

        Clears from memory. Conversations are kept in the database for audit trail.

        Args:
            session_id: Session identifier to clear
            tenant_id: Tenant identifier for multi-tenancy isolation

        Example:
            >>> agent = SkillCreationAgent()
            >>> await agent._clear_session("session-123", "tenant-456")
        """
        # Clear from memory
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.debug(f"Cleared session from memory: {session_id}")

        # Clear persisted message count tracking
        self._persisted_msg_counts.pop(session_id, None)

        # Note: We keep the conversation in the database for audit trail
        # It will be marked as COMPLETED state in the database

    def _session_id_to_uuid(self, session_id: str, tenant_id: str = "") -> UUID:
        """Convert session_id to UUID (generate UUID from session_id+tenant_id if not valid UUID).

        Args:
            session_id: Session identifier string
            tenant_id: Tenant identifier (included in hash for cross-tenant uniqueness)

        Returns:
            UUID instance
        """
        try:
            return UUID(session_id) if isinstance(session_id, str) else session_id
        except ValueError:
            # If session_id is not a valid UUID, generate UUID4 from MD5 hash
            # Include tenant_id to ensure different tenants get different UUIDs for same session_id
            import hashlib
            combined = f"{tenant_id}:{session_id}"
            return UUID(bytes=hashlib.md5(combined.encode()).digest(), version=4)

    def _serialize_context(self, context: ConversationContext) -> dict:
        """Serialize ConversationContext to JSON-compatible dict.

        Args:
            context: ConversationContext to serialize

        Returns:
            JSON-compatible dictionary
        """
        return {
            "skill_name": context.skill_name,
            "skill_description": context.skill_description,
            "skill_purpose": context.skill_purpose,
            "skill_capabilities": context.skill_capabilities.model_dump()
            if context.skill_capabilities
            else None,
            "examples": context.examples,
            "triggers": context.triggers,
            "storage_layer": context.storage_layer,
            "generated_content": context.generated_content,
            "generated_resources": context.generated_resources,
            "validation_errors": context.validation_errors,
            "validation_attempts": context.validation_attempts,
            "validation_progress": context.validation_progress,
            "max_validation_retries": context.max_validation_retries,
        }

    def _deserialize_context(self, data: dict) -> ConversationContext:
        """Deserialize ConversationContext from JSON dict.

        Args:
            data: JSON dictionary with context data

        Returns:
            ConversationContext instance
        """
        from omniforge.skills.creation.models import SkillCapabilities

        context = ConversationContext()
        context.skill_name = data.get("skill_name")
        context.skill_description = data.get("skill_description")
        context.skill_purpose = data.get("skill_purpose")

        # Deserialize skill_capabilities if present
        capabilities_data = data.get("skill_capabilities")
        if capabilities_data:
            context.skill_capabilities = SkillCapabilities(**capabilities_data)

        context.examples = data.get("examples", [])
        context.triggers = data.get("triggers", [])
        context.storage_layer = data.get("storage_layer")
        context.generated_content = data.get("generated_content")
        context.generated_resources = data.get("generated_resources", {})
        context.validation_errors = data.get("validation_errors", [])
        context.validation_attempts = data.get("validation_attempts", 0)
        context.validation_progress = data.get("validation_progress", {})
        context.max_validation_retries = data.get("max_validation_retries", 3)
        return context
