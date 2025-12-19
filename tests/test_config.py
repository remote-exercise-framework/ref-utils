"""Tests for ref_utils.config module."""

from pathlib import Path

from ref_utils.config import Config, get_config, override_config, set_config


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_values(self) -> None:
        """Test that default values are set correctly."""
        config = Config()
        assert config.user_environ_path == Path("/tmp/.user_environ")
        assert config.pylint_config_path == Path("/etc/pylintrc")
        assert config.mypy_config_path == Path("/etc/mypyrc")
        assert config.user_home_path == Path("/home/user")
        assert config.drop_uid == 9999
        assert config.drop_gid == 9999

    def test_custom_values(self, tmp_path: Path) -> None:
        """Test that custom values can be set."""
        config = Config(
            user_environ_path=tmp_path / ".env",
            pylint_config_path=tmp_path / "pylint.cfg",
            mypy_config_path=tmp_path / "mypy.cfg",
            user_home_path=tmp_path / "home",
            drop_uid=1000,
            drop_gid=1000,
        )
        assert config.user_environ_path == tmp_path / ".env"
        assert config.drop_uid == 1000
        assert config.drop_gid == 1000


class TestGetSetConfig:
    """Tests for get_config and set_config functions."""

    def test_get_default_config(self) -> None:
        """Test that get_config returns a Config instance."""
        config = get_config()
        assert isinstance(config, Config)

    def test_set_config(self, tmp_path: Path) -> None:
        """Test that set_config updates the global config."""
        original = get_config()
        try:
            new_config = Config(user_home_path=tmp_path / "custom")
            set_config(new_config)
            assert get_config().user_home_path == tmp_path / "custom"
        finally:
            set_config(original)


class TestOverrideConfig:
    """Tests for override_config context manager."""

    def test_temporarily_overrides_config(self, tmp_path: Path) -> None:
        """Test that config is temporarily overridden."""
        original_path = get_config().user_home_path
        new_config = Config(user_home_path=tmp_path / "temp")

        with override_config(new_config):
            assert get_config().user_home_path == tmp_path / "temp"

        # Should be restored after context
        assert get_config().user_home_path == original_path

    def test_yields_config(self, tmp_path: Path) -> None:
        """Test that override_config yields the config."""
        new_config = Config(user_home_path=tmp_path / "test")

        with override_config(new_config) as yielded:
            assert yielded is new_config

    def test_restores_on_exception(self, tmp_path: Path) -> None:
        """Test that config is restored even on exception."""
        original_path = get_config().user_home_path
        new_config = Config(user_home_path=tmp_path / "temp")

        try:
            with override_config(new_config):
                raise ValueError("test exception")
        except ValueError:
            pass

        assert get_config().user_home_path == original_path

    def test_nested_overrides(self, tmp_path: Path) -> None:
        """Test that nested overrides work correctly."""
        original_path = get_config().user_home_path
        config1 = Config(user_home_path=tmp_path / "level1")
        config2 = Config(user_home_path=tmp_path / "level2")

        with override_config(config1):
            assert get_config().user_home_path == tmp_path / "level1"

            with override_config(config2):
                assert get_config().user_home_path == tmp_path / "level2"

            assert get_config().user_home_path == tmp_path / "level1"

        assert get_config().user_home_path == original_path
