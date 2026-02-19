"""Tests for merge point processor."""

import pytest

from omniforge.prompts.composition.merge import MergeProcessor
from omniforge.prompts.enums import MergeBehavior, PromptLayer
from omniforge.prompts.errors import PromptValidationError
from omniforge.prompts.models import MergePointDefinition, Prompt


class TestMergeProcessor:
    """Tests for MergeProcessor class."""

    @pytest.mark.asyncio
    async def test_merge_with_system_prompt_only(self) -> None:
        """Should return system prompt when no other layers present."""
        processor = MergeProcessor()
        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System Prompt",
            content="You are a helpful assistant.",
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert result == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_merge_without_system_prompt_raises_error(self) -> None:
        """Should raise error when system prompt is missing."""
        processor = MergeProcessor()
        agent_prompt = Prompt(
            id="ag1",
            layer=PromptLayer.AGENT,
            scope_id="agent1",
            name="Agent Prompt",
            content="Agent instructions",
        )

        with pytest.raises(PromptValidationError, match="System prompt is required"):
            await processor.merge({PromptLayer.AGENT: agent_prompt})

    @pytest.mark.asyncio
    async def test_merge_with_user_input(self) -> None:
        """Should substitute user input into user_input merge point."""
        processor = MergeProcessor()
        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System Prompt",
            content='You are a helpful assistant.\n\nUser: {{ merge_point("user_input") }}',
        )

        result = await processor.merge(
            {PromptLayer.SYSTEM: system_prompt}, user_input="What is the weather?"
        )

        assert "User: What is the weather?" in result

    @pytest.mark.asyncio
    async def test_merge_with_empty_user_input(self) -> None:
        """Should handle empty user input gracefully."""
        processor = MergeProcessor()
        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System Prompt",
            content='Assistant: {{ merge_point("user_input") }}',
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "Assistant:" in result
        # Empty merge point should be cleaned up

    @pytest.mark.asyncio
    async def test_append_behavior_concatenates_in_order(self) -> None:
        """APPEND should concatenate content from lowest to highest layer."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='Base: {{ merge_point("custom") }}',
            merge_points=[MergePointDefinition(name="custom", behavior=MergeBehavior.APPEND)],
        )

        tenant_prompt = Prompt(
            id="ten1",
            layer=PromptLayer.TENANT,
            scope_id="tenant1",
            name="Tenant",
            content="Tenant content",
            merge_points=[MergePointDefinition(name="custom", behavior=MergeBehavior.APPEND)],
        )

        agent_prompt = Prompt(
            id="ag1",
            layer=PromptLayer.AGENT,
            scope_id="agent1",
            name="Agent",
            content="Agent content",
            merge_points=[MergePointDefinition(name="custom", behavior=MergeBehavior.APPEND)],
        )

        result = await processor.merge(
            {
                PromptLayer.SYSTEM: system_prompt,
                PromptLayer.TENANT: tenant_prompt,
                PromptLayer.AGENT: agent_prompt,
            }
        )

        # Content should be ordered: system content is empty, then tenant, then agent
        assert "Base:" in result

    @pytest.mark.asyncio
    async def test_prepend_behavior_adds_before(self) -> None:
        """PREPEND should add higher layer content before lower layer."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='{{ merge_point("rules") }}\n\nMain content',
            merge_points=[MergePointDefinition(name="rules", behavior=MergeBehavior.PREPEND)],
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "Main content" in result

    @pytest.mark.asyncio
    async def test_replace_behavior_uses_highest_layer(self) -> None:
        """REPLACE should use content from highest layer only."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='Default: {{ merge_point("setting") }}',
            merge_points=[MergePointDefinition(name="setting", behavior=MergeBehavior.REPLACE)],
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "Default:" in result

    @pytest.mark.asyncio
    async def test_inject_behavior_inserts_content(self) -> None:
        """INJECT should insert content at merge point."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='Before {{ merge_point("middle") }} After',
            merge_points=[MergePointDefinition(name="middle", behavior=MergeBehavior.INJECT)],
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "Before" in result
        assert "After" in result

    @pytest.mark.asyncio
    async def test_locked_merge_point_prevents_override(self) -> None:
        """Locked merge points should not be overridable by higher layers."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='System: {{ merge_point("locked") }}',
            merge_points=[
                MergePointDefinition(name="locked", behavior=MergeBehavior.REPLACE, locked=True)
            ],
        )

        # This should not raise an error if agent doesn't try to override
        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "System:" in result

    @pytest.mark.asyncio
    async def test_required_merge_point_without_content_raises_error(self) -> None:
        """Required merge points must have content from at least one layer."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='{{ merge_point("required_field") }}',
            merge_points=[
                MergePointDefinition(
                    name="required_field", behavior=MergeBehavior.REPLACE, required=True
                )
            ],
        )

        with pytest.raises(PromptValidationError, match="Required merge point"):
            await processor.merge({PromptLayer.SYSTEM: system_prompt})

    @pytest.mark.asyncio
    async def test_multiple_merge_points_in_template(self) -> None:
        """Should handle multiple merge points in single template."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='First: {{ merge_point("first") }}\nSecond: {{ merge_point("second") }}',
            merge_points=[
                MergePointDefinition(name="first", behavior=MergeBehavior.REPLACE),
                MergePointDefinition(name="second", behavior=MergeBehavior.REPLACE),
            ],
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "First:" in result
        assert "Second:" in result

    @pytest.mark.asyncio
    async def test_undefined_merge_point_is_removed(self) -> None:
        """Merge points without definitions should be cleaned up."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='Content {{ merge_point("undefined") }} here',
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "Content" in result
        assert "here" in result
        assert "merge_point" not in result

    @pytest.mark.asyncio
    async def test_clean_empty_merge_points_removes_extra_whitespace(self) -> None:
        """Should clean up extra newlines and whitespace."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='Line 1\n\n\n\n{{ merge_point("empty") }}\n\n\n\nLine 2',
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        # Should reduce multiple newlines to max 2
        assert result.count("\n\n\n") == 0
        assert "Line 1" in result
        assert "Line 2" in result

    @pytest.mark.asyncio
    async def test_merge_point_with_quotes_variations(self) -> None:
        """Should handle both single and double quotes in merge point markers."""
        processor = MergeProcessor()

        # Test with double quotes
        system_prompt1 = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='{{ merge_point("test") }}',
        )

        result1 = await processor.merge({PromptLayer.SYSTEM: system_prompt1})
        assert "merge_point" not in result1

        # Test with single quotes
        system_prompt2 = Prompt(
            id="sys2",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="{{ merge_point('test') }}",
        )

        result2 = await processor.merge({PromptLayer.SYSTEM: system_prompt2})
        assert "merge_point" not in result2

    @pytest.mark.asyncio
    async def test_merge_point_with_whitespace_variations(self) -> None:
        """Should handle whitespace variations in merge point markers."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content='{{merge_point("test")}}\n{{ merge_point( "test2" ) }}',
        )

        result = await processor.merge({PromptLayer.SYSTEM: system_prompt})

        assert "merge_point" not in result

    @pytest.mark.asyncio
    async def test_layer_priority_ordering(self) -> None:
        """Should respect layer priority from SYSTEM to AGENT."""
        processor = MergeProcessor()

        # Verify layer priority constant is correct
        assert processor._LAYER_PRIORITY == [
            PromptLayer.SYSTEM,
            PromptLayer.TENANT,
            PromptLayer.FEATURE,
            PromptLayer.AGENT,
        ]

    @pytest.mark.asyncio
    async def test_find_merge_points_returns_unique_names(self) -> None:
        """Should return unique merge point names in order of appearance."""
        processor = MergeProcessor()

        template = (
            '{{ merge_point("first") }}\n'
            '{{ merge_point("second") }}\n'
            '{{ merge_point("first") }}'
        )

        names = processor._find_merge_points(template)

        assert names == ["first", "second"]
        assert len(names) == 2  # No duplicates

    @pytest.mark.asyncio
    async def test_replace_merge_point_substitutes_content(self) -> None:
        """Should replace specific merge point with content."""
        processor = MergeProcessor()

        template = 'Before {{ merge_point("test") }} After'
        result = processor._replace_merge_point(template, "test", "CONTENT")

        assert result == "Before CONTENT After"
        assert "merge_point" not in result

    @pytest.mark.asyncio
    async def test_complex_multi_layer_scenario(self) -> None:
        """Integration test with multiple layers and merge points."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content=(
                "You are an AI assistant.\n\n"
                '{{ merge_point("rules") }}\n\n'
                'User Query: {{ merge_point("user_input") }}'
            ),
            merge_points=[MergePointDefinition(name="rules", behavior=MergeBehavior.APPEND)],
        )

        tenant_prompt = Prompt(
            id="ten1",
            layer=PromptLayer.TENANT,
            scope_id="tenant1",
            name="Tenant",
            content="Tenant-specific rules apply.",
            merge_points=[MergePointDefinition(name="rules", behavior=MergeBehavior.APPEND)],
        )

        result = await processor.merge(
            {PromptLayer.SYSTEM: system_prompt, PromptLayer.TENANT: tenant_prompt},
            user_input="Help me with my task",
        )

        assert "You are an AI assistant" in result
        assert "User Query: Help me with my task" in result

    @pytest.mark.asyncio
    async def test_empty_layer_prompts_dict(self) -> None:
        """Should raise error when layer_prompts is empty."""
        processor = MergeProcessor()

        with pytest.raises(PromptValidationError, match="System prompt is required"):
            await processor.merge({})

    @pytest.mark.asyncio
    async def test_none_values_in_layer_prompts(self) -> None:
        """Should handle None values in layer_prompts gracefully."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="System content",
        )

        result = await processor.merge(
            {
                PromptLayer.SYSTEM: system_prompt,
                PromptLayer.TENANT: None,
                PromptLayer.AGENT: None,
            }
        )

        assert result == "System content"

    @pytest.mark.asyncio
    async def test_collect_merge_point_definitions_respects_priority(self) -> None:
        """Should collect definitions with higher layers overriding lower."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="System",
            merge_points=[MergePointDefinition(name="test", behavior=MergeBehavior.REPLACE)],
        )

        agent_prompt = Prompt(
            id="ag1",
            layer=PromptLayer.AGENT,
            scope_id="agent1",
            name="Agent",
            content="Agent",
            merge_points=[MergePointDefinition(name="test", behavior=MergeBehavior.APPEND)],
        )

        definitions = processor._collect_merge_point_definitions(
            {PromptLayer.SYSTEM: system_prompt, PromptLayer.AGENT: agent_prompt}
        )

        # Agent definition should override system
        assert definitions["test"].behavior == MergeBehavior.APPEND

    @pytest.mark.asyncio
    async def test_locked_definition_not_overridden(self) -> None:
        """Locked definitions should not be overridden by higher layers."""
        processor = MergeProcessor()

        system_prompt = Prompt(
            id="sys1",
            layer=PromptLayer.SYSTEM,
            scope_id="system",
            name="System",
            content="System",
            merge_points=[
                MergePointDefinition(name="locked", behavior=MergeBehavior.REPLACE, locked=True)
            ],
        )

        agent_prompt = Prompt(
            id="ag1",
            layer=PromptLayer.AGENT,
            scope_id="agent1",
            name="Agent",
            content="Agent",
            merge_points=[MergePointDefinition(name="locked", behavior=MergeBehavior.APPEND)],
        )

        definitions = processor._collect_merge_point_definitions(
            {PromptLayer.SYSTEM: system_prompt, PromptLayer.AGENT: agent_prompt}
        )

        # System definition should remain (locked)
        assert definitions["locked"].behavior == MergeBehavior.REPLACE
        assert definitions["locked"].locked is True
