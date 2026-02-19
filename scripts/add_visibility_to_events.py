#!/usr/bin/env python3
"""Script to add visibility levels to event emissions in autonomous_executor.py"""

import re
from pathlib import Path

file_path = Path("src/omniforge/skills/autonomous_executor.py")

# Read the file
content = file_path.read_text()

# First, add the import
if "from omniforge.tools.types import VisibilityLevel" not in content:
    content = content.replace(
        "from omniforge.tools.registry import ToolRegistry",
        "from omniforge.tools.registry import ToolRegistry\nfrom omniforge.tools.types import VisibilityLevel"
    )

# Define replacements for each event type with their contexts

replacements = [
    # Starting event
    (
        '''yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Starting autonomous skill execution",
        )''',
        '''yield TaskStatusEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            state=TaskState.WORKING,
            message="Starting autonomous skill execution",
            visibility=VisibilityLevel.SUMMARY,
        )'''
    ),
    # Iteration progress - FULL visibility
    (
        '''yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=iteration_msg)],
                is_partial=True,
            )''',
        '''yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=iteration_msg)],
                is_partial=True,
                visibility=VisibilityLevel.FULL,
            )'''
    ),
    # LLM call failed error
    (
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="LLM_CALL_FAILED",
                        error_message=error_msg,
                    )''',
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="LLM_CALL_FAILED",
                        error_message=error_msg,
                        visibility=VisibilityLevel.SUMMARY,
                    )'''
    ),
    # Thought - FULL visibility
    (
        '''yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Thought: {parsed.thought}")],
                        is_partial=True,
                    )''',
        '''yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Thought: {parsed.thought}")],
                        is_partial=True,
                        visibility=VisibilityLevel.FULL,
                    )'''
    ),
    # Final answer - SUMMARY visibility
    (
        '''yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Final answer: {parsed.final_answer}")],
                        is_partial=False,
                    )''',
        '''yield TaskMessageEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        message_parts=[TextPart(text=f"Final answer: {parsed.final_answer}")],
                        is_partial=False,
                        visibility=VisibilityLevel.SUMMARY,
                    )'''
    ),
    # Invalid response error
    (
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="INVALID_RESPONSE",
                        error_message=error_msg,
                    )''',
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="INVALID_RESPONSE",
                        error_message=error_msg,
                        visibility=VisibilityLevel.SUMMARY,
                    )'''
    ),
    # Action - SUMMARY visibility
    (
        '''yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=f"Action: {parsed.action}")],
                    is_partial=True,
                )''',
        '''yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=f"Action: {parsed.action}")],
                    is_partial=True,
                    visibility=VisibilityLevel.SUMMARY,
                )'''
    ),
    # Tool execution error
    (
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="TOOL_EXECUTION_ERROR",
                        error_message=str(e),
                    )''',
        '''yield TaskErrorEvent(
                        task_id=task_id,
                        timestamp=datetime.utcnow(),
                        error_code="TOOL_EXECUTION_ERROR",
                        error_message=str(e),
                        visibility=VisibilityLevel.SUMMARY,
                    )'''
    ),
    # Observation - FULL visibility
    (
        '''yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=observation)],
                    is_partial=True,
                )''',
        '''yield TaskMessageEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    message_parts=[TextPart(text=observation)],
                    is_partial=True,
                    visibility=VisibilityLevel.FULL,
                )'''
    ),
    # Iteration timeout error
    (
        '''yield TaskErrorEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    error_code="ITERATION_TIMEOUT",
                    error_message=error_msg,
                )''',
        '''yield TaskErrorEvent(
                    task_id=task_id,
                    timestamp=datetime.utcnow(),
                    error_code="ITERATION_TIMEOUT",
                    error_message=error_msg,
                    visibility=VisibilityLevel.SUMMARY,
                )'''
    ),
    # Max iterations error
    (
        '''yield TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code="MAX_ITERATIONS_REACHED",
            error_message=error_msg,
        )''',
        '''yield TaskErrorEvent(
            task_id=task_id,
            timestamp=datetime.utcnow(),
            error_code="MAX_ITERATIONS_REACHED",
            error_message=error_msg,
            visibility=VisibilityLevel.SUMMARY,
        )'''
    ),
    # Partial synthesis - SUMMARY visibility
    (
        '''yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=partial_synthesis)],
                is_partial=False,
            )''',
        '''yield TaskMessageEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                message_parts=[TextPart(text=partial_synthesis)],
                is_partial=False,
                visibility=VisibilityLevel.SUMMARY,
            )'''
    ),
    # Execution error
    (
        '''yield TaskErrorEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                error_code="EXECUTION_ERROR",
                error_message=f"Autonomous execution failed: {str(e)}",
                details={"skill": self.skill.metadata.name},
            )''',
        '''yield TaskErrorEvent(
                task_id=task_id,
                timestamp=datetime.utcnow(),
                error_code="EXECUTION_ERROR",
                error_message=f"Autonomous execution failed: {str(e)}",
                details={"skill": self.skill.metadata.name},
                visibility=VisibilityLevel.SUMMARY,
            )'''
    ),
]

# Apply all replacements
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"✓ Replaced event emission")
    else:
        print(f"✗ Could not find pattern")

# Write back
file_path.write_text(content)
print(f"\nUpdated {file_path}")
