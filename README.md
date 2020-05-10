# ref-utils
Package containing various utility functions used for remote-exercise-framework submission procedure

## Requirements
Check requirements.txt

## Build
```
git clone git@git.noc.ruhr-uni-bochum.de:SysSec-Teaching/ref-utils.git
cd ref-utils
pip install -f requirements.txt
```
Produce pip-installable file with
```
python3 setup.py bdist_wheel
```

## Provided functionality

### Drop & Execute
* `drop_privileges` and `drop_privileges_to(uid, gid)` decorates allow to execute function in unprivileged context
* TODO: ctxt mgr?

### Asserts
Return Boolean value (False) instead of AssertionError in case of failure
* `assert_is_file` - check whether given path points to file
* `assert_is_executable` - check whether given path points to executable file
* `assert_is_dir` - check whether given path points to directory

### Utils
Colored output
* `print_ok` - prints text green
* `print_warn` - prints text yellow
* `print_err` - prints text red

Run (shell) command after dropping privileges. Wraps subprocess.run
* `run` - subprocess.run
* `run_shell` - subprocess.run with `shell=True`. 

### Checks
Various checks to run on instances
* `run_pylint` - pylint linter - disable by setting environment variable NO_LINT="1"
* `run_mypy` - mypy type checker - disable by setting environment variable NO_LINT="1"
* `contains_flag` - execute given python script with python3 and check whether output contains a given flag value
* TODO: stuff like: `exec_trace = exec(/submitted_file); assert_executes_syscalls(exec_trace, 'write /flag' )`

