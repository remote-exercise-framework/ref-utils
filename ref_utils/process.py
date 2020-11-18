"""Functions related to dropping privileges"""
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from types import TracebackType
from typing import Any, Callable, Dict, List, Optional, Type, Tuple, Union
from functools import wraps
import os
import subprocess
import sys
from pathlib import Path

from .utils import print_err, map_to_str, print_ok, decode_or_str
from .error import RefUtilsError, RefUtilsProcessTimeoutError, RefUtilsProcessError

_DEFAULT_DROP_UID = 9999
_DEFAULT_DROP_GID = 9999

def ref_util_exception_hook(type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
    if isinstance(value, RefUtilsError):
        print_err(str(value))
    elif isinstance(value, KeyboardInterrupt):
        print_err('[-] Keyboard Interrupt')
    else:
        #Make sure that we are not leaking any stack trace in case of unexpected exceptions
        #sys.tracebacklimit = 0
        sys.__excepthook__(type_, value, traceback)

def ref_util_install_global_exception_hook() -> None:
    """
    Replace sys.excepthook by non_leaking_excepthook
    """
    sys.excepthook = ref_util_exception_hook


def get_user_env(last_cmd: Optional[Union[str, bytes]]) -> Dict[str, Union[str, bytes]]:
    ret: Dict[str, Union[str, bytes]] = {}
    with open('/tmp/.user_environ', 'r') as f:
        lines = f.readlines()
        for line in lines:
            k, v = line.split('=', 1)
            #Trim newline that is part of printenv's output
            v = v[:-1]
            ret[k] = v
    if last_cmd is not None:
        ret['_'] = last_cmd
    return ret


def _drop_and_execute(conn: Connection, uid: int, gid: int, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    os.setresgid(gid, gid, gid)
    groups = [g for g in os.getgroups() if g != 0]
    os.setgroups(groups)
    os.setresuid(uid, uid, uid)
    try:
        conn.send(original_func(*args, **kwargs))
    except Exception as e:
        #Forward exception to our parent
        conn.send(e)
    finally:
        conn.close()


# def drop_privileges_to(uid: int = _DEFAULT_DROP_UID, gid: int = _DEFAULT_DROP_GID) -> Callable[..., Any]:
#     """
#     Decorator which drops the privileges to given UID, GID tuple before executing the decorated function.
#     Uses fork and setuid to drop privileges.
#     Output is communicated back via a Pipe.
#     """
#     def _drop_privileges_to(func: Callable[..., Any]) -> Callable[..., Any]:
#         @wraps(func)
#         def wrapper(*args: Any, **kwargs: Any) -> Any:
#             parent_conn, child_conn = Pipe()
#             p = Process(target=_drop_and_execute, args=(child_conn, uid, gid, func, *args,), kwargs=kwargs)
#             p.start()
#             output: Any = parent_conn.recv()
#             p.join()
#             return output
#         return wrapper
#     return _drop_privileges_to


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
        if isinstance(output, Exception):
            raise output
        return output
    return wrapper

@drop_privileges
def run(cmd_: List[Union[str, Path, bytes]], *args: str, **kwargs: Any) -> 'subprocess.CompletedProcess[Any]':
    """
    Wrapper for subprocess.run which converts expected exceptions into customs types that
    are automatically unwrapped and printed by the submissions test. If not timeout is set,
    a deafult timeout of 10 seconds will be used.
    """
    #Convert Path to string
    cmd = map_to_str(cmd_)
    check_signal = False

    if not 'env' in kwargs:
        kwargs['env'] = get_user_env(cmd[0])

    if 'timeout' not in kwargs:
        kwargs['timeout'] = 10

    if kwargs.get('check_signal', False):
        del kwargs['check_signal']
        check_signal = True

    try:
        ret = subprocess.run(cmd, *args, **kwargs) # type: ignore
        if check_signal and ret.returncode < 0:
            raise RefUtilsProcessError(' '.join([str(e) for e in ret.args]) , ret.returncode, ret.stdout, ret.stderr)
        return ret

    except subprocess.TimeoutExpired as err:
        raise RefUtilsProcessTimeoutError(' '.join([str(e) for e in err.cmd]), kwargs['timeout'])
    except subprocess.CalledProcessError as err:
        raise RefUtilsProcessError(' '.join([str(e) for e in err.cmd]) , err.returncode, err.stdout, err.stderr)

def run_capture_output(*args: str, check_signal: bool = True, **kwargs: Any) -> Tuple[int, bytes]:
    """
    Wrapper of subprocess.run that redirects stderr to stdout and returns
    (returncode, stdout). This methods raises the same exceptions as ref-utils
    run() method.
    """
    p = run(*args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check_signal=check_signal)
    return p.returncode, p.stdout

def get_payload_from_executable(cmd_: List[Union[str, Path, bytes]], check: bool = True, check_signal: bool = True, verbose: bool = True, timeout: int = 10) -> Tuple[int, bytes]:
    """
    Get the payload from a script/binary by executing it and returning the output.
    Args:
        cmd: The command to execute.
        check: Same as for subprocess.run.
        verbose: Print messages about what is currently done.
        timeout: Seconds to wait for the target to terminate.
    Returns:
        A tuple (exit_code, output: bytes)
    """
    #Convert Path to string
    cmd = map_to_str(cmd_)
    cmd_as_str = ' '.join(cmd) # type: ignore

    if verbose:
        print_ok(f'[+] Executing {cmd_as_str} and using its output as payload for the target..')

    p = run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        timeout=timeout, check_signal=check_signal)

    return p.returncode, p.stdout

def run_with_payload(cmd_: List[Union[str, Path, bytes]], input: Optional[List[Union[str, bytes]]] = None, flag: Optional[bytes] = None, check: bool = False, check_signal: bool = True, timeout: int=10) -> Tuple[int, bytes]:
    #Convert Path to string
    cmd = map_to_str(cmd_)

    p = run(cmd, check=check,
            input=input,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check_signal=check_signal,
            )

    if flag and flag not in p.stdout:
        output = decode_or_str(p.stdout)
        msg = f'[!] Wrong output: {output}'
        raise RefUtilsError(msg)

    return p.returncode, p.stdout
