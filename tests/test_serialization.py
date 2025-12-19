"""Tests for ref_utils.serialization module."""
import json
from subprocess import CompletedProcess

import pytest

from ref_utils.error import (
    RefUtilsAssertionError,
    RefUtilsError,
    RefUtilsProcessError,
    RefUtilsProcessTimeoutError,
)
from ref_utils.serialization import (
    IPCSerializer,
    TypeCodec,
    reset_serializer,
    safe_dumps,
    safe_loads,
)


@pytest.fixture(autouse=True)
def reset_default_serializer() -> None:
    """Reset the default serializer between tests."""
    reset_serializer()
    yield
    reset_serializer()


class TestBasicTypes:
    """Tests for serialization of basic Python types."""

    def test_none(self) -> None:
        """Test None serialization."""
        assert safe_loads(safe_dumps(None)) is None

    def test_bool_true(self) -> None:
        """Test True serialization."""
        assert safe_loads(safe_dumps(True)) is True

    def test_bool_false(self) -> None:
        """Test False serialization."""
        assert safe_loads(safe_dumps(False)) is False

    def test_int(self) -> None:
        """Test integer serialization."""
        assert safe_loads(safe_dumps(42)) == 42
        assert safe_loads(safe_dumps(-100)) == -100
        assert safe_loads(safe_dumps(0)) == 0

    def test_float(self) -> None:
        """Test float serialization."""
        assert safe_loads(safe_dumps(3.14)) == 3.14
        assert safe_loads(safe_dumps(-0.5)) == -0.5

    def test_string(self) -> None:
        """Test string serialization."""
        assert safe_loads(safe_dumps("hello")) == "hello"
        assert safe_loads(safe_dumps("")) == ""
        assert safe_loads(safe_dumps("unicode: \u00e9\u00e8")) == "unicode: \u00e9\u00e8"

    def test_bytes(self) -> None:
        """Test bytes serialization via base64."""
        data = b"hello world"
        result = safe_loads(safe_dumps(data))
        assert result == data
        assert isinstance(result, bytes)

    def test_bytes_binary(self) -> None:
        """Test binary data with non-UTF8 bytes."""
        data = b"\x00\x01\xff\xfe\x80"
        result = safe_loads(safe_dumps(data))
        assert result == data

    def test_list(self) -> None:
        """Test list serialization."""
        data = [1, 2, 3, "four", None]
        assert safe_loads(safe_dumps(data)) == data

    def test_nested_list(self) -> None:
        """Test nested list serialization."""
        data = [[1, 2], [3, [4, 5]]]
        assert safe_loads(safe_dumps(data)) == data

    def test_tuple_becomes_list(self) -> None:
        """Test that tuples become lists after round-trip."""
        data = (1, 2, 3)
        result = safe_loads(safe_dumps(data))
        assert result == [1, 2, 3]

    def test_dict(self) -> None:
        """Test dict serialization."""
        data = {"a": 1, "b": "two", "c": None}
        assert safe_loads(safe_dumps(data)) == data

    def test_nested_dict(self) -> None:
        """Test nested dict serialization."""
        data = {"outer": {"inner": {"deep": 42}}}
        assert safe_loads(safe_dumps(data)) == data

    def test_dict_with_bytes(self) -> None:
        """Test dict containing bytes values."""
        data = {"stdout": b"hello", "stderr": b"error"}
        result = safe_loads(safe_dumps(data))
        assert result["stdout"] == b"hello"
        assert result["stderr"] == b"error"


class TestCompletedProcess:
    """Tests for CompletedProcess serialization."""

    def test_basic(self) -> None:
        """Test basic CompletedProcess serialization."""
        cp = CompletedProcess(args=["echo", "hello"], returncode=0)
        result = safe_loads(safe_dumps(cp))
        assert isinstance(result, CompletedProcess)
        assert result.args == ["echo", "hello"]
        assert result.returncode == 0

    def test_with_output(self) -> None:
        """Test CompletedProcess with stdout/stderr."""
        cp = CompletedProcess(
            args=["test"],
            returncode=1,
            stdout=b"output data",
            stderr=b"error data",
        )
        result = safe_loads(safe_dumps(cp))
        assert result.stdout == b"output data"
        assert result.stderr == b"error data"
        assert result.returncode == 1

    def test_with_string_args(self) -> None:
        """Test CompletedProcess with string args."""
        cp = CompletedProcess(args="echo hello", returncode=0)
        result = safe_loads(safe_dumps(cp))
        assert result.args == "echo hello"

    def test_with_none_output(self) -> None:
        """Test CompletedProcess with None stdout/stderr."""
        cp = CompletedProcess(args=["test"], returncode=0, stdout=None, stderr=None)
        result = safe_loads(safe_dumps(cp))
        assert result.stdout is None
        assert result.stderr is None


