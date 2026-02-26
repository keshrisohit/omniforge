"""Artifact storage tools for OmniForge agents.

These tools allow agents to persist and retrieve artifacts via the ReAct
reasoning loop. The agent decides what to store — skills return raw data,
the agent wraps the output in an artifact for durable cross-session access.

Security: tenant_id is always sourced from ToolCallContext, never from
LLM-controlled arguments, preventing cross-tenant escalation.
"""

import time
from typing import Any, Optional

from omniforge.tools.base import (
    BaseTool,
    ParameterType,
    ToolCallContext,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)
from omniforge.tools.registry import ToolRegistry
from omniforge.tools.types import ToolType


class StoreArtifactTool(BaseTool):
    """Tool to persist a skill output as a named, typed artifact.

    Artifacts are tenant-scoped and content-addressable by the returned ID.
    """

    def __init__(self, artifact_store: Any) -> None:
        """Initialize with the artifact store.

        Args:
            artifact_store: ArtifactStore-protocol object for persistence
        """
        self._store = artifact_store

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="store_artifact",
            type=ToolType.FUNCTION,
            description=(
                "Persist data as a named, typed artifact for durable storage. "
                "Use after a skill returns data that should be saved for future retrieval. "
                "Returns an artifact_id that can be used with fetch_artifact."
            ),
            parameters=[
                ToolParameter(
                    name="type",
                    type=ParameterType.STRING,
                    description=(
                        "Artifact category. One of: document, dataset, code, image, structured"
                    ),
                    required=True,
                ),
                ToolParameter(
                    name="title",
                    type=ParameterType.STRING,
                    description="Human-readable artifact title (1–500 characters)",
                    required=True,
                ),
                ToolParameter(
                    name="content",
                    type=ParameterType.STRING,
                    description=(
                        "Artifact content to store. "
                        "Provide as a JSON string for structured data (dict or list), "
                        "or plain text for documents and code."
                    ),
                    required=True,
                ),
                ToolParameter(
                    name="metadata",
                    type=ParameterType.STRING,
                    description=(
                        "Optional JSON string of key-value metadata "
                        "(string, int, float, or bool values only)"
                    ),
                    required=False,
                ),
                ToolParameter(
                    name="mime_type",
                    type=ParameterType.STRING,
                    description="Optional IANA media type (e.g. 'application/json', 'text/plain')",
                    required=False,
                ),
            ],
            timeout_ms=15000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Store an artifact in the tenant-scoped artifact store.

        Args:
            context: Execution context (tenant_id and agent_id sourced here)
            arguments: Dict with type, title, content, and optional metadata/mime_type

        Returns:
            ToolResult with artifact_id on success, or error message
        """
        from omniforge.agents.models import Artifact, ArtifactType

        start = time.time()

        # Validate tenant context is available
        if not context.tenant_id:
            return ToolResult(
                success=False,
                error="Cannot store artifact: tenant_id is not set in execution context.",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Validate and parse artifact type
        raw_type = (arguments.get("type") or "").strip().lower()
        try:
            artifact_type = ArtifactType(raw_type)
        except ValueError:
            valid = ", ".join(t.value for t in ArtifactType)
            return ToolResult(
                success=False,
                error=f"Invalid artifact type '{raw_type}'. Valid types: {valid}",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Validate title
        title = (arguments.get("title") or "").strip()
        if not title:
            return ToolResult(
                success=False,
                error="title is required and must not be empty.",
                duration_ms=int((time.time() - start) * 1000),
            )
        if len(title) > 500:
            return ToolResult(
                success=False,
                error="title must be 500 characters or fewer.",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Validate content
        raw_content = arguments.get("content")
        if raw_content is None:
            return ToolResult(
                success=False,
                error="content is required.",
                duration_ms=int((time.time() - start) * 1000),
            )

        # Parse content: try JSON first for structured types, else keep as string
        import json

        inline_content: Any = raw_content
        if isinstance(raw_content, str):
            try:
                parsed = json.loads(raw_content)
                if isinstance(parsed, (dict, list)):
                    inline_content = parsed
            except (json.JSONDecodeError, ValueError):
                pass  # Keep as plain string

        # Parse optional metadata
        metadata: Optional[dict] = None
        raw_metadata = arguments.get("metadata")
        if raw_metadata:
            if isinstance(raw_metadata, dict):
                metadata = raw_metadata
            elif isinstance(raw_metadata, str):
                try:
                    parsed_meta = json.loads(raw_metadata)
                    if isinstance(parsed_meta, dict):
                        metadata = parsed_meta
                    else:
                        return ToolResult(
                            success=False,
                            error="metadata must be a JSON object (key-value pairs).",
                            duration_ms=int((time.time() - start) * 1000),
                        )
                except (json.JSONDecodeError, ValueError):
                    return ToolResult(
                        success=False,
                        error="metadata must be valid JSON.",
                        duration_ms=int((time.time() - start) * 1000),
                    )

        mime_type: Optional[str] = (arguments.get("mime_type") or "").strip() or None

        try:
            artifact = Artifact(
                type=artifact_type,
                title=title,
                inline_content=inline_content,
                metadata=metadata,
                mime_type=mime_type,
                tenant_id=context.tenant_id,
                created_by_agent_id=context.agent_id,
            )
            artifact_id = await self._store.store(artifact)
            return ToolResult(
                success=True,
                result={
                    "artifact_id": artifact_id,
                    "type": artifact_type.value,
                    "title": title,
                    "message": f"Artifact '{title}' stored successfully with ID '{artifact_id}'.",
                },
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to store artifact: {exc}",
                duration_ms=int((time.time() - start) * 1000),
            )


class FetchArtifactTool(BaseTool):
    """Tool to retrieve a previously stored artifact by ID."""

    def __init__(self, artifact_store: Any) -> None:
        """Initialize with the artifact store.

        Args:
            artifact_store: ArtifactStore-protocol object for retrieval
        """
        self._store = artifact_store

    @property
    def definition(self) -> ToolDefinition:
        """Get tool definition."""
        return ToolDefinition(
            name="fetch_artifact",
            type=ToolType.FUNCTION,
            description=(
                "Retrieve a previously stored artifact by its ID. "
                "Returns the artifact's content, type, title, and metadata. "
                "Only artifacts belonging to the current tenant are accessible."
            ),
            parameters=[
                ToolParameter(
                    name="artifact_id",
                    type=ParameterType.STRING,
                    description="The artifact ID returned by store_artifact",
                    required=True,
                ),
            ],
            timeout_ms=10000,
        )

    async def execute(self, context: ToolCallContext, arguments: dict[str, Any]) -> ToolResult:
        """Fetch an artifact from the tenant-scoped artifact store.

        Args:
            context: Execution context (tenant_id sourced here for isolation)
            arguments: Dict with artifact_id key

        Returns:
            ToolResult with artifact content on success, or not-found error
        """
        start = time.time()

        if not context.tenant_id:
            return ToolResult(
                success=False,
                error="Cannot fetch artifact: tenant_id is not set in execution context.",
                duration_ms=int((time.time() - start) * 1000),
            )

        artifact_id = (arguments.get("artifact_id") or "").strip()
        if not artifact_id:
            return ToolResult(
                success=False,
                error="artifact_id is required.",
                duration_ms=int((time.time() - start) * 1000),
            )

        try:
            artifact = await self._store.fetch(artifact_id, context.tenant_id)
            if artifact is None:
                return ToolResult(
                    success=False,
                    error=f"Artifact '{artifact_id}' not found.",
                    duration_ms=int((time.time() - start) * 1000),
                )
            return ToolResult(
                success=True,
                result={
                    "artifact_id": artifact.id,
                    "type": artifact.type.value,
                    "title": artifact.title,
                    "content": artifact.inline_content,
                    "metadata": artifact.metadata,
                    "mime_type": artifact.mime_type,
                    "created_by_agent_id": artifact.created_by_agent_id,
                },
                duration_ms=int((time.time() - start) * 1000),
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                error=f"Failed to fetch artifact: {exc}",
                duration_ms=int((time.time() - start) * 1000),
            )


def register_artifact_tools(registry: ToolRegistry, artifact_store: Any) -> None:
    """Register StoreArtifactTool and FetchArtifactTool in the given tool registry.

    Args:
        registry: The ToolRegistry to register tools into
        artifact_store: ArtifactStore-protocol object passed to both tools

    Example:
        >>> registry = ToolRegistry()
        >>> register_artifact_tools(registry, my_artifact_store)
        >>> "store_artifact" in registry.list_tools()
        True
    """
    registry.register(StoreArtifactTool(artifact_store))
    registry.register(FetchArtifactTool(artifact_store))
