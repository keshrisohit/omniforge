"""Tests for A2A protocol models."""

import pytest
from pydantic import ValidationError

from omniforge.agents.models import (
    AgentCapabilities,
    AgentCard,
    AgentIdentity,
    AgentSkill,
    Artifact,
    AuthScheme,
    DataPart,
    FilePart,
    HandoffCapability,
    MessagePart,
    OrchestrationCapability,
    SecurityConfig,
    SkillInputMode,
    SkillOutputMode,
    TextPart,
)


class TestAgentIdentity:
    """Tests for AgentIdentity model."""

    def test_create_valid_identity(self) -> None:
        """Should create identity with valid fields."""
        identity = AgentIdentity(
            id="agent-123",
            name="Test Agent",
            description="A test agent for testing",
            version="1.0.0",
        )

        assert identity.id == "agent-123"
        assert identity.name == "Test Agent"
        assert identity.description == "A test agent for testing"
        assert identity.version == "1.0.0"

    def test_identity_with_empty_id_raises_error(self) -> None:
        """Should fail with empty id."""
        with pytest.raises(ValidationError):
            AgentIdentity(id="", name="Test Agent", description="Test", version="1.0.0")

    def test_identity_with_long_id_raises_error(self) -> None:
        """Should fail with id exceeding max length."""
        with pytest.raises(ValidationError):
            AgentIdentity(id="a" * 256, name="Test Agent", description="Test", version="1.0.0")

    def test_identity_with_empty_name_raises_error(self) -> None:
        """Should fail with empty name."""
        with pytest.raises(ValidationError):
            AgentIdentity(id="agent-123", name="", description="Test", version="1.0.0")

    def test_identity_with_invalid_version_raises_error(self) -> None:
        """Should fail with invalid semantic version."""
        with pytest.raises(ValidationError, match="semantic versioning"):
            AgentIdentity(
                id="agent-123",
                name="Test Agent",
                description="Test",
                version="invalid",
            )

    def test_identity_with_non_numeric_version_raises_error(self) -> None:
        """Should fail with non-numeric version parts."""
        with pytest.raises(ValidationError, match="must be numeric"):
            AgentIdentity(id="agent-123", name="Test Agent", description="Test", version="1.x.0")

    def test_identity_with_two_part_version(self) -> None:
        """Should accept two-part semantic version."""
        identity = AgentIdentity(
            id="agent-123", name="Test Agent", description="Test", version="1.0"
        )
        assert identity.version == "1.0"


class TestAgentCapabilities:
    """Tests for AgentCapabilities model."""

    def test_create_capabilities_with_defaults(self) -> None:
        """Should create capabilities with default values."""
        caps = AgentCapabilities()

        assert caps.streaming is False
        assert caps.push_notifications is False
        assert caps.multi_turn is False
        assert caps.hitl_support is False

    def test_create_capabilities_with_all_enabled(self) -> None:
        """Should create capabilities with all features enabled."""
        caps = AgentCapabilities(
            streaming=True, push_notifications=True, multi_turn=True, hitl_support=True
        )

        assert caps.streaming is True
        assert caps.push_notifications is True
        assert caps.multi_turn is True
        assert caps.hitl_support is True


class TestAgentSkill:
    """Tests for AgentSkill model."""

    def test_create_valid_skill(self) -> None:
        """Should create skill with valid fields."""
        skill = AgentSkill(
            id="skill-1",
            name="Code Analysis",
            description="Analyzes code quality",
            input_modes=[SkillInputMode.TEXT, SkillInputMode.FILE],
            output_modes=[SkillOutputMode.TEXT, SkillOutputMode.STRUCTURED],
        )

        assert skill.id == "skill-1"
        assert skill.name == "Code Analysis"
        assert skill.description == "Analyzes code quality"
        assert SkillInputMode.TEXT in skill.input_modes
        assert SkillOutputMode.TEXT in skill.output_modes

    def test_skill_with_tags_and_examples(self) -> None:
        """Should create skill with optional tags and examples."""
        skill = AgentSkill(
            id="skill-1",
            name="Code Analysis",
            description="Analyzes code quality",
            tags=["code", "analysis", "quality"],
            examples=["Analyze this Python file", "Check code quality"],
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )

        assert skill.tags == ["code", "analysis", "quality"]
        assert len(skill.examples) == 2

    def test_skill_with_empty_input_modes_raises_error(self) -> None:
        """Should fail with empty input modes."""
        with pytest.raises(ValidationError, match="At least one mode"):
            AgentSkill(
                id="skill-1",
                name="Test",
                description="Test",
                input_modes=[],
                output_modes=[SkillOutputMode.TEXT],
            )

    def test_skill_with_empty_output_modes_raises_error(self) -> None:
        """Should fail with empty output modes."""
        with pytest.raises(ValidationError, match="At least one mode"):
            AgentSkill(
                id="skill-1",
                name="Test",
                description="Test",
                input_modes=[SkillInputMode.TEXT],
                output_modes=[],
            )