class TestRefUtilsErrors:
    """Tests for RefUtilsError serialization."""

    def test_ref_utils_error(self) -> None:
        """Test RefUtilsError serialization."""
        error = RefUtilsError("test error message")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, RefUtilsError)
        assert str(result) == "test error message"

    def test_ref_utils_process_timeout_error(self) -> None:
        """Test RefUtilsProcessTimeoutError serialization."""
        error = RefUtilsProcessTimeoutError("./test_cmd", 30)
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, RefUtilsProcessTimeoutError)
        assert result.cmd == "./test_cmd"
        assert result.timeout == 30

    def test_ref_utils_process_error(self) -> None:
        """Test RefUtilsProcessError serialization."""
        error = RefUtilsProcessError("./failing_cmd", 1, b"stdout data", b"stderr data")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, RefUtilsProcessError)
        assert result.exit_code == 1
        assert result.stdout == b"stdout data"
        assert result.stderr == b"stderr data"

    def test_ref_utils_assertion_error(self) -> None:
        """Test RefUtilsAssertionError serialization."""
        error = RefUtilsAssertionError("assertion failed")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, RefUtilsAssertionError)
        assert str(result) == "assertion failed"


class TestStandardExceptions:
    """Tests for standard Python exception serialization."""

    def test_value_error(self) -> None:
        """Test ValueError serialization."""
        error = ValueError("invalid value")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, ValueError)
        assert str(result) == "invalid value"

    def test_type_error(self) -> None:
        """Test TypeError serialization."""
        error = TypeError("wrong type")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, TypeError)
        assert str(result) == "wrong type"

    def test_os_error(self) -> None:
        """Test OSError serialization."""
        error = OSError("file not found")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, OSError)
        assert "file not found" in str(result)

    def test_file_not_found_error(self) -> None:
        """Test FileNotFoundError serialization."""
        error = FileNotFoundError("missing.txt")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, FileNotFoundError)
        assert "missing.txt" in str(result)

    def test_permission_error(self) -> None:
        """Test PermissionError serialization."""
        error = PermissionError("access denied")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, PermissionError)
        assert "access denied" in str(result)

    def test_runtime_error(self) -> None:
        """Test RuntimeError serialization."""
        error = RuntimeError("runtime failure")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, RuntimeError)
        assert str(result) == "runtime failure"

    def test_key_error(self) -> None:
        """Test KeyError serialization."""
        error = KeyError("missing_key")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, KeyError)

    def test_index_error(self) -> None:
        """Test IndexError serialization."""
        error = IndexError("list index out of range")
        result = safe_loads(safe_dumps(error))
        assert isinstance(result, IndexError)
        assert "list index out of range" in str(result)


class TestGenericException:
    """Tests for generic exception handling."""

    def test_unregistered_builtin_exception(self) -> None:
        """Test exception type not explicitly registered but in builtins."""
        error = ZeroDivisionError("division by zero")
        result = safe_loads(safe_dumps(error))
        # Should be reconstructed via generic handler
        assert isinstance(result, ZeroDivisionError)
        assert "division by zero" in str(result)

    def test_custom_exception_becomes_runtime_error(self) -> None:
        """Test that custom exception from non-builtin module becomes RuntimeError."""

        class CustomError(Exception):
            pass

        error = CustomError("custom error message")
        result = safe_loads(safe_dumps(error))
        # Should be wrapped in RuntimeError (no dynamic imports)
        assert isinstance(result, RuntimeError)
        assert "CustomError" in str(result)
        assert "custom error message" in str(result)


