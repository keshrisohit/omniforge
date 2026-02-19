"""Tests for PromptConfig dataclass."""

from omniforge.prompts import MergeBehavior
from omniforge.prompts.sdk import PromptConfig


class TestPromptConfig:
    """Tests for PromptConfig dataclass."""

    def test_create_minimal(self) -> None:
        """Should create PromptConfig with minimal parameters."""
        config = PromptConfig(agent_prompt="You are a helpful assistant.")

        assert config.agent_prompt == "You are a helpful assistant."
        assert config.variables == {}
        assert config.merge_behavior == {}

    def test_create_with_variables(self) -> None:
        """Should create PromptConfig with variables."""
        config = PromptConfig(
            agent_prompt="Hello {{ name }}",
            variables={"name": "World"},
        )

        assert config.agent_prompt == "Hello {{ name }}"
        assert config.variables == {"name": "World"}

    def test_create_with_merge_behavior(self) -> None:
        """Should create PromptConfig with merge behavior."""
        config = PromptConfig(
            agent_prompt="Instructions",
            merge_behavior={"context": MergeBehavior.APPEND},
        )

        assert config.agent_prompt == "Instructions"
        assert config.merge_behavior == {"context": MergeBehavior.APPEND}

    def test_create_with_all_parameters(self) -> None:
        """Should create PromptConfig with all parameters."""
        config = PromptConfig(
            agent_prompt="You are {{ role }}. {{ instructions }}",
            variables={"role": "a helpful assistant", "instructions": "Be concise."},
            merge_behavior={
                "context": MergeBehavior.APPEND,
                "examples": MergeBehavior.PREPEND,
            },
        )

        assert config.agent_prompt == "You are {{ role }}. {{ instructions }}"
        assert len(config.variables) == 2
        assert config.variables["role"] == "a helpful assistant"
        assert config.variables["instructions"] == "Be concise."
        assert len(config.merge_behavior) == 2
        assert config.merge_behavior["context"] == MergeBehavior.APPEND
        assert config.merge_behavior["examples"] == MergeBehavior.PREPEND
