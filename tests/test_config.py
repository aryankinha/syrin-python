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

    def test_config_default_values(self):
        """Config default values."""
        config = GlobalConfig()
        assert config.trace is False
        assert config.default_model is None

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