class TestUnknownTypeHandling:
    """Tests for unknown type handling policies."""

    def test_error_policy_raises(self) -> None:
        """Test that error policy raises on unknown type tag."""
        serializer = IPCSerializer(unknown_policy="error")
        # Manually create data with unknown type
        data = json.dumps({"_type": "UnknownType", "_data": {"foo": "bar"}}).encode()
        with pytest.raises(ValueError) as exc_info:
            serializer.deserialize(data)
        assert "Unknown type tag" in str(exc_info.value)

    def test_preserve_policy_returns_dict(self) -> None:
        """Test that preserve policy returns dict with metadata."""
        serializer = IPCSerializer(unknown_policy="preserve")
        data = json.dumps({"_type": "UnknownType", "_data": {"foo": "bar"}}).encode()
        result = serializer.deserialize(data)
        assert result["_type"] == "unknown"
        assert result["_original_type"] == "UnknownType"
        assert result["_raw"] == {"foo": "bar"}

    def test_drop_policy_returns_none(self) -> None:
        """Test that drop policy returns None."""
        serializer = IPCSerializer(unknown_policy="drop")
        data = json.dumps({"_type": "UnknownType", "_data": {"foo": "bar"}}).encode()
        result = serializer.deserialize(data)
        assert result is None


class TestSerializationErrors:
    """Tests for serialization error handling."""

    def test_unserializable_type_raises(self) -> None:
        """Test that unserializable types raise TypeError with data."""

        class Unserializable:
            pass

        obj = Unserializable()
        with pytest.raises(TypeError) as exc_info:
            safe_dumps(obj)
        assert "Unserializable" in str(exc_info.value)
        assert "Data:" in str(exc_info.value)

    def test_error_includes_repr(self) -> None:
        """Test that serialization error includes object repr."""

        class CustomClass:
            def __repr__(self) -> str:
                return "<CustomClass instance>"

        obj = CustomClass()
        with pytest.raises(TypeError) as exc_info:
            safe_dumps(obj)
        assert "<CustomClass instance>" in str(exc_info.value)

    def test_error_handles_repr_failure(self) -> None:
        """Test that serialization handles repr failure gracefully."""

        class BadRepr:
            def __repr__(self) -> str:
                raise RuntimeError("repr failed")

        obj = BadRepr()
        with pytest.raises(TypeError) as exc_info:
            safe_dumps(obj)
        assert "<repr failed>" in str(exc_info.value)


class TestCustomTypeRegistration:
    """Tests for custom type registration."""

    def test_register_custom_type(self) -> None:
        """Test registering and using a custom type."""
        from dataclasses import dataclass

        @dataclass
        class Point:
            x: int
            y: int

        serializer = IPCSerializer()
        serializer.register(
            TypeCodec(
                type_tag="Point",
                target_type=Point,
                to_dict=lambda p: {"x": p.x, "y": p.y},
                from_dict=lambda d: Point(d["x"], d["y"]),
            )
        )

        point = Point(10, 20)
        data = serializer.serialize(point)
        result = serializer.deserialize(data)
        assert isinstance(result, Point)
        assert result.x == 10
        assert result.y == 20

    def test_subclass_uses_base_codec(self) -> None:
        """Test that subclasses can use base class codec."""

        class CustomRefError(RefUtilsError):
            pass

        error = CustomRefError("custom error")
        result = safe_loads(safe_dumps(error))
        # Should be deserialized as RefUtilsError (base class)
        assert isinstance(result, RefUtilsError)
        assert "custom error" in str(result)


class TestWireFormat:
    """Tests for the JSON wire format."""

    def test_bytes_format(self) -> None:
        """Test bytes are encoded as base64."""
        data = safe_dumps(b"hello")
        parsed = json.loads(data)
        assert parsed["_type"] == "bytes"
        assert parsed["_data"] == "aGVsbG8="  # base64 of "hello"

    def test_completed_process_format(self) -> None:
        """Test CompletedProcess wire format."""
        cp = CompletedProcess(args=["test"], returncode=0, stdout=b"out", stderr=b"err")
        data = safe_dumps(cp)
        parsed = json.loads(data)
        assert parsed["_type"] == "CompletedProcess"
        assert parsed["_data"]["returncode"] == 0
        assert parsed["_data"]["args"] == ["test"]

    def test_exception_format(self) -> None:
        """Test exception wire format."""
        error = RefUtilsError("test message")
        data = safe_dumps(error)
        parsed = json.loads(data)
        assert parsed["_type"] == "RefUtilsError"
        assert parsed["_data"]["message"] == "test message"


