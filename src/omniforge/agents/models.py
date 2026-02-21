"""Pydantic models for A2A (Agent-to-Agent) protocol.

This module defines the data models for agent identity, capabilities, skills,
message parts, and artifacts following the A2A protocol specification.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SkillInputMode(str, Enum):
    """Supported input modes for agent skills."""

    TEXT = "text"
    FILE = "file"
    STRUCTURED = "structured"


class SkillOutputMode(str, Enum):
    """Supported output modes for agent skills."""

    TEXT = "text"
    FILE = "file"
    STRUCTURED = "structured"
    ARTIFACT = "artifact"


class ArtifactType(str, Enum):
    """Closed set of artifact categories."""

    DOCUMENT = "document"
    DATASET = "dataset"
    CODE = "code"
    IMAGE = "image"
    STRUCTURED = "structured"


class AuthScheme(str, Enum):
    """Supported authentication schemes for agent APIs."""

    BEARER = "bearer"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    NONE = "none"


class AgentIdentity(BaseModel):
    """Agent identity information.

    Attributes:
        id: Unique identifier for the agent (1-255 characters)
        name: Human-readable agent name (1-255 characters)
        description: Brief description of agent's purpose
        version: Semantic version string (e.g., "1.0.0")
    """

    id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str
    version: str = Field(..., min_length=1, max_length=50)

    @field_validator("version")
    @classmethod
    def validate_semver_format(cls, value: str) -> str:
        """Validate that version follows semantic versioning format.

        Args:
            value: The version string to validate

        Returns:
            The validated version string

        Raises:
            ValueError: If version format is invalid
        """
        parts = value.split(".")
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError("Version must follow semantic versioning (e.g., '1.0.0')")
        for part in parts:
            if not part.isdigit():
                raise ValueError("Version parts must be numeric")
        return value


class HandoffCapability(BaseModel):
    """Handoff capability configuration for an agent.

    Attributes:
        supports_handoff: Whether the agent supports handoff pattern
        handoff_triggers: List of triggers that initiate handoff (e.g., ["create skill"])
        workflow_states: List of workflow states the agent can handle
        requires_exclusive_control: Whether agent requires exclusive thread control
        max_session_duration_seconds: Maximum duration for a handoff session (0 = unlimited)
    """

    supports_handoff: bool = False
    handoff_triggers: list[str] = Field(default_factory=list)
    workflow_states: list[str] = Field(default_factory=list)
    requires_exclusive_control: bool = False
    max_session_duration_seconds: int = Field(default=0, ge=0)

    @field_validator("handoff_triggers", "workflow_states")
    @classmethod
    def validate_non_empty_strings(cls, value: list[str]) -> list[str]:
        """Validate that list items are non-empty strings.

        Args:
            value: List of strings to validate

        Returns:
            The validated list

        Raises:
            ValueError: If any string is empty
        """
        for item in value:
            if not item or not item.strip():
                raise ValueError("List items must be non-empty strings")
        return value


class OrchestrationCapability(BaseModel):
    """Orchestration capability configuration for an agent.

    Attributes:
        can_orchestrate: Whether the agent can orchestrate other agents
        can_be_orchestrated: Whether the agent can be orchestrated by others
        supported_delegation_strategies: List of supported delegation strategies
        max_concurrent_delegations: Maximum number of concurrent delegations (0 = unlimited)
    """

    can_orchestrate: bool = False
    can_be_orchestrated: bool = True
    supported_delegation_strategies: list[str] = Field(default_factory=list)
    max_concurrent_delegations: int = Field(default=0, ge=0)

    @field_validator("supported_delegation_strategies")
    @classmethod
    def validate_non_empty_strings(cls, value: list[str]) -> list[str]:
        """Validate that delegation strategies are non-empty strings.

        Args:
            value: List of delegation strategies to validate

        Returns:
            The validated list

        Raises:
            ValueError: If any strategy is empty
        """
        for strategy in value:
            if not strategy or not strategy.strip():
                raise ValueError("Delegation strategies must be non-empty strings")
        return value


class AgentCapabilities(BaseModel):
    """Agent capabilities configuration.

    Attributes:
        streaming: Whether agent supports streaming responses
        push_notifications: Whether agent can send push notifications
        multi_turn: Whether agent supports multi-turn conversations
        hitl_support: Whether agent supports human-in-the-loop interactions
        handoff: Handoff capability configuration (optional)
        orchestration: Orchestration capability configuration (optional)
    """

    streaming: bool = False
    push_notifications: bool = False
    multi_turn: bool = False
    hitl_support: bool = False
    handoff: Optional[HandoffCapability] = None
    orchestration: Optional[OrchestrationCapability] = None


class AgentSkill(BaseModel):
    """Definition of an agent skill.

    Attributes:
        id: Unique identifier for the skill (1-255 characters)
        name: Human-readable skill name (1-255 characters)
        description: Detailed description of skill functionality
        tags: Optional list of tags for categorization
        examples: Optional list of usage examples
        input_modes: Supported input modes for this skill
        output_modes: Supported output modes for this skill
    """

    id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: str
    tags: Optional[list[str]] = None
    examples: Optional[list[str]] = None
    input_modes: list[SkillInputMode] = Field(..., alias="inputModes")
    output_modes: list[SkillOutputMode] = Field(..., alias="outputModes")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("input_modes", "output_modes")
    @classmethod
    def validate_modes_not_empty(cls, value: list) -> list:
        """Validate that modes list is not empty.

        Args:
            value: The modes list to validate

        Returns:
            The validated modes list

        Raises:
            ValueError: If modes list is empty
        """
        if not value:
            raise ValueError("At least one mode must be specified")
        return value


class SecurityConfig(BaseModel):
    """Security configuration for agent API access.

    Attributes:
        auth_scheme: Authentication scheme required for API access
        require_https: Whether HTTPS is required for API calls
    """

    auth_scheme: AuthScheme
    require_https: bool = True


class AgentCard(BaseModel):
    """A2A compliant agent discovery document.

    This model represents the complete agent card following A2A protocol
    specifications, with JSON aliases for camelCase compliance.

    Attributes:
        protocol_version: A2A protocol version (e.g., "1.0")
        identity: Agent identity information
        capabilities: Agent capabilities configuration
        skills: List of available skills
        service_endpoint: URL endpoint for agent API
        security: Security configuration
    """

    protocol_version: str = Field(..., min_length=1, max_length=20, alias="protocolVersion")
    identity: AgentIdentity
    capabilities: AgentCapabilities
    skills: list[AgentSkill]
    service_endpoint: str = Field(..., min_length=1, alias="serviceEndpoint")
    security: SecurityConfig

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("skills")
    @classmethod
    def validate_skills_not_empty(cls, value: list[AgentSkill]) -> list[AgentSkill]:
        """Validate that skills list is not empty.

        Args:
            value: The skills list to validate

        Returns:
            The validated skills list

        Raises:
            ValueError: If skills list is empty
        """
        if not value:
            raise ValueError("Agent must have at least one skill")
        return value


class TextPart(BaseModel):
    """Text message part.

    Attributes:
        type: Message part type identifier
        text: The text content
    """

    type: str = Field(default="text", frozen=True)
    text: str


class FilePart(BaseModel):
    """File message part.

    Attributes:
        type: Message part type identifier
        file_url: URL to the file resource
        mime_type: MIME type of the file
        filename: Optional original filename
    """

    type: str = Field(default="file", frozen=True)
    file_url: str
    mime_type: str
    filename: Optional[str] = None


class DataPart(BaseModel):
    """Structured data message part.

    Attributes:
        type: Message part type identifier
        data: The structured data (dict or list)
        schema_url: Optional URL to JSON schema definition
    """

    type: str = Field(default="data", frozen=True)
    data: Union[dict, list]
    schema_url: Optional[str] = None


class ArtifactPart(BaseModel):
    """Reference to a stored artifact, used as a message part.

    Attributes:
        type: Message part type identifier (always "artifact")
        artifact_id: ID of the stored artifact
        title: Optional human-readable hint
    """

    type: str = Field(default="artifact", frozen=True)
    artifact_id: str = Field(..., min_length=1, max_length=255)
    title: Optional[str] = None


# Union type for all message parts
MessagePart = Union[TextPart, FilePart, DataPart, ArtifactPart]


class Artifact(BaseModel):
    """Agent output artifact.

    Attributes:
        id: Unique identifier for the artifact. If None, the store generates a UUID.
        type: Artifact category from the ArtifactType enum
        title: Human-readable artifact title
        inline_content: Artifact content stored inline (str, dict, or list)
        metadata: Optional metadata dictionary
        tenant_id: Tenant namespace for store-level isolation
        storage_url: External URL where artifact content is stored
        mime_type: IANA media type of the artifact content
        size_bytes: Size of the artifact content in bytes
        schema_url: JSON Schema URL for structured artifact types
        created_by_agent_id: ID of the agent that produced this artifact
        created_at: Timestamp when the artifact was created
    """

    id: Optional[str] = None
    type: ArtifactType
    title: str = Field(..., min_length=1, max_length=500)
    inline_content: Optional[Union[str, dict, list]] = None
    metadata: Optional[dict[str, Union[str, int, float, bool]]] = None
    tenant_id: str
    storage_url: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = Field(None, ge=0)
    schema_url: Optional[str] = None
    created_by_agent_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_content_present(self) -> "Artifact":
        """Validate that at least one of inline_content or storage_url is set.

        Raises:
            ValueError: If both inline_content and storage_url are None
        """
        if self.inline_content is None and self.storage_url is None:
            raise ValueError("Artifact must have at least one of inline_content or storage_url")
        return self
