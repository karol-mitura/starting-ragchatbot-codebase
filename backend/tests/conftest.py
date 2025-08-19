import os
import sys
from unittest.mock import MagicMock, Mock, patch
from fastapi.testclient import TestClient
from typing import Generator

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Course, CourseChunk, Lesson
from vector_store import SearchResults


@pytest.fixture
def sample_course():
    """Create a sample course for testing"""
    lessons = [
        Lesson(
            lesson_number=1,
            title="Introduction",
            lesson_link="http://example.com/lesson1",
        ),
        Lesson(
            lesson_number=2,
            title="Advanced Topics",
            lesson_link="http://example.com/lesson2",
        ),
    ]
    return Course(
        title="Test Course",
        instructor="Test Instructor",
        course_link="http://example.com/course",
        lessons=lessons,
    )


@pytest.fixture
def sample_course_chunks():
    """Create sample course chunks for testing"""
    return [
        CourseChunk(
            content="Introduction to machine learning concepts and algorithms.",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=0,
        ),
        CourseChunk(
            content="Deep learning fundamentals and neural networks.",
            course_title="Test Course",
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Advanced neural network architectures and training.",
            course_title="Test Course",
            lesson_number=2,
            chunk_index=0,
        ),
    ]


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store"""
    mock = Mock()

    # Mock search results with content
    mock.search.return_value = SearchResults(
        documents=["Introduction to machine learning concepts and algorithms."],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
        error=None,
    )

    # Mock other methods
    mock.get_lesson_link.return_value = "http://example.com/lesson1"
    mock._resolve_course_name.return_value = "Test Course"
    mock.get_all_courses_metadata.return_value = [
        {
            "title": "Test Course",
            "instructor": "Test Instructor",
            "course_link": "http://example.com/course",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Introduction",
                    "lesson_link": "http://example.com/lesson1",
                }
            ],
        }
    ]

    return mock


@pytest.fixture
def empty_search_results():
    """Create empty search results for testing no-results scenarios"""
    return SearchResults(documents=[], metadata=[], distances=[], error=None)


@pytest.fixture
def error_search_results():
    """Create error search results for testing error scenarios"""
    return SearchResults.empty("Test error message")


@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client"""
    mock_client = Mock()

    # Mock response for regular message
    mock_response = Mock()
    mock_response.content = [Mock(text="Test AI response")]
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_tool_response():
    """Create a mock Anthropic client response with tool use"""
    mock_client = Mock()

    # Mock initial tool use response
    mock_tool_block = Mock()
    mock_tool_block.type = "tool_use"
    mock_tool_block.name = "search_course_content"
    mock_tool_block.input = {"query": "test query"}
    mock_tool_block.id = "tool_123"

    mock_initial_response = Mock()
    mock_initial_response.content = [mock_tool_block]
    mock_initial_response.stop_reason = "tool_use"

    # Mock final response after tool execution
    mock_final_response = Mock()
    mock_final_response.content = [Mock(text="Final AI response with tool results")]

    # Configure client to return different responses on subsequent calls
    mock_client.messages.create.side_effect = [
        mock_initial_response,
        mock_final_response,
    ]

    return mock_client


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager"""
    mock = Mock()
    mock.get_tool_definitions.return_value = [
        {
            "name": "search_course_content",
            "description": "Search course materials",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
    ]
    mock.execute_tool.return_value = "Mock tool result"
    mock.get_last_sources.return_value = [
        {"text": "Test Course - Lesson 1", "link": "http://example.com/lesson1"}
    ]
    mock.reset_sources.return_value = None

    return mock


@pytest.fixture
def mock_rag_system():
    """Create a mock RAG system for API testing"""
    mock = Mock()
    
    # Mock session manager
    mock_session_manager = Mock()
    mock_session_manager.create_session.return_value = "test-session-123"
    mock.session_manager = mock_session_manager
    
    # Mock query response
    mock.query.return_value = (
        "This is a test response about machine learning concepts.",
        [{"text": "Test Course - Lesson 1 content", "link": "http://example.com/lesson1"}]
    )
    
    # Mock course analytics
    mock.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course", "Advanced Course"]
    }
    
    # Mock document loading
    mock.add_course_folder.return_value = (2, 10)  # 2 courses, 10 chunks
    
    return mock




@pytest.fixture
def test_client(mock_rag_system) -> Generator[TestClient, None, None]:
    """Create a test client with mocked dependencies"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional
    
    # Create test app
    app = FastAPI(title="Course Materials RAG System Test", root_path="")
    
    # Add middleware
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    
    # Pydantic models
    class Source(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Source]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()
            
            answer, sources = mock_rag_system.query(request.query, session_id)
            
            formatted_sources = []
            for source in sources:
                if isinstance(source, dict):
                    formatted_sources.append(Source(text=source.get("text", ""), link=source.get("link")))
                else:
                    formatted_sources.append(Source(text=str(source), link=None))
            
            return QueryResponse(
                answer=answer,
                sources=formatted_sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Course Materials RAG System API"}
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_api_query_request():
    """Sample API query request data"""
    return {
        "query": "What is machine learning?",
        "session_id": "test-session-123"
    }


@pytest.fixture
def sample_api_query_response():
    """Sample API query response data"""
    return {
        "answer": "Machine learning is a subset of artificial intelligence.",
        "sources": [
            {"text": "Test Course - Lesson 1 content", "link": "http://example.com/lesson1"}
        ],
        "session_id": "test-session-123"
    }
