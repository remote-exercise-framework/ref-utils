"""Configuration module for ref-utils with testable path abstraction."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator


@dataclass
class Config:
    """Configuration for ref-utils paths and constants.

    All container-specific paths are configurable here to enable testing
    without requiring a container environment.
    """

    user_environ_path: Path = field(default_factory=lambda: Path("/tmp/.user_environ"))
    pylint_config_path: Path = field(default_factory=lambda: Path("/etc/pylintrc"))
    mypy_config_path: Path = field(default_factory=lambda: Path("/etc/mypyrc"))
    user_home_path: Path = field(default_factory=lambda: Path("/home/user"))
    drop_uid: int = 9999
    drop_gid: int = 9999


# Context variable for thread-safe config override
_config_var: ContextVar[Config] = ContextVar("config", default=Config())


def get_config() -> Config:
    """Get the current configuration."""
    return _config_var.get()


def set_config(config: Config) -> None:
    """Set the global configuration."""
    _config_var.set(config)


@contextmanager
def override_config(config: Config) -> Generator[Config, None, None]:
    """Context manager for temporarily overriding config (useful for testing).

    Args:
        config: The temporary configuration to use.

    Yields:
        The provided config object.
    """
    token = _config_var.set(config)
    try:
        yield config
    finally:
        _config_var.reset(token)
