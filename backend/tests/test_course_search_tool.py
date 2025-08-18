from unittest.mock import Mock, patch

import pytest
from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Test CourseSearchTool.execute() method with various scenarios"""

    def test_execute_basic_query_success(self, mock_vector_store):
        """Test successful execution of basic search query"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("machine learning basics")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="machine learning basics", course_name=None, lesson_number=None
        )
        assert "[Test Course]" in result
        assert "Introduction to machine learning" in result
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["text"] == "Test Course"

    def test_execute_with_course_filter(self, mock_vector_store):
        """Test execution with course name filtering"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("deep learning", course_name="AI Course")

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="deep learning", course_name="AI Course", lesson_number=None
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_execute_with_lesson_filter(self, mock_vector_store):
        """Test execution with lesson number filtering"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("neural networks", lesson_number=2)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="neural networks", course_name=None, lesson_number=2
        )
        assert isinstance(result, str)

    def test_execute_with_both_filters(self, mock_vector_store):
        """Test execution with both course and lesson filters"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("algorithms", course_name="CS101", lesson_number=3)

        # Verify
        mock_vector_store.search.assert_called_once_with(
            query="algorithms", course_name="CS101", lesson_number=3
        )
        assert isinstance(result, str)

    def test_execute_empty_results(self, mock_vector_store, empty_search_results):
        """Test execution when search returns no results"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("nonexistent topic")

        # Verify
        assert "No relevant content found" in result
        assert len(tool.last_sources) == 0

    def test_execute_empty_results_with_filters(
        self, mock_vector_store, empty_search_results
    ):
        """Test execution with no results when filters are applied"""
        # Setup
        mock_vector_store.search.return_value = empty_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("topic", course_name="Missing Course", lesson_number=999)

        # Verify
        assert (
            "No relevant content found in course 'Missing Course' in lesson 999"
            in result
        )

    def test_execute_search_error(self, mock_vector_store, error_search_results):
        """Test execution when vector store returns an error"""
        # Setup
        mock_vector_store.search.return_value = error_search_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify
        assert result == "Test error message"
        assert len(tool.last_sources) == 0

    def test_execute_multiple_results_formatting(self, mock_vector_store):
        """Test formatting when multiple search results are returned"""
        # Setup - mock multiple results
        multi_results = SearchResults(
            documents=[
                "First result about machine learning",
                "Second result about deep learning",
            ],
            metadata=[
                {"course_title": "ML Course", "lesson_number": 1},
                {"course_title": "DL Course", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
            error=None,
        )
        mock_vector_store.search.return_value = multi_results
        mock_vector_store.get_lesson_link.side_effect = [
            "http://example.com/ml/lesson1",
            "http://example.com/dl/lesson2",
        ]

        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("machine learning")

        # Verify formatting
        assert "[ML Course - Lesson 1]" in result
        assert "[DL Course - Lesson 2]" in result
        assert "First result about machine learning" in result
        assert "Second result about deep learning" in result

        # Verify sources
        assert len(tool.last_sources) == 2
        assert tool.last_sources[0]["text"] == "ML Course - Lesson 1"
        assert tool.last_sources[0]["link"] == "http://example.com/ml/lesson1"
        assert tool.last_sources[1]["text"] == "DL Course - Lesson 2"
        assert tool.last_sources[1]["link"] == "http://example.com/dl/lesson2"

    def test_execute_missing_metadata_handling(self, mock_vector_store):
        """Test handling when metadata is incomplete"""
        # Setup - mock results with missing metadata
        incomplete_results = SearchResults(
            documents=["Content without complete metadata"],
            metadata=[{"course_title": None, "lesson_number": None}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = incomplete_results
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify graceful handling of missing metadata
        assert "[unknown]" in result
        assert "Content without complete metadata" in result

    def test_execute_lesson_without_link(self, mock_vector_store):
        """Test handling when lesson link is not available"""
        # Setup
        mock_vector_store.get_lesson_link.return_value = None
        tool = CourseSearchTool(mock_vector_store)

        # Execute
        result = tool.execute("test query")

        # Verify
        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["link"] is None

    def test_sources_reset_between_calls(self, mock_vector_store):
        """Test that sources are properly managed between multiple calls"""
        # Setup
        tool = CourseSearchTool(mock_vector_store)

        # Execute first query
        result1 = tool.execute("first query")
        first_sources = tool.last_sources.copy()

        # Execute second query
        result2 = tool.execute("second query")
        second_sources = tool.last_sources

        # Verify sources are updated, not accumulated
        assert len(first_sources) == 1
        assert len(second_sources) == 1
        # Sources should be fresh for each query (not accumulated)
        assert first_sources == second_sources  # In this mock setup they'll be the same


class TestCourseSearchToolDefinition:
    """Test CourseSearchTool tool definition and interface"""

    def test_get_tool_definition_structure(self, mock_vector_store):
        """Test that tool definition has correct structure"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        assert "name" in definition
        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition

        schema = definition["input_schema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert "required" in schema
        assert "query" in schema["required"]

        properties = schema["properties"]
        assert "query" in properties
        assert "course_name" in properties
        assert "lesson_number" in properties

    def test_tool_definition_parameter_types(self, mock_vector_store):
        """Test that tool definition parameter types are correct"""
        tool = CourseSearchTool(mock_vector_store)
        definition = tool.get_tool_definition()

        properties = definition["input_schema"]["properties"]

        assert properties["query"]["type"] == "string"
        assert properties["course_name"]["type"] == "string"
        assert properties["lesson_number"]["type"] == "integer"


class TestCourseSearchToolIntegration:
    """Test CourseSearchTool integration with ToolManager"""

    def test_tool_manager_registration(self, mock_vector_store):
        """Test that CourseSearchTool can be registered with ToolManager"""
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()

        # This should not raise an exception
        manager.register_tool(tool)

        definitions = manager.get_tool_definitions()
        assert len(definitions) == 1
        assert definitions[0]["name"] == "search_course_content"

    def test_tool_execution_through_manager(self, mock_vector_store):
        """Test executing CourseSearchTool through ToolManager"""
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(tool)

        result = manager.execute_tool("search_course_content", query="test")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_sources_retrieval_through_manager(self, mock_vector_store):
        """Test retrieving sources through ToolManager"""
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(tool)

        # Execute search to populate sources
        manager.execute_tool("search_course_content", query="test")

        # Retrieve sources
        sources = manager.get_last_sources()
        assert len(sources) == 1
        assert "text" in sources[0]
        assert "link" in sources[0]

    def test_sources_reset_through_manager(self, mock_vector_store):
        """Test resetting sources through ToolManager"""
        tool = CourseSearchTool(mock_vector_store)
        manager = ToolManager()
        manager.register_tool(tool)

        # Execute search and verify sources exist
        manager.execute_tool("search_course_content", query="test")
        assert len(manager.get_last_sources()) > 0

        # Reset sources and verify they're cleared
        manager.reset_sources()
        assert len(manager.get_last_sources()) == 0
        assert len(tool.last_sources) == 0
