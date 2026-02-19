"""Tests for conversation models."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omniforge.conversation.models import Conversation, Message, MessageRole


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_message_role_values(self) -> None:
        """MessageRole should have all expected values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

    def test_message_role_is_string_enum(self) -> None:
        """MessageRole should be a string enum."""
        assert isinstance(MessageRole.USER, str)
        assert MessageRole.USER == "user"

    def test_message_role_iteration(self) -> None:
        """MessageRole should be iterable."""
        roles = list(MessageRole)
        assert len(roles) == 3
        assert MessageRole.USER in roles
        assert MessageRole.ASSISTANT in roles
        assert MessageRole.SYSTEM in roles

    def test_message_role_from_string(self) -> None:
        """MessageRole should be creatable from string values."""
        assert MessageRole("user") == MessageRole.USER
        assert MessageRole("assistant") == MessageRole.ASSISTANT
        assert MessageRole("system") == MessageRole.SYSTEM

    def test_message_role_invalid_value_raises_error(self) -> None:
        """MessageRole should raise error for invalid values."""
        with pytest.raises(ValueError):
            MessageRole("invalid_role")


class TestMessage:
    """Tests for Message model."""

    def test_message_creation_minimal(self) -> None:
        """Message should be created with required fields."""
        conv_id = uuid4()
        message = Message(
            conversation_id=conv_id,
            role=MessageRole.USER,
            content="Hello, world!",
        )

        assert isinstance(message.id, UUID)
        assert message.conversation_id == conv_id
        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.created_at, datetime)
        assert message.metadata is None

    def test_message_creation_with_all_fields(self) -> None:
        """Message should be created with all fields."""
        msg_id = uuid4()
        conv_id = uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        metadata = {"source": "api", "version": "1.0"}

        message = Message(
            id=msg_id,
            conversation_id=conv_id,
            role=MessageRole.ASSISTANT,
            content="I can help you with that!",
            created_at=created_at,
            metadata=metadata,
        )

        assert message.id == msg_id
        assert message.conversation_id == conv_id
        assert message.role == MessageRole.ASSISTANT
        assert message.content == "I can help you with that!"
        assert message.created_at == created_at
        assert message.metadata == metadata

    def test_message_auto_generates_id(self) -> None:
        """Message should auto-generate UUID if not provided."""
        message1 = Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="Test",
        )
        message2 = Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="Test",
        )

        assert isinstance(message1.id, UUID)
        assert isinstance(message2.id, UUID)
        assert message1.id != message2.id

    def test_message_auto_sets_created_at(self) -> None:
        """Message should auto-set created_at if not provided."""
        before = datetime.utcnow()
        message = Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="Test",
        )
        after = datetime.utcnow()

        assert before <= message.created_at <= after

    def test_message_missing_required_field_raises_error(self) -> None:
        """Message should raise error if required fields are missing."""
        with pytest.raises(ValidationError) as exc_info:
            Message(
                conversation_id=uuid4(),
                role=MessageRole.USER,
                # Missing content
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("content",)
        assert errors[0]["type"] == "missing"

    def test_message_invalid_role_raises_error(self) -> None:
        """Message should raise error for invalid role."""
        with pytest.raises(ValidationError):
            Message(
                conversation_id=uuid4(),
                role="invalid_role",  # type: ignore
                content="Test",
            )

    def test_message_role_enum_value_used(self) -> None:
        """Message should use enum value for role."""
        message = Message(
            conversation_id=uuid4(),
            role=MessageRole.SYSTEM,
            content="System message",
        )

        # Due to use_enum_values config, role should be string
        assert message.role == "system"

    def test_message_json_serialization(self) -> None:
        """Message should be serializable to JSON."""
        message = Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="Test message",
        )

        json_data = message.model_dump_json()
        assert isinstance(json_data, str)
        assert "Test message" in json_data
        assert "user" in json_data

    def test_message_json_deserialization(self) -> None:
        """Message should be deserializable from JSON."""
        message = Message(
            conversation_id=uuid4(),
            role=MessageRole.USER,
            content="Test message",
        )

        json_data = message.model_dump_json()
        restored = Message.model_validate_json(json_data)

        assert restored.id == message.id
        assert restored.conversation_id == message.conversation_id
        assert restored.role == message.role
        assert restored.content == message.content

    def test_message_with_different_roles(self) -> None:
        """Message should work with all MessageRole values."""
        conv_id = uuid4()

        for role in MessageRole:
            message = Message(
                conversation_id=conv_id,
                role=role,
                content=f"Message from {role}",
            )
            assert message.role == role.value


