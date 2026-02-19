"""Experiment management for A/B testing prompts.

This package provides functionality for creating and managing A/B test experiments,
including traffic allocation, variant selection, and statistical analysis.
"""

from omniforge.prompts.experiments.allocation import TrafficAllocator
from omniforge.prompts.experiments.analysis import AnalysisResult, ExperimentAnalyzer
from omniforge.prompts.experiments.manager import ExperimentManager, VariantSelection

__all__ = [
    "ExperimentManager",
    "TrafficAllocator",
    "ExperimentAnalyzer",
    "AnalysisResult",
    "VariantSelection",
]
