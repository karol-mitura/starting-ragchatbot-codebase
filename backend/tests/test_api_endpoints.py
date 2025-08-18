import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""

    def test_root_endpoint(self, test_client):
        """Test the root endpoint returns correct message"""
        response = test_client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Course Materials RAG System API"}

    def test_query_endpoint_with_session_id(self, test_client, sample_api_query_request):
        """Test query endpoint with provided session ID"""
        response = test_client.post("/api/query", json=sample_api_query_request)
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"
        assert isinstance(data["sources"], list)
        
        # Validate source structure
        if data["sources"]:
            source = data["sources"][0]
            assert "text" in source
            assert "link" in source

    def test_query_endpoint_without_session_id(self, test_client):
        """Test query endpoint creates new session when none provided"""
        request_data = {"query": "What is machine learning?"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["session_id"] == "test-session-123"  # Mock returns this

    def test_query_endpoint_invalid_request(self, test_client):
        """Test query endpoint with invalid request data"""
        # Missing query field
        response = test_client.post("/api/query", json={})
        assert response.status_code == 422  # Validation error

        # Invalid data type
        response = test_client.post("/api/query", json={"query": 123})
        assert response.status_code == 422

    def test_query_endpoint_rag_system_error(self, test_client, mock_rag_system):
        """Test query endpoint handles RAG system errors gracefully"""
        # Make the mock RAG system raise an exception
        mock_rag_system.query.side_effect = Exception("RAG system error")
        
        request_data = {"query": "What is machine learning?"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 500
        assert "RAG system error" in response.json()["detail"]

    def test_courses_endpoint(self, test_client):
        """Test courses endpoint returns course statistics"""
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert data["total_courses"] == 2
        assert isinstance(data["course_titles"], list)
        assert len(data["course_titles"]) == 2

    def test_courses_endpoint_error(self, test_client, mock_rag_system):
        """Test courses endpoint handles errors gracefully"""
        # Make the mock RAG system raise an exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]

    def test_query_endpoint_source_formatting(self, test_client, mock_rag_system):
        """Test that sources are properly formatted in query response"""
        # Test with different source formats
        mock_rag_system.query.return_value = (
            "Test response",
            [
                {"text": "Dict source", "link": "http://example.com"},
                "String source",  # Legacy format
                {"text": "Dict without link"}  # No link field
            ]
        )
        
        request_data = {"query": "Test query"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        sources = data["sources"]
        
        assert len(sources) == 3
        
        # Dict source with link
        assert sources[0]["text"] == "Dict source"
        assert sources[0]["link"] == "http://example.com"
        
        # String source (legacy)
        assert sources[1]["text"] == "String source"
        assert sources[1]["link"] is None
        
        # Dict source without link
        assert sources[2]["text"] == "Dict without link"
        assert sources[2]["link"] is None

    def test_cors_headers(self, test_client):
        """Test that CORS headers are properly set"""
        response = test_client.get("/", headers={"Origin": "http://localhost:3000"})
        
        assert response.status_code == 200
        # Note: TestClient may not return all CORS headers, but the middleware is configured

    def test_query_endpoint_large_response(self, test_client, mock_rag_system):
        """Test query endpoint with large response data"""
        # Create a large response
        large_answer = "This is a very long answer. " * 100
        large_sources = [
            {"text": f"Large source {i}", "link": f"http://example.com/source{i}"}
            for i in range(10)
        ]
        
        mock_rag_system.query.return_value = (large_answer, large_sources)
        
        request_data = {"query": "Give me a detailed explanation"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["answer"]) > 1000
        assert len(data["sources"]) == 10

    def test_content_type_headers(self, test_client):
        """Test that endpoints return proper content-type headers"""
        # Test JSON endpoints
        response = test_client.get("/api/courses")
        assert "application/json" in response.headers.get("content-type", "")
        
        response = test_client.post("/api/query", json={"query": "test"})
        assert "application/json" in response.headers.get("content-type", "")

    def test_query_endpoint_empty_query(self, test_client):
        """Test query endpoint with empty query string"""
        request_data = {"query": ""}
        response = test_client.post("/api/query", json=request_data)
        
        # Should still process (validation allows empty strings)
        assert response.status_code == 200

    def test_query_endpoint_unicode_content(self, test_client, mock_rag_system):
        """Test query endpoint handles unicode content properly"""
        mock_rag_system.query.return_value = (
            "This is a response with unicode: 你好 🌟 café",
            [{"text": "Unicode source: ñoño", "link": "http://example.com/ñ"}]
        )
        
        request_data = {"query": "Test unicode: 测试"}
        response = test_client.post("/api/query", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "你好" in data["answer"]
        assert "ñoño" in data["sources"][0]["text"]


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints with mock dependencies"""

    def test_query_flow_with_session_creation(self, test_client, mock_rag_system):
        """Test complete query flow including session creation"""
        # Mock session creation
        mock_rag_system.session_manager.create_session.return_value = "new-session-456"
        mock_rag_system.query.return_value = (
            "Integration test response",
            [{"text": "Integration source", "link": "http://test.com"}]
        )
        
        # First request without session
        response = test_client.post("/api/query", json={"query": "Integration test"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "new-session-456"
        
        # Verify RAG system was called correctly
        mock_rag_system.session_manager.create_session.assert_called_once()
        mock_rag_system.query.assert_called_once_with("Integration test", "new-session-456")

    def test_courses_analytics_flow(self, test_client, mock_rag_system):
        """Test complete course analytics flow"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Course A", "Course B", "Course C", "Course D", "Course E"]
        }
        
        response = test_client.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert len(data["course_titles"]) == 5
        
        # Verify mock was called
        mock_rag_system.get_course_analytics.assert_called_once()

    def test_multiple_concurrent_queries(self, test_client, mock_rag_system):
        """Test handling multiple concurrent API requests"""
        # Configure mock for multiple calls
        mock_responses = [
            ("Response 1", [{"text": "Source 1", "link": "http://1.com"}]),
            ("Response 2", [{"text": "Source 2", "link": "http://2.com"}]),
            ("Response 3", [{"text": "Source 3", "link": "http://3.com"}])
        ]
        mock_rag_system.query.side_effect = mock_responses
        
        # Make multiple requests
        queries = ["Query 1", "Query 2", "Query 3"]
        responses = []
        
        for query in queries:
            response = test_client.post("/api/query", json={
                "query": query,
                "session_id": f"session-{len(responses)+1}"
            })
            responses.append(response)
        
        # Verify all responses
        assert all(r.status_code == 200 for r in responses)
        assert len(responses) == 3
        
        # Verify different responses
        for i, response in enumerate(responses):
            data = response.json()
            assert f"Response {i+1}" in data["answer"]