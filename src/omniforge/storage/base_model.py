"""Centralized SQLAlchemy declarative base for all ORM models.

This module provides a single source of truth for the declarative base class
used by all ORM models across the OmniForge application. Using a single base
ensures all models are registered with the same metadata registry, preventing
table fragmentation and schema creation issues.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models in OmniForge.

    All SQLAlchemy ORM models must inherit from this class to ensure proper
    table registration and schema management.
    """

    pass
