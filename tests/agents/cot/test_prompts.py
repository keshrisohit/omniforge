"""Tests for ReAct system prompt templates."""

from omniforge.agents.cot.prompts import (
    build_react_system_prompt,
    format_single_tool,
    format_tool_descriptions,
)
from omniforge.tools.base import (
    ParameterType,
    ToolDefinition,
    ToolParameter,
    ToolType,
)


class TestFormatSingleTool:
    """Tests for format_single_tool function."""

    def test_format_tool_with_no_parameters(self) -> None:
        """Tool with no parameters should format correctly."""
        tool = ToolDefinition(
            name="get_time",
            type=ToolType.FUNCTION,
            description="Get the current time",
        )

        result = format_single_tool(tool)

        assert "**get_time**: Get the current time" in result
        assert "Parameters:" not in result

    def test_format_tool_with_required_parameters(self) -> None:
        """Tool with required parameters should show them correctly."""
        tool = ToolDefinition(
            name="search",
            type=ToolType.FUNCTION,
            description="Search for information",
            parameters=[
                ToolParameter(
                    name="query",
                    type=ParameterType.STRING,
                    description="Search query text",
                    required=True,
                ),
            ],
        )

        result = format_single_tool(tool)

        assert "**search**: Search for information" in result
        assert "Parameters:" in result
        assert "- query (string, required): Search query text" in result

    def test_format_tool_with_optional_parameters(self) -> None:
        """Tool with optional parameters should show defaults."""
        tool = ToolDefinition(
            name="fetch_data",
            type=ToolType.FUNCTION,
            description="Fetch data from API",
            parameters=[
                ToolParameter(
                    name="timeout",
                    type=ParameterType.INTEGER,
                    description="Request timeout in seconds",
                    required=False,
                    default=30,
                ),
            ],
        )

        result = format_single_tool(tool)

        assert "**fetch_data**: Fetch data from API" in result
        assert "Parameters:" in result
        assert "- timeout (integer, optional, default=30): Request timeout in seconds" in result

    def test_format_tool_with_mixed_parameters(self) -> None:
        """Tool with both required and optional parameters."""
        tool = ToolDefinition(
            name="create_file",
            type=ToolType.FUNCTION,
            description="Create a new file",
            parameters=[
                ToolParameter(
                    name="path",
                    type=ParameterType.STRING,
                    description="File path",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description="File content",
                    required=True,
                ),
                ToolParameter(
                    name="overwrite",
                    type=ParameterType.BOOLEAN,
                    description="Overwrite existing file",
                    required=False,
                    default=False,
                ),
            ],
        )

        result = format_single_tool(tool)

        assert "**create_file**: Create a new file" in result
        assert "- path (string, required): File path" in result
        assert "- content (string, required): File content" in result
        assert "- overwrite (boolean, optional, default=False): Overwrite existing file" in result

    def test_format_tool_with_optional_parameter_no_default(self) -> None:
        """Optional parameter with no default value should not show default."""
        tool = ToolDefinition(
            name="process",
            type=ToolType.FUNCTION,
            description="Process data",
            parameters=[
                ToolParameter(
                    name="config",
                    type=ParameterType.OBJECT,
                    description="Optional configuration",
                    required=False,
                    default=None,
                ),
            ],
        )

        result = format_single_tool(tool)

        assert "default=" not in result
        assert "- config (object, optional): Optional configuration" in result

    def test_format_tool_with_all_parameter_types(self) -> None:
        """Tool with all parameter types should format correctly."""
        tool = ToolDefinition(
            name="complex_tool",
            type=ToolType.FUNCTION,
            description="A complex tool",
            parameters=[
                ToolParameter(
                    name="text",
                    type=ParameterType.STRING,
                    description="Text input",
                    required=True,
                ),
                ToolParameter(
                    name="count",
                    type=ParameterType.INTEGER,
                    description="Count value",
                    required=True,
                ),
                ToolParameter(
                    name="ratio",
                    type=ParameterType.FLOAT,
                    description="Ratio value",
                    required=False,
                    default=0.5,
                ),
                ToolParameter(
                    name="enabled",
                    type=ParameterType.BOOLEAN,
                    description="Enable flag",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="items",
                    type=ParameterType.ARRAY,
                    description="List of items",
                    required=False,
                ),
                ToolParameter(
                    name="metadata",
                    type=ParameterType.OBJECT,
                    description="Metadata object",
                    required=False,
                ),
            ],
        )

        result = format_single_tool(tool)

        assert "**complex_tool**: A complex tool" in result
        assert "- text (string, required): Text input" in result
        assert "- count (integer, required): Count value" in result
        assert "- ratio (float, optional, default=0.5): Ratio value" in result
        assert "- enabled (boolean, optional, default=True): Enable flag" in result
        assert "- items (array, optional): List of items" in result
        assert "- metadata (object, optional): Metadata object" in result


