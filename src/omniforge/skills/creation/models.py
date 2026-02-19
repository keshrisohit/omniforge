"""Pydantic models for Skill Creation Assistant.

This module defines the data models for conversational skill creation including
conversation state management, skill patterns, and validation results following
official Anthropic Agent Skills guidelines.
"""

import re
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ConversationState(str, Enum):
    """Finite State Machine states for skill creation conversation flow.

    The conversation progresses through these states as the assistant gathers
    information and generates the skill definition.
    """

    IDLE = "idle"
    INTENT_DETECTION = "intent_detection"
    CHECKING_EXISTING = "checking_existing"
    GATHERING_PURPOSE = "gathering_purpose"
    GATHERING_DETAILS = "gathering_details"
    CONFIRMING_SPEC = "confirming_spec"
    GENERATING = "generating"
    VALIDATING = "validating"
    FIXING_ERRORS = "fixing_errors"
    SELECTING_STORAGE = "selecting_storage"
    SAVING = "saving"
    COMPLETED = "completed"
    ERROR = "error"


class SkillCapabilities(BaseModel):
    """LLM-determined skill capabilities and requirements.

    This model captures what the LLM determines about a skill's needs
    based on analyzing the purpose and gathered context. It replaces
    the previous pattern-based approach with flexible capability flags
    and LLM-generated suggestions.

    Attributes:
        needs_file_operations: Whether skill needs to read/write files
        needs_external_knowledge: Whether skill needs reference docs or external knowledge
        needs_script_execution: Whether skill needs to run scripts/commands
        needs_multi_step_workflow: Whether skill involves multiple sequential steps
        suggested_tools: LLM-suggested tool permissions (e.g., ["Read", "Write", "Bash(git:*)"])
        suggested_assets: LLM-suggested asset files with name, purpose, and type
        suggested_references: LLM-suggested reference topics with purpose
        suggested_scripts: LLM-suggested scripts with name, purpose, and language
        reasoning: LLM explanation of capability determination
        confidence: LLM confidence score (0.0-1.0)
    """

    # Core capabilities
    needs_file_operations: bool = False
    needs_external_knowledge: bool = False
    needs_script_execution: bool = False
    needs_multi_step_workflow: bool = False

    # LLM suggestions (each dict has keys like "name", "purpose", "type", etc.)
    suggested_tools: list[str] = Field(default_factory=list)
    suggested_assets: list[dict[str, str]] = Field(default_factory=list)
    suggested_references: list[dict[str, str]] = Field(default_factory=list)
    suggested_scripts: list[dict[str, str]] = Field(default_factory=list)

    # Reasoning
    reasoning: str = ""
    confidence: float = 0.0


class OfficialSkillSpec(BaseModel):
    """Official Anthropic skill specification (name + description only).

    This model represents the minimal skill specification following official
    Anthropic Agent Skills guidelines, containing only the required metadata.

    Attributes:
        name: Skill identifier in kebab-case (1-64 chars, lowercase letters/numbers/hyphens)
        description: Brief description of skill's purpose (1-1024 characters)
    """

    name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(..., min_length=1, max_length=1024)

    @field_validator("name")
    @classmethod
    def validate_kebab_case(cls, value: str) -> str:
        """Validate that skill name follows kebab-case format.

        Per Anthropic spec: lowercase letters, numbers, and hyphens only,
        must start with a lowercase letter.

        Args:
            value: The skill name to validate

        Returns:
            The validated skill name

        Raises:
            ValueError: If name format is invalid
        """
        if not re.match(r"^[a-z][a-z0-9-]*$", value):
            raise ValueError(
                "Skill name must be kebab-case: start with lowercase letter, "
                "contain only lowercase letters, numbers, and hyphens"
            )
        return value