class TestExceptionRaisingAndSerialization:
    """Tests that verify exceptions can be raised, serialized, and re-raised correctly."""

    def test_value_error_roundtrip_and_raise(self) -> None:
        """Test ValueError can be serialized, deserialized, and re-raised."""
        original = ValueError("invalid input value")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, ValueError)
        with pytest.raises(ValueError) as exc_info:
            raise restored
        assert "invalid input value" in str(exc_info.value)

    def test_type_error_roundtrip_and_raise(self) -> None:
        """Test TypeError can be serialized, deserialized, and re-raised."""
        original = TypeError("expected str, got int")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, TypeError)
        with pytest.raises(TypeError) as exc_info:
            raise restored
        assert "expected str, got int" in str(exc_info.value)

    def test_key_error_roundtrip_and_raise(self) -> None:
        """Test KeyError can be serialized, deserialized, and re-raised."""
        original = KeyError("missing_key")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, KeyError)
        with pytest.raises(KeyError):
            raise restored

    def test_index_error_roundtrip_and_raise(self) -> None:
        """Test IndexError can be serialized, deserialized, and re-raised."""
        original = IndexError("list index out of range")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, IndexError)
        with pytest.raises(IndexError) as exc_info:
            raise restored
        assert "list index out of range" in str(exc_info.value)

    def test_file_not_found_error_roundtrip_and_raise(self) -> None:
        """Test FileNotFoundError can be serialized, deserialized, and re-raised."""
        original = FileNotFoundError("No such file: /tmp/missing.txt")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, FileNotFoundError)
        with pytest.raises(FileNotFoundError) as exc_info:
            raise restored
        assert "missing.txt" in str(exc_info.value)

    def test_permission_error_roundtrip_and_raise(self) -> None:
        """Test PermissionError can be serialized, deserialized, and re-raised."""
        original = PermissionError("Permission denied: /etc/shadow")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, PermissionError)
        with pytest.raises(PermissionError) as exc_info:
            raise restored
        assert "Permission denied" in str(exc_info.value)

    def test_runtime_error_roundtrip_and_raise(self) -> None:
        """Test RuntimeError can be serialized, deserialized, and re-raised."""
        original = RuntimeError("unexpected runtime condition")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, RuntimeError)
        with pytest.raises(RuntimeError) as exc_info:
            raise restored
        assert "unexpected runtime condition" in str(exc_info.value)

    def test_attribute_error_roundtrip_and_raise(self) -> None:
        """Test AttributeError can be serialized, deserialized, and re-raised."""
        original = AttributeError("'NoneType' object has no attribute 'foo'")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, AttributeError)
        with pytest.raises(AttributeError) as exc_info:
            raise restored
        assert "NoneType" in str(exc_info.value)

    def test_os_error_roundtrip_and_raise(self) -> None:
        """Test OSError can be serialized, deserialized, and re-raised."""
        original = OSError("OS-level error occurred")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, OSError)
        with pytest.raises(OSError) as exc_info:
            raise restored
        assert "OS-level error" in str(exc_info.value)

    def test_timeout_error_roundtrip_and_raise(self) -> None:
        """Test TimeoutError can be serialized, deserialized, and re-raised."""
        original = TimeoutError("operation timed out after 30s")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, TimeoutError)
        with pytest.raises(TimeoutError) as exc_info:
            raise restored
        assert "timed out" in str(exc_info.value)

    def test_ref_utils_error_roundtrip_and_raise(self) -> None:
        """Test RefUtilsError can be serialized, deserialized, and re-raised."""
        original = RefUtilsError("ref-utils specific error")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, RefUtilsError)
        with pytest.raises(RefUtilsError) as exc_info:
            raise restored
        assert "ref-utils specific error" in str(exc_info.value)

    def test_ref_utils_process_error_roundtrip_and_raise(self) -> None:
        """Test RefUtilsProcessError preserves all attributes after roundtrip."""
        original = RefUtilsProcessError(
            cmd="./failing_script.sh",
            exit_code=127,
            stdout=b"some stdout output",
            stderr=b"command not found",
        )
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, RefUtilsProcessError)
        assert restored.exit_code == 127
        assert restored.stdout == b"some stdout output"
        assert restored.stderr == b"command not found"

        with pytest.raises(RefUtilsProcessError):
            raise restored

    def test_ref_utils_timeout_error_roundtrip_and_raise(self) -> None:
        """Test RefUtilsProcessTimeoutError preserves cmd and timeout."""
        original = RefUtilsProcessTimeoutError(cmd="./slow_script.sh", timeout=60)
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, RefUtilsProcessTimeoutError)
        assert restored.cmd == "./slow_script.sh"
        assert restored.timeout == 60

        with pytest.raises(RefUtilsProcessTimeoutError):
            raise restored

    def test_zero_division_error_via_generic_handler(self) -> None:
        """Test ZeroDivisionError (not explicitly registered) via generic handler."""
        original = ZeroDivisionError("division by zero")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        # Should be reconstructed via generic exception handler
        assert isinstance(restored, ZeroDivisionError)
        with pytest.raises(ZeroDivisionError) as exc_info:
            raise restored
        assert "division by zero" in str(exc_info.value)

    def test_assertion_error_via_generic_handler(self) -> None:
        """Test AssertionError via generic handler."""
        original = AssertionError("assertion failed: x > 0")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, AssertionError)
        with pytest.raises(AssertionError) as exc_info:
            raise restored
        assert "assertion failed" in str(exc_info.value)

    def test_exception_with_multiple_args(self) -> None:
        """Test exception with multiple constructor arguments."""
        original = ValueError("arg1", "arg2", "arg3")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, ValueError)
        assert restored.args == ("arg1", "arg2", "arg3")

    def test_exception_with_empty_message(self) -> None:
        """Test exception with empty message."""
        original = RuntimeError()
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert isinstance(restored, RuntimeError)
        assert restored.args == ()

    def test_nested_exception_in_data_structure(self) -> None:
        """Test exception nested in a data structure."""
        original = {
            "success": False,
            "error": ValueError("nested error"),
            "data": None,
        }
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert restored["success"] is False
        assert isinstance(restored["error"], ValueError)
        assert "nested error" in str(restored["error"])

    def test_list_of_exceptions(self) -> None:
        """Test serializing a list of different exceptions."""
        original = [
            ValueError("value error"),
            TypeError("type error"),
            RuntimeError("runtime error"),
        ]
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        assert len(restored) == 3
        assert isinstance(restored[0], ValueError)
        assert isinstance(restored[1], TypeError)
        assert isinstance(restored[2], RuntimeError)

    def test_custom_exception_becomes_runtime_error_but_raisable(self) -> None:
        """Test that custom exceptions become RuntimeError but are still raisable."""

        class CustomAppError(Exception):
            pass

        original = CustomAppError("custom application error")
        serialized = safe_dumps(original)
        restored = safe_loads(serialized)

        # Custom exception becomes RuntimeError (no dynamic imports)
        assert isinstance(restored, RuntimeError)
        assert "CustomAppError" in str(restored)
        assert "custom application error" in str(restored)

        # Should still be raisable
        with pytest.raises(RuntimeError) as exc_info:
            raise restored
        assert "CustomAppError" in str(exc_info.value)


