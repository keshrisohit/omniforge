"""Evaluation test set for intent classification accuracy.

This module provides comprehensive evaluation of LLM intent classification
using 30+ test cases across all ActionType values. Runs against real LLM
to measure accuracy, precision, and recall.

Usage:
    # Run evaluation (requires OPENAI_API_KEY or other LLM provider)
    pytest tests/conversation/test_intent_evaluation.py -m eval -v

    # Skip in CI (marked with skipif)
    pytest  # Will skip evaluation by default in CI

The evaluation generates a detailed report including:
- Overall accuracy
- Per-class precision and recall
- Confusion matrix
- Failed cases with explanations
"""

import asyncio
import os
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

import pytest

from omniforge.conversation.intent_analyzer import LLMIntentAnalyzer
from omniforge.conversation.models import Message, MessageRole
from omniforge.routing.models import ActionType


@dataclass
class IntentTestCase:
    """Single test case for intent classification evaluation.

    Attributes:
        message: User message to classify
        expected_action: Ground truth ActionType
        description: Explanation of why this classification is correct
        conversation_history: Optional conversation context
    """

    message: str
    expected_action: ActionType
    description: str
    conversation_history: Optional[list[Message]] = None


# Test cases organized by ActionType with diverse phrasing
EVALUATION_TEST_CASES = [
    # CREATE_AGENT cases (8 cases)
    IntentTestCase(
        message="Create a customer service agent",
        expected_action=ActionType.CREATE_AGENT,
        description="Direct agent creation request",
    ),
    IntentTestCase(
        message="Build me a chatbot for technical support",
        expected_action=ActionType.CREATE_AGENT,
        description="Chatbot creation with specific purpose",
    ),
    IntentTestCase(
        message="I need an AI assistant to help with data analysis",
        expected_action=ActionType.CREATE_AGENT,
        description="Assistant creation with domain focus",
    ),
    IntentTestCase(
        message="Set up a new agent that monitors stock prices",
        expected_action=ActionType.CREATE_AGENT,
        description="Agent creation with monitoring task",
    ),
    IntentTestCase(
        message="Make an agent for automated email responses",
        expected_action=ActionType.CREATE_AGENT,
        description="Short imperative agent creation",
    ),
    IntentTestCase(
        message="Can you create a bot to schedule meetings?",
        expected_action=ActionType.CREATE_AGENT,
        description="Polite agent creation request",
    ),
    IntentTestCase(
        message="I want to design a new agent for content moderation",
        expected_action=ActionType.CREATE_AGENT,
        description="Design-focused agent creation",
    ),
    IntentTestCase(
        message="Help me build an agent that processes invoices",
        expected_action=ActionType.CREATE_AGENT,
        description="Collaborative agent creation request",
    ),
    # CREATE_SKILL cases (6 cases)
    IntentTestCase(
        message="Add sentiment analysis skill",
        expected_action=ActionType.CREATE_SKILL,
        description="Direct skill addition request",
    ),
    IntentTestCase(
        message="Create a skill for parsing CSV files",
        expected_action=ActionType.CREATE_SKILL,
        description="Skill creation with specific function",
    ),
    IntentTestCase(
        message="I need a new skill that sends email notifications",
        expected_action=ActionType.CREATE_SKILL,
        description="Skill creation with action focus",
    ),
    IntentTestCase(
        message="Build a capability for web scraping",
        expected_action=ActionType.CREATE_SKILL,
        description="Capability synonym for skill",
    ),
    IntentTestCase(
        message="Add a tool for translating text",
        expected_action=ActionType.CREATE_SKILL,
        description="Tool synonym for skill",
    ),
    IntentTestCase(
        message="Create a skill that analyzes sentiment from social media posts",
        expected_action=ActionType.CREATE_SKILL,
        description="Detailed skill creation request",
    ),
    # UPDATE_AGENT cases (5 cases)
    IntentTestCase(
        message="Update the pricing agent's description",
        expected_action=ActionType.UPDATE_AGENT,
        description="Specific field update request",
    ),
    IntentTestCase(
        message="Change my agent to run daily instead of weekly",
        expected_action=ActionType.UPDATE_AGENT,
        description="Schedule configuration change",
    ),
    IntentTestCase(
        message="Modify the data processor agent settings",
        expected_action=ActionType.UPDATE_AGENT,
        description="General settings modification",
    ),
    IntentTestCase(
        message="I want to update my chatbot's personality",
        expected_action=ActionType.UPDATE_AGENT,
        description="Personality/behavior update",
    ),
    IntentTestCase(
        message="Edit the customer service agent configuration",
        expected_action=ActionType.UPDATE_AGENT,
        description="Configuration edit request",
    ),
    # QUERY_INFO cases (6 cases)
    IntentTestCase(
        message="What agents do I have?",
        expected_action=ActionType.QUERY_INFO,
        description="Direct agent listing query",
    ),
    IntentTestCase(
        message="How does the platform work?",
        expected_action=ActionType.QUERY_INFO,
        description="Platform explanation request",
    ),
    IntentTestCase(
        message="List all my skills",
        expected_action=ActionType.QUERY_INFO,
        description="Skill listing command",
    ),
    IntentTestCase(
        message="Can you show me the available agents?",
        expected_action=ActionType.QUERY_INFO,
        description="Polite listing request",
    ),
    IntentTestCase(
        message="What can I do with this platform?",
        expected_action=ActionType.QUERY_INFO,
        description="Capabilities inquiry",
    ),
    IntentTestCase(
        message="Tell me about my data analysis agent",
        expected_action=ActionType.QUERY_INFO,
        description="Specific agent information request",
    ),
    # EXECUTE_TASK cases (6 cases)
    IntentTestCase(
        message="Run the data analysis agent",
        expected_action=ActionType.EXECUTE_TASK,
        description="Direct agent execution command",
    ),
    IntentTestCase(
        message="Execute the report generation task",
        expected_action=ActionType.EXECUTE_TASK,
        description="Task execution with 'execute' verb",
    ),
    IntentTestCase(
        message="Process this dataset for me",
        expected_action=ActionType.EXECUTE_TASK,
        description="Implicit task execution request",
    ),
    IntentTestCase(
        message="Start the customer service bot",
        expected_action=ActionType.EXECUTE_TASK,
        description="Bot start command",
    ),
    IntentTestCase(
        message="Analyze the sales data from last quarter",
        expected_action=ActionType.EXECUTE_TASK,
        description="Analysis task with specific data",
    ),
    IntentTestCase(
        message="Can you run my sentiment analysis agent on these tweets?",
        expected_action=ActionType.EXECUTE_TASK,
        description="Agent execution with data reference",
    ),
    # MANAGE_PLATFORM cases (3 cases)
    IntentTestCase(
        message="Configure my dashboard settings",
        expected_action=ActionType.MANAGE_PLATFORM,
        description="Dashboard configuration request",
    ),
    IntentTestCase(
        message="Update platform settings",
        expected_action=ActionType.MANAGE_PLATFORM,
        description="Platform settings update",
    ),
    IntentTestCase(
        message="Manage user permissions",
        expected_action=ActionType.MANAGE_PLATFORM,
        description="User management request",
    ),
    # UNKNOWN cases (7 cases including edge cases)
    IntentTestCase(
        message="Hello",
        expected_action=ActionType.UNKNOWN,
        description="Simple greeting without clear intent",
    ),
    IntentTestCase(
        message="I'm not sure what I need",
        expected_action=ActionType.UNKNOWN,
        description="User expressing uncertainty",
    ),
    IntentTestCase(
        message="asdf",
        expected_action=ActionType.UNKNOWN,
        description="Random text without meaning",
    ),
    IntentTestCase(
        message="🎉",
        expected_action=ActionType.UNKNOWN,
        description="Single emoji message",
    ),
    IntentTestCase(
        message="hmm...",
        expected_action=ActionType.UNKNOWN,
        description="Thinking/pondering expression",
    ),
    IntentTestCase(
        message="",
        expected_action=ActionType.UNKNOWN,
        description="Empty message",
    ),
    IntentTestCase(
        message="What?",
        expected_action=ActionType.UNKNOWN,
        description="Unclear question",
    ),
]


