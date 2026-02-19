"""Unit tests for LLM intent analyzer."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from omniforge.conversation.intent_analyzer import IntentAnalysisError, LLMIntentAnalyzer
from omniforge.conversation.models import Message, MessageRole
from omniforge.routing.models import ActionType


class TestLLMIntentAnalyzer:
    """Tests for LLMIntentAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> LLMIntentAnalyzer:
        """Create analyzer instance with test configuration."""
        return LLMIntentAnalyzer(model="openrouter/arcee-ai/trinity-large-preview:free", temperature=0.1, max_tokens=500, timeout=2.0)

    @pytest.fixture
    def mock_llm_response(self) -> MagicMock:
        """Create mock LLM response with valid JSON."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": 0.95,
                "entities": {"agent_name": "TestBot"},
                "reasoning": "User wants to create a new agent",
            }
        )
        return response

    @pytest.mark.asyncio
    async def test_analyze_success(
        self, analyzer: LLMIntentAnalyzer, mock_llm_response: MagicMock
    ) -> None:
        """Analyzer should successfully parse valid LLM response."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_llm_response

            decision = await analyzer.analyze("create an agent called TestBot")

            assert decision.action_type == ActionType.CREATE_AGENT
            assert decision.confidence == 0.95
            assert decision.entities == {"agent_name": "TestBot"}
            assert "create a new agent" in decision.reasoning.lower()

    @pytest.mark.asyncio
    async def test_analyze_with_conversation_history(
        self, analyzer: LLMIntentAnalyzer, mock_llm_response: MagicMock
    ) -> None:
        """Analyzer should include conversation history in LLM messages."""
        conversation_id = uuid4()
        history = [
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content="Hello",
            ),
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="Hi! How can I help?",
            ),
        ]

        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_llm_response

            await analyzer.analyze("create an agent", conversation_history=history)

            # Verify history was passed to _call_llm
            messages = mock_call.call_args[0][0]
            assert len(messages) >= 4  # system + 2 history + current
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "Hello"
            assert messages[2]["role"] == "assistant"
            assert messages[2]["content"] == "Hi! How can I help?"

    @pytest.mark.asyncio
    async def test_analyze_with_available_agents(
        self, analyzer: LLMIntentAnalyzer, mock_llm_response: MagicMock
    ) -> None:
        """Analyzer should include available agents in system prompt."""
        available_agents = [
            {"id": "agent-1", "name": "TestAgent"},
            {"id": "agent-2", "name": "DataBot"},
        ]

        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = mock_llm_response

            await analyzer.analyze("use TestAgent", available_agents=available_agents)

            # Verify agents were included in system prompt
            messages = mock_call.call_args[0][0]
            system_prompt = messages[0]["content"]
            assert "TestAgent" in system_prompt
            assert "agent-1" in system_prompt
            assert "DataBot" in system_prompt

    @pytest.mark.asyncio
    async def test_analyze_timeout(self, analyzer: LLMIntentAnalyzer) -> None:
        """Analyzer should raise IntentAnalysisError on timeout."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            # Simulate timeout
            mock_call.side_effect = asyncio.TimeoutError()

            with pytest.raises(IntentAnalysisError, match="timed out after 2.0s"):
                await analyzer.analyze("create an agent")

    @pytest.mark.asyncio
    async def test_analyze_llm_error(self, analyzer: LLMIntentAnalyzer) -> None:
        """Analyzer should raise IntentAnalysisError on LLM API error."""
        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("API error")

            with pytest.raises(IntentAnalysisError, match="Intent analysis failed"):
                await analyzer.analyze("create an agent")

    @pytest.mark.asyncio
    async def test_analyze_empty_response(self, analyzer: LLMIntentAnalyzer) -> None:
        """Analyzer should raise IntentAnalysisError for empty response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None

        with patch.object(analyzer, "_call_llm", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = response

            with pytest.raises(IntentAnalysisError, match="empty response"):
                await analyzer.analyze("create an agent")

    @pytest.mark.asyncio
    async def test_parse_response_invalid_json(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should raise IntentAnalysisError for invalid JSON."""
        with pytest.raises(IntentAnalysisError, match="Invalid JSON response"):
            analyzer._parse_response("not valid json {")

    @pytest.mark.asyncio
    async def test_parse_response_unknown_action_type(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should default to UNKNOWN for invalid action type."""
        response_json = json.dumps(
            {
                "action_type": "invalid_action",
                "confidence": 0.8,
                "entities": {},
                "reasoning": "Test",
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.action_type == ActionType.UNKNOWN
        assert decision.confidence == 0.8

    @pytest.mark.asyncio
    async def test_parse_response_confidence_clamping(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should clamp confidence to [0.0, 1.0] range."""
        # Test lower bound
        response_json = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": -0.5,
                "entities": {},
                "reasoning": "Test",
            }
        )
        decision = analyzer._parse_response(response_json)
        assert decision.confidence == 0.0

        # Test upper bound
        response_json = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": 1.5,
                "entities": {},
                "reasoning": "Test",
            }
        )
        decision = analyzer._parse_response(response_json)
        assert decision.confidence == 1.0

    @pytest.mark.asyncio
    async def test_parse_response_missing_fields(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should use defaults for missing optional fields."""
        response_json = json.dumps({"action_type": "query_info"})

        decision = analyzer._parse_response(response_json)

        assert decision.action_type == ActionType.QUERY_INFO
        assert decision.confidence == 0.5  # Default
        assert decision.entities == {}  # Default
        assert decision.reasoning == ""  # Default
        assert decision.target_agent_id is None

    @pytest.mark.asyncio
    async def test_parse_response_invalid_confidence_type(
        self, analyzer: LLMIntentAnalyzer
    ) -> None:
        """Parser should use default confidence for invalid type."""
        response_json = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": "not a number",
                "entities": {},
                "reasoning": "Test",
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.confidence == 0.5  # Default fallback

    @pytest.mark.asyncio
    async def test_parse_response_invalid_entities_type(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should use empty dict for invalid entities type."""
        response_json = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": 0.9,
                "entities": "not a dict",
                "reasoning": "Test",
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.entities == {}  # Default fallback

    @pytest.mark.asyncio
    async def test_parse_response_invalid_reasoning_type(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should use empty string for invalid reasoning type."""
        response_json = json.dumps(
            {
                "action_type": "create_agent",
                "confidence": 0.9,
                "entities": {},
                "reasoning": 123,  # Not a string
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.reasoning == ""  # Default fallback

    @pytest.mark.asyncio
    async def test_parse_response_with_target_agent_id(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should extract target_agent_id when provided."""
        response_json = json.dumps(
            {
                "action_type": "execute_task",
                "confidence": 0.9,
                "entities": {},
                "reasoning": "Run specific agent",
                "target_agent_id": "agent-123",
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.target_agent_id == "agent-123"

    @pytest.mark.asyncio
    async def test_parse_response_invalid_target_agent_id_type(
        self, analyzer: LLMIntentAnalyzer
    ) -> None:
        """Parser should ignore invalid target_agent_id type."""
        response_json = json.dumps(
            {
                "action_type": "execute_task",
                "confidence": 0.9,
                "entities": {},
                "reasoning": "Test",
                "target_agent_id": 123,  # Not a string
            }
        )

        decision = analyzer._parse_response(response_json)

        assert decision.target_agent_id is None

    def test_build_system_prompt_without_agents(self, analyzer: LLMIntentAnalyzer) -> None:
        """System prompt should describe all action types."""
        prompt = analyzer._build_system_prompt(None)

        # Verify all action types are mentioned
        assert "CREATE_AGENT" in prompt
        assert "CREATE_SKILL" in prompt
        assert "EXECUTE_TASK" in prompt
        assert "UPDATE_AGENT" in prompt
        assert "QUERY_INFO" in prompt
        assert "MANAGE_PLATFORM" in prompt
        assert "UNKNOWN" in prompt

        # Verify JSON format is described
        assert "action_type" in prompt
        assert "confidence" in prompt
        assert "entities" in prompt
        assert "reasoning" in prompt

    def test_build_system_prompt_with_agents(self, analyzer: LLMIntentAnalyzer) -> None:
        """System prompt should include available agents."""
        available_agents = [
            {"id": "agent-1", "name": "TestAgent"},
            {"id": "agent-2", "name": "DataBot"},
        ]

        prompt = analyzer._build_system_prompt(available_agents)

        assert "Available agents" in prompt
        assert "TestAgent" in prompt
        assert "agent-1" in prompt
        assert "DataBot" in prompt
        assert "agent-2" in prompt

    def test_build_messages_without_history(self, analyzer: LLMIntentAnalyzer) -> None:
        """Messages should include system prompt and current message only."""
        system_prompt = "Test system prompt"
        current_message = "create an agent"

        messages = analyzer._build_messages(system_prompt, current_message, None)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == system_prompt
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == current_message

    def test_build_messages_with_history(self, analyzer: LLMIntentAnalyzer) -> None:
        """Messages should include system prompt, history, and current message."""
        conversation_id = uuid4()
        history = [
            Message(
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content="Hello",
            ),
            Message(
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content="Hi there!",
            ),
        ]

        system_prompt = "Test system prompt"
        current_message = "create an agent"

        messages = analyzer._build_messages(system_prompt, current_message, history)

        assert len(messages) == 4
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hi there!"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == current_message

    @pytest.mark.asyncio
    async def test_call_llm_parameters(self, analyzer: LLMIntentAnalyzer) -> None:
        """LLM call should use correct parameters."""
        messages = [{"role": "user", "content": "test"}]

        with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
            mock_completion.return_value = MagicMock()

            await analyzer._call_llm(messages)

            mock_completion.assert_called_once()
            call_kwargs = mock_completion.call_args[1]
            assert call_kwargs["model"] == "openrouter/arcee-ai/trinity-large-preview:free"
            assert call_kwargs["messages"] == messages
            assert call_kwargs["temperature"] == 0.1
            assert call_kwargs["max_tokens"] == 500
            assert call_kwargs["api_base"] == "https://openrouter.ai/api/v1"

    def test_initialization_defaults(self) -> None:
        """Analyzer should use default configuration from environment."""
        with patch.dict(
            "os.environ",
            {
                "OMNIFORGE_INTENT_MODEL": "gpt-4",
                "OMNIFORGE_INTENT_TIMEOUT_SEC": "3.5",
            },
        ):
            analyzer = LLMIntentAnalyzer()

            assert analyzer.model == "gpt-4"
            assert analyzer.timeout == 3.5
            assert analyzer.temperature == 0.1  # Default
            assert analyzer.max_tokens == 500  # Default

    def test_initialization_explicit_values(self) -> None:
        """Analyzer should use explicit values over environment."""
        with patch.dict(
            "os.environ",
            {
                "OMNIFORGE_INTENT_MODEL": "gpt-4",
                "OMNIFORGE_INTENT_TIMEOUT_SEC": "3.5",
            },
        ):
            analyzer = LLMIntentAnalyzer(
                model="claude-3", temperature=0.5, max_tokens=1000, timeout=1.0
            )

            assert analyzer.model == "claude-3"
            assert analyzer.timeout == 1.0
            assert analyzer.temperature == 0.5
            assert analyzer.max_tokens == 1000

    @pytest.mark.asyncio
    async def test_all_action_types_parsed_correctly(self, analyzer: LLMIntentAnalyzer) -> None:
        """Parser should correctly handle all ActionType enum values."""
        action_types = [
            "create_agent",
            "create_skill",
            "execute_task",
            "update_agent",
            "query_info",
            "manage_platform",
            "unknown",
        ]

        for action_type_str in action_types:
            response_json = json.dumps(
                {
                    "action_type": action_type_str,
                    "confidence": 0.8,
                    "entities": {},
                    "reasoning": "Test",
                }
            )

            decision = analyzer._parse_response(response_json)

            assert decision.action_type.value == action_type_str
            assert decision.confidence == 0.8
