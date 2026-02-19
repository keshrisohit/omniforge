"""Agent generator with multi-skill detection."""

import re
from typing import Optional

from pydantic import BaseModel, Field


class SkillNeed(BaseModel):
    """Detected skill need from user description.

    Attributes:
        action: What this skill needs to do (e.g., "generate report", "post message")
        integration: Integration type needed (e.g., "notion", "slack")
        order: Suggested execution order (1-indexed)
        description: Plain language description of what this skill does
        data_dependencies: What data this skill needs from previous skills
    """

    action: str = Field(..., min_length=1, max_length=200)
    integration: Optional[str] = None
    order: int = Field(..., ge=1)
    description: str = Field(..., min_length=1, max_length=500)
    data_dependencies: list[str] = Field(default_factory=list)


class SkillNeedsAnalysis(BaseModel):
    """Result of analyzing user request for skill needs.

    Attributes:
        is_multi_skill: Whether multiple skills are needed
        skills_needed: List of detected skill needs
        suggested_flow: Plain language description of the flow
        confidence: Confidence score (0.0-1.0) in the analysis
    """

    is_multi_skill: bool
    skills_needed: list[SkillNeed]
    suggested_flow: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class AgentGenerator:
    """Generates agent configurations from conversational input.

    Uses rule-based detection to identify multi-skill needs and suggest
    appropriate skill compositions.
    """

    # Keywords indicating sequential multi-skill needs
    SEQUENTIAL_KEYWORDS = [
        r"and then",
        r"after that",
        r"then",
        r"followed by",
        r"next",
        r"afterwards",
        r"subsequently",
    ]

    # Keywords indicating parallel/separate actions
    PARALLEL_KEYWORDS = [
        r"and also",
        r"as well as",
        r"both .* and",
        r"while",
        r"simultaneously",
    ]

    # Common integrations
    KNOWN_INTEGRATIONS = [
        "notion",
        "slack",
        "github",
        "linear",
        "jira",
        "google",
        "drive",
        "sheets",
        "docs",
        "gmail",
        "calendar",
        "trello",
        "asana",
        "airtable",
        "hubspot",
        "salesforce",
    ]

    # Action verbs that typically indicate skill boundaries
    ACTION_VERBS = [
        "fetch",
        "get",
        "retrieve",
        "gather",
        "collect",
        "generate",
        "create",
        "make",
        "build",
        "post",
        "send",
        "publish",
        "share",
        "update",
        "modify",
        "change",
        "delete",
        "remove",
        "analyze",
        "process",
        "transform",
        "format",
        "filter",
        "sort",
        "summarize",
    ]

    def __init__(self) -> None:
        """Initialize agent generator."""
        pass

    def determine_skills_needed(self, user_description: str) -> SkillNeedsAnalysis:
        """Analyze user description to determine skill needs.

        Uses rule-based detection to identify:
        - Single vs multi-skill requirements
        - Integration types needed
        - Skill ordering and dependencies
        - Data flow between skills

        Args:
            user_description: User's natural language description of what they want

        Returns:
            SkillNeedsAnalysis with detected skills and suggested flow
        """
        description_lower = user_description.lower()

        # Detect multi-skill indicators
        is_multi_skill = self._detect_multi_skill(description_lower)

        if not is_multi_skill:
            # Single skill
            skill = self._extract_single_skill(user_description, description_lower)
            return SkillNeedsAnalysis(
                is_multi_skill=False,
                skills_needed=[skill],
                suggested_flow=skill.description,
                confidence=0.8,
            )

        # Multi-skill - extract individual skills
        skills = self._extract_multi_skills(user_description, description_lower)

        # Build suggested flow
        flow_description = self._build_flow_description(skills)

        return SkillNeedsAnalysis(
            is_multi_skill=True,
            skills_needed=skills,
            suggested_flow=flow_description,
            confidence=0.7,
        )

    def _detect_multi_skill(self, description_lower: str) -> bool:
        """Detect if description requires multiple skills.

        Args:
            description_lower: Lowercased user description

        Returns:
            True if multi-skill detected
        """
        # Check for sequential keywords
        for keyword in self.SEQUENTIAL_KEYWORDS:
            if re.search(keyword, description_lower):
                return True

        # Check for parallel keywords
        for keyword in self.PARALLEL_KEYWORDS:
            if re.search(keyword, description_lower):
                return True

        # Check for multiple integrations mentioned
        integrations_found = [
            integration
            for integration in self.KNOWN_INTEGRATIONS
            if integration in description_lower
        ]
        if len(integrations_found) >= 2:
            return True

        # Check for multiple action verbs
        actions_found = [verb for verb in self.ACTION_VERBS if verb in description_lower]
        if len(actions_found) >= 3:
            return True

        return False

    def _extract_single_skill(self, original: str, lower: str) -> SkillNeed:
        """Extract single skill from description.

        Args:
            original: Original user description
            lower: Lowercased description

        Returns:
            Single SkillNeed
        """
        # Extract integration
        integration = self._extract_integration(lower)

        # Extract primary action
        action = self._extract_primary_action(lower)

        # Ensure description is not empty
        description = original.strip() or "Automation task"

        return SkillNeed(
            action=action,
            integration=integration,
            order=1,
            description=description,
            data_dependencies=[],
        )

    def _extract_multi_skills(self, original: str, lower: str) -> list[SkillNeed]:
        """Extract multiple skills from description.

        Args:
            original: Original user description
            lower: Lowercased description

        Returns:
            List of SkillNeed objects
        """
        skills: list[SkillNeed] = []

        # Split by sequential keywords to find skill boundaries
        split_pattern = "|".join(f"({kw})" for kw in self.SEQUENTIAL_KEYWORDS)
        segments = re.split(split_pattern, lower, flags=re.IGNORECASE)

        # Clean segments (remove keywords themselves)
        clean_segments = [
            s.strip()
            for s in segments
            if s and s.strip() not in [kw.replace("\\", "") for kw in self.SEQUENTIAL_KEYWORDS]
        ]

        if len(clean_segments) < 2:
            # Fallback: try to split by action verbs
            clean_segments = self._split_by_actions(lower)

        # Extract skill for each segment
        order = 1
        previous_integration = None

        for segment in clean_segments:
            if not segment or len(segment) < 5:
                continue

            action = self._extract_primary_action(segment)
            integration = self._extract_integration(segment) or previous_integration

            # Determine data dependencies
            dependencies = []
            if order > 1:
                # Check if this segment references previous output
                if any(word in segment for word in ["it", "them", "that", "this", "the result"]):
                    dependencies.append("previous_skill_output")

            skill = SkillNeed(
                action=action,
                integration=integration,
                order=order,
                description=segment.strip(),
                data_dependencies=dependencies,
            )

            skills.append(skill)
            order += 1

            if integration:
                previous_integration = integration

        # If we couldn't extract skills properly, fallback to simple split
        if len(skills) < 2:
            skills = self._fallback_skill_extraction(original, lower)

        return skills

    def _split_by_actions(self, text: str) -> list[str]:
        """Split text by action verbs.

        Args:
            text: Text to split

        Returns:
            List of segments
        """
        segments = []
        current_segment = []
        words = text.split()

        for word in words:
            current_segment.append(word)
            if word in self.ACTION_VERBS:
                # Start new segment after action verb
                if len(current_segment) > 3:
                    segments.append(" ".join(current_segment))
                    current_segment = []

        # Add remaining segment
        if current_segment:
            segments.append(" ".join(current_segment))

        return segments

    def _fallback_skill_extraction(self, original: str, lower: str) -> list[SkillNeed]:
        """Fallback skill extraction when detection fails.

        Args:
            original: Original description
            lower: Lowercased description

        Returns:
            List of SkillNeed objects (minimum 2)
        """
        # Find all integrations
        integrations = [i for i in self.KNOWN_INTEGRATIONS if i in lower]

        if len(integrations) >= 2:
            # Create one skill per integration
            skills = []
            for order, integration in enumerate(integrations, 1):
                skills.append(
                    SkillNeed(
                        action=f"process {integration} data",
                        integration=integration,
                        order=order,
                        description=f"Work with {integration}",
                        data_dependencies=["previous_skill_output"] if order > 1 else [],
                    )
                )
            return skills

        # Last resort: split in half
        mid = len(original) // 2
        first_half = original[:mid].strip()
        second_half = original[mid:].strip()

        return [
            SkillNeed(
                action="first task",
                integration=self._extract_integration(lower),
                order=1,
                description=first_half,
                data_dependencies=[],
            ),
            SkillNeed(
                action="second task",
                integration=self._extract_integration(lower),
                order=2,
                description=second_half,
                data_dependencies=["previous_skill_output"],
            ),
        ]

    def _extract_integration(self, text: str) -> Optional[str]:
        """Extract integration type from text.

        Args:
            text: Text to analyze

        Returns:
            Integration name if found, None otherwise
        """
        for integration in self.KNOWN_INTEGRATIONS:
            if integration in text:
                return integration
        return None

    def _extract_primary_action(self, text: str) -> str:
        """Extract primary action from text.

        Args:
            text: Text to analyze

        Returns:
            Action verb or description
        """
        # Find first action verb
        for verb in self.ACTION_VERBS:
            if verb in text:
                # Extract surrounding context (up to 5 words)
                words = text.split()
                try:
                    verb_idx = words.index(verb)
                    context_start = max(0, verb_idx - 1)
                    context_end = min(len(words), verb_idx + 4)
                    return " ".join(words[context_start:context_end])
                except ValueError:
                    continue

        # Fallback: return first few words
        words = text.split()
        return " ".join(words[:5]) if words else "process data"

    def _build_flow_description(self, skills: list[SkillNeed]) -> str:
        """Build plain language flow description.

        Args:
            skills: List of skills

        Returns:
            Plain language description of the flow
        """
        descriptions = []

        for i, skill in enumerate(skills, 1):
            prefix = f"{i}. "
            action_desc = skill.action.capitalize()

            if skill.integration:
                desc = f"{prefix}{action_desc} from {skill.integration.capitalize()}"
            else:
                desc = f"{prefix}{action_desc}"

            descriptions.append(desc)

        return "\n".join(descriptions)
