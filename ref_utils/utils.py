""" Utility functions including colored printing or subprocess.run wrapper dropping privileges"""
from types import TracebackType
from typing import Any, List, Optional, Type
import subprocess

import sys

from colorama import Fore, Style

from .process import drop_privileges

SUCCESS = True
FAILURE = False

def print_ok(*args: str, **kwargs: Any) -> None:
    """Print green to signal correctness"""
    _sep = kwargs.get('sep', ' ')
    print(Fore.GREEN + _sep.join([str(o) for o in args]) + Style.RESET_ALL, **kwargs)

def print_warn(*args: str, **kwargs: Any) -> None:
    """Print yellow to warn user"""
    _sep = kwargs.get('sep', ' ')
    print(Fore.YELLOW + _sep.join([str(o) for o in args]) + Style.RESET_ALL, **kwargs)

def print_err(*args: str, **kwargs: Any) -> None:
    """Print red to alert user"""
    _sep = kwargs.get('sep', ' ')
    print(Fore.RED + _sep.join([str(o) for o in args]) + Style.RESET_ALL, **kwargs)

@drop_privileges
def run(cmd: List[str], check_returncode: bool = False, timeout: int = 10) -> Optional[str]:
    """
    Execute a command (with default timeout of 60s)
    """
    output: Optional[str] = None
    try:
        p = subprocess.run(cmd, check=check_returncode, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        output = p.stdout.decode().strip()
    except subprocess.TimeoutExpired:
        print_err(f"[!] Unexpected timeout for: {' '.join(cmd)} (after {timeout}s)")
    except subprocess.CalledProcessError as err:
        print_err(f"[!] Unexpected error: {err}")
    return output

@drop_privileges
def run_shell(cmd: List[str], check_returncode: bool = False, timeout: int = 10) -> Optional[str]:
    """
    Execute a command (with default timeout of 60s)
    """
    output: Optional[str] = None
    try:
        p = subprocess.run(' '.join(cmd), shell=True, check=check_returncode, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           timeout=timeout)
        output = p.stdout.decode().strip()
    except subprocess.TimeoutExpired:
        print_err(f"[!] Unexpected timeout for: {' '.join(cmd)} (after {timeout}s)")
    except subprocess.CalledProcessError as err:
        print_err(f"[!] Unexpected error: {err}")
    return output

def non_leaking_excepthook(type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
    """
    Handle an exception without displaying a traceback on sys.stderr.
    Must overwrite sys.excepthook as follows:
    `sys.excepthook = non_leaking_excepthook`
    """
    if type_ == KeyboardInterrupt:
        print("KeyboardInterrupt")
        sys.exit(0)
    else:
        sys.tracebacklimit = 0
        sys.__excepthook__(type_, value, traceback)
