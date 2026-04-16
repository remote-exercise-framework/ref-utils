# ref-utils
Package containing various utility functions used for remote-exercise-framework submission procedure

## Requirements
Check requirements.txt

## Build
```
git clone git@github.com:remote-exercise-framework/ref-utils.git
cd ref-utils
pip install -f requirements.txt
```
Produce pip-installable file with
```
python3 setup.py bdist_wheel
```

## Provided functionality

### Test Registration
* `@environment_test(task_name="default")` - register a function as an environment check (must return `bool`)
* `@submission_test(task_name="default")` - register a function as a submission test (must return `bool` or `TestResult`)
* `@extended_submission_test(task_name="default")` - register an extended submission test
* `TestResult(success: bool, score: Optional[float])` - return type for scored submission tests
* `run_tests()` - execute all registered tests (deprecated; called automatically by `task.py`)
* `test_result_will_be_submitted()` - check whether the current run is a final submission or just a check
* `get_instance_info()` - retrieve instance metadata (`InstanceInfo` dataclass)
* `get_user_environment()` - retrieve environment variables set by the user

### Drop & Execute
* `drop_privileges` and `drop_privileges_to(uid, gid)` decorators allow executing a function in unprivileged context

### Asserts
Return `False` instead of raising `AssertionError` on failure
* `assert_is_file` - check whether given path points to a file
* `assert_is_exec` - check whether given path points to an executable file
* `assert_is_dir` - check whether given path points to a directory

### Utils
Colored output
* `print_ok` - prints text green
* `print_warn` - prints text yellow
* `print_err` - prints text red

Run (shell) command after dropping privileges. Wraps `subprocess.run`
* `run` - subprocess.run
* `run_shell` - subprocess.run with `shell=True`
* `run_capture_output` - subprocess.run capturing stdout/stderr
* `run_with_payload` - run a binary with specific stdin payload

### Checks
Various checks to run on instances
* `run_pylint` - pylint linter (disable with `NO_LINT="1"`)
* `run_mypy` - mypy type checker (disable with `NO_LINT="1"`)
* `contains_flag` - execute given python script and check whether output contains a given flag value