class TestSecurityConfig:
    """Tests for SecurityConfig model."""

    def test_create_security_config_with_bearer_auth(self) -> None:
        """Should create security config with bearer authentication."""
        config = SecurityConfig(auth_scheme=AuthScheme.BEARER)

        assert config.auth_scheme == AuthScheme.BEARER
        assert config.require_https is True

    def test_create_security_config_without_https(self) -> None:
        """Should create security config allowing HTTP."""
        config = SecurityConfig(auth_scheme=AuthScheme.API_KEY, require_https=False)

        assert config.require_https is False


class TestAgentCard:
    """Tests for AgentCard model."""

    def test_create_valid_agent_card(self) -> None:
        """Should create valid A2A agent card."""
        identity = AgentIdentity(
            id="agent-1", name="Test Agent", description="Test", version="1.0.0"
        )
        capabilities = AgentCapabilities(streaming=True)
        skill = AgentSkill(
            id="skill-1",
            name="Test Skill",
            description="Test",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
        security = SecurityConfig(auth_scheme=AuthScheme.BEARER)

        card = AgentCard(
            protocol_version="1.0",
            identity=identity,
            capabilities=capabilities,
            skills=[skill],
            service_endpoint="https://api.example.com/agent",
            security=security,
        )

        assert card.protocol_version == "1.0"
        assert card.identity.id == "agent-1"
        assert len(card.skills) == 1
        assert card.service_endpoint == "https://api.example.com/agent"

    def test_agent_card_with_empty_skills_raises_error(self) -> None:
        """Should fail with empty skills list."""
        identity = AgentIdentity(
            id="agent-1", name="Test Agent", description="Test", version="1.0.0"
        )
        capabilities = AgentCapabilities()
        security = SecurityConfig(auth_scheme=AuthScheme.BEARER)

        with pytest.raises(ValidationError, match="at least one skill"):
            AgentCard(
                protocol_version="1.0",
                identity=identity,
                capabilities=capabilities,
                skills=[],
                service_endpoint="https://api.example.com/agent",
                security=security,
            )

    def test_agent_card_serialization_with_camelcase_aliases(self) -> None:
        """Should serialize with camelCase aliases for A2A compliance."""
        identity = AgentIdentity(
            id="agent-1", name="Test Agent", description="Test", version="1.0.0"
        )
        capabilities = AgentCapabilities()
        skill = AgentSkill(
            id="skill-1",
            name="Test",
            description="Test",
            input_modes=[SkillInputMode.TEXT],
            output_modes=[SkillOutputMode.TEXT],
        )
        security = SecurityConfig(auth_scheme=AuthScheme.NONE)

        card = AgentCard(
            protocol_version="1.0",
            identity=identity,
            capabilities=capabilities,
            skills=[skill],
            service_endpoint="https://api.example.com",
            security=security,
        )

        json_data = card.model_dump(by_alias=True)
        assert "protocolVersion" in json_data
        assert "serviceEndpoint" in json_data
        assert json_data["protocolVersion"] == "1.0"
        assert json_data["serviceEndpoint"] == "https://api.example.com"

    def test_agent_card_deserialization_with_camelcase_aliases(self) -> None:
        """Should deserialize from camelCase JSON."""
        json_data = {
            "protocolVersion": "1.0",
            "identity": {
                "id": "agent-1",
                "name": "Test Agent",
                "description": "Test",
                "version": "1.0.0",
            },
            "capabilities": {
                "streaming": False,
                "push_notifications": False,
                "multi_turn": False,
                "hitl_support": False,
            },
            "skills": [
                {
                    "id": "skill-1",
                    "name": "Test",
                    "description": "Test",
                    "input_modes": ["text"],
                    "output_modes": ["text"],
                }
            ],
            "serviceEndpoint": "https://api.example.com",
            "security": {"auth_scheme": "none", "require_https": True},
        }

        card = AgentCard.model_validate(json_data)
        assert card.protocol_version == "1.0"
        assert card.service_endpoint == "https://api.example.com"


class TestTextPart:
    """Tests for TextPart model."""

    def test_create_text_part(self) -> None:
        """Should create text message part."""
        part = TextPart(text="Hello, world!")

        assert part.type == "text"
        assert part.text == "Hello, world!"

    def test_text_part_type_is_frozen(self) -> None:
        """Should not allow changing type field."""
        part = TextPart(text="Hello")

        with pytest.raises(ValidationError):
            part.type = "other"


class TestFilePart:
    """Tests for FilePart model."""

    def test_create_file_part(self) -> None:
        """Should create file message part."""
        part = FilePart(
            file_url="https://example.com/file.pdf",
            mime_type="application/pdf",
            filename="document.pdf",
        )

        assert part.type == "file"
        assert part.file_url == "https://example.com/file.pdf"
        assert part.mime_type == "application/pdf"
        assert part.filename == "document.pdf"

    def test_create_file_part_without_filename(self) -> None:
        """Should create file part without optional filename."""
        part = FilePart(file_url="https://example.com/file.pdf", mime_type="application/pdf")

        assert part.filename is None


class TestDataPart:
    """Tests for DataPart model."""

    def test_create_data_part_with_dict(self) -> None:
        """Should create data part with dictionary."""
        part = DataPart(data={"key": "value", "count": 42})

        assert part.type == "data"
        assert part.data == {"key": "value", "count": 42}

    def test_create_data_part_with_list(self) -> None:
        """Should create data part with list."""
        part = DataPart(data=[1, 2, 3, 4, 5])

        assert part.data == [1, 2, 3, 4, 5]

    def test_create_data_part_with_schema_url(self) -> None:
        """Should create data part with schema URL."""
        part = DataPart(data={"name": "John"}, schema_url="https://example.com/schema.json")

        assert part.schema_url == "https://example.com/schema.json"


class TestArtifact:
    """Tests for Artifact model."""

    def test_create_artifact_with_string_content(self) -> None:
        """Should create artifact with string content."""
        artifact = Artifact(
            id="artifact-1",
            type="document",
            title="Analysis Report",
            content="This is the report content.",
        )

        assert artifact.id == "artifact-1"
        assert artifact.type == "document"
        assert artifact.title == "Analysis Report"
        assert artifact.content == "This is the report content."

    def test_create_artifact_with_dict_content(self) -> None:
        """Should create artifact with structured content."""
        artifact = Artifact(
            id="artifact-2",
            type="data",
            title="Metrics",
            content={"cpu": 45.2, "memory": 78.5},
        )

        assert artifact.content == {"cpu": 45.2, "memory": 78.5}

    def test_create_artifact_with_metadata(self) -> None:
        """Should create artifact with metadata."""
        artifact = Artifact(
            id="artifact-3",
            type="code",
            title="Function",
            content="def hello(): pass",
            metadata={"language": "python", "lines": 1, "complexity": 1.0},
        )

        assert artifact.metadata == {"language": "python", "lines": 1, "complexity": 1.0}

    def test_artifact_with_long_id_raises_error(self) -> None:
        """Should fail with id exceeding max length."""
        with pytest.raises(ValidationError):
            Artifact(id="a" * 256, type="document", title="Test", content="Content")

    def test_artifact_with_long_title_raises_error(self) -> None:
        """Should fail with title exceeding max length."""
        with pytest.raises(ValidationError):
            Artifact(id="artifact-1", type="document", title="a" * 501, content="Content")


class TestMessagePartUnion:
    """Tests for MessagePart union type."""

    def test_message_part_accepts_text_part(self) -> None:
        """Should accept TextPart as MessagePart."""
        part: MessagePart = TextPart(text="Hello")
        assert isinstance(part, TextPart)

    def test_message_part_accepts_file_part(self) -> None:
        """Should accept FilePart as MessagePart."""
        part: MessagePart = FilePart(
            file_url="https://example.com/file.pdf", mime_type="application/pdf"
        )
        assert isinstance(part, FilePart)

    def test_message_part_accepts_data_part(self) -> None:
        """Should accept DataPart as MessagePart."""
        part: MessagePart = DataPart(data={"key": "value"})
        assert isinstance(part, DataPart)


class TestHandoffCapability:
    """Tests for HandoffCapability model."""

    def test_create_with_defaults(self) -> None:
        """HandoffCapability should have sensible defaults."""
        capability = HandoffCapability()

        assert capability.supports_handoff is False
        assert capability.handoff_triggers == []
        assert capability.workflow_states == []
        assert capability.requires_exclusive_control is False
        assert capability.max_session_duration_seconds == 0

    def test_create_with_handoff_enabled(self) -> None:
        """HandoffCapability should support handoff configuration."""
        capability = HandoffCapability(
            supports_handoff=True,
            handoff_triggers=["create skill", "manage workflow"],
            workflow_states=["init", "in_progress", "completed"],
            requires_exclusive_control=True,
            max_session_duration_seconds=3600,
        )

        assert capability.supports_handoff is True
        assert capability.handoff_triggers == ["create skill", "manage workflow"]
        assert capability.workflow_states == ["init", "in_progress", "completed"]
        assert capability.requires_exclusive_control is True
        assert capability.max_session_duration_seconds == 3600

    def test_reject_empty_handoff_triggers(self) -> None:
        """HandoffCapability should reject empty trigger strings."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffCapability(
                supports_handoff=True,
                handoff_triggers=["create skill", "", "manage workflow"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("handoff_triggers",) for e in errors)

    def test_reject_whitespace_handoff_triggers(self) -> None:
        """HandoffCapability should reject whitespace-only trigger strings."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffCapability(
                supports_handoff=True,
                handoff_triggers=["create skill", "   ", "manage workflow"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("handoff_triggers",) for e in errors)

    def test_reject_empty_workflow_states(self) -> None:
        """HandoffCapability should reject empty workflow state strings."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffCapability(
                supports_handoff=True,
                workflow_states=["init", "", "completed"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("workflow_states",) for e in errors)

    def test_reject_negative_max_session_duration(self) -> None:
        """HandoffCapability should reject negative max_session_duration_seconds."""
        with pytest.raises(ValidationError) as exc_info:
            HandoffCapability(
                supports_handoff=True,
                max_session_duration_seconds=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("max_session_duration_seconds",) for e in errors)

    def test_serialization_deserialization(self) -> None:
        """HandoffCapability should serialize and deserialize correctly."""
        original = HandoffCapability(
            supports_handoff=True,
            handoff_triggers=["create skill"],
            workflow_states=["init", "active"],
            requires_exclusive_control=True,
            max_session_duration_seconds=1800,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = HandoffCapability(**data)

        assert restored.supports_handoff == original.supports_handoff
        assert restored.handoff_triggers == original.handoff_triggers
        assert restored.max_session_duration_seconds == original.max_session_duration_seconds


class TestOrchestrationCapability:
    """Tests for OrchestrationCapability model."""

    def test_create_with_defaults(self) -> None:
        """OrchestrationCapability should have sensible defaults."""
        capability = OrchestrationCapability()

        assert capability.can_orchestrate is False
        assert capability.can_be_orchestrated is True
        assert capability.supported_delegation_strategies == []
        assert capability.max_concurrent_delegations == 0

    def test_create_orchestrator_agent(self) -> None:
        """OrchestrationCapability should support orchestrator configuration."""
        capability = OrchestrationCapability(
            can_orchestrate=True,
            can_be_orchestrated=False,
            supported_delegation_strategies=["parallel", "sequential", "conditional"],
            max_concurrent_delegations=5,
        )

        assert capability.can_orchestrate is True
        assert capability.can_be_orchestrated is False
        assert capability.supported_delegation_strategies == [
            "parallel",
            "sequential",
            "conditional",
        ]
        assert capability.max_concurrent_delegations == 5

    def test_create_sub_agent_only(self) -> None:
        """OrchestrationCapability should support sub-agent only configuration."""
        capability = OrchestrationCapability(
            can_orchestrate=False,
            can_be_orchestrated=True,
        )

        assert capability.can_orchestrate is False
        assert capability.can_be_orchestrated is True

    def test_reject_empty_delegation_strategies(self) -> None:
        """OrchestrationCapability should reject empty delegation strategy strings."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationCapability(
                can_orchestrate=True,
                supported_delegation_strategies=["parallel", "", "sequential"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("supported_delegation_strategies",) for e in errors)

    def test_reject_whitespace_delegation_strategies(self) -> None:
        """OrchestrationCapability should reject whitespace-only strategy strings."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationCapability(
                can_orchestrate=True,
                supported_delegation_strategies=["parallel", "   ", "sequential"],
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("supported_delegation_strategies",) for e in errors)

    def test_reject_negative_max_concurrent_delegations(self) -> None:
        """OrchestrationCapability should reject negative max_concurrent_delegations."""
        with pytest.raises(ValidationError) as exc_info:
            OrchestrationCapability(
                can_orchestrate=True,
                max_concurrent_delegations=-1,
            )

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("max_concurrent_delegations",) for e in errors)

    def test_serialization_deserialization(self) -> None:
        """OrchestrationCapability should serialize and deserialize correctly."""
        original = OrchestrationCapability(
            can_orchestrate=True,
            can_be_orchestrated=False,
            supported_delegation_strategies=["parallel", "sequential"],
            max_concurrent_delegations=3,
        )

        # Serialize to dict
        data = original.model_dump()

        # Deserialize from dict
        restored = OrchestrationCapability(**data)

        assert restored.can_orchestrate == original.can_orchestrate
        assert restored.can_be_orchestrated == original.can_be_orchestrated
        assert restored.supported_delegation_strategies == original.supported_delegation_strategies
        assert restored.max_concurrent_delegations == original.max_concurrent_delegations


class TestAgentCapabilitiesWithHandoffAndOrchestration:
    """Tests for AgentCapabilities with handoff and orchestration extensions."""

    def test_create_capabilities_with_handoff(self) -> None:
        """AgentCapabilities should accept handoff capability."""
        handoff = HandoffCapability(
            supports_handoff=True,
            handoff_triggers=["create skill"],
        )
        caps = AgentCapabilities(handoff=handoff)

        assert caps.handoff is not None
        assert caps.handoff.supports_handoff is True
        assert caps.handoff.handoff_triggers == ["create skill"]

    def test_create_capabilities_with_orchestration(self) -> None:
        """AgentCapabilities should accept orchestration capability."""
        orchestration = OrchestrationCapability(
            can_orchestrate=True,
            supported_delegation_strategies=["parallel"],
        )
        caps = AgentCapabilities(orchestration=orchestration)

        assert caps.orchestration is not None
        assert caps.orchestration.can_orchestrate is True
        assert caps.orchestration.supported_delegation_strategies == ["parallel"]

    def test_create_capabilities_with_both_extensions(self) -> None:
        """AgentCapabilities should accept both handoff and orchestration."""
        handoff = HandoffCapability(supports_handoff=True)
        orchestration = OrchestrationCapability(can_orchestrate=True)
        caps = AgentCapabilities(
            streaming=True,
            multi_turn=True,
            handoff=handoff,
            orchestration=orchestration,
        )

        assert caps.streaming is True
        assert caps.multi_turn is True
        assert caps.handoff is not None
        assert caps.orchestration is not None

    def test_create_capabilities_without_extensions_maintains_backward_compatibility(
        self,
    ) -> None:
        """AgentCapabilities should remain backward compatible without extensions."""
        caps = AgentCapabilities(streaming=True, push_notifications=True)

        assert caps.streaming is True
        assert caps.push_notifications is True
        assert caps.handoff is None
        assert caps.orchestration is None

    def test_serialization_with_extensions(self) -> None:
        """AgentCapabilities should serialize with handoff and orchestration."""
        handoff = HandoffCapability(supports_handoff=True)
        orchestration = OrchestrationCapability(can_orchestrate=True)
        caps = AgentCapabilities(handoff=handoff, orchestration=orchestration)

        data = caps.model_dump()

        assert "handoff" in data
        assert "orchestration" in data
        assert data["handoff"]["supports_handoff"] is True
        assert data["orchestration"]["can_orchestrate"] is True
