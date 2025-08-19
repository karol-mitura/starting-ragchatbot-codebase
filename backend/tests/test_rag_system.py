import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from config import Config
from rag_system import RAGSystem


class TestRAGSystemQueryProcessing:
    """Test RAG system query processing end-to-end"""

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_query_without_session(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """Test query processing without session ID"""
        # Setup mocks
        mock_vector_store = mock_vector_store_class.return_value
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_session_mgr = mock_session_manager.return_value
        mock_tool_manager = mock_tool_manager_class.return_value

        # Mock AI response
        mock_ai_generator.generate_response.return_value = (
            "Machine learning is a subset of AI..."
        )

        # Mock tool manager with sources
        mock_sources = [
            {"text": "ML Course - Lesson 1", "link": "http://example.com/lesson1"}
        ]
        mock_tool_manager.get_last_sources.return_value = mock_sources
        mock_tool_manager.reset_sources.return_value = None

        # Create RAG system with mock config
        config = Config()
        rag_system = RAGSystem(config)

        # Execute query
        response, sources = rag_system.query("What is machine learning?")

        # Verify AI generator was called correctly
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args

        # Check the generated prompt
        assert (
            "Answer this question about course materials: What is machine learning?"
            in call_args[1]["query"]
        )
        assert call_args[1]["conversation_history"] is None
        assert call_args[1]["tools"] is not None
        assert call_args[1]["tool_manager"] is not None

        # Verify sources were retrieved and reset
        assert sources == mock_sources
        rag_system.tool_manager.get_last_sources.assert_called_once()
        rag_system.tool_manager.reset_sources.assert_called_once()

        # Verify session was not used
        mock_session_mgr.get_conversation_history.assert_not_called()
        mock_session_mgr.add_exchange.assert_not_called()

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_query_with_session(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """Test query processing with session ID and conversation history"""
        # Setup mocks
        mock_vector_store = mock_vector_store_class.return_value
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_session_mgr = mock_session_manager.return_value
        mock_tool_manager = mock_tool_manager_class.return_value

        # Mock conversation history
        mock_history = "User: What is AI?\nAssistant: AI is artificial intelligence."
        mock_session_mgr.get_conversation_history.return_value = mock_history

        # Mock AI response
        mock_ai_generator.generate_response.return_value = (
            "Neural networks are a key component..."
        )

        # Mock sources
        mock_sources = [
            {"text": "Deep Learning Course", "link": "http://example.com/dl"}
        ]
        mock_tool_manager.get_last_sources.return_value = mock_sources
        mock_tool_manager.reset_sources.return_value = None

        config = Config()
        rag_system = RAGSystem(config)

        # Execute query with session
        session_id = "test-session-123"
        response, sources = rag_system.query(
            "Tell me about neural networks", session_id
        )

        # Verify session history was retrieved
        mock_session_mgr.get_conversation_history.assert_called_once_with(session_id)

        # Verify AI generator received history
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == mock_history

        # Verify conversation was updated
        mock_session_mgr.add_exchange.assert_called_once_with(
            session_id,
            "Tell me about neural networks",
            "Neural networks are a key component...",
        )

        assert response == "Neural networks are a key component..."
        assert sources == mock_sources

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_query_with_empty_sources(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """Test query processing when no sources are found"""
        # Setup mocks
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_tool_manager = mock_tool_manager_class.return_value
        mock_ai_generator.generate_response.return_value = (
            "I don't have information about that topic."
        )

        # Mock empty sources
        mock_tool_manager.get_last_sources.return_value = []
        mock_tool_manager.reset_sources.return_value = None

        config = Config()
        rag_system = RAGSystem(config)

        # Execute query
        response, sources = rag_system.query("What is quantum computing?")

        # Verify empty sources
        assert sources == []
        assert response == "I don't have information about that topic."

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_query_with_tool_usage_simulation(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """Test query that triggers tool usage through AI generator"""
        # Setup mocks
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_tool_manager = mock_tool_manager_class.return_value

        # Simulate AI generator using tools and returning response
        mock_ai_generator.generate_response.return_value = (
            "Based on course materials, machine learning involves..."
        )

        # Mock tool manager execution
        mock_sources = [
            {
                "text": "ML Fundamentals - Lesson 2",
                "link": "http://example.com/ml/lesson2",
            }
        ]
        mock_tool_manager.get_last_sources.return_value = mock_sources
        mock_tool_manager.reset_sources.return_value = None
        mock_tool_manager.get_tool_definitions.return_value = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            }
        ]

        config = Config()
        rag_system = RAGSystem(config)

        # Execute query that should trigger tool usage
        response, sources = rag_system.query(
            "Explain machine learning algorithms in detail"
        )

        # Verify AI generator was called with tools
        mock_ai_generator.generate_response.assert_called_once()
        call_args = mock_ai_generator.generate_response.call_args

        assert call_args[1]["tools"] is not None  # Tools were provided
        assert call_args[1]["tool_manager"] is not None  # Tool manager was provided

        # Verify tools were properly configured
        tools = call_args[1]["tools"]
        assert len(tools) > 0  # Should have at least one tool

        # Check if search tool is available
        tool_names = [tool["name"] for tool in tools]
        assert "search_course_content" in tool_names

        assert response == "Based on course materials, machine learning involves..."
        assert sources == mock_sources


class TestRAGSystemCourseManagement:
    """Test RAG system course document management"""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_add_course_document_success(
        self,
        mock_doc_processor_class,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        sample_course,
        sample_course_chunks,
    ):
        """Test successful course document addition"""
        # Setup mocks
        mock_doc_processor = mock_doc_processor_class.return_value
        mock_vector_store = mock_vector_store_class.return_value

        # Mock course and chunks from document processor

        mock_course = sample_course
        mock_chunks = sample_course_chunks

        mock_doc_processor.process_course_document.return_value = (
            mock_course,
            mock_chunks,
        )

        config = Config()
        rag_system = RAGSystem(config)

        # Execute document addition
        course, chunk_count = rag_system.add_course_document("test_course.txt")

        # Verify document processor was called
        mock_doc_processor.process_course_document.assert_called_once_with(
            "test_course.txt"
        )

        # Verify vector store operations
        mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)

        # Verify return values
        assert course == mock_course
        assert chunk_count == len(mock_chunks)

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_add_course_document_exception(
        self,
        mock_doc_processor_class,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
    ):
        """Test course document addition with exception"""
        # Setup mocks
        mock_doc_processor = mock_doc_processor_class.return_value
        mock_doc_processor.process_course_document.side_effect = Exception(
            "File not found"
        )

        config = Config()
        rag_system = RAGSystem(config)

        # Execute document addition (should handle exception gracefully)
        course, chunk_count = rag_system.add_course_document("nonexistent.txt")

        # Verify error handling
        assert course is None
        assert chunk_count == 0

    @patch("rag_system.os.path.exists")
    @patch("rag_system.os.path.isfile")
    @patch("rag_system.os.path.join")
    @patch("rag_system.os.listdir")
    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_add_course_folder_success(
        self,
        mock_doc_processor_class,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
        mock_listdir,
        mock_path_join,
        mock_path_isfile,
        mock_path_exists,
        sample_course,
        sample_course_chunks,
    ):
        """Test successful course folder processing"""
        # Setup mocks
        mock_path_exists.return_value = True
        mock_listdir.return_value = [
            "course1.txt",
            "course2.txt",
            "readme.md",
        ]  # Only .txt should be processed
        
        # Mock isfile to return True for .txt files, False for others
        def mock_isfile_side_effect(path):
            return path.endswith('.txt')
        mock_path_isfile.side_effect = mock_isfile_side_effect
        
        # Mock path join to return predictable paths
        def mock_path_join_side_effect(folder, filename):
            return f"{folder}/{filename}"
        mock_path_join.side_effect = mock_path_join_side_effect

        mock_doc_processor = mock_doc_processor_class.return_value
        mock_vector_store = mock_vector_store_class.return_value

        # Mock existing course titles (empty for new courses)
        mock_vector_store.get_existing_course_titles.return_value = []

        # Mock document processing results - create separate course instances
        from models import Course, Lesson

        # Create separate course objects
        mock_course1 = Course(
            title="Course 1",
            instructor=sample_course.instructor,
            course_link=sample_course.course_link,
            lessons=sample_course.lessons,
        )
        mock_chunks1 = sample_course_chunks[:2]

        mock_course2 = Course(
            title="Course 2", 
            instructor=sample_course.instructor,
            course_link=sample_course.course_link,
            lessons=sample_course.lessons,
        )
        mock_chunks2 = sample_course_chunks[2:]

        mock_doc_processor.process_course_document.side_effect = [
            (mock_course1, mock_chunks1),
            (mock_course2, mock_chunks2),
        ]

        config = Config()
        rag_system = RAGSystem(config)

        # Execute folder processing
        total_courses, total_chunks = rag_system.add_course_folder("test_docs_folder")

        # Verify results
        assert total_courses == 2
        assert total_chunks == len(mock_chunks1) + len(mock_chunks2)

        # Verify only .txt files were processed
        assert mock_doc_processor.process_course_document.call_count == 2

    @patch("rag_system.os.path.exists")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_add_course_folder_nonexistent(
        self,
        mock_doc_processor_class,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_path_exists,
    ):
        """Test course folder processing with nonexistent folder"""
        # Setup mocks
        mock_path_exists.return_value = False

        config = Config()
        rag_system = RAGSystem(config)

        # Execute folder processing
        total_courses, total_chunks = rag_system.add_course_folder("nonexistent_folder")

        # Verify no processing occurred
        assert total_courses == 0
        assert total_chunks == 0


class TestRAGSystemAnalytics:
    """Test RAG system analytics and course information"""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_get_course_analytics(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
    ):
        """Test course analytics retrieval"""
        # Setup mocks
        mock_vector_store = mock_vector_store_class.return_value
        mock_vector_store.get_course_count.return_value = 3
        mock_vector_store.get_existing_course_titles.return_value = [
            "Machine Learning Fundamentals",
            "Deep Learning Advanced",
            "AI Ethics",
        ]

        config = Config()
        rag_system = RAGSystem(config)

        # Get analytics
        analytics = rag_system.get_course_analytics()

        # Verify results
        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Machine Learning Fundamentals" in analytics["course_titles"]
        assert "Deep Learning Advanced" in analytics["course_titles"]
        assert "AI Ethics" in analytics["course_titles"]


class TestRAGSystemIntegration:
    """Test RAG system component integration"""

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_component_initialization(
        self,
        mock_doc_processor_class,
        mock_session_manager_class,
        mock_ai_generator_class,
        mock_vector_store_class,
    ):
        """Test that all components are properly initialized"""
        config = Config()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "test_chroma"
        config.EMBEDDING_MODEL = "test-embedding-model"
        config.MAX_RESULTS = 5
        config.ANTHROPIC_API_KEY = "test-api-key"
        config.ANTHROPIC_MODEL = "claude-test-model"
        config.MAX_HISTORY = 2

        rag_system = RAGSystem(config)

        # Verify all components were initialized with correct parameters
        mock_doc_processor_class.assert_called_once_with(800, 100)
        mock_vector_store_class.assert_called_once_with(
            "test_chroma", "test-embedding-model", 5
        )
        mock_ai_generator_class.assert_called_once_with(
            "test-api-key", "claude-test-model"
        )
        mock_session_manager_class.assert_called_once_with(2)

        # Verify tools are registered
        assert hasattr(rag_system, "tool_manager")
        assert hasattr(rag_system, "search_tool")
        assert hasattr(rag_system, "outline_tool")

    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_tool_manager_setup(
        self,
        mock_doc_processor_class,
        mock_session_manager_class,
        mock_ai_generator_class,
        mock_vector_store_class,
    ):
        """Test that tool manager is properly configured with tools"""
        config = Config()
        rag_system = RAGSystem(config)

        # Check that tools are registered with tool manager
        tool_definitions = rag_system.tool_manager.get_tool_definitions()

        # Should have at least search and outline tools
        assert len(tool_definitions) >= 2

        tool_names = [tool["name"] for tool in tool_definitions]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names


class TestRAGSystemConfigurationImpact:
    """Test how configuration affects RAG system behavior"""

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_max_results_zero_impact_on_rag_query(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """CRITICAL TEST: Verify MAX_RESULTS=0 breaks RAG queries"""
        # Create config with MAX_RESULTS=0 (current broken configuration)
        config = Config()
        config.MAX_RESULTS = 0  # This is the critical issue

        # Setup mocks
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_tool_manager = mock_tool_manager_class.return_value
        mock_ai_generator.generate_response.return_value = (
            "I don't have information about that."
        )

        # Mock vector store that will be initialized with MAX_RESULTS=0
        mock_vector_store = mock_vector_store_class.return_value

        rag_system = RAGSystem(config)

        # Verify vector store was initialized with MAX_RESULTS=0
        mock_vector_store_class.assert_called_with(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            0,  # This is the problem - no results will be returned!
        )

        # Mock empty sources (because MAX_RESULTS=0 prevents any search results)
        mock_tool_manager.get_last_sources.return_value = []
        mock_tool_manager.reset_sources.return_value = None

        # Execute query
        response, sources = rag_system.query("What is machine learning?")

        # Verify the broken behavior
        assert sources == []  # No sources due to MAX_RESULTS=0

        # The AI will likely return a "no information" response because tools return empty results
        # This demonstrates the critical configuration issue

    @patch("rag_system.ToolManager")
    @patch("rag_system.CourseSearchTool")
    @patch("rag_system.CourseOutlineTool")
    @patch("rag_system.VectorStore")
    @patch("rag_system.AIGenerator")
    @patch("rag_system.SessionManager")
    @patch("rag_system.DocumentProcessor")
    def test_proper_max_results_impact_on_rag_query(
        self,
        mock_doc_processor,
        mock_session_manager,
        mock_ai_generator_class,
        mock_vector_store_class,
        mock_outline_tool_class,
        mock_search_tool_class,
        mock_tool_manager_class,
    ):
        """Test RAG query behavior with proper MAX_RESULTS configuration"""
        # Create config with proper MAX_RESULTS
        config = Config()
        config.MAX_RESULTS = 5  # Proper configuration

        # Setup mocks
        mock_ai_generator = mock_ai_generator_class.return_value
        mock_tool_manager = mock_tool_manager_class.return_value
        mock_ai_generator.generate_response.return_value = (
            "Based on course materials, machine learning is..."
        )

        # Mock meaningful sources (because MAX_RESULTS>0 allows search results)
        mock_sources = [
            {"text": "ML Course - Lesson 1", "link": "http://example.com/ml"}
        ]
        mock_tool_manager.get_last_sources.return_value = mock_sources
        mock_tool_manager.reset_sources.return_value = None

        rag_system = RAGSystem(config)

        # Verify vector store was initialized with proper MAX_RESULTS
        mock_vector_store_class.assert_called_with(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            5,  # Proper configuration allows search results
        )

        # Execute query
        response, sources = rag_system.query("What is machine learning?")

        # Verify proper behavior
        assert len(sources) > 0  # Sources returned due to proper MAX_RESULTS
        assert "Based on course materials" in response  # AI has context to work with
