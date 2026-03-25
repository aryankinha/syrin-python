"""Tests for global configuration and run() function."""

import syrin
from syrin.config import GlobalConfig, get_config


class TestGlobalConfig:
    """Tests for GlobalConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = GlobalConfig()
        assert config.trace is False
        assert config.default_model is None
        assert config.default_api_key is None

    def test_set_trace(self):
        """Test setting trace value."""
        config = get_config()
        config.trace = True
        assert config.trace is True
        config.trace = False

    def test_get_set_methods(self):
        """Test get/set methods."""
        config = get_config()
        config.set(trace=True)
        assert config.get("trace") is True
        assert config.get("nonexistent", "default") == "default"


class TestConfigure:
    """Tests for syrin.configure()."""

    def test_configure_trace(self):
        """Test configuring trace setting."""
        syrin.configure(trace=True)
        assert syrin.get_config().trace is True
        syrin.configure(trace=False)

    def test_configure_multiple(self):
        """Test configuring multiple values."""
        syrin.configure(trace=True)
        assert syrin.get_config().trace is True


class TestRunFunction:
    """Tests for syrin.run() function."""

    def test_run_function_exists(self):
        """Test that run function exists and is callable."""
        assert callable(syrin.run)

    def test_run_signature(self):
        """Test run function has correct signature."""
        import inspect

        sig = inspect.signature(syrin.run)
        params = list(sig.parameters.keys())
        assert "input" in params
        assert "model" in params
        assert "system_prompt" in params
        assert "tools" in params
        assert "budget" in params


# =============================================================================
# CONFIG EDGE CASES - TRY TO BREAK FUNCTIONALITY
# =============================================================================


class TestGlobalConfigEdgeCases:
    """Edge cases for global configuration."""

    def test_config_get_nonexistent(self):
        """Get nonexistent config value."""
        config = get_config()
        assert config.get("nonexistent") is None

    def test_config_default_return(self):
        """Config get with default."""
        config = get_config()
        result = config.get("missing", "default_value")
        assert result == "default_value"

    def test_config_set_and_get(self):
        """Config set and get."""
        config = get_config()
        config.trace = True
        assert config.trace is True


# =============================================================================
# SECURITY — GlobalConfig whitelist
# =============================================================================


class TestGlobalConfigSecurity:
    """Security: set()/get() must not allow private attribute access."""

    def test_set_private_attribute_is_silently_ignored(self) -> None:
        """Setting a private attribute via set() is silently ignored."""
        config = GlobalConfig()
        config.set(_lock="injected")
        # _lock must still be a real lock, not a string
        assert config._lock != "injected"

    def test_set_unknown_key_is_silently_ignored(self) -> None:
        """Unknown keys in set() are silently ignored."""
        config = GlobalConfig()
        config.set(nonexistent_key="value")  # should not raise
        assert not hasattr(config, "nonexistent_key")

    def test_get_private_attribute_returns_default(self) -> None:
        """get() on a private attribute returns the default."""
        config = GlobalConfig()
        assert config.get("_lock") is None
        assert config.get("_cloud_api_key", "SENTINEL") == "SENTINEL"

    def test_get_unknown_key_returns_default(self) -> None:
        """get() on an unknown key returns the default."""
        config = GlobalConfig()
        assert config.get("__class__") is None
        assert config.get("nonexistent", 42) == 42

    def test_set_whitelisted_keys_work(self) -> None:
        """All whitelisted keys can be set via set()."""
        config = GlobalConfig()
        config.set(trace=True, debug=True)
        assert config.trace is True
        assert config.debug is True
        config.set(trace=False, debug=False)

    def test_get_whitelisted_keys_work(self) -> None:
        """All whitelisted keys can be read via get()."""
        config = GlobalConfig()
        result = config.get("trace")
        assert result is False
