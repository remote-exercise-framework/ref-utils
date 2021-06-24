from functools import wraps
from collections import defaultdict
from typing import Any, Callable, List
from .utils import print_ok, print_err

DEFAULT_GROUP_NAME = 'default'
__registered_test_groups = {}


class TestGroup():

    def __init__(self, name: str) -> None:
        self.name = name
        self.env_tests: List[Callable[..., Any]] = []
        self.submission_tests: List[Callable[..., Any]] = []

def add_environment_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _add_environment_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if group not in __registered_test_groups:
            __registered_test_groups[group] = TestGroup(group)
        __registered_test_groups[group].env_tests.append(wrapper)

        return wrapper
    return _add_environment_test

def add_submission_test(group: str = DEFAULT_GROUP_NAME) -> Callable[[Callable[[Callable[..., Any]], Any]], Any]:

    def _add_submission_test(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: str, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        if group not in __registered_test_groups:
            __registered_test_groups[group] = TestGroup(group)
        __registered_test_groups[group].submission_tests.append(wrapper)

        return wrapper
    return _add_submission_test

def run_tests() -> None:
    """
    Must be called by the test script to execute all tests.
    """
    print_ok('[+] Running tests..')
    passed = True
    has_multiple_groups = len(__registered_test_groups) > 1

    for group_name, tests in __registered_test_groups.items():
        group_passed = True

        if has_multiple_groups:
            print_ok(f'\n[+] Running tests for group {group_name}')

        print_ok('[+] Testing environment...')
        for test in tests.env_tests:
            ret = test()
            passed &= ret
            group_passed &= ret

        #Do not run submission tests if the environ is invalid
        if not passed:
            if has_multiple_groups:
                print_err('[!] Group failed!')
            continue
        print_ok('[+] Environment tests passed')

        print_ok('[+] Testing submission...')
        for test in tests.submission_tests:
            ret = test()
            passed &= ret
            group_passed &= ret

        if not passed and has_multiple_groups:
            print_err('[!] Group failed!')

    if not passed:
        print_err('[!] Some tests failed! Please review your submission to avoid penalties during grading.')
        exit(2)

    print_ok('[+] All tests passed! Good job. Ready to submit!')
    exit(0)
