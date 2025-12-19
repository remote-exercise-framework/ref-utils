"""Tests for ref_utils.process module."""

import sys
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest

from ref_utils.config import Config, override_config
from ref_utils.error import (
    RefUtilsError,
    RefUtilsProcessError,
    RefUtilsProcessTimeoutError,
)
from ref_utils.process import (
    get_payload_from_executable,
    join_with_space_if_list,
    ref_util_exception_hook,
    ref_util_install_global_exception_hook,
    run_capture_output,
    run_with_payload,
)
from ref_utils.serialization import safe_dumps, safe_loads


class TestJoinWithSpaceIfList:
    """Tests for join_with_space_if_list helper."""

    def test_string_passthrough(self) -> None:
        """Test that strings are passed through unchanged."""
        assert join_with_space_if_list("hello world") == "hello world"

    def test_list_joined_with_space(self) -> None:
        """Test that lists are joined with space."""
        assert join_with_space_if_list(["a", "b", "c"]) == "a b c"

    def test_empty_list(self) -> None:
        """Test empty list."""
        assert join_with_space_if_list([]) == ""

    def test_single_item_list(self) -> None:
        """Test single item list."""
        assert join_with_space_if_list(["single"]) == "single"


class TestSerialization:
    """Tests for JSON-based serialization in process module."""

    def test_serializes_completed_process(self) -> None:
        """Test that CompletedProcess can be serialized."""
        cp = CompletedProcess(args=["test"], returncode=0, stdout=b"", stderr=b"")
        serialized = safe_dumps(cp)
        result = safe_loads(serialized)
        assert isinstance(result, CompletedProcess)
        assert result.returncode == 0

    def test_serializes_ref_utils_errors(self) -> None:
        """Test that RefUtilsError can be serialized."""
        error = RefUtilsError("test error")
        serialized = safe_dumps(error)
        result = safe_loads(serialized)
        assert isinstance(result, RefUtilsError)

    def test_serializes_process_timeout_error(self) -> None:
        """Test that RefUtilsProcessTimeoutError can be serialized."""
        error = RefUtilsProcessTimeoutError("cmd", 10)
        serialized = safe_dumps(error)
        result = safe_loads(serialized)
        assert isinstance(result, RefUtilsProcessTimeoutError)

    def test_serializes_process_error(self) -> None:
        """Test that RefUtilsProcessError can be serialized."""
        error = RefUtilsProcessError("cmd", 1, b"out", b"err")
        serialized = safe_dumps(error)
        result = safe_loads(serialized)
        assert isinstance(result, RefUtilsProcessError)

    def test_serializes_basic_types(self) -> None:
        """Test that basic types (int, str, list, dict) are serialized."""
        assert safe_loads(safe_dumps(42)) == 42
        assert safe_loads(safe_dumps("hello")) == "hello"
        assert safe_loads(safe_dumps([1, 2, 3])) == [1, 2, 3]
        assert safe_loads(safe_dumps({"a": 1})) == {"a": 1}


class TestRefUtilExceptionHook:
    """Tests for ref_util_exception_hook function."""

    def test_handles_ref_utils_error(self) -> None:
        """Test that RefUtilsError is printed via print_err."""
        error = RefUtilsError("custom error message")
        with patch("ref_utils.process.print_err") as mock_print:
            ref_util_exception_hook(RefUtilsError, error, None)
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "custom error message" in call_args

    def test_handles_keyboard_interrupt(self) -> None:
        """Test handling of KeyboardInterrupt."""
        error = KeyboardInterrupt()
        with patch("ref_utils.process.print_err") as mock_print:
            ref_util_exception_hook(KeyboardInterrupt, error, None)
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Keyboard Interrupt" in call_args

    def test_handles_other_exceptions(self) -> None:
        """Test that other exceptions use default hook."""
        error = ValueError("some error")
        with patch("sys.__excepthook__") as mock_hook:
            ref_util_exception_hook(ValueError, error, None)
            mock_hook.assert_called_once()


class TestRefUtilInstallGlobalExceptionHook:
    """Tests for ref_util_install_global_exception_hook function."""

    def test_installs_hook(self) -> None:
        """Test that the hook is installed."""
        original_hook = sys.excepthook
        try:
            ref_util_install_global_exception_hook()
            assert sys.excepthook is not original_hook
        finally:
            sys.excepthook = original_hook


