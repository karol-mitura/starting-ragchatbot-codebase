from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator


class TestAIGeneratorBasicFunctionality:
    """Test basic AIGenerator functionality without tools"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_without_tools(self, mock_anthropic_class):
        """Test basic response generation without tool usage"""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="This is a basic AI response")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        # Create AI generator
        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Generate response
        result = ai_generator.generate_response("What is machine learning?")

        # Verify
        assert result == "This is a basic AI response"
        mock_client.messages.create.assert_called_once()

        # Verify API parameters
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["model"] == "claude-test-model"
        assert call_args[1]["temperature"] == 0
        assert call_args[1]["max_tokens"] == 800
        assert call_args[1]["messages"] == [
            {"role": "user", "content": "What is machine learning?"}
        ]
        assert "tools" not in call_args[1]

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_conversation_history(self, mock_anthropic_class):
        """Test response generation with conversation history"""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with history context")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Generate response with history
        history = "User: Previous question\nAssistant: Previous answer"
        result = ai_generator.generate_response(
            "Follow-up question", conversation_history=history
        )

        # Verify system prompt includes history
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation:" in system_content
        assert "Previous question" in system_content


class TestAIGeneratorToolCalling:
    """Test AIGenerator tool calling functionality"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_tools_no_tool_use(self, mock_anthropic_class):
        """Test response generation with tools available but not used"""
        # Setup mock for regular response (no tool use)
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct answer without tools")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tool definitions
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()

        # Generate response
        result = ai_generator.generate_response(
            "What is 2+2?", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify
        assert result == "Direct answer without tools"
        mock_tool_manager.execute_tool.assert_not_called()

        # Verify tools were included in API call
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["tools"] == tools
        assert call_args[1]["tool_choice"] == {"type": "auto"}

    @patch("ai_generator.anthropic.Anthropic")
    def test_generate_response_with_tool_use(self, mock_anthropic_class):
        """Test response generation when AI decides to use tools"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock initial tool use response
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "machine learning"}
        mock_tool_block.id = "tool_call_123"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        # Mock final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [
            Mock(text="Based on the search, machine learning is...")
        ]

        # Configure client to return different responses on subsequent calls
        mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and tool manager
        tools = [{"name": "search_course_content", "description": "Search courses"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = (
            "Search results about machine learning"
        )

        # Generate response
        result = ai_generator.generate_response(
            "What is machine learning?", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="machine learning"
        )

        # Verify final response
        assert result == "Based on the search, machine learning is..."

        # Verify two API calls were made
        assert mock_client.messages.create.call_count == 2

    @patch("ai_generator.anthropic.Anthropic")
    def test_handle_tool_execution_multiple_tools(self, mock_anthropic_class):
        """Test handling multiple tool calls in one response"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock multiple tool blocks
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "search_course_content"
        mock_tool_block1.input = {"query": "neural networks"}
        mock_tool_block1.id = "tool_1"

        mock_tool_block2 = Mock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "get_course_outline"
        mock_tool_block2.input = {"course_title": "AI Course"}
        mock_tool_block2.id = "tool_2"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_block1, mock_tool_block2]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [
            Mock(text="Combined response from multiple tools")
        ]

        mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Neural networks search results",
            "AI Course outline",
        ]

        tools = [{"name": "search_course_content"}, {"name": "get_course_outline"}]

        # Generate response
        result = ai_generator.generate_response(
            "Tell me about neural networks in the AI course",
            tools=tools,
            tool_manager=mock_tool_manager,
        )

        # Verify both tools were called
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="neural networks"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_title="AI Course"
        )

        assert result == "Combined response from multiple tools"


