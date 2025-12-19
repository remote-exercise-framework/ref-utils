"""Tests for ref_utils.assertion module."""
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from ref_utils.assertion import _assert, assert_is_dir, assert_is_exec, assert_is_file


class TestAssert:
    """Tests for the _assert helper function."""

    def test_assert_true_condition(self) -> None:
        """Test that _assert returns True for true conditions."""
        assert _assert(True, "error message", silent=False) is True

    def test_assert_false_condition_silent(self) -> None:
        """Test that _assert returns False silently when silent=True."""
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            result = _assert(False, "error message", silent=True)
            assert result is False
            # Should not print anything in silent mode
            assert mock_stdout.getvalue() == ""

    def test_assert_false_condition_prints_error(self) -> None:
        """Test that _assert prints error message when silent=False."""
        with patch("ref_utils.assertion.print_err") as mock_print_err:
            result = _assert(False, "test error", silent=False)
            assert result is False
            mock_print_err.assert_called_once()
            call_args = mock_print_err.call_args[0][0]
            assert "test error" in call_args


class TestAssertIsExec:
    """Tests for assert_is_exec function."""

    def test_existing_executable(self, tmp_path: Path) -> None:
        """Test with an existing executable file."""
        exec_file = tmp_path / "test_exec"
        exec_file.write_text("#!/bin/bash\necho hello")
        exec_file.chmod(0o755)

        assert assert_is_exec(exec_file) is True

    def test_existing_executable_as_string(self, tmp_path: Path) -> None:
        """Test with path provided as string."""
        exec_file = tmp_path / "test_exec"
        exec_file.write_text("#!/bin/bash\necho hello")
        exec_file.chmod(0o755)

        assert assert_is_exec(str(exec_file)) is True

    def test_non_existing_file(self, tmp_path: Path) -> None:
        """Test with a non-existing file."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_exec(non_existing) is False

    def test_non_executable_file(self, tmp_path: Path) -> None:
        """Test with an existing but non-executable file."""
        non_exec = tmp_path / "not_exec"
        non_exec.write_text("some content")
        non_exec.chmod(0o644)

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_exec(non_exec) is False

    def test_directory_not_executable(self, tmp_path: Path) -> None:
        """Test that a directory is not considered an executable."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_exec(test_dir) is False

    def test_silent_mode(self, tmp_path: Path) -> None:
        """Test silent mode doesn't print errors."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err") as mock_print:
            assert assert_is_exec(non_existing, silent=True) is False
            mock_print.assert_not_called()


class TestAssertIsFile:
    """Tests for assert_is_file function."""

    def test_existing_file(self, tmp_path: Path) -> None:
        """Test with an existing file."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")

        assert assert_is_file(test_file) is True

    def test_existing_file_as_string(self, tmp_path: Path) -> None:
        """Test with path provided as string."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")

        assert assert_is_file(str(test_file)) is True

    def test_non_existing_file(self, tmp_path: Path) -> None:
        """Test with a non-existing file."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_file(non_existing) is False

    def test_directory_is_not_file(self, tmp_path: Path) -> None:
        """Test that a directory is not considered a file."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_file(test_dir) is False

    def test_silent_mode(self, tmp_path: Path) -> None:
        """Test silent mode doesn't print errors."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err") as mock_print:
            assert assert_is_file(non_existing, silent=True) is False
            mock_print.assert_not_called()


class TestAssertIsDir:
    """Tests for assert_is_dir function."""

    def test_existing_directory(self, tmp_path: Path) -> None:
        """Test with an existing directory."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        assert assert_is_dir(test_dir) is True

    def test_existing_directory_as_string(self, tmp_path: Path) -> None:
        """Test with path provided as string."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        assert assert_is_dir(str(test_dir)) is True

    def test_non_existing_directory(self, tmp_path: Path) -> None:
        """Test with a non-existing directory."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_dir(non_existing) is False

    def test_file_is_not_directory(self, tmp_path: Path) -> None:
        """Test that a file is not considered a directory."""
        test_file = tmp_path / "test_file.txt"
        test_file.write_text("content")

        with patch("ref_utils.assertion.print_err"):
            assert assert_is_dir(test_file) is False

    def test_silent_mode(self, tmp_path: Path) -> None:
        """Test silent mode doesn't print errors."""
        non_existing = tmp_path / "does_not_exist"

        with patch("ref_utils.assertion.print_err") as mock_print:
            assert assert_is_dir(non_existing, silent=True) is False
            mock_print.assert_not_called()

    def test_tmp_path_is_directory(self, tmp_path: Path) -> None:
        """Test that tmp_path fixture itself is a directory."""
        assert assert_is_dir(tmp_path) is True
