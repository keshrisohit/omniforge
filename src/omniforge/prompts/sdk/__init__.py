"""SDK module for developer-facing prompt management API.

This module provides the high-level SDK interface for programmatic
prompt management, including the PromptManager and PromptConfig classes.
"""

from omniforge.prompts.sdk.config import PromptConfig
from omniforge.prompts.sdk.manager import PromptManager

__all__ = ["PromptConfig", "PromptManager"]