class TestAIGeneratorToolExecutionDetails:
    """Test detailed aspects of tool execution handling"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_result_formatting(self, mock_anthropic_class):
        """Test that tool results are properly formatted for Claude"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_123"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response")]

        mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        # Generate response
        result = ai_generator.generate_response(
            "test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify final API call message structure
        final_call_args = mock_client.messages.create.call_args_list[1]
        messages = final_call_args[1]["messages"]

        # Should have original user message, assistant tool use, and tool result
        assert len(messages) == 3

        # Check tool result message format
        tool_result_message = messages[2]
        assert tool_result_message["role"] == "user"
        assert len(tool_result_message["content"]) == 1

        tool_result = tool_result_message["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool_123"
        assert "[Round 1] Tool execution result" in tool_result["content"]

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_without_manager(self, mock_anthropic_class):
        """Test graceful fallback when no tool_manager provided"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock simple response for fallback
        mock_response = Mock()
        mock_response.content = [Mock(text="Simple response without tools")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Generate response without tool manager - should fall back gracefully
        result = ai_generator.generate_response(
            "test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=None,  # No tool manager provided!
        )

        # Should return fallback response, not raise exception
        assert result == "Simple response without tools"


class TestAIGeneratorSystemPrompt:
    """Test AI generator system prompt handling"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_system_prompt_content(self, mock_anthropic_class):
        """Test that system prompt contains expected content"""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Generate response
        ai_generator.generate_response("test query")

        # Check system prompt content
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]

        # Verify key elements of system prompt
        assert "course materials" in system_content.lower()
        assert (
            "search tool" in system_content.lower()
            or "content search tool" in system_content.lower()
        )
        assert "tool" in system_content.lower()
        assert "educational" in system_content.lower()

    @patch("ai_generator.anthropic.Anthropic")
    def test_system_prompt_with_history(self, mock_anthropic_class):
        """Test system prompt when conversation history is provided"""
        # Setup mock
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Generate response with history
        history = "User: What is AI?\nAssistant: AI is artificial intelligence."
        ai_generator.generate_response(
            "Follow up question", conversation_history=history
        )

        # Check that system prompt includes both base prompt and history
        call_args = mock_client.messages.create.call_args
        system_content = call_args[1]["system"]

        assert "course materials" in system_content.lower()  # Base prompt
        assert "Previous conversation:" in system_content  # History section
        assert "What is AI?" in system_content  # Actual history content


class TestAIGeneratorConfiguration:
    """Test AI generator configuration and initialization"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_initialization(self, mock_anthropic_class):
        """Test AIGenerator initialization with API key and model"""
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-sonnet-4")

        # Verify anthropic client was initialized with correct API key
        mock_anthropic_class.assert_called_once_with(api_key="test-api-key")

        # Verify model is stored correctly
        assert ai_generator.model == "claude-sonnet-4"

        # Verify base parameters are configured
        expected_base_params = {
            "model": "claude-sonnet-4",
            "temperature": 0,
            "max_tokens": 800,
        }
        assert ai_generator.base_params == expected_base_params

    def test_system_prompt_is_static(self):
        """Test that system prompt is defined as a static class attribute"""
        # Verify system prompt exists and is not empty
        assert hasattr(AIGenerator, "SYSTEM_PROMPT")
        assert len(AIGenerator.SYSTEM_PROMPT) > 100  # Should be substantial
        assert isinstance(AIGenerator.SYSTEM_PROMPT, str)


class TestAIGeneratorSequentialToolCalling:
    """Test sequential tool calling functionality"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_sequential_tool_calling_two_rounds(self, mock_anthropic_class):
        """Test successful 2-round sequential tool calling"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock first tool use response
        mock_tool_block1 = Mock()
        mock_tool_block1.type = "tool_use"
        mock_tool_block1.name = "get_course_outline"
        mock_tool_block1.input = {"course_title": "Course X"}
        mock_tool_block1.id = "tool_1"

        mock_first_response = Mock()
        mock_first_response.content = [mock_tool_block1]
        mock_first_response.stop_reason = "tool_use"

        # Mock second tool use response
        mock_tool_block2 = Mock()
        mock_tool_block2.type = "tool_use"
        mock_tool_block2.name = "search_course_content"
        mock_tool_block2.input = {"query": "machine learning basics"}
        mock_tool_block2.id = "tool_2"

        mock_second_response = Mock()
        mock_second_response.content = [mock_tool_block2]
        mock_second_response.stop_reason = "tool_use"

        # Mock final response without tools
        mock_final_response = Mock()
        mock_final_response.content = [
            Mock(text="Based on both searches, here's the comprehensive answer")
        ]

        # Configure client to return responses in sequence
        mock_client.messages.create.side_effect = [
            mock_first_response,
            mock_second_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and tool manager
        tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course X Outline: Lesson 4 - Machine Learning Basics",
            "Related courses found: AI Fundamentals, ML Introduction",
        ]

        # Generate response
        result = ai_generator.generate_response(
            "Find courses that discuss the same topic as lesson 4 of Course X",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2,
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_title="Course X"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="machine learning basics"
        )

        # Verify final response
        assert result == "Based on both searches, here's the comprehensive answer"

        # Verify 3 API calls were made (2 with tools, 1 final without tools)
        assert mock_client.messages.create.call_count == 3

    @patch("ai_generator.anthropic.Anthropic")
    def test_sequential_tool_calling_early_termination(self, mock_anthropic_class):
        """Test early termination when Claude doesn't use tools in first round"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock response without tool use
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct answer without needing tools")]
        mock_response.stop_reason = "end_turn"

        mock_client.messages.create.return_value = mock_response

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and tool manager
        tools = [{"name": "search_course_content"}]
        mock_tool_manager = Mock()

        # Generate response
        result = ai_generator.generate_response(
            "What is 2+2?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2,
        )

        # Verify no tools were executed
        mock_tool_manager.execute_tool.assert_not_called()

        # Verify only 1 API call was made
        assert mock_client.messages.create.call_count == 1
        assert result == "Direct answer without needing tools"

    @patch("ai_generator.anthropic.Anthropic")
    def test_max_rounds_enforcement(self, mock_anthropic_class):
        """Test that system enforces maximum rounds limit"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use responses for both rounds
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_1"

        mock_tool_response = Mock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final answer after max rounds")]

        # Both rounds will want to use tools, but we enforce the limit
        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_tool_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and tool manager
        tools = [{"name": "search_course_content"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Search result"

        # Generate response with max_tool_rounds=2
        result = ai_generator.generate_response(
            "Complex query requiring multiple searches",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2,
        )

        # Verify exactly 2 tool executions (max rounds enforced)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify 3 API calls (2 tool rounds + 1 final)
        assert mock_client.messages.create.call_count == 3

        assert result == "Final answer after max rounds"

    @patch("ai_generator.anthropic.Anthropic")
    def test_tool_execution_error_handling(self, mock_anthropic_class):
        """Test graceful handling of tool execution errors"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_1"

        mock_tool_response = Mock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Answer despite tool error")]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and failing tool manager
        tools = [{"name": "search_course_content"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        # Generate response
        result = ai_generator.generate_response(
            "test query", tools=tools, tool_manager=mock_tool_manager, max_tool_rounds=2
        )

        # Should not raise exception, but handle gracefully
        assert result == "Answer despite tool error"

        # Verify tool was attempted
        mock_tool_manager.execute_tool.assert_called_once()

    @patch("ai_generator.anthropic.Anthropic")
    def test_conversation_context_preservation(self, mock_anthropic_class):
        """Test that conversation context is preserved across rounds"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_1"

        mock_tool_response = Mock()
        mock_tool_response.content = [mock_tool_block]
        mock_tool_response.stop_reason = "tool_use"

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final answer")]

        mock_client.messages.create.side_effect = [
            mock_tool_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tools and tool manager
        tools = [{"name": "search_course_content"}]
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Generate response
        result = ai_generator.generate_response(
            "test query", tools=tools, tool_manager=mock_tool_manager, max_tool_rounds=2
        )

        # Check that final API call includes conversation history
        final_call_args = mock_client.messages.create.call_args_list[1]
        messages = final_call_args[1]["messages"]

        # Should have user query, assistant tool use, tool results
        assert len(messages) == 3
        assert messages[0]["role"] == "user"  # Original query
        assert messages[1]["role"] == "assistant"  # Claude's tool use
        assert messages[2]["role"] == "user"  # Tool results

        # Check tool result formatting includes round number
        tool_result_content = messages[2]["content"][0]["content"]
        assert "[Round 1]" in tool_result_content


class TestAIGeneratorConfigurationAndFallbacks:
    """Test configuration validation and fallback scenarios"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_max_tool_rounds_validation(self, mock_anthropic_class):
        """Test validation of max_tool_rounds parameter"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Test validation clamps values to reasonable range
        result = ai_generator.generate_response("test", max_tool_rounds=-1)
        assert result == "Response"  # Should work, clamped to 1

        result = ai_generator.generate_response("test", max_tool_rounds=10)
        assert result == "Response"  # Should work, clamped to 5

    @patch("ai_generator.anthropic.Anthropic")
    def test_fallback_to_simple_response(self, mock_anthropic_class):
        """Test fallback when no tools or tool manager provided"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Simple response")]
        mock_response.stop_reason = "end_turn"
        mock_client.messages.create.return_value = mock_response
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Test with no tools
        result = ai_generator.generate_response(
            "test query", tools=None, tool_manager=None
        )
        assert result == "Simple response"

        # Test with tools but no manager
        result = ai_generator.generate_response(
            "test query", tools=[{"name": "test"}], tool_manager=None
        )
        assert result == "Simple response"


class TestAIGeneratorErrorHandling:
    """Test AI generator error handling scenarios"""

    @patch("ai_generator.anthropic.Anthropic")
    def test_api_exception_handling(self, mock_anthropic_class):
        """Test graceful handling of API exceptions"""
        # Setup mock to raise exception
        mock_client = Mock()
        mock_client.messages.create.side_effect = Exception("API error")
        mock_anthropic_class.return_value = mock_client

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Should return user-friendly error message, not raise exception
        result = ai_generator.generate_response("test query")
        assert "unexpected error occurred" in result.lower()

    @patch("ai_generator.anthropic.Anthropic")
    def test_backward_compatibility_single_tool_call(self, mock_anthropic_class):
        """Test that existing single tool call behavior still works"""
        # Setup mock client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client

        # Mock tool use response
        mock_tool_block = Mock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search_course_content"
        mock_tool_block.input = {"query": "test"}
        mock_tool_block.id = "tool_123"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_block]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response")]

        mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        ai_generator = AIGenerator("test-api-key", "claude-test-model")

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        # Test with max_tool_rounds=1 (backward compatibility)
        result = ai_generator.generate_response(
            "test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
            max_tool_rounds=1,
        )

        # Should work like before
        assert result == "Final response"
        assert mock_tool_manager.execute_tool.call_count == 1
