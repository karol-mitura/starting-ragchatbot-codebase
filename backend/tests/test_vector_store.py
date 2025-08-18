from unittest.mock import MagicMock, Mock, patch

import chromadb
import pytest
from models import Course, CourseChunk, Lesson
from vector_store import SearchResults, VectorStore


class TestVectorStoreSearch:
    """Test VectorStore.search() method and its interaction with MAX_RESULTS"""

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_with_max_results_zero(
        self, mock_embedding_func, mock_chroma_client
    ):
        """CRITICAL TEST: Verify that MAX_RESULTS=0 causes empty search results"""
        # Setup mocks
        mock_collection = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance

        # Create vector store with MAX_RESULTS=0 (current broken config)
        vector_store = VectorStore("test_path", "test_model", max_results=0)

        # Mock ChromaDB query response (this won't be called due to n_results=0)
        mock_collection.query.return_value = {
            "documents": [[]],  # Empty because n_results=0
            "metadatas": [[]],
            "distances": [[]],
        }

        # Execute search
        result = vector_store.search("test query")

        # Verify that query is called with n_results=0, causing empty results
        mock_collection.query.assert_called_once_with(
            query_texts=["test query"], n_results=0, where=None  # This is the problem!
        )

        # Verify empty results
        assert (
            result.is_empty()
        ), "Search with MAX_RESULTS=0 should return empty results"
        assert (
            len(result.documents) == 0
        ), "Documents should be empty when MAX_RESULTS=0"

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_with_proper_max_results(
        self, mock_embedding_func, mock_chroma_client
    ):
        """Test search with proper MAX_RESULTS > 0"""
        # Setup mocks
        mock_collection = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance

        # Create vector store with proper MAX_RESULTS
        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock ChromaDB query response with actual results
        mock_collection.query.return_value = {
            "documents": [["Test content about machine learning"]],
            "metadatas": [[{"course_title": "ML Course", "lesson_number": 1}]],
            "distances": [[0.1]],
        }

        # Execute search
        result = vector_store.search("machine learning")

        # Verify that query is called with proper n_results
        mock_collection.query.assert_called_once_with(
            query_texts=["machine learning"],
            n_results=5,  # This should work!
            where=None,
        )

        # Verify results are returned
        assert (
            not result.is_empty()
        ), "Search with proper MAX_RESULTS should return results"
        assert len(result.documents) == 1, "Should return the mocked document"
        assert result.documents[0] == "Test content about machine learning"

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_with_course_name_filter(
        self, mock_embedding_func, mock_chroma_client
    ):
        """Test search with course name filtering"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock course name resolution
        mock_catalog.query.return_value = {
            "documents": [["ML Fundamentals"]],
            "metadatas": [[{"title": "ML Fundamentals"}]],
        }

        # Mock content search
        mock_content.query.return_value = {
            "documents": [["Content from ML Fundamentals course"]],
            "metadatas": [[{"course_title": "ML Fundamentals", "lesson_number": 1}]],
            "distances": [[0.1]],
        }

        # Execute search with course filter
        result = vector_store.search("neural networks", course_name="ML")

        # Verify course name resolution was called
        mock_catalog.query.assert_called_once_with(query_texts=["ML"], n_results=1)

        # Verify content search with filter
        mock_content.query.assert_called_once_with(
            query_texts=["neural networks"],
            n_results=5,
            where={"course_title": "ML Fundamentals"},
        )

        assert not result.is_empty()
        assert result.documents[0] == "Content from ML Fundamentals course"

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_with_lesson_filter(self, mock_embedding_func, mock_chroma_client):
        """Test search with lesson number filtering"""
        # Setup mocks
        mock_collection = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock content search
        mock_collection.query.return_value = {
            "documents": [["Lesson 2 content"]],
            "metadatas": [[{"course_title": "Test Course", "lesson_number": 2}]],
            "distances": [[0.1]],
        }

        # Execute search with lesson filter
        result = vector_store.search("algorithms", lesson_number=2)

        # Verify content search with lesson filter
        mock_collection.query.assert_called_once_with(
            query_texts=["algorithms"], n_results=5, where={"lesson_number": 2}
        )

        assert not result.is_empty()
        assert result.documents[0] == "Lesson 2 content"

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_with_combined_filters(
        self, mock_embedding_func, mock_chroma_client
    ):
        """Test search with both course and lesson filters"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock course name resolution
        mock_catalog.query.return_value = {
            "documents": [["Advanced ML"]],
            "metadatas": [[{"title": "Advanced ML"}]],
        }

        # Mock content search
        mock_content.query.return_value = {
            "documents": [["Advanced ML lesson 3 content"]],
            "metadatas": [[{"course_title": "Advanced ML", "lesson_number": 3}]],
            "distances": [[0.1]],
        }

        # Execute search with both filters
        result = vector_store.search(
            "deep learning", course_name="Advanced", lesson_number=3
        )

        # Verify content search with combined filter
        expected_filter = {
            "$and": [{"course_title": "Advanced ML"}, {"lesson_number": 3}]
        }
        mock_content.query.assert_called_once_with(
            query_texts=["deep learning"], n_results=5, where=expected_filter
        )

        assert not result.is_empty()

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_course_not_found(self, mock_embedding_func, mock_chroma_client):
        """Test search when course name cannot be resolved"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock empty course resolution
        mock_catalog.query.return_value = {"documents": [[]], "metadatas": [[]]}

        # Execute search with invalid course name
        result = vector_store.search("test query", course_name="NonexistentCourse")

        # Verify error result
        assert result.error is not None
        assert "No course found matching 'NonexistentCourse'" in result.error

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_search_chromadb_exception(self, mock_embedding_func, mock_chroma_client):
        """Test search when ChromaDB raises an exception"""
        # Setup mocks
        mock_collection = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.return_value = mock_collection
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock ChromaDB exception
        mock_collection.query.side_effect = Exception("ChromaDB connection error")

        # Execute search
        result = vector_store.search("test query")

        # Verify error handling
        assert result.error is not None
        assert "Search error: ChromaDB connection error" in result.error


class TestVectorStoreFilterBuilding:
    """Test VectorStore._build_filter() method"""

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_build_filter_no_params(self, mock_embedding_func, mock_chroma_client):
        """Test filter building with no parameters"""
        vector_store = VectorStore("test_path", "test_model", max_results=5)
        filter_dict = vector_store._build_filter(None, None)
        assert filter_dict is None

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_build_filter_course_only(self, mock_embedding_func, mock_chroma_client):
        """Test filter building with course title only"""
        vector_store = VectorStore("test_path", "test_model", max_results=5)
        filter_dict = vector_store._build_filter("Test Course", None)

        expected = {"course_title": "Test Course"}
        assert filter_dict == expected

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_build_filter_lesson_only(self, mock_embedding_func, mock_chroma_client):
        """Test filter building with lesson number only"""
        vector_store = VectorStore("test_path", "test_model", max_results=5)
        filter_dict = vector_store._build_filter(None, 3)

        expected = {"lesson_number": 3}
        assert filter_dict == expected

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_build_filter_both_params(self, mock_embedding_func, mock_chroma_client):
        """Test filter building with both parameters"""
        vector_store = VectorStore("test_path", "test_model", max_results=5)
        filter_dict = vector_store._build_filter("Advanced Course", 5)

        expected = {"$and": [{"course_title": "Advanced Course"}, {"lesson_number": 5}]}
        assert filter_dict == expected


class TestVectorStoreCourseResolution:
    """Test VectorStore._resolve_course_name() method"""

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_resolve_course_name_success(self, mock_embedding_func, mock_chroma_client):
        """Test successful course name resolution"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock successful resolution
        mock_catalog.query.return_value = {
            "documents": [["Machine Learning Fundamentals"]],
            "metadatas": [[{"title": "Machine Learning Fundamentals"}]],
        }

        # Test resolution
        resolved = vector_store._resolve_course_name("ML")

        assert resolved == "Machine Learning Fundamentals"
        mock_catalog.query.assert_called_once_with(query_texts=["ML"], n_results=1)

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_resolve_course_name_not_found(
        self, mock_embedding_func, mock_chroma_client
    ):
        """Test course name resolution when no match found"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock no results
        mock_catalog.query.return_value = {"documents": [[]], "metadatas": [[]]}

        # Test resolution failure
        resolved = vector_store._resolve_course_name("NonexistentCourse")
        assert resolved is None

    @patch("vector_store.chromadb.PersistentClient")
    @patch(
        "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    )
    def test_resolve_course_name_exception(
        self, mock_embedding_func, mock_chroma_client
    ):
        """Test course name resolution when exception occurs"""
        # Setup mocks
        mock_catalog = Mock()
        mock_content = Mock()
        mock_client_instance = Mock()
        mock_client_instance.get_or_create_collection.side_effect = [
            mock_catalog,
            mock_content,
        ]
        mock_chroma_client.return_value = mock_client_instance

        vector_store = VectorStore("test_path", "test_model", max_results=5)

        # Mock exception
        mock_catalog.query.side_effect = Exception("Database error")

        # Test exception handling
        resolved = vector_store._resolve_course_name("Test Course")
        assert resolved is None


class TestSearchResults:
    """Test SearchResults utility class"""

    def test_search_results_from_chroma(self):
        """Test creating SearchResults from ChromaDB response"""
        chroma_result = {
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"course": "Course1"}, {"course": "Course2"}]],
            "distances": [[0.1, 0.2]],
        }

        result = SearchResults.from_chroma(chroma_result)

        assert len(result.documents) == 2
        assert result.documents[0] == "Document 1"
        assert result.metadata[0]["course"] == "Course1"
        assert result.distances[0] == 0.1

    def test_search_results_empty_creation(self):
        """Test creating empty SearchResults with error"""
        result = SearchResults.empty("No results found")

        assert result.error == "No results found"
        assert result.is_empty()
        assert len(result.documents) == 0

    def test_search_results_is_empty(self):
        """Test is_empty() method"""
        # Empty results
        empty_result = SearchResults([], [], [], None)
        assert empty_result.is_empty()

        # Non-empty results
        non_empty_result = SearchResults(["doc"], [{}], [0.1], None)
        assert not non_empty_result.is_empty()
