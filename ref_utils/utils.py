"""Functions related to colored printing"""
from typing import List, Optional
import subprocess

from colorama import Fore, Style

from .process import drop_privileges

SUCCESS = True
FAILURE = False

def print_ok(*args, **kwargs):
    """Print green to signal correctness"""
    print(Fore.GREEN, *args, Style.RESET_ALL, **kwargs, sep='')

def print_warn(*args, **kwargs):
    """Print yellow to warn user"""
    print(Fore.YELLOW, *args, Style.RESET_ALL, **kwargs, sep='')

def print_err(*args, **kwargs):
    """Print red to alert user"""
    print(Fore.RED, *args, Style.RESET_ALL, **kwargs, sep='')

@drop_privileges
def run(cmd: List[str], check_returncode: bool = False, timeout: int = 60) -> Optional[str]:
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
