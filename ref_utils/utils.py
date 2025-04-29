""" Utility functions including colored printing or subprocess.run wrapper dropping privileges"""
import sys
import os
import typing as t
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


def test_result_will_be_submitted() -> bool:
    """
    Whether this test execution is going to be submitted as solution.
    """
    val = os.environ.get("RESULT_WILL_BE_SUBMITTED")
    if val:
        return val.lower() in ["1", "true"]
    return False

def get_user_environment() -> t.Dict[str, Union[str, bytes]]:
    """
    The task tool (task-wrapper.c) dumps the user environment in the moment it is executed
    to disk. This function retrives the dumped environment from the file and returns it.
    This allows to restore the user's exact environment which is paramount for tasks that
    require a stable stack layout.
    Returns:
        The mapping of all key value pairs of the user environment variables that where
        defined during submission.
    """
    ret: t.Dict[str, Union[str, bytes]] = {}
    content = Path('/tmp/.user_environ').read_text()
    lines = content.split('\x00')
    for line in lines:
        if line == '':
            continue

        try:
            k, v = line.split('=', 1)
        except Exception as e:
            print_err(f'Unexpected error while processing "{line}". Error: {e}.')
        else:
            ret[k] = v
    return ret

def write_stdout(data: AnyStr) -> None:
    sys.stdout.write(data) # type: ignore


def decode_or_str(data: str | bytes | bytearray) -> str:
    """
    Get a str representing the passed `data`.
    If the bytes are valid UTF8 they are converted to a str.
    Else, they are converted to str via `str(data)`.
    """
    if not data:
        return ''
    if isinstance(data, str):
        return data

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