# TASK-016: Add configuration and tuning support

**Priority:** P2 (Nice to Have)
**Estimated Effort:** Small (<1 day)
**Dependencies:** TASK-005, TASK-012

---

## Description

Implement configuration and tuning support (FR-8) for autonomous skill execution. Enable platform administrators to set global defaults and allow skills to override specific settings. Configuration is validated at skill load time with clear error messages.

## Files to Create/Modify

- `src/omniforge/skills/config.py` - Add platform configuration
- `src/omniforge/skills/orchestrator.py` - Configuration loading
- Configuration file: `config/autonomous.yaml`

## Implementation Requirements

### Platform Configuration File

```yaml
# config/autonomous.yaml
autonomous:
  # Default execution settings
  default_max_iterations: 15
  default_max_retries_per_tool: 3
  default_timeout_per_iteration_ms: 30000
  enable_error_recovery: true
  default_model: "claude-sonnet-4"

  # Visibility defaults by role
  visibility:
    end_user: SUMMARY
    developer: FULL
    admin: FULL

  # Cost management (optional)
  cost_limits:
    enabled: false
    max_cost_per_execution_usd: 1.0
    warn_at_pct: 80

  # Rate limiting (optional)
  rate_limits:
    enabled: false
    max_iterations_per_minute: 100
    max_concurrent_executions: 10

  # Script execution (from TASK-007)
  script_execution:
    sandbox_mode: docker  # or "subprocess" for dev
    timeout_seconds: 30
    max_memory_mb: 512
    allow_network: false
```

### PlatformConfig Class

```python
@dataclass
class PlatformAutonomousConfig:
    """Platform-level autonomous execution configuration."""
    default_max_iterations: int = 15
    default_max_retries_per_tool: int = 3
    default_timeout_per_iteration_ms: int = 30000
    enable_error_recovery: bool = True
    default_model: str = "claude-sonnet-4"

    # Visibility
    visibility_end_user: str = "SUMMARY"
    visibility_developer: str = "FULL"
    visibility_admin: str = "FULL"

    # Cost limits
    cost_limits_enabled: bool = False
    max_cost_per_execution_usd: float = 1.0

    # Rate limits
    rate_limits_enabled: bool = False
    max_iterations_per_minute: int = 100

    @classmethod
    def from_yaml(cls, path: str) -> "PlatformAutonomousConfig":
        """Load configuration from YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data.get("autonomous", {}))

    @classmethod
    def from_env(cls) -> "PlatformAutonomousConfig":
        """Load configuration from environment variables."""
        import os
        return cls(
            default_max_iterations=int(os.getenv("OMNIFORGE_MAX_ITERATIONS", "15")),
            default_model=os.getenv("OMNIFORGE_DEFAULT_MODEL", "claude-sonnet-4"),
            # ... other fields
        )
```

### Configuration Validation

```python
def validate_skill_config(
    skill: Skill,
    platform_config: PlatformAutonomousConfig,
) -> list[str]:
    """Validate skill configuration against platform limits.

    Returns list of validation warnings/errors.
    """
    warnings = []

    # Check max_iterations bounds
    if skill.metadata.max_iterations:
        if skill.metadata.max_iterations > 100:
            warnings.append(
                f"max_iterations ({skill.metadata.max_iterations}) exceeds maximum (100)"
            )
        if skill.metadata.max_iterations < 1:
            warnings.append(
                f"max_iterations ({skill.metadata.max_iterations}) must be at least 1"
            )

    # Check timeout format
    if skill.metadata.timeout_per_iteration:
        if not is_valid_duration(skill.metadata.timeout_per_iteration):
            warnings.append(
                f"Invalid timeout format: {skill.metadata.timeout_per_iteration}. "
                f"Use format like '30s', '1m', '500ms'"
            )

    return warnings
```

### Configuration Merging

```python
def merge_configs(
    platform: PlatformAutonomousConfig,
    skill: SkillMetadata,
) -> AutonomousConfig:
    """Merge platform defaults with skill-specific overrides."""
    return AutonomousConfig(
        max_iterations=skill.max_iterations or platform.default_max_iterations,
        max_retries_per_tool=skill.max_retries_per_tool or platform.default_max_retries_per_tool,
        timeout_per_iteration_ms=parse_duration_ms(skill.timeout_per_iteration) or platform.default_timeout_per_iteration_ms,
        model=skill.model or platform.default_model,
        enable_error_recovery=platform.enable_error_recovery,
    )
```

### Duration Parsing

```python
def parse_duration_ms(duration: Optional[str]) -> Optional[int]:
    """Parse duration string to milliseconds.

    Supports: '30s', '1m', '500ms', '1.5s'
    """
    if not duration:
        return None

    match = re.match(r'^(\d+(?:\.\d+)?)\s*(ms|s|m)$', duration.lower())
    if not match:
        return None

    value = float(match.group(1))
    unit = match.group(2)

    if unit == 'ms':
        return int(value)
    elif unit == 's':
        return int(value * 1000)
    elif unit == 'm':
        return int(value * 60 * 1000)

    return None
```

## Acceptance Criteria

- [ ] Platform configuration file loads correctly
- [ ] Environment variable overrides work
- [ ] Skill configuration merged with platform defaults
- [ ] Validation errors are clear and actionable
- [ ] Duration strings parsed correctly (30s, 1m, 500ms)
- [ ] Invalid configurations fail with helpful messages
- [ ] Configuration changes don't require restart (reload support)
- [ ] Unit tests for configuration loading and validation

## Testing

```python
def test_platform_config_from_yaml(tmp_path):
    """Should load configuration from YAML file."""
    config_file = tmp_path / "autonomous.yaml"
    config_file.write_text("""
autonomous:
  default_max_iterations: 20
  default_model: claude-haiku-4
""")
    config = PlatformAutonomousConfig.from_yaml(str(config_file))
    assert config.default_max_iterations == 20
    assert config.default_model == "claude-haiku-4"

def test_merge_configs():
    """Skill overrides should take precedence."""
    platform = PlatformAutonomousConfig(default_max_iterations=15)
    skill = SkillMetadata(name="test", max_iterations=20)
    merged = merge_configs(platform, skill)
    assert merged.max_iterations == 20

def test_duration_parsing():
    """Duration strings should parse correctly."""
    assert parse_duration_ms("30s") == 30000
    assert parse_duration_ms("1m") == 60000
    assert parse_duration_ms("500ms") == 500
    assert parse_duration_ms("invalid") is None

def test_validation_errors():
    """Invalid configurations should produce clear errors."""
    skill = create_skill(max_iterations=200)  # Over limit
    warnings = validate_skill_config(skill, platform_config)
    assert any("exceeds maximum" in w for w in warnings)
```

## Technical Notes

- Use PyYAML for configuration loading
- Support environment variable overrides for cloud deployments
- Consider hot-reload for configuration changes
- Log configuration at startup (INFO level)
- Sensitive values (if any) should be redacted in logs
