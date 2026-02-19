# TASK-009: Rename Existing SkillTool to FunctionTool

**Phase**: 4 - Rename & Integration
**Complexity**: Medium
**Dependencies**: TASK-007
**Estimated Time**: 30-45 minutes

## Objective

Rename the existing SkillTool (Python function invocation) to FunctionTool with backward compatibility.

## What to Build

### 1. Create `src/omniforge/tools/builtin/function.py`

New module with renamed classes:
- `FunctionDefinition` (copy of SkillDefinition)
- `FunctionRegistry` (copy of SkillRegistry)
- `FunctionTool` (copy of SkillTool, tool name: "function")
- `function` decorator (copy of skill decorator)

Update the tool definition:
- name: "function" (not "skill")
- description: "Invoke an internal Python function by name"

### 2. Modify `src/omniforge/tools/builtin/skill.py`

Add deprecation warnings:
```python
import warnings

class SkillTool(FunctionTool):
    """DEPRECATED: Use FunctionTool instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SkillTool is deprecated, use FunctionTool instead",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
```

Re-export with deprecation for backward compatibility:
- SkillDefinition = FunctionDefinition (with deprecation warning)
- SkillRegistry = FunctionRegistry (with deprecation warning)
- skill = function (with deprecation warning)

### 3. Update `src/omniforge/tools/builtin/__init__.py`

Export both old (deprecated) and new names:
```python
from omniforge.tools.builtin.function import (
    FunctionDefinition,
    FunctionRegistry,
    FunctionTool,
    function,
)
# Deprecated aliases
from omniforge.tools.builtin.skill import (
    SkillDefinition,
    SkillRegistry,
    SkillTool,
    skill,
)
```

## Key Requirements

- Full backward compatibility (existing code works with deprecation warnings)
- Clear deprecation messages pointing to new names
- Tool name changes from "skill" to "function"
- All internal usages should use new names

## Acceptance Criteria

- [ ] FunctionTool works identically to old SkillTool
- [ ] Using old names produces DeprecationWarning
- [ ] Tool definition name is "function" not "skill"
- [ ] Existing tests pass with new names
- [ ] tests/tools/builtin/test_function.py created
- [ ] tests/tools/builtin/test_skill.py updated with deprecation tests
