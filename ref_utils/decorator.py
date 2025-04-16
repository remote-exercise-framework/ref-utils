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
DEFAULT_TASK_NAME = 'default'
__registered_tasks: ty.Dict[str, '_Task'] = {}

@dataclass
class TestResult():
    """
    The result returned from a submission test.
    """

    # Whether the test should be considered successful.
    success: bool
    # The score that was achieved for this particular test.
    # None, if not scored.
    score: ty.Optional[float]


@dataclass
class _TestResult():
    """
    Class used to serialize data before sending it to the webserver.
    """
    task_name: str
    success: bool
    score: ty.Optional[float]

class _Task():
    """
    A submission test can contain multiple tasks that are each checked individually and
    do not require other tasks to success.
    A Task consists of (see decorators below):
        - none or multiple environment tests
        - none or one submission_test
        - none or one extended_submission_test
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.env_tests: ty.List[Callable[..., Any]] = []
        self.submission_test: ty.Optional[Callable[..., Any]]= None
        self.extended_submission_test: ty.Optional[Callable[..., Any]] = None

def add_environment_test(task_name: str = DEFAULT_TASK_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:
    warnings.warn("Please use @environment_test instead of @add_environment_test")
    return environment_test(task_name)

def environment_test(task_name: str = DEFAULT_TASK_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _environment_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if task_name not in __registered_tasks:
            __registered_tasks[task_name] = _Task(task_name)
        __registered_tasks[task_name].env_tests.append(wrapper)

        return wrapper
    return _environment_test

def add_submission_test(task_name: str = DEFAULT_TASK_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:
    warnings.warn("Please use @submission_test instead of @add_submission_test")
    return submission_test(task_name)

def submission_test(task_name: str = DEFAULT_TASK_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _submission_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if task_name not in __registered_tasks:
            __registered_tasks[task_name] = _Task(task_name)
        g = __registered_tasks[task_name]
        if g.submission_test is not None:
            raise RefUtilsError("The @submission_test decorator can only be used once. Set the task_name kwarg to different values, if you have multiple tasks.")
        g.submission_test = wrapper

        return wrapper
    return _submission_test

def extended_submission_test(task_name: str = DEFAULT_TASK_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _extended_submission_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if task_name not in __registered_tasks:
            __registered_tasks[task_name] = _Task(task_name)
        g = __registered_tasks[task_name]
        if g.extended_submission_test is not None:
            raise RefUtilsError("The @extended_submission_test decorator can only be used once. Set the task_name kwarg to different values, if you have multiple tasks.")
        __registered_tasks[task_name].extended_submission_test = wrapper

        return wrapper
    return _extended_submission_test



def run_tests() -> None:
    """
    Must be called by the test script to execute all tests.
    """
    print_ok('[+] Running tests..')
    all_tests_passed = True
    has_multiple_tasks = len(__registered_tasks) > 1
    task_test_results: ty.List[_TestResult] = []

    # Run all sub-tasks one after another.
    for task_name, tests in __registered_tasks.items():
        task_passed = True

        TEST_RESULT_PATH.unlink(missing_ok=True)

        if has_multiple_tasks:
            print_ok(f'[+] *** Running tests for task \"{task_name}\" ***')

        if tests.env_tests and not tests.submission_test and not tests.extended_submission_test:
            raise RefUtilsError("Using @environment_test without @submission_test or @extended_submission_test is not allowed")

        print_ok('[+] Testing environment...')
        for test in tests.env_tests:
            ret = test()
            if not isinstance(ret, bool):
                raise RefUtilsError("Function with the @environment_test decorator must return a bool")
            task_passed &= ret
            all_tests_passed &= ret

        #Do not run submission tests if the environ is invalid
        if not task_passed:
            task_test_results.append(_TestResult(task_name, False, None))
            if has_multiple_tasks:
                # Only print this if we have multiple tasks. If we only have one,
                # the would just duplicate the error printed at the end.
                print_err('[!] Task failed!')
            continue
        print_ok('[+] Environment tests passed')

        print_ok('[+] Testing submission...')
        if tests.submission_test:
            try:
                ret = tests.submission_test()
            except RefUtilsError as e:
                print_err(str(e))
                ret = False
            except KeyboardInterrupt:
                print_err('[-] Keyboard Interrupt')
                ret = False

            if isinstance(ret, bool):
                ret = _TestResult(task_name, ret, None)
            elif isinstance(ret, TestResult):
                ret = _TestResult(task_name, ret.success, ret.score)
            else:
                raise RefUtilsError(f"Submission test returned unexpected type: {type(ret)}")

            task_test_results.append(ret)
            task_passed &= ret.success
            all_tests_passed &= ret.success
        else:
            # If there is no test, we consider this to be an success.
            task_test_results.append(_TestResult(task_name, True, None))
            print_ok("[+] No test found")

        if not task_passed and has_multiple_tasks:
            # Avoid printing errors twice.
            # If this is the only task, i.e., !has_multiple_tasks,
            # we will print the error message further below.
            print_err('[!] Task failed!')
        elif task_passed:
            print_ok('[+] Test passed')

    if not all_tests_passed:
        print_err('[!] Some tests failed! Please review your submission to avoid penalties during grading.')
    else:
        print_ok('[+] All tests passed! Good job. Ready to submit!')

    results = json.dumps([asdict(e) for e in task_test_results])
    TEST_RESULT_PATH.write_text(results)