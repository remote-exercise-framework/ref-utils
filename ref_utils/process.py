"""Functions related to processes"""
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from typing import Any, Callable
from functools import wraps
import os


DEFAULT_DROP_UID = 9999
DEFAULT_DROP_GID = 9999


def _drop_and_execute(conn: Connection, uid: int, gid: int, original_func: Callable, *args, **kwargs) -> None:
    os.setresgid(gid, gid, gid)
    groups = [g for g in os.getgroups() if g != 0]
    os.setgroups(groups)
    os.setresuid(uid, uid, uid)
    if args and kwargs:
        conn.send(original_func(*args, **kwargs))
    elif args:
        conn.send(original_func(*args))
    else:
        conn.send(original_func())
    conn.close()


def drop_privileges_to(uid: int = DEFAULT_DROP_UID, gid: int = DEFAULT_DROP_GID) -> Callable:
    """
    Decorator which drops the privileges before executing the function.
    Uses fork and setuid to drop privileges.
    Output is communicated back via a Pipe.
    """
    def _drop_privileges_to(func) -> Any:
        @wraps(func)
        def wrapper(*args, **kwargs):
            parent_conn, child_conn = Pipe()
            p = Process(target=_drop_and_execute, args=(child_conn, uid, gid, func, *args,), kwargs=kwargs)
            p.start()
            output: Any = parent_conn.recv()
            p.join()
            return output
        return wrapper
    return _drop_privileges_to


def drop_privileges(func) -> Any:
    """
    Decorator which drops the privileges before executing the function.
    Uses fork and setuid to drop privileges.
    Output is communicated back via a Pipe.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        parent_conn, child_conn = Pipe()
        p = Process(target=_drop_and_execute, args=(child_conn, DEFAULT_DROP_UID, DEFAULT_DROP_GID, func, *args,), kwargs=kwargs)
        p.start()
        output: Any = parent_conn.recv()
        p.join()
        return output
    return wrapper
