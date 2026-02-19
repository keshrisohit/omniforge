"""Pydantic models for prompt management.

This module defines data models for prompts, versions, experiments,
merge points, and composed prompt results.
"""

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator

from omniforge.prompts.enums import (
    ExperimentStatus,
    MergeBehavior,
    PromptLayer,
)


class MergePointDefinition(BaseModel):
    """Definition of a merge point in a prompt.

    Merge points allow child prompts to inject, append, or replace content
    at specific locations in parent prompts.

    Attributes:
        name: Unique name for the merge point
        behavior: How child content should be merged
        required: Whether child layers must provide content for this merge point
        locked: Whether this merge point can be modified by child layers
        description: Optional human-readable description
    """

    name: str = Field(..., min_length=1, max_length=255)
    behavior: MergeBehavior
    required: bool = False
    locked: bool = False
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name_format(cls, value: str) -> str:
        """Validate that merge point name is alphanumeric with underscores.

        Args:
            value: The name to validate

        Returns:
            The validated name

        Raises:
            ValueError: If name format is invalid
        """
        if not value.replace("_", "").replace("-", "").isalnum():
            raise ValueError(
                "Merge point name must contain only alphanumeric characters, "
                "underscores, and hyphens"
            )
        return value


class VariableSchema(BaseModel):
    """JSON Schema definition for prompt variables.

    Defines the structure and validation rules for variables that can be
    substituted into prompt templates.

    Attributes:
        properties: Dictionary mapping variable names to their JSON schema
        required: List of required variable names
    """

    properties: dict[str, dict[str, Any]] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)

    @field_validator("required")
    @classmethod
    def validate_required_in_properties(cls, value: list[str], info: Any) -> list[str]:
        """Validate that all required variables are defined in properties.

        Args:
            value: The required variables list
            info: Validation context with other field values

        Returns:
            The validated required list

        Raises:
            ValueError: If required variable is not in properties
        """
        if hasattr(info, "data") and "properties" in info.data:
            properties = info.data["properties"]
            for var_name in value:
                if var_name not in properties:
                    raise ValueError(
                        f"Required variable '{var_name}' must be defined in properties"
                    )
        return value


class Prompt(BaseModel):
    """Full prompt model with layer, content, and configuration.

    Prompts are organized in hierarchical layers and support versioning,
    merge points, and variable substitution.

    Attributes:
        id: Unique identifier for the prompt
        layer: Hierarchical layer (SYSTEM, TENANT, FEATURE, AGENT, USER)
        scope_id: Scope identifier (e.g., tenant_id, agent_id)
        name: Human-readable prompt name
        content: The prompt template content
        merge_points: List of merge point definitions
        variables_schema: Schema for prompt variables
        parent_prompt_id: Optional ID of parent prompt in hierarchy
        is_locked: Whether this prompt is locked from modifications
        is_active: Whether this prompt is active (not soft-deleted)
        tenant_id: Tenant ID for multi-tenancy isolation
        created_at: Timestamp when prompt was created
        updated_at: Timestamp of last update
        version: Current version number
    """

    id: str = Field(..., min_length=1, max_length=255)
    layer: PromptLayer
    scope_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    content: str
    merge_points: list[MergePointDefinition] = Field(default_factory=list)
    variables_schema: Optional[VariableSchema] = None
    parent_prompt_id: Optional[str] = None
    is_locked: bool = False
    is_active: bool = True
    tenant_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = Field(default=1, ge=1)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        """Validate that content is not empty or whitespace-only.

        Args:
            value: The content to validate

        Returns:
            The validated content

        Raises:
            ValueError: If content is empty or whitespace-only
        """
        if not value or not value.strip():
            raise ValueError("Prompt content cannot be empty or whitespace-only")
        return value

    @field_validator("merge_points")
    @classmethod
    def validate_unique_merge_point_names(
        cls, value: list[MergePointDefinition]
    ) -> list[MergePointDefinition]:
        """Validate that merge point names are unique.

        Args:
            value: The merge points list to validate

        Returns:
            The validated merge points list

        Raises:
            ValueError: If duplicate merge point names are found
        """
        names = [mp.name for mp in value]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate merge point names found: {', '.join(set(duplicates))}")
        return value


