"""Functions related to dropping privileges"""
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from types import TracebackType
from typing import Any, Callable, List, Optional, Type
from functools import wraps
import os
import subprocess
import sys

from .utils import print_err

_DEFAULT_DROP_UID = 9999
_DEFAULT_DROP_GID = 9999


class NLProcess(Process):
    """
    Non-Leaking Process - use custom non_leaking_excepthook to mask exceptions
    """
    def run(self) -> None:
        try:
            super().run()
        except KeyboardInterrupt:
            print("KeyboardInterrupt!")
            sys.exit(0)
        except Exception:
            non_leaking_excepthook(*sys.exc_info())


def non_leaking_excepthook(type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
    """
    Handle an exception without displaying a traceback on sys.stderr.
    Must overwrite sys.excepthook as follows:
    `sys.excepthook = non_leaking_excepthook`
    """
    if type_ == KeyboardInterrupt:
        print("KeyboardInterrupt!")
        sys.exit(0)
    else:
        sys.tracebacklimit = 0
        sys.__excepthook__(type_, value, traceback)


def setup_non_leaking_excepthook() -> None:
    """
    Replace sys.excepthook by non_leaking_excepthook
    """
    sys.excepthook = non_leaking_excepthook


def _drop_and_execute(conn: Connection, uid: int, gid: int, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    os.setresgid(gid, gid, gid)
    groups = [g for g in os.getgroups() if g != 0]
    os.setgroups(groups)
    os.setresuid(uid, uid, uid)
    conn.send(original_func(*args, **kwargs))
    conn.close()


def drop_privileges_to(uid: int = _DEFAULT_DROP_UID, gid: int = _DEFAULT_DROP_GID) -> Callable[..., Any]:
    """
    Decorator which drops the privileges to given UID, GID tuple before executing the decorated function.
    Uses fork and setuid to drop privileges.
    Output is communicated back via a Pipe.
    """
    def _drop_privileges_to(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            parent_conn, child_conn = Pipe()
            p = NLProcess(target=_drop_and_execute, args=(child_conn, uid, gid, func, *args,), kwargs=kwargs)
            p.start()
            output: Any = parent_conn.recv()
            p.join()
            return output
        return wrapper
    return _drop_privileges_to


def drop_privileges(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator which drops the privileges to default UID, GID tuple before executing the decorated function.
    Uses fork and setuid to drop privileges.
    Output is communicated back via a Pipe.
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        parent_conn, child_conn = Pipe()
        p = NLProcess(target=_drop_and_execute, args=(child_conn, _DEFAULT_DROP_UID, _DEFAULT_DROP_GID, func, *args,), kwargs=kwargs)
        p.start()
        output: Any = parent_conn.recv()
        p.join()
        return output
    return wrapper



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
