# TASK-003: Implement Jinja2 Template Renderer and Syntax Validation

## Objective

Create a secure, sandboxed Jinja2 template renderer and syntax validator for prompt templates.

## Requirements

### Template Renderer (`src/omniforge/prompts/composition/renderer.py`)

**PromptTemplateLoader**:
- Minimal BaseLoader that returns templates from strings (no file access)
- Implements `get_source` method for string-based templates

**TemplateRenderer**:
- Use `SandboxedEnvironment` from jinja2.sandbox
- Configure with `autoescape=False`, `trim_blocks=True`, `lstrip_blocks=True`
- Register custom filters:
  - `default`: Return default value if empty
  - `truncate`: Truncate string to length with suffix
  - `capitalize_first`: Capitalize first character
  - `bullet_list`: Format list as bullet points
- `async render(template, variables)`: Render template with variables
- `validate_syntax(template)`: Return list of syntax errors without rendering
- Handle and convert Jinja2 exceptions to `PromptRenderError`

### Syntax Validator (`src/omniforge/prompts/validation/syntax.py`)

**SyntaxValidator**:
- `validate(content: str) -> list[str]`: Validate Jinja2 syntax
- Parse template without rendering
- Return descriptive error messages with line numbers
- Catch `TemplateSyntaxError` and format appropriately

### Package Init Files
- `src/omniforge/prompts/composition/__init__.py`
- `src/omniforge/prompts/validation/__init__.py`

## Acceptance Criteria
- [ ] SandboxedEnvironment prevents code execution
- [ ] No filesystem access allowed from templates
- [ ] All custom filters work correctly
- [ ] Syntax validation catches malformed templates
- [ ] Render errors converted to PromptRenderError with context
- [ ] UndefinedError handled for missing variables
- [ ] Unit tests cover valid/invalid templates
- [ ] Tests verify sandbox security (cannot access dangerous functions)

## Dependencies
- TASK-001 (errors module)

## Estimated Complexity
Medium
