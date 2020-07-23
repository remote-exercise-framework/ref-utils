from functools import wraps
from .utils import print_ok, print_err

__environment_test_functions = []
__submission_test_functions = []

def add_environment_test(func):
    global __environment_test_function

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    __environment_test_functions.append(wrapper)
    return wrapper

def add_submission_test(func):
    global __submission_test_functions

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    __submission_test_functions.append(wrapper)
    return wrapper


def __test_environ():
    global __environment_test_functions
    for ii, test in enumerate(__environment_test_functions):
        print_ok(f'[+] Environment test {ii+1} of {len(__environment_test_functions)}')
        ret = test()
        if not ret:
            return
    return True

def __test_submission():
    global __submission_test_functions
    for ii, test in enumerate(__submission_test_functions):
        print_ok(f'[+] Submission test {ii+1} of {len(__submission_test_functions)}')
        ret = test()
        if not ret:
            return
    return True


def run_tests():
    global __environment_test_function

    print_ok('[+] Running tests..')
    print_ok('[+] Testing environment..')
    ret = __test_environ()
    if ret:
        print_ok('[+] Environment tests passed :-)\n')

    if ret:
        print_ok('[+] Testing submission...')
        ret = __test_submission()


    if not ret:
        print_err('[!] Some tests failed! Please review your submission to avoid penalties during grading.')    
