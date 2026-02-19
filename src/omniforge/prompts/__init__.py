"""Prompt management module.

This module provides prompt templating, versioning, composition,
and A/B testing capabilities for OmniForge agents.
"""

from omniforge.prompts.defaults import get_default_registry, populate_default_templates
from omniforge.prompts.enums import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
    ValidationSeverity,
)
from omniforge.prompts.errors import (
    ExperimentNotFoundError,
    ExperimentStateError,
    MergePointConflictError,
    PromptCompositionError,
    PromptConcurrencyError,
    PromptError,
    PromptLockViolationError,
    PromptNotFoundError,
    PromptRenderError,
    PromptValidationError,
    PromptVersionNotFoundError,
)
from omniforge.prompts.models import (
    ComposedPrompt,
    ExperimentVariant,
    MergePointDefinition,
    Prompt,
    PromptExperiment,
    PromptVersion,
    VariableSchema,
)
from omniforge.prompts.registry import PromptTemplateRegistry
from omniforge.prompts.sdk import PromptConfig, PromptManager
from omniforge.prompts.security import (
    LAYER_ACCESS,
    can_access_tenant_prompts,
    can_modify_layer,
    check_prompt_access,
)

__all__ = [
    # Enums
    "ExperimentStatus",
    "MergeBehavior",
    "PromptLayer",
    "ValidationSeverity",
    # Errors
    "ExperimentNotFoundError",
    "ExperimentStateError",
    "MergePointConflictError",
    "PromptCompositionError",
    "PromptConcurrencyError",
    "PromptError",
    "PromptLockViolationError",
    "PromptNotFoundError",
    "PromptRenderError",
    "PromptValidationError",
    "PromptVersionNotFoundError",
    # Models
    "ComposedPrompt",
    "ExperimentVariant",
    "MergePointDefinition",
    "Prompt",
    "PromptExperiment",
    "PromptVersion",
    "VariableSchema",
    # Registry
    "PromptTemplateRegistry",
    "get_default_registry",
    "populate_default_templates",
    # SDK
    "PromptConfig",
    "PromptManager",
    # Security
    "LAYER_ACCESS",
    "can_access_tenant_prompts",
    "can_modify_layer",
    "check_prompt_access",
]
