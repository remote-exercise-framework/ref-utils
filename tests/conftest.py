"""Pytest configuration and fixtures for ref-utils tests."""
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest

from ref_utils.config import Config, override_config


@pytest.fixture
def test_config(tmp_path: Path) -> Config:
    """Provide a Config with all paths pointing to tmp_path."""
    return Config(
        user_environ_path=tmp_path / ".user_environ",
        pylint_config_path=tmp_path / "pylintrc",
        mypy_config_path=tmp_path / "mypyrc",
        user_home_path=tmp_path / "home",
        drop_uid=9999,
        drop_gid=9999,
    )


@pytest.fixture
def use_test_config(test_config: Config) -> Generator[Config, None, None]:
    """Context fixture that overrides config for the test."""
    with override_config(test_config):
        yield test_config


@pytest.fixture
def user_environ_file(test_config: Config) -> Path:
    """Create a mock user environment file with sample data."""
    content = "HOME=/home/user\x00USER=testuser\x00PATH=/usr/bin\x00"
    test_config.user_environ_path.write_text(content)
    return test_config.user_environ_path


@pytest.fixture
def disable_exception_hook() -> Generator[None, None, None]:
    """Disable the global exception hook installed by ref_utils during tests."""
    original_hook = sys.excepthook
    yield
    sys.excepthook = original_hook


@pytest.fixture
def reset_registered_tasks() -> Generator[None, None, None]:
    """Reset the global __registered_tasks dict between tests."""
    # Import the module to access its internal state
    from ref_utils import decorator

    original_tasks = decorator.__registered_tasks.copy()
    decorator.__registered_tasks.clear()
    yield
    decorator.__registered_tasks.clear()
    decorator.__registered_tasks.update(original_tasks)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing process functions."""
    with patch("subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_multiprocessing():
    """Mock multiprocessing.Process and Pipe for testing privilege dropping."""
    with patch("ref_utils.process.Process") as mock_process, patch(
        "ref_utils.process.Pipe"
    ) as mock_pipe:
        yield mock_process, mock_pipe
