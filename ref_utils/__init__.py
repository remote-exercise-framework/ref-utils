"""Import functions to avoid .dot import for user""" # pylint: disable = invalid-name
__all__ = ['process', 'assertion', 'utils', "decorator"]
from .process import drop_privileges, run, get_payload_from_executable, ref_util_install_global_exception_hook, run_with_payload, run_capture_output
from .assertion import assert_is_dir, assert_is_exec, assert_is_file
from .utils import print_ok, print_warn, print_err, write_stdout, decode_or_str, test_result_will_be_submitted, get_user_environment
from .decorator import add_environment_test, add_submission_test, environment_test, submission_test, run_tests, TestResult

ref_util_install_global_exception_hook()
