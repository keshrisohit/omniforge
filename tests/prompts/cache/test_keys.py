"""Tests for cache key generation."""

from omniforge.prompts.cache.keys import generate_cache_key


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""

    def test_generate_key_with_version_ids_only(self) -> None:
        """Cache key should be generated from version IDs alone."""
        version_ids = {"system": "v1", "tenant": "v2"}
        key = generate_cache_key(version_ids)

        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 produces 64 hex characters

    def test_generate_key_with_version_ids_and_variables(self) -> None:
        """Cache key should include both version IDs and stable variables."""
        version_ids = {"system": "v1", "tenant": "v2"}
        variables = {"context": "test", "setting": "prod"}
        key = generate_cache_key(version_ids, variables)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_same_inputs_produce_same_key(self) -> None:
        """Same inputs should produce identical cache keys (deterministic)."""
        version_ids = {"system": "v1", "tenant": "v2"}
        variables = {"context": "test"}

        key1 = generate_cache_key(version_ids, variables)
        key2 = generate_cache_key(version_ids, variables)

        assert key1 == key2

    def test_different_version_ids_produce_different_keys(self) -> None:
        """Different version IDs should produce different cache keys."""
        version_ids1 = {"system": "v1", "tenant": "v2"}
        version_ids2 = {"system": "v1", "tenant": "v3"}

        key1 = generate_cache_key(version_ids1)
        key2 = generate_cache_key(version_ids2)

        assert key1 != key2

    def test_different_stable_variables_produce_different_keys(self) -> None:
        """Different stable variable values should produce different keys."""
        version_ids = {"system": "v1"}
        variables1 = {"context": "test1"}
        variables2 = {"context": "test2"}

        key1 = generate_cache_key(version_ids, variables1)
        key2 = generate_cache_key(version_ids, variables2)

        assert key1 != key2

    def test_user_input_excluded_from_key(self) -> None:
        """user_input variable should be excluded (too variable for caching)."""
        version_ids = {"system": "v1"}
        variables1 = {"context": "test", "user_input": "hello"}
        variables2 = {"context": "test", "user_input": "world"}

        key1 = generate_cache_key(version_ids, variables1)
        key2 = generate_cache_key(version_ids, variables2)

        # Keys should be identical despite different user_input
        assert key1 == key2

    def test_timestamp_excluded_from_key(self) -> None:
        """timestamp variable should be excluded (too variable for caching)."""
        version_ids = {"system": "v1"}
        variables1 = {"context": "test", "timestamp": "2024-01-01"}
        variables2 = {"context": "test", "timestamp": "2024-01-02"}

        key1 = generate_cache_key(version_ids, variables1)
        key2 = generate_cache_key(version_ids, variables2)

        # Keys should be identical despite different timestamp
        assert key1 == key2

    def test_request_id_excluded_from_key(self) -> None:
        """request_id variable should be excluded (too variable for caching)."""
        version_ids = {"system": "v1"}
        variables1 = {"context": "test", "request_id": "req-1"}
        variables2 = {"context": "test", "request_id": "req-2"}

        key1 = generate_cache_key(version_ids, variables1)
        key2 = generate_cache_key(version_ids, variables2)

        # Keys should be identical despite different request_id
        assert key1 == key2

    def test_key_ordering_independence(self) -> None:
        """Cache key should be the same regardless of dictionary ordering."""
        version_ids1 = {"system": "v1", "tenant": "v2", "feature": "v3"}
        version_ids2 = {"feature": "v3", "tenant": "v2", "system": "v1"}

        key1 = generate_cache_key(version_ids1)
        key2 = generate_cache_key(version_ids2)

        assert key1 == key2

    def test_empty_variables_dict(self) -> None:
        """Empty variables dict should work correctly."""
        version_ids = {"system": "v1"}
        key = generate_cache_key(version_ids, {})

        assert isinstance(key, str)
        assert len(key) == 64

    def test_none_variables(self) -> None:
        """None variables should work correctly."""
        version_ids = {"system": "v1"}
        key = generate_cache_key(version_ids, None)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_complex_nested_variables(self) -> None:
        """Complex nested variable structures should be handled."""
        version_ids = {"system": "v1"}
        variables = {
            "config": {"nested": {"value": 123}},
            "list_data": [1, 2, 3],
        }
        key = generate_cache_key(version_ids, variables)

        assert isinstance(key, str)
        assert len(key) == 64

    def test_variable_order_independence(self) -> None:
        """Variable dict ordering should not affect cache key."""
        version_ids = {"system": "v1"}
        variables1 = {"a": 1, "b": 2, "c": 3}
        variables2 = {"c": 3, "a": 1, "b": 2}

        key1 = generate_cache_key(version_ids, variables1)
        key2 = generate_cache_key(version_ids, variables2)

        assert key1 == key2