class TestConversation:
    """Tests for Conversation model."""

    def test_conversation_creation_minimal(self) -> None:
        """Conversation should be created with required fields."""
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
        )

        assert isinstance(conversation.id, UUID)
        assert conversation.tenant_id == "tenant-123"
        assert conversation.user_id == "user-456"
        assert conversation.title is None
        assert isinstance(conversation.created_at, datetime)
        assert isinstance(conversation.updated_at, datetime)
        assert conversation.metadata is None

    def test_conversation_creation_with_all_fields(self) -> None:
        """Conversation should be created with all fields."""
        conv_id = uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        updated_at = datetime(2024, 1, 2, 12, 0, 0)
        metadata = {"tags": ["support", "urgent"], "priority": "high"}

        conversation = Conversation(
            id=conv_id,
            tenant_id="tenant-123",
            user_id="user-456",
            title="Support Request",
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

        assert conversation.id == conv_id
        assert conversation.tenant_id == "tenant-123"
        assert conversation.user_id == "user-456"
        assert conversation.title == "Support Request"
        assert conversation.created_at == created_at
        assert conversation.updated_at == updated_at
        assert conversation.metadata == metadata

    def test_conversation_auto_generates_id(self) -> None:
        """Conversation should auto-generate UUID if not provided."""
        conv1 = Conversation(tenant_id="tenant-1", user_id="user-1")
        conv2 = Conversation(tenant_id="tenant-1", user_id="user-1")

        assert isinstance(conv1.id, UUID)
        assert isinstance(conv2.id, UUID)
        assert conv1.id != conv2.id

    def test_conversation_auto_sets_timestamps(self) -> None:
        """Conversation should auto-set timestamps if not provided."""
        before = datetime.utcnow()
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
        )
        after = datetime.utcnow()

        assert before <= conversation.created_at <= after
        assert before <= conversation.updated_at <= after

    def test_conversation_missing_tenant_id_raises_error(self) -> None:
        """Conversation should raise error if tenant_id is missing."""
        with pytest.raises(ValidationError) as exc_info:
            Conversation(user_id="user-123")  # type: ignore

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("tenant_id",) for error in errors)

    def test_conversation_missing_user_id_raises_error(self) -> None:
        """Conversation should raise error if user_id is missing."""
        with pytest.raises(ValidationError) as exc_info:
            Conversation(tenant_id="tenant-123")  # type: ignore

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("user_id",) for error in errors)

    def test_conversation_with_title(self) -> None:
        """Conversation should support optional title."""
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
            title="My Conversation",
        )

        assert conversation.title == "My Conversation"

    def test_conversation_with_metadata(self) -> None:
        """Conversation should support optional metadata."""
        metadata = {
            "source": "web",
            "campaign": "onboarding",
            "tags": ["new-user"],
        }
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
            metadata=metadata,
        )

        assert conversation.metadata == metadata
        assert conversation.metadata["source"] == "web"
        assert "new-user" in conversation.metadata["tags"]

    def test_conversation_json_serialization(self) -> None:
        """Conversation should be serializable to JSON."""
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
            title="Test Conversation",
        )

        json_data = conversation.model_dump_json()
        assert isinstance(json_data, str)
        assert "tenant-123" in json_data
        assert "user-456" in json_data
        assert "Test Conversation" in json_data

    def test_conversation_json_deserialization(self) -> None:
        """Conversation should be deserializable from JSON."""
        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
            title="Test Conversation",
        )

        json_data = conversation.model_dump_json()
        restored = Conversation.model_validate_json(json_data)

        assert restored.id == conversation.id
        assert restored.tenant_id == conversation.tenant_id
        assert restored.user_id == conversation.user_id
        assert restored.title == conversation.title

    def test_conversation_tenant_isolation_fields(self) -> None:
        """Conversation should have required fields for tenant isolation."""
        conversation = Conversation(
            tenant_id="tenant-abc",
            user_id="user-xyz",
        )

        # These fields are critical for multi-tenancy
        assert conversation.tenant_id == "tenant-abc"
        assert conversation.user_id == "user-xyz"
        assert isinstance(conversation.id, UUID)

    def test_conversation_updated_at_can_differ_from_created_at(self) -> None:
        """Conversation updated_at can be different from created_at."""
        created = datetime(2024, 1, 1, 12, 0, 0)
        updated = datetime(2024, 1, 5, 14, 30, 0)

        conversation = Conversation(
            tenant_id="tenant-123",
            user_id="user-456",
            created_at=created,
            updated_at=updated,
        )

        assert conversation.created_at == created
        assert conversation.updated_at == updated
        assert conversation.updated_at > conversation.created_at
