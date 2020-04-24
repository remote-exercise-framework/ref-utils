"""Various checks you may want to run during submission tests"""
from pathlib import Path
from typing import List, Optional

from .utils import print_ok, print_warn, print_err, run, SUCCESS, FAILURE


def contains_flag(flag: str, python_script: Path, silent: bool = False) -> bool:
    """
    Run submitted file and match whether it contains the flag value.
    """
    cmd = ["python3", python_script]
    output: Optional[str] = run(cmd, check_returncode=True, timeout=10)
    if output is None:
        return FAILURE
    if not flag in output:
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
    if not python_files:
        return SUCCESS
    lint_output = run(["pylint", "--exit-zero", "--rcfile", "/etc/pylintrc"] +
                      [str(f.resolve()) for f in python_files])
    if lint_output is None:
        return FAILURE
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
    if not python_files:
        return SUCCESS
    lint_output = run(["mypy", "--config-file", "/etc/mypyrc"] + [str(f.resolve()) for f in python_files])
    if lint_output is None:
        return FAILURE
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
    python_files = [f for f in Path("/home/user").glob("**/*.py") if not f.name.startswith(".")]
    if not python_files:
        return tests_passed
    print_ok(f'[+] Testing {len(python_files)} Python source code files')
    tests_passed &= run_pylint(python_files)
    tests_passed &= run_mypy(python_files)
    return tests_passed
