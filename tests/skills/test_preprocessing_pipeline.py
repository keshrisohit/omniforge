"""Integration tests for preprocessing pipeline.

This module tests the full preprocessing pipeline flow:
ContextLoader → DynamicInjector → StringSubstitutor

Tests focus on:
- End-to-end pipeline integration
- Data flow between components
- Real-world usage scenarios
- Error handling across components
"""

from pathlib import Path

import pytest

from omniforge.skills.context_loader import ContextLoader
from omniforge.skills.dynamic_injector import DynamicInjector
from omniforge.skills.models import Skill, SkillMetadata
from omniforge.skills.string_substitutor import StringSubstitutor, SubstitutionContext


class TestPreprocessingPipeline:
    """Integration tests for the full preprocessing pipeline."""

    def _create_skill(self, content: str, skill_dir: Path) -> Skill:
        """Create a mock skill for testing.

        Args:
            content: SKILL.md content
            skill_dir: Skill directory path

        Returns:
            Mock Skill object
        """
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill for preprocessing pipeline",
        )

        return Skill(
            metadata=metadata,
            content=content,
            path=skill_dir / "SKILL.md",
            base_path=skill_dir,
            storage_layer="test",
            script_paths=None,
        )

    def test_pipeline_basic_flow(self, tmp_path: Path) -> None:
        """Should process content through all preprocessing stages."""
        # Setup: Create skill with supporting files
        (tmp_path / "reference.md").write_text("API documentation content")

        skill_content = """# Data Processor

Process data from $ARGUMENTS.

Supporting files:
- reference.md: API documentation (50 lines)
"""

        skill = self._create_skill(skill_content, tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        assert loaded_context.skill_content == skill_content
        assert "reference.md" in loaded_context.available_files
        assert loaded_context.skill_dir == tmp_path

        # Stage 2: String Substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="data.csv",
            skill_dir=str(tmp_path),
            workspace=str(tmp_path),
            user="testuser",
            session_id="session-test-123",
        )

        result = substitutor.substitute(loaded_context.skill_content, sub_context)

        assert "data.csv" in result.content
        assert "$ARGUMENTS" not in result.content
        assert result.substitutions_made >= 1

    @pytest.mark.asyncio
    async def test_pipeline_with_dynamic_injection(self, tmp_path: Path) -> None:
        """Should handle dynamic command injection in pipeline."""
        skill_content = """# Dynamic Processor

Current date: !`echo '2026-01-27'`
Process file: $ARGUMENTS
Working in: ${WORKSPACE}
"""

        skill = self._create_skill(skill_content, tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Stage 2: Dynamic Injection
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        assert "!`echo" not in injected.content
        assert "2026-01-27" in injected.content
        assert len(injected.injections) == 1
        assert injected.injections[0].success

        # Stage 3: String Substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="data.csv",
            workspace=str(tmp_path),
        )

        result = substitutor.substitute(injected.content, sub_context)

        assert "data.csv" in result.content
        assert str(tmp_path) in result.content
        assert "2026-01-27" in result.content

    @pytest.mark.asyncio
    async def test_pipeline_order_matters(self, tmp_path: Path) -> None:
        """Dynamic injection should happen before string substitution."""
        # This content has a command that outputs a variable reference
        skill_content = "Value: !`echo '$RESULT'`"

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Correct order: Inject first, then substitute
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(custom_vars={"RESULT": "success"})
        result = substitutor.substitute(injected.content, sub_context)

        # The command output '$RESULT' should be substituted
        assert "success" in result.content
        assert "$RESULT" not in result.content

    def test_pipeline_with_file_references(self, tmp_path: Path) -> None:
        """Should preserve file references through pipeline."""
        # Create supporting files
        (tmp_path / "api.md").write_text("# API Reference")
        (tmp_path / "examples.md").write_text("# Examples")

        skill_content = """# Skill

User: $USER processes $ARGUMENTS

See api.md for API details.
Check examples.md for usage.
"""

        skill = self._create_skill(skill_content, tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        assert len(loaded_context.available_files) == 2
        assert "api.md" in loaded_context.available_files
        assert "examples.md" in loaded_context.available_files

        # Stage 2: String Substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="data.csv",
            user="alice",
        )

        result = substitutor.substitute(loaded_context.skill_content, sub_context)

        # File references should be preserved
        assert "api.md" in result.content
        assert "examples.md" in result.content

        # Variables should be substituted
        assert "alice" in result.content
        assert "data.csv" in result.content

    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, tmp_path: Path) -> None:
        """Should handle errors gracefully in pipeline."""
        skill_content = """# Error Handling Test

Command: !`exit 1`
Undefined: ${UNDEFINED_VAR}
Argument: $ARGUMENTS
"""

        skill = self._create_skill(skill_content, tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Stage 2: Dynamic Injection (command fails)
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        assert not injected.injections[0].success
        assert "[Command failed:" in injected.content

        # Stage 3: String Substitution (undefined variable)
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(arguments="data.csv")

        result = substitutor.substitute(injected.content, sub_context)

        # Should track undefined variable
        assert "UNDEFINED_VAR" in result.undefined_vars
        assert "${UNDEFINED_VAR}" in result.content

        # Should substitute defined variable
        assert "data.csv" in result.content

    @pytest.mark.asyncio
    async def test_pipeline_security_validation(self, tmp_path: Path) -> None:
        """Security validation should work in pipeline context."""
        skill_content = """# Security Test

Safe command: !`echo 'hello'`
Unsafe command: !`rm -rf /`
Process: $ARGUMENTS
"""

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Dynamic injection with restrictions
        injector = DynamicInjector(allowed_tools=["Bash(echo:*)"])
        injected = await injector.process(loaded_context.skill_content)

        # Safe command should succeed
        assert any(inj.success for inj in injected.injections)

        # Unsafe command should be blocked
        assert any(not inj.success for inj in injected.injections)
        assert "blocked by security policy" in injected.content.lower()

        # String substitution should still work
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(arguments="data.csv")
        result = substitutor.substitute(injected.content, sub_context)

        assert "data.csv" in result.content

    def test_pipeline_empty_content(self, tmp_path: Path) -> None:
        """Should handle empty content gracefully."""
        skill = self._create_skill("", tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        assert loaded_context.skill_content == ""
        assert loaded_context.line_count == 0

        # Stage 2: String Substitution with auto-append
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(arguments="data.csv")
        result = substitutor.substitute(loaded_context.skill_content, sub_context)

        # Auto-append should add arguments
        assert "ARGUMENTS: data.csv" in result.content

    @pytest.mark.asyncio
    async def test_pipeline_complex_real_world_scenario(self, tmp_path: Path) -> None:
        """Test realistic preprocessing scenario with all features."""
        # Create realistic skill structure
        (tmp_path / "api_reference.md").write_text("# Complete API Reference\n\nDetailed API docs")
        (tmp_path / "examples.md").write_text("# Usage Examples\n\nExample code")

        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()
        (templates_dir / "output.md").write_text("# Output Template")

        skill_content = """# Advanced Data Processor

**Session**: ${CLAUDE_SESSION_ID}
**User**: $USER
**Workspace**: ${WORKSPACE}

Process the file: $ARGUMENTS

Current date: !`date +%Y-%m-%d`
System user: !`whoami`

## Supporting Documentation

- api_reference.md: Complete API documentation (500 lines)
- examples.md: Usage examples and patterns (200 lines)
- templates/output.md: Output template for reports

## Process Steps

1. Load data from $ARGUMENTS
2. Validate against API in api_reference.md
3. Apply examples from examples.md
4. Generate report using templates/output.md
"""

        skill = self._create_skill(skill_content, tmp_path)

        # Stage 1: Context Loading
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Verify file references detected
        assert len(loaded_context.available_files) == 3
        assert "api_reference.md" in loaded_context.available_files
        assert "examples.md" in loaded_context.available_files
        assert "templates/output.md" in loaded_context.available_files

        # Verify line count hints parsed
        api_ref = loaded_context.available_files["api_reference.md"]
        assert api_ref.estimated_lines == 500

        # Build available files prompt
        files_prompt = context_loader.build_available_files_prompt(loaded_context)
        assert "AVAILABLE SUPPORTING FILES" in files_prompt
        assert "api_reference.md" in files_prompt
        assert "500 lines" in files_prompt

        # Stage 2: Dynamic Injection
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        # Verify commands executed
        assert len(injected.injections) == 2
        assert all(inj.success for inj in injected.injections)
        assert "!`date" not in injected.content
        assert "!`whoami" not in injected.content

        # Stage 3: String Substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="customer_data.csv",
            session_id="session-20260127-abc123",
            skill_dir=str(tmp_path),
            workspace=str(tmp_path),
            user="alice",
        )

        result = substitutor.substitute(injected.content, sub_context)

        # Verify all substitutions made
        assert "customer_data.csv" in result.content
        assert "session-20260127-abc123" in result.content
        assert "alice" in result.content
        assert str(tmp_path) in result.content

        # Verify no variable placeholders remain
        assert "$ARGUMENTS" not in result.content
        assert "${CLAUDE_SESSION_ID}" not in result.content
        assert "$USER" not in result.content
        assert "${WORKSPACE}" not in result.content

        # Verify file references preserved
        assert "api_reference.md" in result.content
        assert "examples.md" in result.content
        assert "templates/output.md" in result.content

        # Verify no undefined variables
        assert len(result.undefined_vars) == 0

        # Verify multiple substitutions
        assert result.substitutions_made >= 4


class TestPreprocessingEdgeCases:
    """Edge case tests for preprocessing pipeline integration."""

    def _create_skill(self, content: str, skill_dir: Path) -> Skill:
        """Create a mock skill for testing."""
        metadata = SkillMetadata(name="test-skill", description="Test")
        return Skill(
            metadata=metadata,
            content=content,
            path=skill_dir / "SKILL.md",
            base_path=skill_dir,
            storage_layer="test",
            script_paths=None,
        )

    @pytest.mark.asyncio
    async def test_nested_variable_references(self, tmp_path: Path) -> None:
        """Should handle nested variable-like patterns."""
        skill_content = "Path: ${WORKSPACE}/data/${DATE}/file.csv"

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            workspace="/home/user",
            date="2026-01-27",
        )

        result = substitutor.substitute(loaded_context.skill_content, sub_context)

        assert "/home/user/data/2026-01-27/file.csv" in result.content

    @pytest.mark.asyncio
    async def test_unicode_in_pipeline(self, tmp_path: Path) -> None:
        """Should handle unicode characters throughout pipeline."""
        skill_content = """Unicode test: !`echo '你好世界 🚀'`
User: $USER
"""

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Dynamic injection
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        assert "你好世界" in injected.content
        assert "🚀" in injected.content

        # String substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(user="张三")

        result = substitutor.substitute(injected.content, sub_context)

        assert "张三" in result.content
        assert "你好世界" in result.content
        assert "🚀" in result.content

    def test_large_content_handling(self, tmp_path: Path) -> None:
        """Should handle large content efficiently."""
        # Create large content with many references
        large_content = "# Large Skill\n\n"
        large_content += "Process: $ARGUMENTS\n" * 100
        large_content += "User: $USER\n" * 100
        large_content += "Workspace: ${WORKSPACE}\n" * 100

        skill = self._create_skill(large_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Should handle many substitutions
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="data.csv",
            user="testuser",
            workspace="/workspace",
        )

        result = substitutor.substitute(loaded_context.skill_content, sub_context)

        # All occurrences should be substituted
        assert "$ARGUMENTS" not in result.content
        assert "$USER" not in result.content
        assert "${WORKSPACE}" not in result.content
        assert result.substitutions_made == 300

    @pytest.mark.asyncio
    async def test_multiple_commands_and_variables(self, tmp_path: Path) -> None:
        """Should handle multiple commands and variables together."""
        skill_content = """
Date: !`echo '2026-01-27'`
User: $USER processes !`echo 'data.csv'`
Session: ${CLAUDE_SESSION_ID}
Working in: !`pwd` directory
Arguments: $ARGUMENTS
"""

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Dynamic injection
        injector = DynamicInjector(allowed_tools=["Bash"])
        injected = await injector.process(loaded_context.skill_content)

        assert len(injected.injections) == 3
        assert all(inj.success for inj in injected.injections)

        # String substitution
        substitutor = StringSubstitutor()
        sub_context = SubstitutionContext(
            arguments="final_data.csv",
            user="alice",
            session_id="session-test",
        )

        result = substitutor.substitute(injected.content, sub_context)

        # Verify all replacements
        assert "alice" in result.content
        assert "final_data.csv" in result.content
        assert "session-test" in result.content
        assert "2026-01-27" in result.content
        assert "data.csv" in result.content

    def test_context_loader_unsupported_extension(self, tmp_path: Path) -> None:
        """Should skip files with unsupported extensions."""
        # Create files with various extensions
        (tmp_path / "supported.md").write_text("Markdown")
        (tmp_path / "unsupported.exe").write_text("Binary")
        (tmp_path / "also_unsupported.bin").write_text("Binary")

        skill_content = """
Files:
- supported.md: Documentation
- unsupported.exe: Binary file
- also_unsupported.bin: Another binary
"""

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Only supported files should be included
        assert "supported.md" in loaded_context.available_files
        assert "unsupported.exe" not in loaded_context.available_files
        assert "also_unsupported.bin" not in loaded_context.available_files

    @pytest.mark.asyncio
    async def test_error_output_truncation(self, tmp_path: Path) -> None:
        """Should truncate very long error messages."""
        injector = DynamicInjector(allowed_tools=["Bash"], max_output_chars=50)

        # Command that produces long error output
        skill_content = "!`ls /this_directory_definitely_does_not_exist_12345678901234567890123456789012345678901234567890`"

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        injected = await injector.process(loaded_context.skill_content)

        assert not injected.injections[0].success
        assert "truncated" in injected.content
        # Error output should be truncated
        assert len(injected.injections[0].output) < 150

    def test_line_count_extraction_edge_cases(self, tmp_path: Path) -> None:
        """Should handle various line count formats."""
        (tmp_path / "file1.md").write_text("Content")
        (tmp_path / "file2.md").write_text("Content")
        (tmp_path / "file3.md").write_text("Content")

        skill_content = """
Files:
- file1.md: With comma (1,234 lines)
- file2.md: Without comma (567 lines)
- file3.md: No line count mentioned
"""

        skill = self._create_skill(skill_content, tmp_path)
        context_loader = ContextLoader(skill)
        loaded_context = context_loader.load_initial_context()

        # Verify line counts parsed correctly
        assert loaded_context.available_files["file1.md"].estimated_lines == 1234
        assert loaded_context.available_files["file2.md"].estimated_lines == 567
        assert loaded_context.available_files["file3.md"].estimated_lines is None