@dataclass
class EvaluationMetrics:
    """Metrics for intent classification evaluation.

    Attributes:
        accuracy: Overall classification accuracy (0.0-1.0)
        per_class_precision: Precision for each ActionType
        per_class_recall: Recall for each ActionType
        confusion_matrix: Predicted vs expected counts
        failed_cases: List of (test_case, predicted_action) for failures
    """

    accuracy: float
    per_class_precision: dict[ActionType, float]
    per_class_recall: dict[ActionType, float]
    confusion_matrix: dict[tuple[ActionType, ActionType], int]
    failed_cases: list[tuple[IntentTestCase, ActionType]]


async def evaluate_intent_classification(
    analyzer: LLMIntentAnalyzer,
    test_cases: list[IntentTestCase],
) -> EvaluationMetrics:
    """Evaluate intent classification accuracy on test set.

    Args:
        analyzer: LLMIntentAnalyzer instance to evaluate
        test_cases: List of test cases with ground truth labels

    Returns:
        EvaluationMetrics with accuracy, precision, recall, and confusion matrix
    """
    # Run all classifications
    results = []
    for test_case in test_cases:
        try:
            decision = await analyzer.analyze(
                test_case.message,
                conversation_history=test_case.conversation_history,
            )
            results.append((test_case, decision.action_type))
        except Exception as e:
            # If classification fails, mark as UNKNOWN
            print(f"Classification error for '{test_case.message}': {e}")
            results.append((test_case, ActionType.UNKNOWN))

    # Calculate accuracy
    correct = sum(
        1 for test_case, predicted in results if test_case.expected_action == predicted
    )
    accuracy = correct / len(results) if results else 0.0

    # Build confusion matrix: (expected, predicted) -> count
    confusion_matrix: dict[tuple[ActionType, ActionType], int] = defaultdict(int)
    for test_case, predicted in results:
        confusion_matrix[(test_case.expected_action, predicted)] += 1

    # Calculate per-class precision and recall
    per_class_precision: dict[ActionType, float] = {}
    per_class_recall: dict[ActionType, float] = {}

    for action_type in ActionType:
        # True positives: predicted=action_type AND expected=action_type
        tp = confusion_matrix.get((action_type, action_type), 0)

        # False positives: predicted=action_type AND expected!=action_type
        fp = sum(
            confusion_matrix.get((expected, action_type), 0)
            for expected in ActionType
            if expected != action_type
        )

        # False negatives: predicted!=action_type AND expected=action_type
        fn = sum(
            confusion_matrix.get((action_type, predicted), 0)
            for predicted in ActionType
            if predicted != action_type
        )

        # Precision = TP / (TP + FP)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        per_class_precision[action_type] = precision

        # Recall = TP / (TP + FN)
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        per_class_recall[action_type] = recall

    # Collect failed cases
    failed_cases = [
        (test_case, predicted)
        for test_case, predicted in results
        if test_case.expected_action != predicted
    ]

    return EvaluationMetrics(
        accuracy=accuracy,
        per_class_precision=per_class_precision,
        per_class_recall=per_class_recall,
        confusion_matrix=dict(confusion_matrix),
        failed_cases=failed_cases,
    )


