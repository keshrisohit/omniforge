"""Prompt composition module.

This module provides utilities for composing and rendering prompt templates
using Jinja2 with security sandboxing, and for merging prompts across layers.
"""

from omniforge.prompts.composition.engine import CompositionEngine
from omniforge.prompts.composition.merge import MergeProcessor
from omniforge.prompts.composition.renderer import PromptTemplateLoader, TemplateRenderer

__all__ = ["CompositionEngine", "MergeProcessor", "PromptTemplateLoader", "TemplateRenderer"]