class TestFormatToolDescriptions:
    """Tests for format_tool_descriptions function."""

    def test_format_empty_tool_list(self) -> None:
        """Empty tool list should return 'No tools available.'"""
        result = format_tool_descriptions([])

        assert result == "No tools available."

    def test_format_single_tool(self) -> None:
        """Single tool should format correctly."""
        tools = [
            ToolDefinition(
                name="calculator",
                type=ToolType.FUNCTION,
                description="Perform calculations",
            )
        ]

        result = format_tool_descriptions(tools)

        assert "**calculator**: Perform calculations" in result
        assert result.count("**") == 2  # Only one tool formatted

    def test_format_multiple_tools(self) -> None:
        """Multiple tools should be separated by blank lines."""
        tools = [
            ToolDefinition(
                name="search",
                type=ToolType.FUNCTION,
                description="Search the web",
            ),
            ToolDefinition(
                name="calculator",
                type=ToolType.FUNCTION,
                description="Perform calculations",
            ),
        ]

        result = format_tool_descriptions(tools)

        assert "**search**: Search the web" in result
        assert "**calculator**: Perform calculations" in result
        # Tools should be separated by double newline
        assert "\n\n" in result


class TestBuildReactSystemPrompt:
    """Tests for build_react_system_prompt function."""

    def test_prompt_with_empty_tools(self) -> None:
        """Prompt with no tools should still include all rules."""
        prompt = build_react_system_prompt([])

        # Check key sections
        assert "You are an autonomous AI agent" in prompt
        assert "No tools available." in prompt
        assert "Response Format (JSON)" in prompt
        assert "You MUST respond with valid JSON format only" in prompt

    def test_prompt_with_single_tool(self) -> None:
        """Prompt with one tool should include tool description."""
        tools = [
            ToolDefinition(
                name="search",
                type=ToolType.FUNCTION,
                description="Search for information",
                parameters=[
                    ToolParameter(
                        name="query",
                        type=ParameterType.STRING,
                        description="Search query",
                        required=True,
                    )
                ],
            )
        ]

        prompt = build_react_system_prompt(tools)

        assert "**search**: Search for information" in prompt
        assert "- query (string, required): Search query" in prompt

    def test_prompt_with_multiple_tools(self) -> None:
        """Prompt with multiple tools should list all of them."""
        tools = [
            ToolDefinition(
                name="search",
                type=ToolType.FUNCTION,
                description="Search the web",
            ),
            ToolDefinition(
                name="calculator",
                type=ToolType.FUNCTION,
                description="Perform calculations",
            ),
        ]

        prompt = build_react_system_prompt(tools)

        assert "**search**: Search the web" in prompt
        assert "**calculator**: Perform calculations" in prompt

    def test_prompt_contains_all_format_keywords(self) -> None:
        """Prompt should contain all ReAct JSON format keywords."""
        prompt = build_react_system_prompt([])

        # JSON field names
        assert '"thought"' in prompt
        assert '"action"' in prompt
        assert '"action_input"' in prompt
        assert '"final_answer"' in prompt
        assert '"is_final"' in prompt
        assert "Observation:" in prompt  # Still used for tool results

    def test_prompt_contains_critical_rules(self) -> None:
        """Prompt should contain all critical execution rules."""
        prompt = build_react_system_prompt([])

        # Check that critical rules are present
        assert "You MUST use at least one tool before providing Final Answer" in prompt
        assert "You CANNOT answer from memory alone - always verify with tools" in prompt
        assert "NEVER skip directly to final answer without tool execution" in prompt
        assert "You MUST respond with valid JSON format only" in prompt

    def test_prompt_structure(self) -> None:
        """Prompt should have correct structural elements."""
        prompt = build_react_system_prompt([])

        # Check structure
        assert "You are an autonomous AI agent" in prompt
        assert "Now solve the user's task by responding with valid JSON only" in prompt

    def test_prompt_with_complex_tool(self) -> None:
        """Prompt with complex tool should format all details."""
        tools = [
            ToolDefinition(
                name="fetch_data",
                type=ToolType.FUNCTION,
                description="Fetch data from API",
                parameters=[
                    ToolParameter(
                        name="url",
                        type=ParameterType.STRING,
                        description="API endpoint URL",
                        required=True,
                    ),
                    ToolParameter(
                        name="method",
                        type=ParameterType.STRING,
                        description="HTTP method",
                        required=False,
                        default="GET",
                    ),
                    ToolParameter(
                        name="timeout",
                        type=ParameterType.INTEGER,
                        description="Timeout in seconds",
                        required=False,
                        default=30,
                    ),
                ],
            )
        ]

        prompt = build_react_system_prompt(tools)

        assert "**fetch_data**: Fetch data from API" in prompt
        assert "- url (string, required): API endpoint URL" in prompt
        assert "- method (string, optional, default=GET): HTTP method" in prompt
        assert "- timeout (integer, optional, default=30): Timeout in seconds" in prompt

    def test_prompt_contains_skill_navigation_section(self) -> None:
        """Prompt should contain skill path resolution instructions."""
        prompt = build_react_system_prompt([])

        # Check skill navigation section is present
        assert "## Skill Path Resolution" in prompt
        assert "base_path" in prompt
        assert "Path Resolution Rules" in prompt

    def test_prompt_contains_path_resolution_examples(self) -> None:
        """Prompt should contain concrete path resolution examples."""
        prompt = build_react_system_prompt([])

        # Check examples are present
        assert "Example 1: Loading Reference Documents" in prompt
        assert "Example 2: Nested Paths" in prompt
        assert "{base_path}/{relative_path}" in prompt

    def test_prompt_contains_script_execution_guidance(self) -> None:
        """Prompt should contain script execution instructions."""
        prompt = build_react_system_prompt([])

        # Check script execution section
        assert "## Script Execution" in prompt
        assert "NEVER load script contents with Read tool" in prompt
        assert "Always execute via Bash" in prompt
        assert "cd {base_path} && {command}" in prompt

    def test_prompt_contains_multi_llm_compatibility(self) -> None:
        """Prompt should work for multiple LLMs with explicit examples."""
        prompt = build_react_system_prompt([])

        # Check that examples are concrete (not implicit)
        assert "kubernetes-deploy" in prompt  # Example skill name
        assert "/home/user/.claude/skills" in prompt  # Example path
        assert "pdf-processing" in prompt  # Example skill name

    def test_skill_instructions_placed_after_rules(self) -> None:
        """Skill navigation instructions should come after the critical rules."""
        prompt = build_react_system_prompt([])

        # Get positions
        rules_pos = prompt.find("CRITICAL EXECUTION RULES")
        skill_nav_pos = prompt.find("## Skill Path Resolution")

        # Verify order: Rules -> Skill Navigation
        assert rules_pos < skill_nav_pos
        assert rules_pos != -1
        assert skill_nav_pos != -1