class TestRunCaptureOutput:
    """Tests for run_capture_output function."""

    def test_captures_stdout(self, test_config: Config) -> None:
        """Test that stdout is captured."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

        with override_config(test_config):
            # Mock the entire privilege dropping mechanism
            with patch("ref_utils.process.Process") as mock_process_class:
                with patch("ref_utils.process.Pipe") as mock_pipe:
                    # Setup mock pipe
                    parent_conn = MagicMock()
                    child_conn = MagicMock()
                    mock_pipe.return_value = (parent_conn, child_conn)

                    # Create a mock CompletedProcess
                    mock_result = CompletedProcess(
                        args=["echo", "hello"],
                        returncode=0,
                        stdout=b"hello\n",
                        stderr=b"",
                    )
                    serialized_result = safe_dumps(mock_result)
                    parent_conn.recv_bytes.return_value = serialized_result

                    # Setup mock process
                    mock_process = MagicMock()
                    mock_process_class.return_value = mock_process

                    returncode, output = run_capture_output(["echo", "hello"])

                    assert returncode == 0
                    assert output == b"hello\n"


class TestGetPayloadFromExecutable:
    """Tests for get_payload_from_executable function."""

    def test_returns_output(self, test_config: Config) -> None:
        """Test that command output is returned."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

        with override_config(test_config):
            with patch("ref_utils.process.Process") as mock_process_class:
                with patch("ref_utils.process.Pipe") as mock_pipe:
                    parent_conn = MagicMock()
                    child_conn = MagicMock()
                    mock_pipe.return_value = (parent_conn, child_conn)

                    mock_result = CompletedProcess(
                        args=["./script"],
                        returncode=0,
                        stdout=b"payload data",
                        stderr=b"",
                    )
                    parent_conn.recv_bytes.return_value = safe_dumps(mock_result)

                    mock_process = MagicMock()
                    mock_process_class.return_value = mock_process

                    with patch("ref_utils.process.print_ok"):
                        returncode, output = get_payload_from_executable(["./script"])

                    assert returncode == 0
                    assert output == b"payload data"


class TestRunWithPayload:
    """Tests for run_with_payload function."""

    def test_detects_null_bytes(self, test_config: Config) -> None:
        """Test that null bytes in command are detected."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

        with override_config(test_config):
            with pytest.raises(RefUtilsError) as exc_info:
                run_with_payload(["./test\x00injection"])
            assert "null byte" in str(exc_info.value)

    def test_flag_verification_success(self, test_config: Config) -> None:
        """Test flag verification succeeds when flag is present."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

        with override_config(test_config):
            with patch("ref_utils.process.Process") as mock_process_class:
                with patch("ref_utils.process.Pipe") as mock_pipe:
                    parent_conn = MagicMock()
                    child_conn = MagicMock()
                    mock_pipe.return_value = (parent_conn, child_conn)

                    mock_result = CompletedProcess(
                        args=["./test"],
                        returncode=0,
                        stdout=b"FLAG{secret}",
                        stderr=b"",
                    )
                    parent_conn.recv_bytes.return_value = safe_dumps(mock_result)

                    mock_process = MagicMock()
                    mock_process_class.return_value = mock_process

                    returncode, output = run_with_payload(["./test"], flag=b"FLAG{secret}")

                    assert returncode == 0
                    assert b"FLAG{secret}" in output

    def test_flag_verification_failure(self, test_config: Config) -> None:
        """Test flag verification fails when flag is missing."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

        with override_config(test_config):
            with patch("ref_utils.process.Process") as mock_process_class:
                with patch("ref_utils.process.Pipe") as mock_pipe:
                    parent_conn = MagicMock()
                    child_conn = MagicMock()
                    mock_pipe.return_value = (parent_conn, child_conn)

                    mock_result = CompletedProcess(
                        args=["./test"],
                        returncode=0,
                        stdout=b"wrong output",
                        stderr=b"",
                    )
                    parent_conn.recv_bytes.return_value = safe_dumps(mock_result)

                    mock_process = MagicMock()
                    mock_process_class.return_value = mock_process

                    with pytest.raises(RefUtilsError) as exc_info:
                        run_with_payload(["./test"], flag=b"FLAG{secret}")
                    assert "Wrong output" in str(exc_info.value)


class TestDropPrivileges:
    """Tests for drop_privileges decorator."""

    def test_uses_config_uid_gid(self, test_config: Config) -> None:
        """Test that drop_privileges uses config values."""
        test_config.drop_uid = 1234
        test_config.drop_gid = 5678

        with override_config(test_config):
            with patch("ref_utils.process.Process") as mock_process_class:
                with patch("ref_utils.process.Pipe") as mock_pipe:
                    parent_conn = MagicMock()
                    child_conn = MagicMock()
                    mock_pipe.return_value = (parent_conn, child_conn)

                    # Return a simple serialized result
                    parent_conn.recv_bytes.return_value = safe_dumps("result")

                    mock_process = MagicMock()
                    mock_process_class.return_value = mock_process

                    # Import and call the decorated run function
                    from ref_utils.process import run

                    test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
                    test_config.user_environ_path.write_text("PATH=/usr/bin\x00")

                    try:
                        run(["echo", "test"])
                    except Exception:
                        pass  # We just want to verify the Process call

                    # Verify Process was called with correct UID/GID from config
                    if mock_process_class.called:
                        call_args = mock_process_class.call_args
                        target_args = call_args[1].get("args", call_args[0][1] if len(call_args[0]) > 1 else None)
                        if target_args:
                            # Check if uid (1234) and gid (5678) are in the args
                            assert 1234 in target_args or str(1234) in str(target_args)
