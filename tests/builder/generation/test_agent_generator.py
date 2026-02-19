"""Tests for AgentGenerator."""

import pytest

from omniforge.builder.generation.agent_generator import AgentGenerator, SkillNeed


class TestAgentGenerator:
    """Tests for AgentGenerator class."""

    def test_single_skill_detection(self) -> None:
        """Test detection of single skill need."""
        generator = AgentGenerator()

        description = "Generate weekly reports from Notion"
        analysis = generator.determine_skills_needed(description)

        assert not analysis.is_multi_skill
        assert len(analysis.skills_needed) == 1
        assert analysis.skills_needed[0].integration == "notion"
        assert analysis.skills_needed[0].order == 1
        assert analysis.confidence >= 0.7

    def test_multi_skill_sequential_detection(self) -> None:
        """Test detection of sequential multi-skill needs."""
        generator = AgentGenerator()

        description = "Fetch data from Notion and then post it to Slack"
        analysis = generator.determine_skills_needed(description)

        assert analysis.is_multi_skill
        assert len(analysis.skills_needed) >= 2
        assert any(s.integration == "notion" for s in analysis.skills_needed)
        assert any(s.integration == "slack" for s in analysis.skills_needed)

    def test_multi_skill_multiple_integrations(self) -> None:
        """Test detection based on multiple integrations."""
        generator = AgentGenerator()

        description = "Sync data between Notion and Slack"
        analysis = generator.determine_skills_needed(description)

        assert analysis.is_multi_skill
        assert len(analysis.skills_needed) >= 2

    def test_skill_ordering(self) -> None:
        """Test that skills are properly ordered."""
        generator = AgentGenerator()

        description = "Get data from Notion and then send to Slack"
        analysis = generator.determine_skills_needed(description)

        orders = [s.order for s in analysis.skills_needed]
        assert orders == sorted(orders)
        assert orders[0] == 1

    def test_data_dependencies_detection(self) -> None:
        """Test detection of data dependencies between skills."""
        generator = AgentGenerator()

        description = "Fetch data from Notion then post it to Slack"
        analysis = generator.determine_skills_needed(description)

        if len(analysis.skills_needed) >= 2:
            # Second skill should have dependency
            second_skill = analysis.skills_needed[1]
            assert len(second_skill.data_dependencies) > 0

    def test_integration_extraction(self) -> None:
        """Test extraction of integration names."""
        generator = AgentGenerator()

        test_cases = [
            ("Work with Notion data", "notion"),
            ("Send Slack messages", "slack"),
            ("Update GitHub issues", "github"),
            ("No integration mentioned", None),
        ]

        for description, expected_integration in test_cases:
            result = generator._extract_integration(description.lower())
            assert result == expected_integration

    def test_action_extraction(self) -> None:
        """Test extraction of primary actions."""
        generator = AgentGenerator()

        description = "fetch data from database"
        action = generator._extract_primary_action(description)

        assert "fetch" in action.lower()

    def test_complex_multi_skill_scenario(self) -> None:
        """Test complex multi-skill scenario."""
        generator = AgentGenerator()

        description = (
            "Generate weekly report from Notion database, "
            "analyze the data, and then post summary to Slack"
        )
        analysis = generator.determine_skills_needed(description)

        assert analysis.is_multi_skill
        assert len(analysis.skills_needed) >= 2
        assert analysis.suggested_flow
        assert "\n" in analysis.suggested_flow

    def test_parallel_keyword_detection(self) -> None:
        """Test detection of parallel action keywords."""
        generator = AgentGenerator()

        description = "Fetch from Notion and also update GitHub"
        analysis = generator.determine_skills_needed(description)

        assert analysis.is_multi_skill

    def test_suggested_flow_formatting(self) -> None:
        """Test suggested flow is properly formatted."""
        generator = AgentGenerator()

        description = "Get data from Notion then post to Slack"
        analysis = generator.determine_skills_needed(description)

        flow = analysis.suggested_flow
        assert flow
        # Should have numbered steps
        assert any(char.isdigit() for char in flow)

    def test_skill_need_model(self) -> None:
        """Test SkillNeed model validation."""
        skill = SkillNeed(
            action="fetch data",
            integration="notion",
            order=1,
            description="Fetch weekly data from Notion",
            data_dependencies=[],
        )

        assert skill.action == "fetch data"
        assert skill.integration == "notion"
        assert skill.order == 1

    def test_skill_need_model_validation(self) -> None:
        """Test SkillNeed model validation fails on invalid data."""
        with pytest.raises(ValueError):
            SkillNeed(
                action="",  # Empty action should fail
                order=1,
                description="Test",
            )

    def test_confidence_score_range(self) -> None:
        """Test confidence score is within valid range."""
        generator = AgentGenerator()

        descriptions = [
            "Generate report from Notion",
            "Fetch from Notion and post to Slack",
            "Do something with data",
        ]

        for desc in descriptions:
            analysis = generator.determine_skills_needed(desc)
            assert 0.0 <= analysis.confidence <= 1.0

    def test_fallback_extraction(self) -> None:
        """Test fallback when detection is ambiguous."""
        generator = AgentGenerator()

        # Vague description
        description = "Do some automation"
        analysis = generator.determine_skills_needed(description)

        # Should still return at least one skill
        assert len(analysis.skills_needed) >= 1

    def test_multiple_action_verbs(self) -> None:
        """Test detection with multiple action verbs."""
        generator = AgentGenerator()

        description = "Fetch, process, analyze, and publish data"
        analysis = generator.determine_skills_needed(description)

        assert analysis.is_multi_skill

    def test_known_integrations_list(self) -> None:
        """Test known integrations list is comprehensive."""
        generator = AgentGenerator()

        common_integrations = ["notion", "slack", "github", "gmail", "sheets"]

        for integration in common_integrations:
            assert integration in generator.KNOWN_INTEGRATIONS

    def test_action_verbs_list(self) -> None:
        """Test action verbs list is comprehensive."""
        generator = AgentGenerator()

        common_verbs = ["fetch", "get", "post", "send", "generate", "create"]

        for verb in common_verbs:
            assert verb in generator.ACTION_VERBS

    def test_empty_description(self) -> None:
        """Test handling of empty description."""
        generator = AgentGenerator()

        description = ""
        analysis = generator.determine_skills_needed(description)

        # Should still return analysis
        assert analysis is not None
        assert len(analysis.skills_needed) >= 1
