"""Tests for ref_utils.checks module."""

import os
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from ref_utils.checks import (
    _ENV_VAL_TRUE,
    _NO_LINT_ENV_VAR,
    check_all_python_files,
    contains_flag,
    run_mypy,
    run_pylint,
)
from ref_utils.config import Config, override_config
from ref_utils.utils import FAILURE, SUCCESS


def create_mock_run_result(stdout: str = "", returncode: int = 0):
    """Create a mock for the run function that returns a CompletedProcess."""
    mock_result = CompletedProcess(args=["test"], returncode=returncode, stdout=stdout.encode(), stderr=b"")
    return mock_result


class TestContainsFlag:
    """Tests for contains_flag function."""

    def test_flag_found(self, test_config: Config, tmp_path: Path) -> None:
        """Test when flag is found in output."""
        script = tmp_path / "test.py"
        script.write_text("print('FLAG{secret}')")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                mock_run.return_value = create_mock_run_result("FLAG{secret}")
                result = contains_flag("FLAG{secret}", script)
                assert result == SUCCESS

    def test_flag_not_found(self, test_config: Config, tmp_path: Path) -> None:
        """Test when flag is not found in output."""
        script = tmp_path / "test.py"
        script.write_text("print('wrong output')")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_err"):
                    mock_run.return_value = create_mock_run_result("wrong output")
                    result = contains_flag("FLAG{secret}", script)
                    assert result == FAILURE

    def test_empty_output(self, test_config: Config, tmp_path: Path) -> None:
        """Test when run returns empty output."""
        script = tmp_path / "test.py"
        script.write_text("")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_err"):
                    mock_run.return_value = create_mock_run_result("")
                    result = contains_flag("FLAG", script)
                    assert result == FAILURE

    def test_silent_mode(self, test_config: Config, tmp_path: Path) -> None:
        """Test silent mode doesn't print errors."""
        script = tmp_path / "test.py"
        script.write_text("")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_err") as mock_print:
                    mock_run.return_value = create_mock_run_result("no flag here")
                    result = contains_flag("FLAG", script, silent=True)
                    assert result == FAILURE
                    mock_print.assert_not_called()


class TestRunPylint:
    """Tests for run_pylint function."""

    def test_no_files_returns_success(self, test_config: Config) -> None:
        """Test that empty file list returns success."""
        with override_config(test_config):
            result = run_pylint([])
            assert result == SUCCESS

    def test_no_lint_env_var_skips(self, test_config: Config, tmp_path: Path) -> None:
        """Test that NO_LINT=1 skips linting."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch.dict(os.environ, {_NO_LINT_ENV_VAR: _ENV_VAL_TRUE}):
                result = run_pylint([test_file])
                assert result == SUCCESS

    def test_uses_config_path(self, test_config: Config, tmp_path: Path) -> None:
        """Test that pylint uses config path from Config."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")
        test_config.pylint_config_path = tmp_path / "custom_pylintrc"

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_ok"):
                    mock_run.return_value = create_mock_run_result("")
                    run_pylint([test_file])

                    # Check that the config path was used
                    call_args = mock_run.call_args[0][0]
                    assert str(test_config.pylint_config_path) in call_args

    def test_lint_success(self, test_config: Config, tmp_path: Path) -> None:
        """Test successful linting (no output)."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_ok"):
                    mock_run.return_value = create_mock_run_result("")
                    result = run_pylint([test_file])
                    assert result == SUCCESS

    def test_lint_failure(self, test_config: Config, tmp_path: Path) -> None:
        """Test linting with errors."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_warn"):
                    mock_run.return_value = create_mock_run_result("C0114: Missing module docstring")
                    result = run_pylint([test_file])
                    assert result == FAILURE


