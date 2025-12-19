"""JSON-based IPC serialization with type registry.

This module provides a secure alternative to pickle for IPC between
privileged and unprivileged processes. It uses explicit type registration
to control exactly which types can be serialized/deserialized.

Security: Unlike pickle, this implementation cannot execute arbitrary code
during deserialization. Only explicitly registered types are reconstructed.
"""
import base64
import builtins
import json
from dataclasses import dataclass
from subprocess import CompletedProcess
from typing import Any, Callable, Dict, Literal, Optional, Type, TypeVar

T = TypeVar("T")

UnknownTypePolicy = Literal["error", "preserve", "drop"]


@dataclass
class TypeCodec:
    """Encoder/decoder for a specific type."""

    type_tag: str
    target_type: Type[Any]
    to_dict: Callable[[Any], Dict[str, Any]]
    from_dict: Callable[[Dict[str, Any]], Any]


class IPCSerializer:
    """JSON-based serializer with type registry."""

    def __init__(self, unknown_policy: UnknownTypePolicy = "error") -> None:
        self._codecs: Dict[str, TypeCodec] = {}
        self._type_to_tag: Dict[Type[Any], str] = {}
        self.unknown_policy = unknown_policy
        self._register_builtins()

    def register(self, codec: TypeCodec) -> None:
        """Register a type codec."""
        self._codecs[codec.type_tag] = codec
        self._type_to_tag[codec.target_type] = codec.type_tag

    def serialize(self, obj: Any) -> bytes:
        """Serialize object to JSON bytes."""
        data = self._encode(obj)
        return json.dumps(data, ensure_ascii=False).encode("utf-8")

    def deserialize(self, data: bytes) -> Any:
        """Deserialize JSON bytes to object."""
        parsed = json.loads(data.decode("utf-8"))
        return self._decode(parsed)

    def _encode(self, obj: Any) -> Any:
        """Recursively encode an object."""
        if obj is None or isinstance(obj, (bool, int, float, str)):
            return obj
        if isinstance(obj, bytes):
            return {"_type": "bytes", "_data": base64.b64encode(obj).decode("ascii")}
        if isinstance(obj, (list, tuple)):
            return [self._encode(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._encode(v) for k, v in obj.items()}

        # Check registered types (exact match first)
        obj_type = type(obj)
        if obj_type in self._type_to_tag:
            tag = self._type_to_tag[obj_type]
            codec = self._codecs[tag]
            return {"_type": tag, "_data": self._encode_dict(codec.to_dict(obj))}

        # Check for subclass matches (for exception hierarchy)
        for tag, codec in self._codecs.items():
            if isinstance(obj, codec.target_type):
                return {"_type": tag, "_data": self._encode_dict(codec.to_dict(obj))}

        # Serialization failed - include string representation of data in error
        try:
            data_str = repr(obj)
            if len(data_str) > 500:
                data_str = data_str[:500] + "..."
        except Exception:
            data_str = "<repr failed>"

        raise TypeError(f"Cannot serialize type: {obj_type.__name__}. Data: {data_str}")

    def _encode_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Encode values in a dict (for codec output)."""
        return {k: self._encode(v) for k, v in d.items()}

    def _decode(self, data: Any) -> Any:
        """Recursively decode data."""
        if data is None or isinstance(data, (bool, int, float, str)):
            return data
        if isinstance(data, list):
            return [self._decode(item) for item in data]
        if isinstance(data, dict):
            if "_type" in data:
                return self._decode_typed(data)
            return {k: self._decode(v) for k, v in data.items()}
        return data

    def _decode_typed(self, data: Dict[str, Any]) -> Any:
        """Decode a typed object."""
        type_tag = data["_type"]

        if type_tag == "bytes":
            return base64.b64decode(data["_data"])

        if type_tag in self._codecs:
            codec = self._codecs[type_tag]
            decoded_data = {k: self._decode(v) for k, v in data["_data"].items()}
            return codec.from_dict(decoded_data)

        # Unknown type handling
        if self.unknown_policy == "error":
            raise ValueError(f"Unknown type tag: {type_tag}")
        elif self.unknown_policy == "preserve":
            return {
                "_type": "unknown",
                "_original_type": type_tag,
                "_raw": data.get("_data"),
            }
        else:  # "drop"
            return None

    def _register_builtins(self) -> None:
        """Register built-in type codecs."""
        # CompletedProcess
        self.register(
            TypeCodec(
                type_tag="CompletedProcess",
                target_type=CompletedProcess,
                to_dict=lambda cp: {
                    "args": cp.args,
                    "returncode": cp.returncode,
                    "stdout": cp.stdout,
                    "stderr": cp.stderr,
                },
                from_dict=lambda d: CompletedProcess(
                    args=d["args"],
                    returncode=d["returncode"],
                    stdout=d.get("stdout"),
                    stderr=d.get("stderr"),
                ),
            )
        )


# Default instance for the IPC
_default_serializer: Optional[IPCSerializer] = None


def get_serializer() -> IPCSerializer:
    """Get or create the default serializer."""
    global _default_serializer
    if _default_serializer is None:
        _default_serializer = IPCSerializer(unknown_policy="error")
        _register_error_types(_default_serializer)
    return _default_serializer


def reset_serializer() -> None:
    """Reset the default serializer (useful for testing)."""
    global _default_serializer
    _default_serializer = None


def _register_error_types(serializer: IPCSerializer) -> None:
    """Register RefUtilsError types."""
    from .error import (
        RefUtilsAssertionError,
        RefUtilsError,
        RefUtilsProcessError,
        RefUtilsProcessTimeoutError,
    )

    # Order matters - register specific types before base types
    serializer.register(
        TypeCodec(
            type_tag="RefUtilsProcessTimeoutError",
            target_type=RefUtilsProcessTimeoutError,
            to_dict=lambda e: {"cmd": e.cmd, "timeout": e.timeout},
            from_dict=lambda d: RefUtilsProcessTimeoutError(d["cmd"], d["timeout"]),
        )
    )

    serializer.register(
        TypeCodec(
            type_tag="RefUtilsProcessError",
            target_type=RefUtilsProcessError,
            to_dict=lambda e: {
                "cmd": (
                    str(e.msg.split("Execution of ")[1].split(" failed")[0])
                    if "Execution of" in e.msg
                    else ""
                ),
                "exit_code": e.exit_code,
                "stdout": e.stdout,
                "stderr": e.stderr,
            },
            from_dict=lambda d: RefUtilsProcessError(
                d.get("cmd", ""),
                d["exit_code"],
                d.get("stdout", b""),
                d.get("stderr", b""),
            ),
        )
    )

    serializer.register(
        TypeCodec(
            type_tag="RefUtilsAssertionError",
            target_type=RefUtilsAssertionError,
            to_dict=lambda e: {"message": str(e)},
            from_dict=lambda d: RefUtilsAssertionError(d.get("message", "")),
        )
    )

    # Base error type last (catches any RefUtilsError subclass not matched above)
    serializer.register(
        TypeCodec(
            type_tag="RefUtilsError",
            target_type=RefUtilsError,
            to_dict=lambda e: {"message": str(e)},
            from_dict=lambda d: RefUtilsError(d.get("message", "")),
        )
    )

    # Generic exception handler for standard exceptions
    _register_standard_exceptions(serializer)


def _register_standard_exceptions(serializer: IPCSerializer) -> None:
    """Register handlers for common standard exceptions."""
    # Map of exception types we want to support
    # These are commonly raised during subprocess execution
    STANDARD_EXCEPTIONS: Dict[str, Type[Exception]] = {
        "ValueError": ValueError,
        "TypeError": TypeError,
        "OSError": OSError,
        "IOError": IOError,
        "FileNotFoundError": FileNotFoundError,
        "PermissionError": PermissionError,
        "TimeoutError": TimeoutError,
        "RuntimeError": RuntimeError,
        "AttributeError": AttributeError,
        "KeyError": KeyError,
        "IndexError": IndexError,
    }

    for name, exc_type in STANDARD_EXCEPTIONS.items():
        # Use default argument to capture exc_type in closure
        serializer.register(
            TypeCodec(
                type_tag=f"builtin.{name}",
                target_type=exc_type,
                to_dict=lambda e: {"args": list(e.args)},
                from_dict=lambda d, t=exc_type: t(*d.get("args", [])),
            )
        )

    # Generic Exception fallback - handles any Exception subclass
    # This must be registered LAST as it matches any Exception
    serializer.register(
        TypeCodec(
            type_tag="Exception",
            target_type=Exception,
            to_dict=_generic_exception_to_dict,
            from_dict=_generic_exception_from_dict,
        )
    )


def _generic_exception_to_dict(e: Exception) -> Dict[str, Any]:
    """Serialize any exception to a dict."""
    return {
        "type_name": type(e).__name__,
        "type_module": type(e).__module__,
        "args": list(e.args),
        "str": str(e),  # Fallback for reconstruction
    }


def _generic_exception_from_dict(d: Dict[str, Any]) -> Exception:
    """Deserialize an exception from a dict.

    SECURITY: Only reconstructs exceptions from builtins.
    Unknown types are wrapped in RuntimeError - no dynamic imports.
    """
    type_name = d.get("type_name", "Exception")
    type_module = d.get("type_module", "builtins")
    args = d.get("args", [])
    str_repr = d.get("str", "")

    # SECURITY: Only allow builtins exceptions to be reconstructed
    # No dynamic imports from arbitrary modules
    if type_module == "builtins":
        exc_class = getattr(builtins, type_name, None)
        if exc_class is not None and issubclass(exc_class, Exception):
            try:
                return exc_class(*args)
            except TypeError:
                # Constructor doesn't accept these args, use str repr
                return exc_class(str_repr)

    # Non-builtin or unknown: wrap in RuntimeError (no dynamic imports)
    return RuntimeError(f"[{type_module}.{type_name}] {str_repr}")


# Convenience functions matching current API
def safe_dumps(obj: Any) -> bytes:
    """Serialize object to JSON bytes (replaces pickle.dumps)."""
    return get_serializer().serialize(obj)


def safe_loads(data: bytes) -> Any:
    """Deserialize JSON bytes to object (replaces restricted_loads)."""
    return get_serializer().deserialize(data)
