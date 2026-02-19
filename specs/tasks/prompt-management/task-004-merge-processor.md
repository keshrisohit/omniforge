# TASK-004: Implement Merge Point Processor

## Objective

Create the merge processor that combines prompt content from multiple layers at defined merge points.

## Requirements

### Merge Processor (`src/omniforge/prompts/composition/merge.py`)

**MergeProcessor class**:

`async merge(layer_prompts: dict[PromptLayer, Optional[Prompt]], user_input: Optional[str]) -> str`:
- Accept prompts from all layers (SYSTEM, TENANT, FEATURE, AGENT)
- Start with system prompt as base template
- Process each merge point in the system template
- Collect content from all layers that define the merge point
- Apply merge behavior based on MergeBehavior enum:
  - **APPEND**: Higher layer content added after lower layer
  - **PREPEND**: Higher layer content added before lower layer
  - **REPLACE**: Higher layer content replaces lower layer
  - **INJECT**: Content inserted at specified position
- Respect `locked` constraint (locked merge points preserve system content only)
- Handle `required` constraint (raise error if required but no content)
- Substitute user_input into the "user_input" merge point
- Clean up empty merge points (no double newlines, no placeholder text)

**Helper methods**:
- `_extract_merge_point_content(prompt, merge_point_name)`: Get content for a specific merge point
- `_apply_merge_behavior(behavior, contents_by_layer)`: Combine content based on behavior
- `_process_merge_point_markers(template)`: Find and replace `{{ merge_point("name") }}` markers

### Merge Point Marker Syntax
Templates use: `{{ merge_point("name") }}` to mark insertion points

### Edge Cases to Handle
- Missing layer prompts (skip gracefully)
- Empty merge point content (collapse cleanly)
- Conflicting merge points (higher layers win unless locked)
- Multiple feature prompts (already combined in engine)

## Acceptance Criteria
- [ ] APPEND behavior concatenates content in correct order
- [ ] PREPEND behavior prepends higher layer content
- [ ] REPLACE behavior uses first non-empty from highest layer
- [ ] INJECT behavior inserts at correct position
- [ ] Locked merge points cannot be overridden by higher layers
- [ ] Required merge points raise error if empty
- [ ] Empty merge points produce clean output (no extra whitespace)
- [ ] User input is properly incorporated
- [ ] Unit tests cover all merge behaviors
- [ ] Integration test with multi-layer merge scenario

## Dependencies
- TASK-001 (models, enums)
- TASK-003 (renderer for marker processing)

## Estimated Complexity
Complex
