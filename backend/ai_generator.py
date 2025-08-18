from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search and course outline tools.

Tool Usage Guidelines:
- **Content Search Tool**: Use for questions about specific course content or detailed educational materials
- **Course Outline Tool**: Use for questions about course structure, overview, lesson lists, or course information
- **Sequential tool calling supported**: You can make up to 2 rounds of tool calls to gather comprehensive information
- **Multi-step reasoning**: If initial search doesn't provide complete answer, use additional tool calls to gather more specific information
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

When to Use Each Tool:
- **Content questions**: "What is X in course Y?", "How does Z work?", "Explain the concept of..."
- **Outline questions**: "What lessons are in course X?", "Show me the course structure", "What's covered in this course?"

When to Use Sequential Tool Calls:
- **Broad then specific**: Start with general search, then refine with specific parameters
- **Multiple course comparison**: Search different courses or lessons for comparative analysis
- **Comprehensive coverage**: Use outline tool first, then content search for specific lessons
- **Cross-referencing**: Search for related concepts across different parts of the course material
- **Complex queries**: When one search doesn't provide sufficient information for complete answer

For Course Outline Queries:
- Always return the complete course information including course title, course link, and all lesson details
- Present lesson numbers and titles in a clear, organized format
- Include instructor information when available

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool(s) first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
        max_tool_rounds: int = 2,
    ) -> str:
        """
        Generate AI response with support for sequential tool calling.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum rounds of tool calling (default: 2)

        Returns:
            Generated response as string
        """

        try:
            # Validate inputs
            max_tool_rounds = self._validate_tool_rounds_config(max_tool_rounds)

            # If no tools or tool manager, fall back to simple response
            if not tools or not tool_manager:
                return self._generate_simple_response(query, conversation_history)

            # Initialize conversation with user query
            messages = [{"role": "user", "content": query}]
            system_content = self._build_system_content(conversation_history)

            # Sequential tool calling loop
            current_round = 0

            while current_round < max_tool_rounds:
                # Make API call with tools available
                response = self._make_api_call(messages, system_content, tools)

                # Check if Claude wants to use tools
                if response.stop_reason != "tool_use":
                    # No tool use - return final response
                    return response.content[0].text

                # Execute tools for this round
                messages = self._execute_tools_for_round(
                    messages, response, tool_manager, current_round
                )

                current_round += 1

            # Make final API call without tools to get conclusive answer
            final_response = self._make_api_call(messages, system_content, tools=None)
            return final_response.content[0].text

        except Exception as e:
            # Handle errors gracefully
            if "anthropic" in str(type(e)).lower():
                return f"AI service temporarily unavailable. Please try again later."
            return f"An unexpected error occurred while processing your request."

    def _validate_tool_rounds_config(self, max_tool_rounds: int) -> int:
        """Validate and sanitize tool rounds configuration"""
        if max_tool_rounds < 1:
            return 1
        elif max_tool_rounds > 5:  # Safety limit
            return 5
        return max_tool_rounds

    def _build_system_content(self, conversation_history: Optional[str]) -> str:
        """Build system content with optional conversation history"""
        return (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

    def _make_api_call(
        self, messages: List[Dict], system_content: str, tools: Optional[List]
    ) -> Any:
        """Make API call to Claude with current conversation state"""
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        return self.client.messages.create(**api_params)

    def _execute_tools_for_round(
        self, messages: List[Dict], response, tool_manager, current_round: int
    ) -> List[Dict]:
        """
        Execute tools for current round and update conversation context.

        Args:
            messages: Current conversation messages
            response: Claude's response with tool calls
            tool_manager: Tool execution manager
            current_round: Current round number (0-indexed)

        Returns:
            Updated messages list
        """
        # Add Claude's tool use response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Execute all tools in this response
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"[Round {current_round + 1}] {tool_result}",
                        }
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": f"[Round {current_round + 1}] Error executing tool: {str(e)}",
                        }
                    )

        # Add tool results to conversation
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        return messages

    def _generate_simple_response(
        self, query: str, conversation_history: Optional[str]
    ) -> str:
        """Fallback method for simple response without tools"""
        system_content = self._build_system_content(conversation_history)
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        response = self.client.messages.create(**api_params)
        return response.content[0].text

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager
    ):
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()

        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, **content_block.input
                )

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result,
                    }
                )

        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"],
        }

        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
