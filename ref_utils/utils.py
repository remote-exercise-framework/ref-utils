""" Utility functions including colored printing or subprocess.run wrapper dropping privileges"""
from typing import Any

from colorama import Fore, Style

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
