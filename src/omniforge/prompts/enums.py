"""Enumerations for prompt management.

This module defines enums for prompt layers, merge behaviors,
experiment status, and validation severity levels.
"""

from enum import Enum


class PromptLayer(str, Enum):
    """Hierarchical layers for prompt composition.

    Prompts are organized in layers from most general (SYSTEM) to most specific
    (USER), allowing for controlled composition and override behavior.
    """

    SYSTEM = "system"
    TENANT = "tenant"
    FEATURE = "feature"
    AGENT = "agent"
    USER = "user"


class MergeBehavior(str, Enum):
    """Behavior when merging prompts at merge points.

    Defines how child prompts are combined with parent prompts during composition.
    """

    APPEND = "append"
    PREPEND = "prepend"
    REPLACE = "replace"
    INJECT = "inject"


class ExperimentStatus(str, Enum):
    """Status of a prompt A/B test experiment.

    Tracks the lifecycle of an experiment from creation to completion.
    """

    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ValidationSeverity(str, Enum):
    """Severity level for prompt validation issues.

    Used to categorize validation findings from errors to informational messages.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
