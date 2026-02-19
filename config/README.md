# OmniForge Configuration

This directory contains platform-level configuration files for OmniForge.

## Configuration Files

### `autonomous.yaml`

Platform-level defaults for autonomous skill execution. This file defines:

- **Default execution settings**: Max iterations, retries, timeouts, error recovery
- **Visibility settings**: Different visibility levels by user role (end user, developer, admin)
- **Cost management**: Optional cost tracking and limits
- **Rate limiting**: Optional rate limits for concurrent executions

## Usage

### Loading Configuration from YAML

```python
from omniforge.skills import PlatformAutonomousConfig

# Load from YAML file
config = PlatformAutonomousConfig.from_yaml("config/autonomous.yaml")

print(f"Max iterations: {config.default_max_iterations}")
print(f"Default model: {config.default_model}")
```

### Loading Configuration from Environment Variables

```python
from omniforge.skills import PlatformAutonomousConfig
import os

# Set environment variables
os.environ["OMNIFORGE_MAX_ITERATIONS"] = "20"
os.environ["OMNIFORGE_DEFAULT_MODEL"] = "claude-opus-4"

# Load from environment
config = PlatformAutonomousConfig.from_env()

print(f"Max iterations: {config.default_max_iterations}")  # 20
print(f"Default model: {config.default_model}")  # claude-opus-4
```

### Merging Platform Config with Skill Metadata

```python
from omniforge.skills import PlatformAutonomousConfig, merge_configs
from omniforge.skills.models import SkillMetadata

# Platform defaults
platform = PlatformAutonomousConfig(
    default_max_iterations=15,
    default_model="claude-sonnet-4"
)

# Skill with overrides
skill_metadata = SkillMetadata(
    name="data-processor",
    description="Process data files",
    max_iterations=25,  # Override platform default
    timeout_per_iteration="45s"
)

# Merge to get final config
final_config = merge_configs(platform, skill_metadata)

print(f"Final max iterations: {final_config.max_iterations}")  # 25
print(f"Final timeout: {final_config.timeout_per_iteration_ms}")  # 45000
```

### Validating Skill Configuration

```python
from omniforge.skills import PlatformAutonomousConfig, validate_skill_config
from omniforge.skills.models import SkillMetadata

platform = PlatformAutonomousConfig()

# Skill with invalid settings
skill_metadata = SkillMetadata(
    name="test-skill",
    description="Test skill",
    timeout_per_iteration="invalid-format"
)

# Validate
warnings = validate_skill_config(skill_metadata, platform)

if warnings:
    for warning in warnings:
        print(f"Warning: {warning}")
```

### Duration Parsing

```python
from omniforge.skills import parse_duration_ms, is_valid_duration

# Parse duration strings to milliseconds
print(parse_duration_ms("30s"))   # 30000
print(parse_duration_ms("1m"))    # 60000
print(parse_duration_ms("500ms")) # 500

# Check if duration is valid
print(is_valid_duration("30s"))    # True
print(is_valid_duration("invalid")) # False
```

## Environment Variables

All platform configuration settings can be overridden with environment variables:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `OMNIFORGE_MAX_ITERATIONS` | Maximum ReAct loop iterations | 15 |
| `OMNIFORGE_MAX_RETRIES_PER_TOOL` | Max retries per tool | 3 |
| `OMNIFORGE_TIMEOUT_PER_ITERATION_MS` | Timeout per iteration (ms) | 30000 |
| `OMNIFORGE_ENABLE_ERROR_RECOVERY` | Enable error recovery | true |
| `OMNIFORGE_DEFAULT_MODEL` | Default LLM model | claude-sonnet-4 |
| `OMNIFORGE_VISIBILITY_END_USER` | End user visibility level | SUMMARY |
| `OMNIFORGE_VISIBILITY_DEVELOPER` | Developer visibility level | FULL |
| `OMNIFORGE_VISIBILITY_ADMIN` | Admin visibility level | FULL |
| `OMNIFORGE_COST_LIMITS_ENABLED` | Enable cost tracking | false |
| `OMNIFORGE_MAX_COST_PER_EXECUTION_USD` | Max cost per execution | 1.0 |
| `OMNIFORGE_RATE_LIMITS_ENABLED` | Enable rate limiting | false |
| `OMNIFORGE_MAX_ITERATIONS_PER_MINUTE` | Max iterations per minute | 100 |

## Configuration Hierarchy

The configuration system follows a hierarchy:

1. **Platform defaults** (from `autonomous.yaml` or code defaults)
2. **Environment variable overrides** (prefixed with `OMNIFORGE_`)
3. **Skill-level overrides** (from skill metadata)

Skills can override platform defaults by specifying values in their metadata:

```yaml
---
name: my-skill
description: My custom skill
max-iterations: 20        # Override platform default
timeout-per-iteration: 1m # Override platform default
model: claude-opus-4      # Override platform default
---

Skill instructions here...
```

## Duration Format

Timeouts and durations use a human-readable format:

- `ms` - milliseconds (e.g., `500ms`)
- `s` - seconds (e.g., `30s`, `1.5s`)
- `m` - minutes (e.g., `1m`, `2.5m`)

Examples:
- `30s` = 30 seconds = 30,000 milliseconds
- `1m` = 1 minute = 60,000 milliseconds
- `500ms` = 500 milliseconds