class TestRunMypy:
    """Tests for run_mypy function."""

    def test_no_files_returns_success(self, test_config: Config) -> None:
        """Test that empty file list returns success."""
        with override_config(test_config):
            result = run_mypy([])
            assert result == SUCCESS

    def test_no_lint_env_var_skips(self, test_config: Config, tmp_path: Path) -> None:
        """Test that NO_LINT=1 skips type checking."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x: int = 1")

        with override_config(test_config):
            with patch.dict(os.environ, {_NO_LINT_ENV_VAR: _ENV_VAL_TRUE}):
                result = run_mypy([test_file])
                assert result == SUCCESS

    def test_uses_config_path(self, test_config: Config, tmp_path: Path) -> None:
        """Test that mypy uses config path from Config."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x: int = 1")
        test_config.mypy_config_path = tmp_path / "custom_mypyrc"

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_ok"):
                    mock_run.return_value = create_mock_run_result("")
                    run_mypy([test_file])

                    call_args = mock_run.call_args[0][0]
                    assert str(test_config.mypy_config_path) in call_args

    def test_type_check_success(self, test_config: Config, tmp_path: Path) -> None:
        """Test successful type checking."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x: int = 1")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_ok"):
                    mock_run.return_value = create_mock_run_result("")
                    result = run_mypy([test_file])
                    assert result == SUCCESS

    def test_type_check_failure(self, test_config: Config, tmp_path: Path) -> None:
        """Test type checking with errors."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x: int = 'not an int'")

        with override_config(test_config):
            with patch("ref_utils.checks.run") as mock_run:
                with patch("ref_utils.checks.print_warn"):
                    mock_run.return_value = create_mock_run_result("error: Incompatible types")
                    result = run_mypy([test_file])
                    assert result == FAILURE


class TestCheckAllPythonFiles:
    """Tests for check_all_python_files function."""

    def test_no_files_returns_success(self, test_config: Config) -> None:
        """Test that no files returns success."""
        test_config.user_home_path.mkdir(parents=True, exist_ok=True)

        with override_config(test_config):
            result = check_all_python_files()
            assert result is True

    def test_no_lint_env_var_skips(self, test_config: Config) -> None:
        """Test that NO_LINT=1 skips all checks."""
        test_config.user_home_path.mkdir(parents=True, exist_ok=True)
        test_file = test_config.user_home_path / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch.dict(os.environ, {_NO_LINT_ENV_VAR: _ENV_VAL_TRUE}):
                result = check_all_python_files()
                assert result is True

    def test_finds_python_files(self, test_config: Config) -> None:
        """Test that Python files are found in user home."""
        test_config.user_home_path.mkdir(parents=True, exist_ok=True)
        test_file = test_config.user_home_path / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch("ref_utils.checks.run_pylint") as mock_pylint:
                with patch("ref_utils.checks.run_mypy") as mock_mypy:
                    with patch("ref_utils.checks.print_ok"):
                        mock_pylint.return_value = SUCCESS
                        mock_mypy.return_value = SUCCESS
                        result = check_all_python_files()

                        # Verify pylint and mypy were called
                        mock_pylint.assert_called_once()
                        mock_mypy.assert_called_once()
                        assert result is True

    def test_ignores_hidden_files(self, test_config: Config) -> None:
        """Test that hidden files (starting with .) are ignored."""
        test_config.user_home_path.mkdir(parents=True, exist_ok=True)
        hidden_file = test_config.user_home_path / ".hidden.py"
        hidden_file.write_text("x = 1")
        visible_file = test_config.user_home_path / "visible.py"
        visible_file.write_text("y = 2")

        with override_config(test_config):
            with patch("ref_utils.checks.run_pylint") as mock_pylint:
                with patch("ref_utils.checks.run_mypy") as mock_mypy:
                    with patch("ref_utils.checks.print_ok"):
                        mock_pylint.return_value = SUCCESS
                        mock_mypy.return_value = SUCCESS
                        check_all_python_files()

                        # Check that only visible file was passed
                        call_args = mock_pylint.call_args[0][0]
                        file_names = [f.name for f in call_args]
                        assert "visible.py" in file_names
                        assert ".hidden.py" not in file_names

    def test_uses_config_user_home(self, test_config: Config) -> None:
        """Test that user_home_path from config is used."""
        custom_home = test_config.user_home_path
        custom_home.mkdir(parents=True, exist_ok=True)
        test_file = custom_home / "test.py"
        test_file.write_text("x = 1")

        with override_config(test_config):
            with patch("ref_utils.checks.run_pylint") as mock_pylint:
                with patch("ref_utils.checks.run_mypy") as mock_mypy:
                    with patch("ref_utils.checks.print_ok"):
                        mock_pylint.return_value = SUCCESS
                        mock_mypy.return_value = SUCCESS
                        check_all_python_files()

                        # Verify the file from custom home was found
                        call_args = mock_pylint.call_args[0][0]
                        assert any(str(custom_home) in str(f) for f in call_args)
