""" Utility functions including colored printing or subprocess.run wrapper dropping privileges"""
import sys
from typing import Any, AnyStr, List, Union

from pathlib import Path
from colorama import Fore, Style


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


def write_stdout(data: AnyStr) -> None:
    sys.stdout.write(data) # type: ignore


def decode_or_str(data: bytes) -> str:
    """
    Get a str representing the passed `data`.
    If the bytes are valid UTF8 they are converted to a str.
    Else, they are converted to str via `str(data)`.
    """
    if not data:
        return ''
    try:
        return data.decode()
    except: # pylint: disable =bare-except
        return str(data)


def map_path_as_posix(cmd: List[Union[Path, str, bytes]]) -> List[Union[str, bytes]]:
    ret: List[Union[str, bytes]] = []
    for c in cmd:
        if isinstance(c, Path):
            ret.append(c.as_posix())
        else:
            ret.append(c)
    return ret