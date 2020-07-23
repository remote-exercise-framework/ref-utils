""" Utility functions including colored printing or subprocess.run wrapper dropping privileges"""
import sys
from typing import Any, Union

from pathlib import Path
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

def write_stdout(data: bytes):
    sys.stdout.write(data)

def decode_or_str(data: bytes):
    if not data:
        return ''
    try:
        return data.decode()
    except:
        return str(data)

def map_to_str(cmd):
    ret = []
    for c in cmd:
        if isinstance(c, Path):
            ret.append(c.as_posix())
        elif isinstance(c, (str, bytes)):
            ret.append(c)
        else:
            raise TypeError(f'Unsupported type {type(c)} in cmd')
    return ret