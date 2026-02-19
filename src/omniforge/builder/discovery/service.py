"""Skill discovery service for conversation-based recommendations."""

from typing import Optional

from pydantic import BaseModel

from omniforge.builder.models import PublicSkill
from omniforge.builder.repository import PublicSkillRepository


class SkillRecommendation(BaseModel):
    """Skill recommendation for conversation context.

    Attributes:
        skill: The recommended public skill
        relevance_score: Relevance score (0.0-1.0)
        reason: Human-readable explanation of why skill was recommended
    """

    skill: PublicSkill
    relevance_score: float
    reason: str


class SkillDiscoveryService:
    """Service for discovering and recommending public skills.

    Provides intelligent skill recommendations based on conversation context,
    user requirements, and integration needs.
    """

    def __init__(self, repository: PublicSkillRepository) -> None:
        """Initialize discovery service.

        Args:
            repository: PublicSkillRepository for querying skills
        """
        self._repo = repository

    async def discover_by_context(
        self,
        description: str,
        integrations: Optional[list[str]] = None,
        limit: int = 5,
    ) -> list[SkillRecommendation]:
        """Discover skills based on conversation context.

        Searches for relevant public skills that match the user's
        description and required integrations.

        Args:
            description: User's description of what they want to do
            integrations: Required integrations (e.g., ["notion", "slack"])
            limit: Maximum number of recommendations

        Returns:
            List of SkillRecommendation objects ordered by relevance
        """
        recommendations: list[SkillRecommendation] = []

        # Extract keywords from description (simple word extraction)
        keywords = self._extract_keywords(description)

        # Search by keywords
        for keyword in keywords[:3]:  # Use top 3 keywords
            skills = await self._repo.search(keyword=keyword, limit=limit * 2)

            for skill in skills:
                # Skip if already recommended
                if any(r.skill.id == skill.id for r in recommendations):
                    continue

                # Calculate relevance score
                relevance = self._calculate_relevance(
                    skill=skill,
                    description=description,
                    required_integrations=integrations,
                )

                # Generate reason
                reason = self._generate_reason(
                    skill=skill,
                    matched_keyword=keyword,
                    integrations=integrations,
                )

                recommendations.append(
                    SkillRecommendation(
                        skill=skill,
                        relevance_score=relevance,
                        reason=reason,
                    )
                )

        # If integrations specified, prioritize skills with matching integrations
        if integrations:
            for integration in integrations:
                skills = await self._repo.get_by_integration(
                    integration=integration,
                    limit=limit,
                )

                for skill in skills:
                    # Skip if already recommended
                    if any(r.skill.id == skill.id for r in recommendations):
                        continue

                    relevance = self._calculate_relevance(
                        skill=skill,
                        description=description,
                        required_integrations=integrations,
                    )

                    reason = f"Uses {integration} integration, highly popular"

                    recommendations.append(
                        SkillRecommendation(
                            skill=skill,
                            relevance_score=relevance,
                            reason=reason,
                        )
                    )

        # Sort by relevance score and limit
        recommendations.sort(key=lambda r: r.relevance_score, reverse=True)
        return recommendations[:limit]

    async def discover_by_integration(
        self,
        integration: str,
        limit: int = 10,
    ) -> list[PublicSkill]:
        """Discover skills for a specific integration.

        Args:
            integration: Integration type (e.g., "notion", "slack")
            limit: Maximum number of results

        Returns:
            List of PublicSkill objects ordered by popularity
        """
        return await self._repo.get_by_integration(
            integration=integration,
            limit=limit,
        )

    async def get_popular_skills(self, limit: int = 10) -> list[PublicSkill]:
        """Get most popular public skills.

        Args:
            limit: Maximum number of results

        Returns:
            List of PublicSkill objects ordered by usage_count DESC
        """
        return await self._repo.get_top_skills(limit=limit)

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text.

        Simple implementation that splits on spaces and filters short words.
        More sophisticated NLP could be added later.

        Args:
            text: Input text

        Returns:
            List of keywords
        """
        # Convert to lowercase and split
        words = text.lower().split()

        # Filter out common words and short words
        stop_words = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "from",
            "by",
            "i",
            "want",
            "need",
            "create",
            "make",
            "build",
        }

        keywords = [
            word.strip(".,!?;:") for word in words if len(word) > 3 and word not in stop_words
        ]

        return keywords

    def _calculate_relevance(
        self,
        skill: PublicSkill,
        description: str,
        required_integrations: Optional[list[str]] = None,
    ) -> float:
        """Calculate relevance score for a skill.

        Args:
            skill: PublicSkill to score
            description: User's description
            required_integrations: Required integrations

        Returns:
            Relevance score (0.0-1.0)
        """
        score = 0.0

        # Base score from usage count (normalize to 0.0-0.3)
        usage_score = min(skill.usage_count / 100.0, 0.3)
        score += usage_score

        # Rating contribution (0.0-0.2)
        rating_score = (skill.rating_avg / 5.0) * 0.2
        score += rating_score

        # Keyword match in name (0.0-0.25)
        description_lower = description.lower()
        if any(word in description_lower for word in skill.name.lower().split("-")):
            score += 0.25

        # Keyword match in description (0.0-0.15)
        skill_desc_words = set(skill.description.lower().split())
        user_words = set(description_lower.split())
        overlap = len(skill_desc_words.intersection(user_words))
        if overlap > 0:
            score += min(overlap * 0.03, 0.15)

        # Integration match (0.0-0.2)
        if required_integrations:
            matching_integrations = set(skill.integrations).intersection(
                set(i.lower() for i in required_integrations)
            )
            if matching_integrations:
                score += 0.2 * (len(matching_integrations) / len(required_integrations))

        return min(score, 1.0)

    def _generate_reason(
        self,
        skill: PublicSkill,
        matched_keyword: Optional[str] = None,
        integrations: Optional[list[str]] = None,
    ) -> str:
        """Generate human-readable reason for recommendation.

        Args:
            skill: PublicSkill being recommended
            matched_keyword: Keyword that matched
            integrations: Required integrations

        Returns:
            Explanation string
        """
        reasons = []

        # Usage popularity
        if skill.usage_count > 50:
            reasons.append(f"used {skill.usage_count} times")
        elif skill.usage_count > 10:
            reasons.append("popular choice")

        # Rating
        if skill.rating_avg >= 4.5:
            reasons.append(f"highly rated ({skill.rating_avg:.1f}/5.0)")
        elif skill.rating_avg >= 4.0:
            reasons.append(f"well rated ({skill.rating_avg:.1f}/5.0)")

        # Keyword match
        if matched_keyword:
            reasons.append(f"matches '{matched_keyword}'")

        # Integration match
        if integrations:
            matching = set(skill.integrations).intersection(set(i.lower() for i in integrations))
            if matching:
                reasons.append(f"supports {', '.join(matching)}")

        if not reasons:
            return "Relevant to your request"

        return ", ".join(reasons).capitalize()
