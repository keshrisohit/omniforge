"""Model registry to ensure all ORM models are imported before table creation.

This module provides a centralized registration mechanism to ensure all ORM model
modules are imported before any metadata operations (like create_all or drop_all).
This prevents incomplete schema creation due to lazy imports.
"""

# Global flag to track if models have been registered
_models_registered = False


def register_all_models() -> None:
    """Import all ORM model modules to register them with Base.metadata.

    This function must be called before any metadata operations (create_all, drop_all)
    to ensure all tables are registered. It imports all model modules, triggering
    class definitions that register tables with the shared Base.metadata.

    This function is idempotent - calling it multiple times has no additional effect
    after the first call. This prevents duplicate index creation errors in test suites.

    The imports use `as _` to indicate the modules are imported for side effects
    (class registration) rather than direct use.
    """
    global _models_registered

    # Skip if models are already registered
    if _models_registered:
        return

    # Storage models (cost, usage, reasoning, audit, oauth)
    from omniforge.storage import models as _  # noqa: F401

    # Conversation models (conversations, messages)
    from omniforge.conversation import orm as _  # noqa: F401

    # Builder models (agent configs, credentials, executions, public skills)
    from omniforge.builder.models import orm as _  # noqa: F401

    # Mark as registered
    _models_registered = True
