"""LLM tracing integration with Opik.

This module provides optional Opik integration for LiteLLM calls.
If OPIK_API_KEY is set, all LLM calls are automatically traced.
"""

import os
from typing import Optional


def setup_opik_tracing() -> bool:
    """Setup Opik tracing for LiteLLM if configured.

    Checks for OPIK_API_KEY environment variable and patches
    litellm.acompletion with Opik tracking.

    Returns:
        True if Opik tracing was enabled, False otherwise
    """
    opik_api_key = os.getenv("OPIK_API_KEY")
    opik_workspace = os.getenv("OPIK_WORKSPACE", "default")
    opik_project = os.getenv("OPIK_PROJECT_NAME", "omniforge")

    if not opik_api_key:
        return False

    try:
        # Import Opik and LiteLLM
        import litellm
        from opik.integrations.litellm import track_completion

        # Configure Opik
        import opik

        opik.configure(api_key=opik_api_key, workspace=opik_workspace)

        # Wrap litellm.acompletion with Opik tracking
        litellm.acompletion = track_completion(project_name=opik_project)(
            litellm.acompletion
        )

        print(f"✓ Opik tracing enabled (workspace: {opik_workspace}, project: {opik_project})")
        return True

    except ImportError as e:
        # Only print if opik module is actually missing (not other import errors)
        if "opik" in str(e):
            print(
                "Opik not installed. Install with: pip install opik\n"
                "Tracing will be disabled."
            )
        return False
    except Exception as e:
        print(f"Failed to setup Opik tracing: {e}")
        return False


def get_tracing_status() -> dict[str, Optional[str]]:
    """Get current tracing configuration status.

    Returns:
        Dict with tracing status information
    """
    return {
        "enabled": os.getenv("OPIK_API_KEY") is not None,
        "workspace": os.getenv("OPIK_WORKSPACE", "default"),
        "api_key_set": bool(os.getenv("OPIK_API_KEY")),
    }