class PromptVersion(BaseModel):
    """Immutable version snapshot of a prompt.

    Each version captures the complete state of a prompt at a point in time,
    enabling rollback and historical tracking.

    Attributes:
        id: Unique identifier for this version
        prompt_id: ID of the parent prompt
        version_number: Sequential version number
        content: The prompt content at this version
        merge_points: Merge point definitions at this version
        variables_schema: Variable schema at this version
        change_message: Optional description of changes in this version
        created_by: Optional ID of user who created this version
        created_at: Timestamp when version was created
    """

    id: str = Field(..., min_length=1, max_length=255)
    prompt_id: str = Field(..., min_length=1, max_length=255)
    version_number: int = Field(..., ge=1)
    content: str
    merge_points: list[MergePointDefinition] = Field(default_factory=list)
    variables_schema: Optional[VariableSchema] = None
    change_message: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        """Validate that content is not empty or whitespace-only.

        Args:
            value: The content to validate

        Returns:
            The validated content

        Raises:
            ValueError: If content is empty or whitespace-only
        """
        if not value or not value.strip():
            raise ValueError("Prompt content cannot be empty or whitespace-only")
        return value


class ExperimentVariant(BaseModel):
    """A/B test variant with traffic allocation.

    Each variant represents a different prompt version being tested,
    with a percentage of traffic allocated to it.

    Attributes:
        id: Unique identifier for the variant
        name: Human-readable variant name
        prompt_version_id: ID of the prompt version to use
        traffic_percentage: Percentage of traffic allocated (0-100)
        metrics: Optional dictionary of performance metrics
    """

    id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    prompt_version_id: str = Field(..., min_length=1, max_length=255)
    traffic_percentage: float = Field(..., ge=0, le=100)
    metrics: Optional[dict[str, Union[int, float]]] = None

    @field_validator("traffic_percentage")
    @classmethod
    def validate_traffic_percentage_precision(cls, value: float) -> float:
        """Validate that traffic percentage has at most 2 decimal places.

        Args:
            value: The traffic percentage to validate

        Returns:
            The validated traffic percentage

        Raises:
            ValueError: If more than 2 decimal places
        """
        if round(value, 2) != value:
            raise ValueError("Traffic percentage must have at most 2 decimal places")
        return value


class PromptExperiment(BaseModel):
    """A/B test experiment for prompt optimization.

    Experiments enable testing multiple prompt versions simultaneously
    to determine which performs best.

    Attributes:
        id: Unique identifier for the experiment
        name: Human-readable experiment name
        description: Optional detailed description
        prompt_id: ID of the prompt being tested
        status: Current experiment status
        variants: List of experiment variants
        success_metric: Name of the metric to optimize
        start_time: Optional timestamp when experiment started
        end_time: Optional timestamp when experiment ended
        created_by: Optional ID of user who created the experiment
        created_at: Timestamp when experiment was created
        updated_at: Timestamp of last update
    """

    id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    prompt_id: str = Field(..., min_length=1, max_length=255)
    status: ExperimentStatus
    variants: list[ExperimentVariant] = Field(..., min_length=2)
    success_metric: str = Field(..., min_length=1, max_length=255)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("variants")
    @classmethod
    def validate_traffic_allocation_sum(
        cls, value: list[ExperimentVariant]
    ) -> list[ExperimentVariant]:
        """Validate that traffic percentages sum to 100%.

        Args:
            value: The variants list to validate

        Returns:
            The validated variants list

        Raises:
            ValueError: If traffic allocation does not sum to 100%
        """
        total_traffic = sum(variant.traffic_percentage for variant in value)
        # Allow small floating point precision errors
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"Variant traffic percentages must sum to 100%, got {total_traffic}")
        return value

    @field_validator("variants")
    @classmethod
    def validate_unique_variant_names(
        cls, value: list[ExperimentVariant]
    ) -> list[ExperimentVariant]:
        """Validate that variant names are unique.

        Args:
            value: The variants list to validate

        Returns:
            The validated variants list

        Raises:
            ValueError: If duplicate variant names are found
        """
        names = [variant.name for variant in value]
        if len(names) != len(set(names)):
            duplicates = [name for name in names if names.count(name) > 1]
            raise ValueError(f"Duplicate variant names found: {', '.join(set(duplicates))}")
        return value


class ComposedPrompt(BaseModel):
    """Result of composing prompts across layers.

    Contains the final rendered prompt after merging all layers,
    along with metadata about the composition process.

    Attributes:
        content: The final composed prompt content
        layer_versions: Dictionary mapping layers to version numbers used
        cache_key: Optional cache key for the composed prompt
        composition_time_ms: Time taken to compose the prompt in milliseconds
        composed_at: Timestamp when composition was performed
    """

    content: str
    layer_versions: dict[str, int] = Field(default_factory=dict)
    cache_key: Optional[str] = None
    composition_time_ms: float = Field(..., ge=0)
    composed_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        """Validate that content is not empty or whitespace-only.

        Args:
            value: The content to validate

        Returns:
            The validated content

        Raises:
            ValueError: If content is empty or whitespace-only
        """
        if not value or not value.strip():
            raise ValueError("Composed prompt content cannot be empty or whitespace-only")
        return value
