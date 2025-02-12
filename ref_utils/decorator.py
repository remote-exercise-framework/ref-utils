from functools import wraps
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, List
import typing as ty

from ref_utils.error import RefUtilsError
from .utils import print_ok, print_err
from dataclasses import dataclass, asdict
import warnings
import json

TEST_RESULT_PATH = Path("/var/test_result")
DEFAULT_GROUP_NAME = 'default'
__registered_test_groups: ty.Dict[str, 'TestGroup'] = {}


@dataclass
class TestResult():
    """
    The result of an submission test.
    """
    name: str
    success: bool
    score: ty.Optional[float]

class TestGroup():
    """
    Tests can be grouped and a group is only successfull when all tests in it pass.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.env_tests: ty.List[Callable[..., Any]] = []
        self.submission_test: ty.Optional[Callable[..., Any]]= None
        self.extended_submission_test: ty.Optional[Callable[..., Any]] = None

def add_environment_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:
    warnings.warn("Please use @environment_test instead of @add_environment_test")
    return environment_test(group)

def environment_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _environment_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if group not in __registered_test_groups:
            __registered_test_groups[group] = TestGroup(group)
        __registered_test_groups[group].env_tests.append(wrapper)

        return wrapper
    return _environment_test

def add_submission_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:
    warnings.warn("Please use @submission_test instead of @add_submission_test")
    return submission_test(group)

def submission_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _submission_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if group not in __registered_test_groups:
            __registered_test_groups[group] = TestGroup(group)
        g = __registered_test_groups[group]
        if g.submission_test is not None:
            raise RefUtilsError("The @submission_test decorator can only be used once. Set the group kwarg to different values, if you have multiple tasks.")
        g.submission_test = wrapper

        return wrapper
    return _submission_test

def extended_submission_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _extended_submission_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if group not in __registered_test_groups:
            __registered_test_groups[group] = TestGroup(group)
        g = __registered_test_groups[group]
        if g.extended_submission_test is not None:
            raise RefUtilsError("The @extended_submission_test decorator can only be used once. Set the group kwarg to different values, if you have multiple tasks.")
        __registered_test_groups[group].extended_submission_test = wrapper

        return wrapper
    return _extended_submission_test


def run_tests() -> None:
    """
    Must be called by the test script to execute all tests.
    """
    print_ok('[+] Running tests..')
    all_tests_passed = True
    has_multiple_groups = len(__registered_test_groups) > 1
    group_test_results: ty.List[TestResult] = []

    # Run all sub-tasks one after another.
    for group_name, tests in __registered_test_groups.items():
        group_passed = True

        TEST_RESULT_PATH.unlink(missing_ok=True)

        if has_multiple_groups:
            print_ok(f'[+] *** Running tests for group \"{group_name}\" ***')

        if tests.env_tests and not tests.submission_test and not tests.extended_submission_test:
            raise RefUtilsError("Using @environment_test without @submission_test or @extended_submission_test is not allowed")

        print_ok('[+] Testing environment...')
        for test in tests.env_tests:
            ret = test()
            if not isinstance(ret, bool):
                raise RefUtilsError("Function with the @environment_test decorator must return a bool")
            group_passed &= ret
            all_tests_passed = False

        #Do not run submission tests if the environ is invalid
        if not group_passed:
            group_test_results.append(TestResult(group_name, False, None))
            if has_multiple_groups:
                # Only print this if we have multiple groups. If we only have one,
                # the would just duplicate the error printed at the end.
                print_err('[!] Group failed!')
            continue
        print_ok('[+] Environment tests passed')

        print_ok('[+] Testing submission...')
        if tests.submission_test:
            ret = tests.submission_test()
            if isinstance(ret, bool):
                ret = TestResult(group_name, ret, None)
            elif isinstance(ret, TestResult):
                pass
            else:
                raise RefUtilsError(f"Submission test returned unexpected type: {type(ret)}")

            group_test_results.append(ret)
            group_passed &= ret.success
            all_tests_passed = False
        else:
            # If there is no test, we consider this to be an success.
            group_test_results.append(TestResult(group_name, True, None))
            print_ok("[+] No test found")

        if not group_passed and has_multiple_groups:
            # Avoid printing errors twice.
            print_err('[!] Group failed!')
        elif group_passed:
            print_ok('[+] Test passed')

    if not all_tests_passed:
        print_err('[!] Some tests failed! Please review your submission to avoid penalties during grading.')
    else:
        print_ok('[+] All tests passed! Good job. Ready to submit!')

    results = json.dumps([asdict(e) for e in group_test_results])
    TEST_RESULT_PATH.write_text(results)