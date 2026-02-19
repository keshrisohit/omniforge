"""Skill suggestion integration for conversation flow."""

from typing import Optional

from omniforge.builder.discovery.service import SkillDiscoveryService, SkillRecommendation
from omniforge.builder.generation.agent_generator import SkillNeed
from omniforge.builder.models import PublicSkill


class SkillSuggestionManager:
    """Manages skill suggestions during conversation.

    Integrates AgentGenerator's skill needs analysis with PublicSkillRepository's
    discovery service to suggest relevant public skills.
    """

    def __init__(self, discovery_service: SkillDiscoveryService) -> None:
        """Initialize skill suggestion manager.

        Args:
            discovery_service: SkillDiscoveryService for querying public skills
        """
        self._discovery = discovery_service

    async def suggest_skills_for_need(
        self,
        skill_need: SkillNeed,
        limit: int = 3,
    ) -> list[SkillRecommendation]:
        """Suggest public skills for a detected skill need.

        Args:
            skill_need: Detected skill need from AgentGenerator
            limit: Maximum number of suggestions

        Returns:
            List of SkillRecommendation objects ordered by relevance
        """
        # Build search query from skill need
        search_description = f"{skill_need.action} {skill_need.description}"

        # Determine integrations filter
        integrations = [skill_need.integration] if skill_need.integration else None

        # Discover matching public skills
        recommendations = await self._discovery.discover_by_context(
            description=search_description,
            integrations=integrations,
            limit=limit,
        )

        return recommendations

    async def suggest_skills_for_all_needs(
        self,
        skill_needs: list[SkillNeed],
        limit_per_need: int = 2,
    ) -> dict[int, list[SkillRecommendation]]:
        """Suggest public skills for multiple skill needs.

        Args:
            skill_needs: List of detected skill needs
            limit_per_need: Maximum suggestions per need

        Returns:
            Dict mapping skill need order to list of recommendations
        """
        suggestions: dict[int, list[SkillRecommendation]] = {}

        for need in skill_needs:
            recommendations = await self.suggest_skills_for_need(
                skill_need=need,
                limit=limit_per_need,
            )
            suggestions[need.order] = recommendations

        return suggestions

    async def suggest_by_integration(
        self,
        integration: str,
        limit: int = 5,
    ) -> list[PublicSkill]:
        """Suggest popular public skills for an integration.

        Args:
            integration: Integration type (e.g., "notion", "slack")
            limit: Maximum number of suggestions

        Returns:
            List of PublicSkill objects ordered by popularity
        """
        return await self._discovery.discover_by_integration(
            integration=integration,
            limit=limit,
        )

    def format_recommendations_for_display(
        self,
        recommendations: list[SkillRecommendation],
    ) -> list[dict[str, str]]:
        """Format recommendations for conversation display.

        Args:
            recommendations: List of SkillRecommendation objects

        Returns:
            List of dicts with name, description, reason
        """
        return [
            {
                "name": rec.skill.name,
                "description": rec.skill.description,
                "reason": rec.reason,
                "id": rec.skill.id,
            }
            for rec in recommendations
        ]

    async def get_skill_by_id(self, skill_id: str) -> Optional[PublicSkill]:
        """Get public skill by ID.

        Args:
            skill_id: Skill ID

        Returns:
            PublicSkill if found, None otherwise
        """
        # Note: discovery service doesn't expose get_by_id directly,
        # so we need to access the repository
        return await self._discovery._repo.get_by_id(skill_id)

    def match_user_selection(
        self,
        user_input: str,
        available_skills: list[dict[str, str]],
    ) -> list[str]:
        """Parse user selection of skills.

        Args:
            user_input: User's selection (e.g., "1,3" or "none" or "all")
            available_skills: List of available skill dicts

        Returns:
            List of selected skill IDs
        """
        input_lower = user_input.lower().strip()

        # Handle special cases
        if "none" in input_lower or "no" in input_lower:
            return []

        if "all" in input_lower:
            return [skill["id"] for skill in available_skills]

        # Parse comma-separated numbers
        selected_ids = []
        parts = input_lower.split(",")

        for part in parts:
            part = part.strip()
            if part.isdigit():
                index = int(part) - 1  # Convert to 0-indexed
                if 0 <= index < len(available_skills):
                    selected_ids.append(available_skills[index]["id"])

        return selected_ids

    def build_mixed_skills_summary(
        self,
        public_skill_ids: list[str],
        custom_skill_needs: list[SkillNeed],
        all_public_skills: list[PublicSkill],
    ) -> tuple[list[str], list[str]]:
        """Build summary of mixed public and custom skills.

        Args:
            public_skill_ids: Selected public skill IDs
            custom_skill_needs: Remaining needs for custom skills
            all_public_skills: All available public skills for lookup

        Returns:
            Tuple of (public_skill_names, custom_skill_descriptions)
        """
        # Get public skill names
        public_names = []
        for skill_id in public_skill_ids:
            skill = next((s for s in all_public_skills if s.id == skill_id), None)
            if skill:
                public_names.append(skill.name)

        # Get custom skill descriptions
        custom_descriptions = [need.description for need in custom_skill_needs]

        return public_names, custom_descriptions
