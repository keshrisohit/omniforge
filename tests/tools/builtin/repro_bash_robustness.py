
import asyncio
import pytest
from omniforge.tools.builtin.bash import BashTool
from omniforge.tools.base import ToolCallContext

@pytest.mark.asyncio
async def test_bash_tool_handles_string_argument():
    tool = BashTool()
    context = ToolCallContext(correlation_id="test", task_id="test", agent_id="test")

    # Test passing just a string instead of a dict
    result = await tool.execute(context, "echo 'robustness test'")

    assert result.success is True
    assert "robustness test" in result.result["stdout"]

@pytest.mark.asyncio
async def test_bash_tool_handles_command_key_capital():
    tool = BashTool()
    context = ToolCallContext(correlation_id="test", task_id="test", agent_id="test")

    # Test passing dict with "Command" (capital C)
    result = await tool.execute(context, {"Command": "echo 'capital test'"})

    assert result.success is True
    assert "capital test" in result.result["stdout"]
