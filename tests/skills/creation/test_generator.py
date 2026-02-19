"""Tests for SKILL.md generator.

This module tests the SkillMdGenerator class to ensure it generates SKILL.md
content that strictly follows official Anthropic Agent Skills format.
"""

import pytest
import yaml

from omniforge.skills.creation.generator import SkillMdGenerator
from omniforge.skills.creation.models import (
    ConversationContext,
    ConversationState,
    SkillCapabilities,
)


class MockLLMGenerator:
    """Mock LLM generator for testing."""

    def __init__(self, response: str) -> None:
        """Initialize mock with canned response.

        Args:
            response: Response to return from generate_stream
        """
        self.response = response

    async def generate_stream(self, message: str) -> list[str]:
        """Mock streaming response.

        Args:
            message: Input message (unused in mock)

        Yields:
            Response chunks
        """
        # Yield response in small chunks to simulate streaming
        chunk_size = 50
        for i in range(0, len(self.response), chunk_size):
            yield self.response[i : i + chunk_size]


@pytest.fixture
def mock_llm() -> MockLLMGenerator:
    """Create mock LLM generator with default response.

    Returns:
        Mock LLM generator
    """
    body_content = """# Format Product Names

This skill formats product names into their full display form.

## When to Use

Use this skill when writing documentation or customer-facing content where
product abbreviations need to be expanded consistently.

## Instructions

1. Identify abbreviated product names in the input text
2. Expand abbreviations according to official product naming
3. Maintain consistent capitalization and spacing
4. Preserve original context and sentence structure

## Examples

Input: "Check the API docs"
Output: "Check the Application Programming Interface documentation"
"""
    return MockLLMGenerator(body_content)


@pytest.fixture
def sample_context() -> ConversationContext:
    """Create sample conversation context.

    Returns:
        Sample context for testing
    """
    return ConversationContext(
        state=ConversationState.GENERATING,
        skill_name="format-product-names",
        skill_description=(
            "Formats product names into their full display form when writing "
            "documentation. Use when abbreviations need expansion."
        ),
        skill_purpose="Expand product abbreviations consistently",
        skill_capabilities=SkillCapabilities(
            needs_file_operations=False,
            needs_external_knowledge=True,
            needs_script_execution=False,
            needs_multi_step_workflow=False,
        ),
        examples=["API -> Application Programming Interface"],
        triggers=["Writing documentation", "Customer-facing content"],
    )


