"""Functions related to dropping privileges"""
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from typing import Any, Callable
from functools import wraps
import os


_DEFAULT_DROP_UID = 9999
_DEFAULT_DROP_GID = 9999


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
            p = Process(target=_drop_and_execute, args=(child_conn, uid, gid, func, *args,), kwargs=kwargs)
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
        p = Process(target=_drop_and_execute, args=(child_conn, _DEFAULT_DROP_UID, _DEFAULT_DROP_GID, func, *args,), kwargs=kwargs)
        p.start()
        output: Any = parent_conn.recv()
        p.join()
        return output
    return wrapper
