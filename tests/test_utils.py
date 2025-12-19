"""Tests for ref_utils.utils module."""
import os
from pathlib import Path
from unittest.mock import patch

from colorama import Fore, Style

from ref_utils.config import Config, override_config
from ref_utils.utils import (
    decode_or_str,
    get_user_environment,
    map_path_as_posix,
    print_err,
    print_ok,
    print_warn,
    test_result_will_be_submitted as check_result_will_be_submitted,
    write_stdout,
)


class TestPrintOk:
    """Tests for print_ok function."""

    def test_prints_green_text(self) -> None:
        """Test that print_ok prints green text."""
        with patch("builtins.print") as mock_print:
            print_ok("test message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert Fore.GREEN in call_args
            assert "test message" in call_args
            assert Style.RESET_ALL in call_args

    def test_multiple_args(self) -> None:
        """Test print_ok with multiple arguments."""
        with patch("builtins.print") as mock_print:
            print_ok("arg1", "arg2")
            call_args = mock_print.call_args[0][0]
            assert "arg1" in call_args
            assert "arg2" in call_args

    def test_custom_separator(self) -> None:
        """Test print_ok with custom separator."""
        with patch("builtins.print") as mock_print:
            print_ok("a", "b", sep="-")
            call_args = mock_print.call_args[0][0]
            assert "a-b" in call_args


class TestPrintWarn:
    """Tests for print_warn function."""

    def test_prints_yellow_text(self) -> None:
        """Test that print_warn prints yellow text."""
        with patch("builtins.print") as mock_print:
            print_warn("warning message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert Fore.YELLOW in call_args
            assert "warning message" in call_args
            assert Style.RESET_ALL in call_args


class TestPrintErr:
    """Tests for print_err function."""

    def test_prints_red_text(self) -> None:
        """Test that print_err prints red text."""
        with patch("builtins.print") as mock_print:
            print_err("error message")
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert Fore.RED in call_args
            assert "error message" in call_args
            assert Style.RESET_ALL in call_args


class TestWriteStdout:
    """Tests for write_stdout function."""

    def test_writes_to_stdout(self) -> None:
        """Test that write_stdout writes directly to stdout."""
        with patch("sys.stdout") as mock_stdout:
            write_stdout("test data")
            mock_stdout.write.assert_called_once_with("test data")


class TestTestResultWillBeSubmitted:
    """Tests for test_result_will_be_submitted function."""

    def test_returns_true_for_1(self) -> None:
        """Test that '1' returns True."""
        with patch.dict(os.environ, {"RESULT_WILL_BE_SUBMITTED": "1"}):
            assert check_result_will_be_submitted() is True

    def test_returns_true_for_true(self) -> None:
        """Test that 'true' returns True."""
        with patch.dict(os.environ, {"RESULT_WILL_BE_SUBMITTED": "true"}):
            assert check_result_will_be_submitted() is True

    def test_returns_true_for_TRUE(self) -> None:
        """Test that 'TRUE' (uppercase) returns True."""
        with patch.dict(os.environ, {"RESULT_WILL_BE_SUBMITTED": "TRUE"}):
            assert check_result_will_be_submitted() is True

    def test_returns_false_for_0(self) -> None:
        """Test that '0' returns False."""
        with patch.dict(os.environ, {"RESULT_WILL_BE_SUBMITTED": "0"}):
            assert check_result_will_be_submitted() is False

    def test_returns_false_for_false(self) -> None:
        """Test that 'false' returns False."""
        with patch.dict(os.environ, {"RESULT_WILL_BE_SUBMITTED": "false"}):
            assert check_result_will_be_submitted() is False

    def test_returns_false_when_unset(self) -> None:
        """Test that unset env var returns False."""
        with patch.dict(os.environ, {}, clear=True):
            # Make sure the env var is not set
            os.environ.pop("RESULT_WILL_BE_SUBMITTED", None)
            assert check_result_will_be_submitted() is False


class TestGetUserEnvironment:
    """Tests for get_user_environment function."""

    def test_parses_null_byte_format(self, test_config: Config) -> None:
        """Test parsing of null-byte separated environment."""
        content = "KEY1=value1\x00KEY2=value2\x00KEY3=value3\x00"
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text(content)

        with override_config(test_config):
            env = get_user_environment()
            assert env["KEY1"] == "value1"
            assert env["KEY2"] == "value2"
            assert env["KEY3"] == "value3"

    def test_handles_empty_lines(self, test_config: Config) -> None:
        """Test that empty lines are skipped."""
        content = "KEY1=value1\x00\x00KEY2=value2\x00"
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text(content)

        with override_config(test_config):
            env = get_user_environment()
            assert len(env) == 2
            assert "KEY1" in env
            assert "KEY2" in env

    def test_handles_equals_in_value(self, test_config: Config) -> None:
        """Test that '=' in values is preserved."""
        content = "KEY=value=with=equals\x00"
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text(content)

        with override_config(test_config):
            env = get_user_environment()
            assert env["KEY"] == "value=with=equals"

    def test_empty_file(self, test_config: Config) -> None:
        """Test handling of empty file."""
        test_config.user_environ_path.parent.mkdir(parents=True, exist_ok=True)
        test_config.user_environ_path.write_text("")

        with override_config(test_config):
            env = get_user_environment()
            assert env == {}


class TestDecodeOrStr:
    """Tests for decode_or_str function."""

    def test_string_passthrough(self) -> None:
        """Test that strings are passed through unchanged."""
        assert decode_or_str("hello") == "hello"

    def test_bytes_utf8_decode(self) -> None:
        """Test that valid UTF-8 bytes are decoded."""
        assert decode_or_str(b"hello") == "hello"

    def test_bytes_unicode(self) -> None:
        """Test decoding of unicode bytes."""
        assert decode_or_str("héllo".encode("utf-8")) == "héllo"

    def test_invalid_bytes_fallback(self) -> None:
        """Test fallback for invalid UTF-8 bytes."""
        invalid_bytes = b"\xff\xfe"
        result = decode_or_str(invalid_bytes)
        # Should return str() representation
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string(self) -> None:
        """Test handling of empty string."""
        assert decode_or_str("") == ""

    def test_empty_bytes(self) -> None:
        """Test handling of empty bytes."""
        assert decode_or_str(b"") == ""

    def test_bytearray(self) -> None:
        """Test handling of bytearray."""
        assert decode_or_str(bytearray(b"test")) == "test"


class TestMapPathAsPosix:
    """Tests for map_path_as_posix function."""

    def test_strings_unchanged(self) -> None:
        """Test that strings are passed through unchanged."""
        cmd = ["python", "script.py"]
        result = map_path_as_posix(cmd)
        assert result == ["python", "script.py"]

    def test_bytes_unchanged(self) -> None:
        """Test that bytes are passed through unchanged."""
        cmd = [b"python", b"script.py"]
        result = map_path_as_posix(cmd)
        assert result == [b"python", b"script.py"]

    def test_empty_list(self) -> None:
        """Test with empty list."""
        assert map_path_as_posix([]) == []

    def test_mixed_strings_and_bytes(self) -> None:
        """Test with mixed string and bytes types."""
        cmd = ["python", b"script.py"]
        result = map_path_as_posix(cmd)
        assert result == ["python", b"script.py"]