@pytest.mark.asyncio
async def test_generate_complete_skill_md(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test generating complete SKILL.md with frontmatter and body.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    generator = SkillMdGenerator(mock_llm)
    content = await generator.generate(sample_context)

    # Verify structure
    assert content.startswith("---\n")
    assert "---\n\n#" in content or "---\n#" in content

    # Verify frontmatter exists
    frontmatter_end = content.find("---", 4)
    assert frontmatter_end > 0

    # Verify body exists
    body_start = frontmatter_end + 3
    assert len(content[body_start:].strip()) > 0


@pytest.mark.asyncio
async def test_generate_frontmatter_only_two_fields(sample_context: ConversationContext) -> None:
    """Test that frontmatter contains ONLY name and description fields.

    Args:
        sample_context: Sample context
    """
    generator = SkillMdGenerator(MockLLMGenerator("# Test\n\nBody content"))
    frontmatter = generator.generate_frontmatter(sample_context)

    # Parse YAML frontmatter
    yaml_content = frontmatter.strip("---\n")
    parsed = yaml.safe_load(yaml_content)

    # Verify ONLY name and description fields
    assert set(parsed.keys()) == {"name", "description"}
    assert parsed["name"] == "format-product-names"
    assert parsed["description"] == (
        "Formats product names into their full display form when writing "
        "documentation. Use when abbreviations need expansion."
    )


@pytest.mark.asyncio
async def test_generate_frontmatter_validates_name(sample_context: ConversationContext) -> None:
    """Test that frontmatter generation validates name format.

    Args:
        sample_context: Sample context
    """
    generator = SkillMdGenerator(MockLLMGenerator("# Test"))

    # Invalid name should raise error
    sample_context.skill_name = "InvalidName"
    with pytest.raises(ValueError, match="Invalid skill name format"):
        generator.generate_frontmatter(sample_context)


@pytest.mark.asyncio
async def test_generate_body_under_500_lines(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test that generated body is under 500 lines.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    generator = SkillMdGenerator(mock_llm)
    body = await generator.generate_body(sample_context)

    line_count = len(body.split("\n"))
    assert line_count < 500


@pytest.mark.asyncio
async def test_generate_body_exceeds_limit_raises_error(
    sample_context: ConversationContext,
) -> None:
    """Test that body exceeding 500 lines raises error.

    Args:
        sample_context: Sample context
    """
    # Create mock that returns 501 lines
    long_body = "\n".join([f"Line {i}" for i in range(501)])
    mock_llm = MockLLMGenerator(long_body)

    generator = SkillMdGenerator(mock_llm)

    with pytest.raises(ValueError, match="exceeds 500 line limit"):
        await generator.generate_body(sample_context)


def test_validate_name_format_valid() -> None:
    """Test validation of valid skill names."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    # Valid names
    valid_names = [
        "format-product-names",
        "data-validation",
        "processing-orders",
        "a",
        "test-123",
    ]

    for name in valid_names:
        is_valid, error = generator.validate_name_format(name)
        assert is_valid is True, f"Name '{name}' should be valid"
        assert error is None


def test_validate_name_format_invalid_uppercase() -> None:
    """Test validation rejects uppercase letters."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    is_valid, error = generator.validate_name_format("Format-Names")
    assert is_valid is False
    assert error is not None
    assert "lowercase" in error.lower()


def test_validate_name_format_invalid_special_chars() -> None:
    """Test validation rejects special characters."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    invalid_names = [
        "format_names",  # underscore
        "format.names",  # period
        "format names",  # space
        "format@names",  # special char
    ]

    for name in invalid_names:
        is_valid, error = generator.validate_name_format(name)
        assert is_valid is False, f"Name '{name}' should be invalid"
        assert error is not None


def test_validate_name_format_invalid_start() -> None:
    """Test validation rejects names not starting with lowercase letter."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    invalid_names = [
        "-format-names",  # starts with hyphen
        "1format-names",  # starts with number
        "Format-names",  # starts with uppercase
    ]

    for name in invalid_names:
        is_valid, error = generator.validate_name_format(name)
        assert is_valid is False, f"Name '{name}' should be invalid"
        assert error is not None


def test_validate_name_format_invalid_length() -> None:
    """Test validation rejects names exceeding 64 characters."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    # 65 character name
    long_name = "a" * 65
    is_valid, error = generator.validate_name_format(long_name)
    assert is_valid is False
    assert "1-64 characters" in error

    # Empty name
    is_valid, error = generator.validate_name_format("")
    assert is_valid is False


def test_validate_name_format_invalid_consecutive_hyphens() -> None:
    """Test validation rejects consecutive hyphens."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    is_valid, error = generator.validate_name_format("format--names")
    assert is_valid is False
    assert "consecutive hyphens" in error


def test_validate_name_format_invalid_trailing_hyphen() -> None:
    """Test validation rejects trailing hyphen."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    is_valid, error = generator.validate_name_format("format-names-")
    assert is_valid is False
    assert "end with a hyphen" in error


@pytest.mark.asyncio
async def test_generate_missing_required_fields(mock_llm: MockLLMGenerator) -> None:
    """Test that generate raises error if required fields missing.

    Args:
        mock_llm: Mock LLM generator
    """
    generator = SkillMdGenerator(mock_llm)

    # Missing skill_name
    context = ConversationContext(skill_description="Some description")
    with pytest.raises(ValueError, match="skill_name and skill_description"):
        await generator.generate(context)

    # Missing skill_description
    context = ConversationContext(skill_name="test-skill")
    with pytest.raises(ValueError, match="skill_name and skill_description"):
        await generator.generate(context)


@pytest.mark.asyncio
async def test_strip_unauthorized_frontmatter() -> None:
    """Test stripping unauthorized fields from frontmatter."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    # Content with extra frontmatter fields
    content = """---
name: test-skill
description: Test description
author: John Doe
version: 1.0.0
tags: [test, example]
---

# Test Skill

Body content here.
"""

    cleaned = generator._strip_unauthorized_frontmatter(content)

    # Parse cleaned frontmatter
    frontmatter_end = cleaned.find("---", 4)
    yaml_content = cleaned[4:frontmatter_end].strip()
    parsed = yaml.safe_load(yaml_content)

    # Verify ONLY name and description remain
    assert set(parsed.keys()) == {"name", "description"}
    assert parsed["name"] == "test-skill"
    assert parsed["description"] == "Test description"

    # Verify body is preserved
    assert "# Test Skill" in cleaned
    assert "Body content here." in cleaned


@pytest.mark.asyncio
async def test_fix_validation_errors(sample_context: ConversationContext) -> None:
    """Test fixing validation errors in generated content.

    Args:
        sample_context: Sample context
    """
    # Mock LLM that returns fixed content
    fixed_content = """---
name: test-skill
description: Fixed description that is third person
---

# Test Skill

Fixed body content.
"""
    mock_llm = MockLLMGenerator(fixed_content)
    generator = SkillMdGenerator(mock_llm)

    errors = [
        "Description is not third person",
        "Body exceeds 500 lines",
    ]

    invalid_content = "some invalid content"
    fixed = await generator.fix_validation_errors(invalid_content, errors)

    # Verify fixed content structure
    assert fixed.startswith("---\n")
    assert "name: test-skill" in fixed
    assert "description:" in fixed
    assert "# Test Skill" in fixed


@pytest.mark.asyncio
async def test_generate_body_includes_capability_guidance(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test that body generation includes capability-specific guidance in prompt.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    generator = SkillMdGenerator(mock_llm)

    # Test different capability combinations
    capabilities_list = [
        SkillCapabilities(needs_file_operations=True),
        SkillCapabilities(needs_multi_step_workflow=True),
        SkillCapabilities(needs_external_knowledge=True),
        SkillCapabilities(needs_script_execution=True),
    ]

    for capabilities in capabilities_list:
        sample_context.skill_capabilities = capabilities
        body = await generator.generate_body(sample_context)

        # Verify body was generated (not empty)
        assert len(body.strip()) > 0


@pytest.mark.asyncio
async def test_generate_workflow_capability_uses_steps(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test that workflow capability includes workflow steps in prompt.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    sample_context.skill_capabilities = SkillCapabilities(needs_multi_step_workflow=True)
    sample_context.workflow_steps = [
        "Validate input data",
        "Process the data",
        "Generate output",
    ]

    generator = SkillMdGenerator(mock_llm)

    # Generate body (this tests that prompt is built correctly)
    body = await generator.generate_body(sample_context)
    assert len(body) > 0


@pytest.mark.asyncio
async def test_generate_knowledge_capability_uses_topics(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test that knowledge capability includes reference topics in prompt.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    sample_context.skill_capabilities = SkillCapabilities(needs_external_knowledge=True)
    sample_context.references_topics = [
        "API documentation",
        "Brand guidelines",
        "Style guide",
    ]

    generator = SkillMdGenerator(mock_llm)

    # Generate body (this tests that prompt is built correctly)
    body = await generator.generate_body(sample_context)
    assert len(body) > 0


@pytest.mark.asyncio
async def test_generate_script_capability_uses_scripts(
    mock_llm: MockLLMGenerator, sample_context: ConversationContext
) -> None:
    """Test that script capability includes scripts in prompt.

    Args:
        mock_llm: Mock LLM generator
        sample_context: Sample context
    """
    sample_context.skill_capabilities = SkillCapabilities(needs_script_execution=True)
    sample_context.scripts_needed = [
        "deploy.sh",
        "backup.py",
    ]

    generator = SkillMdGenerator(mock_llm)

    # Generate body (this tests that prompt is built correctly)
    body = await generator.generate_body(sample_context)
    assert len(body) > 0


@pytest.mark.asyncio
async def test_generate_frontmatter_missing_fields() -> None:
    """Test that generate_frontmatter raises error if fields missing."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    # Missing both fields
    context = ConversationContext()
    with pytest.raises(ValueError, match="skill_name and skill_description are required"):
        generator.generate_frontmatter(context)

    # Missing description
    context = ConversationContext(skill_name="test-skill")
    with pytest.raises(ValueError, match="skill_name and skill_description are required"):
        generator.generate_frontmatter(context)

    # Missing name
    context = ConversationContext(skill_description="Test description")
    with pytest.raises(ValueError, match="skill_name and skill_description are required"):
        generator.generate_frontmatter(context)


# Script validation tests


def test_check_script_syntax_valid_python() -> None:
    """Test syntax checking for valid Python script."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    valid_python = """#!/usr/bin/env python3
import sys

def main():
    print("Hello, world!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

    is_valid, error = generator._check_script_syntax(valid_python, "python")
    assert is_valid is True
    assert error is None


def test_check_script_syntax_invalid_python() -> None:
    """Test syntax checking for invalid Python script."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    invalid_python = """#!/usr/bin/env python3
def main():
    print("Missing closing quote)
    return 0
"""

    is_valid, error = generator._check_script_syntax(invalid_python, "python")
    assert is_valid is False
    assert error is not None
    assert "syntax error" in error.lower() or "error" in error.lower()


def test_check_script_syntax_valid_bash() -> None:
    """Test syntax checking for valid Bash script."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    valid_bash = """#!/bin/bash
set -euo pipefail

main() {
    echo "Hello, world!"
    return 0
}

main "$@"
"""

    is_valid, error = generator._check_script_syntax(valid_bash, "bash")
    assert is_valid is True
    assert error is None


def test_check_script_syntax_invalid_bash_missing_shebang() -> None:
    """Test syntax checking catches missing shebang in Bash."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    invalid_bash = """echo "Missing shebang"
exit 0
"""

    is_valid, error = generator._check_script_syntax(invalid_bash, "bash")
    assert is_valid is False
    assert error is not None
    assert "shebang" in error.lower()


def test_check_script_syntax_invalid_bash_unmatched_quotes() -> None:
    """Test syntax checking catches unmatched quotes in Bash."""
    generator = SkillMdGenerator(MockLLMGenerator("test"))

    invalid_bash = """#!/bin/bash
echo "Unmatched quote
exit 0
"""

    is_valid, error = generator._check_script_syntax(invalid_bash, "bash")
    assert is_valid is False
    assert error is not None


@pytest.mark.asyncio
async def test_validate_script_python_valid() -> None:
    """Test validation of a valid Python script."""
    # Mock LLM that returns valid validation result
    validation_response = """{
        "is_valid": true,
        "syntax_errors": [],
        "security_issues": [],
        "quality_issues": [],
        "warnings": [],
        "suggestions": ["Consider adding type hints"],
        "overall_assessment": "Script is production-ready"
    }"""

    mock_llm = MockLLMGenerator(validation_response)
    generator = SkillMdGenerator(mock_llm)

    valid_python = """#!/usr/bin/env python3
import sys

def main():
    print("Hello, world!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

    context = ConversationContext(
        skill_name="test-skill",
        skill_description="Test skill",
    )

    is_valid, result = await generator._validate_script("scripts/test.py", valid_python, context)

    assert is_valid is True
    assert result.get("is_valid") is True
    assert len(result.get("syntax_errors", [])) == 0
    assert len(result.get("security_issues", [])) == 0


@pytest.mark.asyncio
async def test_validate_script_python_syntax_error() -> None:
    """Test validation catches Python syntax errors."""
    mock_llm = MockLLMGenerator("test")
    generator = SkillMdGenerator(mock_llm)

    invalid_python = """#!/usr/bin/env python3
def main():
    print("Missing closing quote)
"""

    context = ConversationContext(skill_name="test-skill", skill_description="Test")

    is_valid, result = await generator._validate_script("scripts/test.py", invalid_python, context)

    assert is_valid is False
    assert len(result.get("syntax_errors", [])) > 0


@pytest.mark.asyncio
async def test_validate_script_detects_security_issues() -> None:
    """Test validation detects security issues via LLM."""
    # Mock LLM that returns security issues
    validation_response = """{
        "is_valid": false,
        "syntax_errors": [],
        "security_issues": ["Hardcoded API key found", "Uses absolute paths"],
        "quality_issues": [],
        "warnings": [],
        "suggestions": [],
        "overall_assessment": "Security issues must be addressed"
    }"""

    mock_llm = MockLLMGenerator(validation_response)
    generator = SkillMdGenerator(mock_llm)

    insecure_script = """#!/usr/bin/env python3
API_KEY = "hardcoded-secret-key-12345"

def main():
    print(f"Using API key: {API_KEY}")
"""

    context = ConversationContext(skill_name="test-skill", skill_description="Test")

    is_valid, result = await generator._validate_script("scripts/test.py", insecure_script, context)

    assert is_valid is False
    assert len(result.get("security_issues", [])) > 0


@pytest.mark.asyncio
async def test_regenerate_script_with_fixes() -> None:
    """Test regenerating a script with validation feedback."""
    # Mock LLM that returns fixed script
    fixed_script = """#!/usr/bin/env python3
import os
import sys

def main():
    api_key = os.environ.get("API_KEY")
    if not api_key:
        print("ERROR: API_KEY environment variable not set")
        return 1
    print("Using API key from environment")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

    mock_llm = MockLLMGenerator(fixed_script)
    generator = SkillMdGenerator(mock_llm)

    original_script = """#!/usr/bin/env python3
API_KEY = "hardcoded-key"
print(API_KEY)
"""

    validation_result = {
        "is_valid": False,
        "syntax_errors": [],
        "security_issues": ["Hardcoded API key found"],
        "quality_issues": ["Missing error handling"],
        "warnings": [],
        "suggestions": ["Use environment variables for secrets"],
        "overall_assessment": "Security issues present"
    }

    context = ConversationContext(skill_name="test-skill", skill_description="Test")

    fixed = await generator._regenerate_script_with_fixes(
        "scripts/test.py",
        original_script,
        validation_result,
        context,
    )

    # Verify fixed script is returned
    assert len(fixed) > 0
    assert "#!/usr/bin/env python3" in fixed
    # Should not contain hardcoded key
    assert "hardcoded" not in fixed.lower()


@pytest.mark.asyncio
async def test_generate_resources_validates_scripts() -> None:
    """Test that generate_resources validates generated scripts."""
    # Mock LLM that returns script in FILE blocks and validation result
    script_response = """FILE: scripts/deploy.sh
CONTENT:
#!/bin/bash
set -euo pipefail
echo "Deploying..."
exit 0
END_FILE"""

    validation_response = """{
        "is_valid": true,
        "syntax_errors": [],
        "security_issues": [],
        "quality_issues": [],
        "warnings": [],
        "suggestions": [],
        "overall_assessment": "Script is production-ready"
    }"""

    # Create a mock that returns different responses for different prompts
    class MultiResponseMock:
        def __init__(self):
            self.call_count = 0

        async def generate_stream(self, prompt: str):
            self.call_count += 1
            # First call: script generation
            if "Generate production-ready scripts" in prompt or "Generate scripts" in prompt:
                response = script_response
            # Second call: validation
            else:
                response = validation_response

            chunk_size = 50
            for i in range(0, len(response), chunk_size):
                yield response[i : i + chunk_size]

    mock_llm = MultiResponseMock()
    generator = SkillMdGenerator(mock_llm)

    context = ConversationContext(
        skill_name="test-deploy",
        skill_description="Test deployment skill",
        skill_purpose="Deploy application",
        skill_capabilities=SkillCapabilities(needs_script_execution=True),
        scripts_needed=["Deploy the application"],
    )

    await generator.generate_resources(context)

    # Verify script was generated
    assert len(context.generated_resources) > 0
    assert any("deploy.sh" in path for path in context.generated_resources.keys())