class TestSecurityProperties:
    """Tests verifying security properties of the serializer."""

    def test_no_code_execution_on_deserialize(self) -> None:
        """Test that malicious payloads cannot execute code."""
        # Attempt to inject a type that would execute code in pickle
        malicious_data = json.dumps(
            {
                "_type": "os.system",
                "_data": {"cmd": "echo pwned"},
            }
        ).encode()
        with pytest.raises(ValueError) as exc_info:
            safe_loads(malicious_data)
        assert "Unknown type tag" in str(exc_info.value)

    def test_no_dynamic_import(self) -> None:
        """Test that generic exception handler doesn't import arbitrary modules."""
        # Create serialized exception claiming to be from a dangerous module
        data = json.dumps(
            {
                "_type": "Exception",
                "_data": {
                    "type_name": "DangerousException",
                    "type_module": "os",  # Attacker tries to trigger os import
                    "args": ["malicious"],
                    "str": "test",
                },
            }
        ).encode()
        result = safe_loads(data)
        # Should be wrapped in RuntimeError, not actually import os
        assert isinstance(result, RuntimeError)
        assert "[os.DangerousException]" in str(result)

    def test_deeply_nested_data(self) -> None:
        """Test handling of deeply nested data (potential DoS)."""
        # Create deeply nested dict
        data: dict = {}
        current = data
        for i in range(100):
            current["nested"] = {}
            current = current["nested"]
        current["value"] = "deep"

        result = safe_loads(safe_dumps(data))
        # Should succeed without stack overflow
        assert result is not None