class ConversationContext(BaseModel):
    """Context accumulation for skill creation conversation.

    Tracks conversation state and accumulates information gathered through
    the conversation flow to eventually generate a complete skill definition.

    Attributes:
        session_id: Unique identifier for this conversation session
        state: Current FSM state of the conversation
        skill_name: Accumulated skill name (kebab-case)
        skill_description: Accumulated skill description
        skill_purpose: User-provided purpose/goal for the skill
        skill_capabilities: LLM-determined capabilities and requirements
        examples: User-provided examples of skill usage
        workflow_steps: Workflow steps (for multi-step skills)
        triggers: Triggering conditions or scenarios for the skill
        references_topics: Topics/domains requiring reference material
        scripts_needed: Scripts or commands needed for execution
        allowed_tools: Tool permissions (e.g., ["Read", "Write", "Bash(git:*)"])
        storage_layer: Selected storage layer (global, tenant, etc.)
        generated_content: Generated skill markdown content
        generated_resources: Generated supporting resources (scripts, configs)
        validation_attempts: Number of validation attempts made
        validation_errors: Accumulated validation errors
        max_validation_retries: Maximum number of validation retries allowed
        message_history: Conversation message history for context
        asked_questions: Questions already asked (to prevent loops)
        inference_attempts: Number of inference attempts made
        max_inference_attempts: Maximum inference attempts allowed
    """

    # Session tracking
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    state: ConversationState = ConversationState.IDLE

    # Skill metadata accumulation
    skill_name: Optional[str] = None
    skill_description: Optional[str] = None
    skill_purpose: Optional[str] = None

    # Capabilities (LLM-determined requirements)
    skill_capabilities: Optional[SkillCapabilities] = None
    examples: list[str] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    triggers: list[str] = Field(default_factory=list)
    references_topics: list[str] = Field(default_factory=list)
    scripts_needed: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)  # Tool permissions e.g., ["Read", "Write", "Bash(git:*)"]

    # Storage and generation
    storage_layer: Optional[str] = None
    generated_content: Optional[str] = None
    generated_resources: dict[str, str] = Field(default_factory=dict)

    # Validation tracking
    validation_attempts: int = 0
    validation_errors: list[str] = Field(default_factory=list)
    max_validation_retries: int = 3
    validation_progress: dict[str, int] = Field(default_factory=dict)  # Track error reduction

    # Existing skill suggestions (populated during CHECKING_EXISTING state)
    existing_skill_suggestions: list[dict[str, str]] = Field(default_factory=list)

    # Message history
    message_history: list[dict[str, str]] = Field(default_factory=list)

    # Question tracking (prevent loops)
    asked_questions: list[str] = Field(default_factory=list)
    inference_attempts: int = 0
    max_inference_attempts: int = 2

    def to_official_spec(self) -> Optional[OfficialSkillSpec]:
        """Convert context to official Anthropic skill specification.

        Creates an OfficialSkillSpec if both name and description are available
        and valid according to Anthropic guidelines.

        Returns:
            OfficialSkillSpec if name and description are valid, None otherwise
        """
        if not self.skill_name or not self.skill_description:
            return None

        try:
            return OfficialSkillSpec(name=self.skill_name, description=self.skill_description)
        except Exception:
            return None

    def can_retry_validation(self) -> bool:
        """Check if validation can be retried.

        Returns:
            True if validation attempts are below max retries, False otherwise
        """
        return self.validation_attempts < self.max_validation_retries

    def increment_validation_attempt(self) -> None:
        """Increment validation attempt counter."""
        self.validation_attempts += 1

    def reset_validation(self) -> None:
        """Reset validation tracking."""
        self.validation_attempts = 0
        self.validation_errors.clear()
        self.validation_progress.clear()

    def can_infer(self) -> bool:
        """Check if inference can be attempted.

        Returns:
            True if inference attempts are below max, False otherwise
        """
        return self.inference_attempts < self.max_inference_attempts

    def increment_inference_attempt(self) -> None:
        """Increment inference attempt counter."""
        self.inference_attempts += 1

    def track_validation_progress(self, error_count: int) -> bool:
        """Track validation error count to detect progress.

        Args:
            error_count: Current number of validation errors

        Returns:
            True if making progress (errors decreasing), False otherwise
        """
        attempt = self.validation_attempts
        if attempt == 0:
            self.validation_progress[str(attempt)] = error_count
            return True

        prev_count = self.validation_progress.get(str(attempt - 1), float("inf"))
        self.validation_progress[str(attempt)] = error_count

        # Progress means fewer errors than before
        return error_count < prev_count

    def has_asked_question(self, question: str) -> bool:
        """Check if a similar question has been asked.

        Args:
            question: Question text to check

        Returns:
            True if question or very similar question was already asked
        """
        question_lower = question.lower().strip()
        # Simple similarity check: consider similar if significant overlap in key words
        question_words = set(question_lower.split())

        for asked in self.asked_questions:
            asked_words = set(asked.lower().split())
            # If more than 50% overlap, consider it similar
            overlap = len(question_words & asked_words)
            if overlap > len(question_words) * 0.5:
                return True
        return False


class ValidationResult(BaseModel):
    """Result of skill validation.

    Contains validation outcome, errors, warnings, and the path to the
    validated skill file if successful.

    Attributes:
        is_valid: Whether validation succeeded
        errors: List of validation errors
        warnings: List of validation warnings (non-blocking)
        skill_path: Path to validated skill file if successful
    """

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skill_path: Optional[str] = None

    def has_errors(self) -> bool:
        """Check if validation has errors.

        Returns:
            True if errors exist, False otherwise
        """
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        """Check if validation has warnings.

        Returns:
            True if warnings exist, False otherwise
        """
        return len(self.warnings) > 0

    def add_error(self, error: str) -> None:
        """Add a validation error.

        Args:
            error: The error message to add
        """
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a validation warning.

        Args:
            warning: The warning message to add
        """
        self.warnings.append(warning)
