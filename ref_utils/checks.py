"""Various checks you may want to run during submission tests"""
import os
import subprocess
from pathlib import Path
from typing import List

from .config import get_config
from .process import run
from .utils import FAILURE, SUCCESS, print_err, print_ok, print_warn

_NO_LINT_ENV_VAR = "NO_LINT"
_ENV_VAL_TRUE = "1"
_ENV_VAL_FALSE = "0"

def contains_flag(flag: str, python_script: Path, silent: bool = False) -> bool:
    """
    Run submitted file and match whether it contains the flag value.
    """
    cmd: List[str] = ["python3", python_script.as_posix()]
    result = run(cmd, check_signal=False, timeout=10, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.decode() if result.stdout else ""
    if flag not in output:
        if not silent:
            print_err("[!] Failed to find flag")
        return FAILURE
    if not silent:
        print_ok("[+] Correct flag found")
    return SUCCESS


def run_pylint(python_files: List[Path]) -> bool:
    """
    Run pylint with custom config on user code (only interesting if submission contains .py files)
    """
    if not python_files or os.environ.get(_NO_LINT_ENV_VAR, '') == _ENV_VAL_TRUE:
        return SUCCESS
    result = run(["pylint", "--exit-zero", "--rcfile", str(get_config().pylint_config_path)] +
                 [str(f.resolve()) for f in python_files],
                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lint_output = result.stdout.decode() if result.stdout else ""
    if lint_output != "":
        print_warn("[!] pylint's syntax and coding style checks failed:")
        print_warn('    ' + '\n    '.join(lint_output.split('\n')))
        return FAILURE
    print_ok("[+] pylint's syntax and coding style checks passed")
    return SUCCESS


def run_mypy(python_files: List[Path]) -> bool:
    """
    Run mypy with custom config on user code (only interesting if submission contains typed .py files)
    """
    if not python_files or os.environ.get(_NO_LINT_ENV_VAR, '') == _ENV_VAL_TRUE:
        return SUCCESS
    cmd = ["mypy", "--config-file", str(get_config().mypy_config_path)]
    cmd += [str(f.resolve()) for f in python_files]
    result = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lint_output = result.stdout.decode() if result.stdout else ""
    if lint_output != "":
        print_warn("[!] mypy's type checks failed:")
        print_warn('    ' + '\n    '.join(lint_output.split('\n')))
        return FAILURE
    print_ok("[+] mypy's type checks passed")
    return SUCCESS


def check_all_python_files() -> bool:
    """
    Run checks only suited for Python files (mypy + pylint)
    """
    tests_passed = True
    python_files = [f for f in get_config().user_home_path.glob("**/*.py") if not f.name.startswith(".")]
    if not python_files or os.environ.get(_NO_LINT_ENV_VAR, '') == _ENV_VAL_TRUE:
        return tests_passed
    print_ok(f'[+] Testing {len(python_files)} Python source code files')
    tests_passed &= run_pylint(python_files)
    tests_passed &= run_mypy(python_files)
    return tests_passed
