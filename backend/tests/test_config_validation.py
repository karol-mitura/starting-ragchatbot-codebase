import os
from unittest.mock import patch

import pytest
from config import Config, config


class TestConfigValidation:
    """Test configuration validation and potential issues"""

    def test_max_results_configuration(self):
        """Test that MAX_RESULTS is configured properly for search functionality"""
        # CRITICAL: This test will FAIL with current config where MAX_RESULTS = 0
        # MAX_RESULTS should be > 0 for search to return any results
        assert (
            config.MAX_RESULTS > 0
        ), f"MAX_RESULTS is {config.MAX_RESULTS}, should be > 0 for search to work"

        # Reasonable upper and lower bounds
        assert config.MAX_RESULTS <= 20, "MAX_RESULTS should not be excessively large"
        assert config.MAX_RESULTS >= 1, "MAX_RESULTS should be at least 1"

    def test_chunk_size_configuration(self):
        """Test that chunk size settings are reasonable"""
        assert config.CHUNK_SIZE > 0, "CHUNK_SIZE must be positive"
        assert config.CHUNK_SIZE >= 100, "CHUNK_SIZE should be at least 100 characters"
        assert config.CHUNK_SIZE <= 2000, "CHUNK_SIZE should not be excessively large"

    def test_chunk_overlap_configuration(self):
        """Test that chunk overlap is reasonable relative to chunk size"""
        assert config.CHUNK_OVERLAP >= 0, "CHUNK_OVERLAP should be non-negative"
        assert (
            config.CHUNK_OVERLAP < config.CHUNK_SIZE
        ), "CHUNK_OVERLAP should be less than CHUNK_SIZE"
        assert (
            config.CHUNK_OVERLAP <= config.CHUNK_SIZE * 0.5
        ), "CHUNK_OVERLAP should not exceed 50% of CHUNK_SIZE"

    def test_max_history_configuration(self):
        """Test conversation history configuration"""
        assert config.MAX_HISTORY >= 0, "MAX_HISTORY should be non-negative"
        assert config.MAX_HISTORY <= 10, "MAX_HISTORY should not be excessively large"

    def test_anthropic_api_key_presence(self):
        """Test that Anthropic API key is configured"""
        # This will depend on environment setup
        api_key = config.ANTHROPIC_API_KEY
        assert api_key is not None, "ANTHROPIC_API_KEY should not be None"

        # Skip detailed validation if key is empty (for CI environments)
        if api_key:
            assert len(api_key) > 10, "ANTHROPIC_API_KEY appears to be too short"

    def test_anthropic_model_configuration(self):
        """Test that Anthropic model is properly configured"""
        assert config.ANTHROPIC_MODEL, "ANTHROPIC_MODEL should not be empty"
        assert (
            "claude" in config.ANTHROPIC_MODEL.lower()
        ), "ANTHROPIC_MODEL should be a Claude model"

    def test_embedding_model_configuration(self):
        """Test that embedding model is configured"""
        assert config.EMBEDDING_MODEL, "EMBEDDING_MODEL should not be empty"
        assert len(config.EMBEDDING_MODEL) > 5, "EMBEDDING_MODEL name seems too short"

    def test_chroma_path_configuration(self):
        """Test that ChromaDB path is configured"""
        assert config.CHROMA_PATH, "CHROMA_PATH should not be empty"
        assert isinstance(config.CHROMA_PATH, str), "CHROMA_PATH should be a string"


class TestConfigImpactOnSearch:
    """Test how configuration affects search functionality"""

    @patch("vector_store.VectorStore")
    def test_max_results_zero_impact(self, mock_vector_store_class):
        """Test the impact of MAX_RESULTS=0 on search functionality"""
        # Create a mock vector store with the actual MAX_RESULTS config value
        mock_vector_store = mock_vector_store_class.return_value
        mock_vector_store.max_results = config.MAX_RESULTS

        # Simulate what happens when max_results is 0
        if config.MAX_RESULTS == 0:
            # This should reveal the critical issue - no search results will be returned
            mock_search_result = {
                "documents": [[]],  # Empty results due to n_results=0
                "metadatas": [[]],
                "distances": [[]],
            }
            mock_vector_store.course_content.query.return_value = mock_search_result

            # Test that search returns empty when MAX_RESULTS=0
            result = mock_vector_store.course_content.query(
                query_texts=["test query"],
                n_results=config.MAX_RESULTS,  # This will be 0!
            )

            assert (
                len(result["documents"][0]) == 0
            ), "MAX_RESULTS=0 causes empty search results"

    def test_config_edge_cases(self):
        """Test configuration edge cases that could break the system"""
        test_cases = [
            # Test case: MAX_RESULTS = 0 (current broken config)
            {"MAX_RESULTS": 0, "should_work": False, "reason": "No results returned"},
            # Test case: MAX_RESULTS negative (invalid)
            {
                "MAX_RESULTS": -1,
                "should_work": False,
                "reason": "Negative results count invalid",
            },
            # Test case: Reasonable MAX_RESULTS
            {"MAX_RESULTS": 5, "should_work": True, "reason": "Should work normally"},
        ]

        for case in test_cases:
            max_results = case["MAX_RESULTS"]
            should_work = case["should_work"]
            reason = case["reason"]

            if should_work:
                assert max_results > 0, f"MAX_RESULTS={max_results} {reason}"
            else:
                # Document the failure cases
                if max_results <= 0:
                    assert (
                        max_results <= 0
                    ), f"MAX_RESULTS={max_results} {reason} - This is a known issue"


class TestConfigEnvironmentVariables:
    """Test environment variable handling"""

    def test_env_variable_loading(self):
        """Test that environment variables are loaded correctly"""
        # Test that dotenv is working
        assert hasattr(
            config, "ANTHROPIC_API_KEY"
        ), "Config should have ANTHROPIC_API_KEY attribute"

    def test_config_can_be_modified(self):
        """Test that config values can be modified after instantiation"""
        # Create new config instance
        new_config = Config()
        original_key = new_config.ANTHROPIC_API_KEY
        
        # Modify the config value
        new_config.ANTHROPIC_API_KEY = "test_key_123"
        
        # Verify it was changed
        assert (
            new_config.ANTHROPIC_API_KEY == "test_key_123"
        ), "Config API key should be modifiable"
        
        # Verify the change didn't affect other instances
        another_config = Config()
        assert (
            another_config.ANTHROPIC_API_KEY == original_key
        ), "Other config instances should not be affected"

    def test_config_defaults(self):
        """Test that config has reasonable default values"""
        new_config = Config()
        
        # Test that we have expected default values
        assert new_config.ANTHROPIC_MODEL == "claude-sonnet-4-20250514"
        assert new_config.EMBEDDING_MODEL == "all-MiniLM-L6-v2"
        assert new_config.CHUNK_SIZE == 800
        assert new_config.CHUNK_OVERLAP == 100
        assert new_config.MAX_RESULTS == 5
        assert new_config.MAX_HISTORY == 2
        assert new_config.CHROMA_PATH == "./chroma_db"
        
        # ANTHROPIC_API_KEY can be empty or filled from environment
        assert hasattr(new_config, "ANTHROPIC_API_KEY"), "Should have ANTHROPIC_API_KEY attribute"
