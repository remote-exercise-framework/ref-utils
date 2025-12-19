"""Import functions to avoid .dot import for user"""  # pylint: disable = invalid-name

__all__ = [
    # Modules
    "process",
    "assertion",
    "utils",
    "decorator",
    "config",
    "serialization",
    # Config
    "Config",
    "get_config",
    "set_config",
    "override_config",
    # Assertion
    "assert_is_dir",
    "assert_is_exec",
    "assert_is_file",
    # Decorator
    "TestResult",
    "TaskTestResult",
    "environment_test",
    "submission_test",
    "add_environment_test",
    "add_submission_test",
    "run_tests",
    # Process
    "drop_privileges",
    "run",
    "run_capture_output",
    "run_with_payload",
    "get_payload_from_executable",
    "ref_util_install_global_exception_hook",
    # Serialization
    "IPCSerializer",
    "TypeCodec",
    "safe_dumps",
    "safe_loads",
    "get_serializer",
    # Utils
    "print_ok",
    "print_warn",
    "print_err",
    "write_stdout",
    "decode_or_str",
    "test_result_will_be_submitted",
    "get_user_environment",
]
from .assertion import assert_is_dir, assert_is_exec, assert_is_file
from .config import Config, get_config, override_config, set_config
from .decorator import (
    TaskTestResult,
    TestResult,
    add_environment_test,
    add_submission_test,
    environment_test,
    run_tests,
    submission_test,
)
from .process import (
    drop_privileges,
    get_payload_from_executable,
    ref_util_install_global_exception_hook,
    run,
    run_capture_output,
    run_with_payload,
)
from .serialization import (
    IPCSerializer,
    TypeCodec,
    get_serializer,
    safe_dumps,
    safe_loads,
)
from .utils import (
    decode_or_str,
    get_user_environment,
    print_err,
    print_ok,
    print_warn,
    test_result_will_be_submitted,
    write_stdout,
)

ref_util_install_global_exception_hook()