def print_evaluation_report(metrics: EvaluationMetrics, total_cases: int) -> None:
    """Print detailed evaluation report to stdout.

    Args:
        metrics: Calculated evaluation metrics
        total_cases: Total number of test cases evaluated
    """
    print("\n" + "=" * 80)
    print("INTENT CLASSIFICATION EVALUATION REPORT")
    print("=" * 80)

    # Overall accuracy
    print(f"\nOverall Accuracy: {metrics.accuracy:.2%} ({int(metrics.accuracy * total_cases)}/{total_cases})")  # noqa: E501

    # Per-class metrics
    print("\n" + "-" * 80)
    print("Per-Class Metrics:")
    print("-" * 80)
    print(f"{'Action Type':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
    print("-" * 80)

    for action_type in ActionType:
        precision = metrics.per_class_precision.get(action_type, 0.0)
        recall = metrics.per_class_recall.get(action_type, 0.0)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        print(f"{action_type.value:<20} {precision:>10.2%}  {recall:>10.2%}  {f1:>10.2%}")

    # Confusion matrix
    print("\n" + "-" * 80)
    print("Confusion Matrix (Expected vs Predicted):")
    print("-" * 80)

    # Get all action types for matrix headers
    action_types = list(ActionType)
    header = "Expected \\ Predicted".ljust(20)
    for action_type in action_types:
        header += f" {action_type.value[:6]:>6}"
    print(header)
    print("-" * 80)

    for expected in action_types:
        row = f"{expected.value:<20}"
        for predicted in action_types:
            count = metrics.confusion_matrix.get((expected, predicted), 0)
            row += f" {count:>6}"
        print(row)

    # Failed cases
    if metrics.failed_cases:
        print("\n" + "-" * 80)
        print(f"Failed Cases ({len(metrics.failed_cases)}):")
        print("-" * 80)
        for i, (test_case, predicted) in enumerate(metrics.failed_cases, 1):
            print(f"\n{i}. Message: \"{test_case.message}\"")
            print(f"   Expected: {test_case.expected_action.value}")
            print(f"   Predicted: {predicted.value}")
            print(f"   Reason: {test_case.description}")
    else:
        print("\n" + "-" * 80)
        print("✓ All test cases passed!")
        print("-" * 80)

    print("\n" + "=" * 80)


@pytest.mark.eval
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Evaluation uses real LLM calls and costs money - skip in CI",
)
@pytest.mark.asyncio
async def test_intent_classification_evaluation() -> None:
    """Evaluate LLM intent classification accuracy on comprehensive test set.

    This test runs the real LLMIntentAnalyzer on 30+ diverse test cases
    covering all ActionType values. It generates a detailed evaluation
    report with accuracy, precision, recall, and confusion matrix.

    Run manually with:
        pytest tests/conversation/test_intent_evaluation.py -m eval -v

    Requires LLM API key to be set (OPENAI_API_KEY, OMNIFORGE_OPENROUTER_API_KEY,
    or OMNIFORGE_GROQ_API_KEY).

    Skipped in CI to avoid LLM costs.
    """
    # Create analyzer - use openrouter or groq if available for cost efficiency
    # Default to gpt-4o-mini if using OpenAI
    model = os.getenv("OMNIFORGE_LLM_DEFAULT_MODEL", "gpt-4o-mini")
    analyzer = LLMIntentAnalyzer(
        model=model,
        temperature=0.1,
        max_tokens=500,
        timeout=5.0,  # Longer timeout for evaluation
    )

    # Run evaluation
    print(f"\nRunning evaluation on {len(EVALUATION_TEST_CASES)} test cases...")
    metrics = await evaluate_intent_classification(analyzer, EVALUATION_TEST_CASES)

    # Print detailed report
    print_evaluation_report(metrics, len(EVALUATION_TEST_CASES))

    # Assert minimum accuracy threshold
    # Set to 0.75 (75%) as baseline based on evaluation results
    # Current performance: ~88% with groq/llama-3.3-70b-versatile
    min_accuracy = 0.75
    assert metrics.accuracy >= min_accuracy, (
        f"Intent classification accuracy {metrics.accuracy:.2%} "
        f"below minimum threshold {min_accuracy:.2%}"
    )


