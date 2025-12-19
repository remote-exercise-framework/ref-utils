"""Tests for ref_utils.error module."""

import pytest

from ref_utils.error import (
    RefUtilsAssertionError,
    RefUtilsError,
    RefUtilsProcessError,
    RefUtilsProcessTimeoutError,
)


class TestRefUtilsError:
    """Tests for RefUtilsError base class."""

    def test_inheritance(self) -> None:
        """Test that RefUtilsError inherits from Exception."""
        assert issubclass(RefUtilsError, Exception)

    def test_instantiation(self) -> None:
        """Test basic instantiation."""
        error = RefUtilsError("test error message")
        assert str(error) == "test error message"

    def test_can_be_raised(self) -> None:
        """Test that RefUtilsError can be raised and caught."""
        with pytest.raises(RefUtilsError) as exc_info:
            raise RefUtilsError("test error")
        assert "test error" in str(exc_info.value)

    def test_with_multiple_args(self) -> None:
        """Test instantiation with multiple arguments."""
        error = RefUtilsError("arg1", "arg2")
        assert error.args == ("arg1", "arg2")


class TestRefUtilsProcessTimeoutError:
    """Tests for RefUtilsProcessTimeoutError."""

    def test_inheritance(self) -> None:
        """Test that RefUtilsProcessTimeoutError inherits from RefUtilsError."""
        assert issubclass(RefUtilsProcessTimeoutError, RefUtilsError)

    def test_message_formatting(self) -> None:
        """Test that the error message is formatted correctly."""
        error = RefUtilsProcessTimeoutError("./test_cmd", 30)
        error_str = str(error)
        assert "./test_cmd" in error_str
        assert "30" in error_str
        assert "Timeout" in error_str

    def test_attributes(self) -> None:
        """Test that cmd and timeout attributes are set."""
        error = RefUtilsProcessTimeoutError("./my_command", 10)
        assert error.cmd == "./my_command"
        assert error.timeout == 10

    def test_can_be_raised(self) -> None:
        """Test that the error can be raised and caught."""
        with pytest.raises(RefUtilsProcessTimeoutError) as exc_info:
            raise RefUtilsProcessTimeoutError("./cmd", 5)
        assert exc_info.value.cmd == "./cmd"
        assert exc_info.value.timeout == 5


class TestRefUtilsProcessError:
    """Tests for RefUtilsProcessError."""

    def test_inheritance(self) -> None:
        """Test that RefUtilsProcessError inherits from RefUtilsError."""
        assert issubclass(RefUtilsProcessError, RefUtilsError)

    def test_positive_exit_code(self) -> None:
        """Test message formatting with positive exit code."""
        error = RefUtilsProcessError("./test", 1, b"stdout", b"stderr")
        error_str = str(error)
        assert "./test" in error_str
        assert "1" in error_str
        assert "stdout" in error_str
        assert "stderr" in error_str

    def test_negative_exit_code_with_signal_name(self) -> None:
        """Test that negative exit codes show signal names."""
        # -9 corresponds to SIGKILL
        error = RefUtilsProcessError("./test", -9, b"", b"")
        error_str = str(error)
        assert "-9" in error_str
        assert "SIGKILL" in error_str

    def test_negative_exit_code_sigterm(self) -> None:
        """Test signal name for SIGTERM (-15)."""
        error = RefUtilsProcessError("./test", -15, b"", b"")
        error_str = str(error)
        assert "-15" in error_str
        assert "SIGTERM" in error_str

    def test_negative_exit_code_sigsegv(self) -> None:
        """Test signal name for SIGSEGV (-11)."""
        error = RefUtilsProcessError("./test", -11, b"", b"")
        error_str = str(error)
        assert "-11" in error_str
        assert "SIGSEGV" in error_str

    def test_attributes(self) -> None:
        """Test that attributes are set correctly."""
        error = RefUtilsProcessError("./cmd", 42, b"out", b"err")
        assert error.exit_code == 42
        assert error.stdout == b"out"
        assert error.stderr == b"err"

    def test_with_bytes_output(self) -> None:
        """Test that bytes output is decoded correctly."""
        stdout = b"stdout content"
        stderr = b"stderr content"
        error = RefUtilsProcessError("./test", 1, stdout, stderr)
        error_str = str(error)
        assert "stdout content" in error_str
        assert "stderr content" in error_str

    def test_with_none_output(self) -> None:
        """Test handling of None stdout/stderr."""
        # The code calls decode_or_str which should handle None/empty
        error = RefUtilsProcessError("./test", 1, b"", b"")
        error_str = str(error)
        assert "STDOUT" in error_str
        assert "STDERR" in error_str

    def test_can_be_raised(self) -> None:
        """Test that the error can be raised and caught."""
        with pytest.raises(RefUtilsProcessError) as exc_info:
            raise RefUtilsProcessError("./cmd", 2, b"out", b"err")
        assert exc_info.value.exit_code == 2


class TestRefUtilsAssertionError:
    """Tests for RefUtilsAssertionError."""

    def test_inheritance(self) -> None:
        """Test that RefUtilsAssertionError inherits from RefUtilsError."""
        assert issubclass(RefUtilsAssertionError, RefUtilsError)

    def test_instantiation(self) -> None:
        """Test basic instantiation."""
        error = RefUtilsAssertionError("assertion failed")
        assert "assertion failed" in str(error)

    def test_can_be_raised(self) -> None:
        """Test that the error can be raised and caught."""
        with pytest.raises(RefUtilsAssertionError):
            raise RefUtilsAssertionError("test")
