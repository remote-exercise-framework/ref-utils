"""Exception-free assert functions"""
from pathlib import Path
from typing import Any, Union # pylint: disable = unused-import

from .error import RefUtilsAssertionError

import signal
import os

from .utils import print_err

def _assert(condition: bool, error_msg: str, silent: bool) -> bool:
    """Custom 'assertion' that prints a warning rather than throwing AssertionError"""
    if not condition:
        if not silent:
            print_err(f"[!] {error_msg}")
        return False
    return True

def assert_is_exec(executable: Union[str, 'os.PathLike[Any]', Path], silent: bool = False) -> bool:
    """Assert file exists and is executable"""
    if not isinstance(executable, Path):
        return assert_is_exec(Path(executable))
    return _assert(executable.exists and executable.is_file() and os.access(executable, os.X_OK),
                   f"Executable file {executable} not found or not executable", silent)

def assert_is_file(file_: Union[str, 'os.PathLike[Any]', Path], silent: bool = False) -> bool:
    """Assert file exists"""
    if not isinstance(file_, Path):
        return assert_is_file(Path(file_))
    return _assert(file_.exists and file_.is_file(), f"File {file_} not found", silent)

def assert_is_dir(directory: Union[str, 'os.PathLike[Any]', Path], silent: bool = False) -> bool:
    """Assert directory exists"""
    if not isinstance(directory, Path):
        return assert_is_dir(Path(directory))
    return _assert(directory.exists and directory.is_dir(), f"Directory {directory} not found", silent)