@pytest.mark.eval
@pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Evaluation uses real LLM calls and costs money - skip in CI",
)
@pytest.mark.asyncio
async def test_context_dependent_classification() -> None:
    """Test intent classification with conversation context.

    Verifies that the analyzer correctly uses conversation history
    for context-dependent messages like 'yes', 'do that', etc.
    """
    model = os.getenv("OMNIFORGE_LLM_DEFAULT_MODEL", "gpt-4o-mini")
    analyzer = LLMIntentAnalyzer(model=model, temperature=0.1)

    # Context: user previously asked about creating an agent
    conversation_id = uuid4()
    conversation_history = [
        Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content="Can I create an agent for customer service?",
        ),
        Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content="Yes, you can create an agent for customer service. Would you like to proceed?",  # noqa: E501
        ),
    ]

    # Test cases with context
    context_cases = [
        IntentTestCase(
            message="yes",
            expected_action=ActionType.CREATE_AGENT,
            description="Affirmative response in agent creation context",
            conversation_history=conversation_history,
        ),
        IntentTestCase(
            message="do that",
            expected_action=ActionType.CREATE_AGENT,
            description="Imperative response in agent creation context",
            conversation_history=conversation_history,
        ),
        IntentTestCase(
            message="go ahead",
            expected_action=ActionType.CREATE_AGENT,
            description="Confirmation in agent creation context",
            conversation_history=conversation_history,
        ),
    ]

    metrics = await evaluate_intent_classification(analyzer, context_cases)
    print_evaluation_report(metrics, len(context_cases))

    # Context-dependent cases should have high accuracy
    assert metrics.accuracy >= 0.60, (
        f"Context-dependent accuracy {metrics.accuracy:.2%} too low"
    )
