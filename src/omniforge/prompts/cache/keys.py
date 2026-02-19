"""Cache key generation for prompt caching.

This module provides utilities for generating deterministic cache keys
based on prompt version IDs and variable values.
"""

import hashlib
import json
from typing import Any, Optional


def generate_cache_key(
    version_ids: dict[str, str],
    variables: Optional[dict[str, Any]] = None,
) -> str:
    """Generate a deterministic cache key for a composed prompt.

    The cache key is a SHA256 hash of:
    - Sorted version IDs from all layers (deterministic ordering)
    - Sorted stable variables (excluding highly variable items like user_input)

    Args:
        version_ids: Dictionary mapping layer names to version IDs
        variables: Optional dictionary of variables to include in the key

    Returns:
        SHA256 hash string (hexadecimal)

    Example:
        >>> version_ids = {"system": "v1", "tenant": "v2"}
        >>> variables = {"context": "test", "user_input": "hello"}
        >>> key = generate_cache_key(version_ids, variables)
        >>> isinstance(key, str) and len(key) == 64
        True
    """
    # Create a deterministic string representation of version IDs
    # Sort by layer name to ensure consistent ordering
    sorted_versions = sorted(version_ids.items())
    version_string = json.dumps(sorted_versions, sort_keys=True)

    # Filter out highly variable items that should not affect caching
    # Only include stable variables that affect prompt composition
    stable_variables = {}
    if variables:
        # Exclude variables that change too frequently to be useful for caching
        exclude_vars = {"user_input", "timestamp", "request_id"}
        stable_variables = {
            key: value for key, value in variables.items() if key not in exclude_vars
        }

    # Create deterministic string representation of variables
    # Sort keys to ensure consistent ordering
    variables_string = json.dumps(stable_variables, sort_keys=True)

    # Combine version and variable strings
    combined_string = f"{version_string}|{variables_string}"

    # Generate SHA256 hash
    hash_obj = hashlib.sha256(combined_string.encode("utf-8"))
    return hash_obj.hexdigest()
