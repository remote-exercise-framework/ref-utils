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
import errno

from .utils import print_err, map_path_as_posix, print_ok, decode_or_str, print_warn
from .error import RefUtilsError, RefUtilsProcessTimeoutError, RefUtilsProcessError

_DEFAULT_DROP_UID = 9999
_DEFAULT_DROP_GID = 9999

"""
An exception handler that converts some raised exceptions into a more
readable representation.
"""
def ref_util_exception_hook(type_: Type[BaseException], value: BaseException, traceback: TracebackType) -> None:
    if isinstance(value, RefUtilsError):
        # We raised the exception, thus __str__() gives us a deatiled error
        # description.
        print_err(str(value))
    elif isinstance(value, KeyboardInterrupt):
        print_err('[-] Keyboard Interrupt')
    else:
        #Make sure that we are not leaking any stack trace in case of unexpected exceptions
        # sys.tracebacklimit = 0
        sys.__excepthook__(type_, value, traceback)

def ref_util_install_global_exception_hook() -> None:
    """
    Replace sys.excepthook by non_leaking_excepthook
    """
    sys.excepthook = ref_util_exception_hook


def get_user_env(last_cmd: Optional[Union[str, bytes]]) -> Dict[str, Union[str, bytes]]:
    ret: Dict[str, Union[str, bytes]] = {}
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
    are automatically unwrapped and printed by the submissions test. If no timeout is passed,
    a deafult timeout of 10 seconds will be used. The Args listed below can be used in addition to
    the arguments normally expected by `subprocess.run`. Furthermore, the following arguments
    behave differently to `subprocess.run` default behavior:
        'env': If not passed, `env` is set to the user environment as of
            `task <...>` was called.
        'timeout': If not passed, `timeout` is set to 10.
    Args:
        check_signal = False: Raise a `RefUtilsProcessError` exceptions if the process is
            terminated by a signal. If False, a process is allowed to terminated via a signal.
    """
    #Convert Path to string
    cmd = map_path_as_posix(cmd_)

    if not 'env' in kwargs:
        # Restore the environment from the user as of the time she called `task ...`.
        # NOTE: The stored environment contains user controlled input!
        # Never restore the environment in a privileged context.
        kwargs['env'] = get_user_env(cmd[0])

    if 'timeout' not in kwargs:
        kwargs['timeout'] = 10

    check_signal = kwargs.get('check_signal', None)
    assert check_signal is None or type(check_signal) == bool
    if check_signal is not None:
        # Strip from kwargs we are about to pass to pythons run() method.
        del kwargs['check_signal']

    try:
        #pylint: disable=subprocess-run-check
        ret = subprocess.run(cmd, *args, **kwargs) # type: ignore
        if check_signal and ret.returncode < 0:
            raise RefUtilsProcessError(' '.join([str(e) for e in ret.args]) , ret.returncode, ret.stdout, ret.stderr)
        return ret
    except subprocess.TimeoutExpired as err:
        raise RefUtilsProcessTimeoutError(' '.join([str(e) for e in err.cmd]), kwargs['timeout']) from err
    except subprocess.CalledProcessError as err:
        raise RefUtilsProcessError(' '.join([str(e) for e in err.cmd]) , err.returncode, err.stdout, err.stderr) from err
    except PermissionError as err:
        raise RefUtilsError(f'Failed to execute: {err}.\nIs the target executable and has a correct shebang?:') from err
    except OSError as os_err:
        hints = ""
        if os_err.errno == errno.ENOEXEC:
            hints = '\nLooks like the file has the wrong format to be executed.\n'
            hints += 'Check whether it has a shebang and is of the expected type.'
        raise RefUtilsError(f'Failed to execute: {os_err}.{hints}') from os_err

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
    cmd = map_path_as_posix(cmd_)
    cmd_as_str = ' '.join(cmd) # type: ignore

    if verbose:
        print_ok(f'[+] Executing {cmd_as_str} and using its output as payload for the target..')

    p = run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        timeout=timeout, check_signal=check_signal)

    return p.returncode, p.stdout

def run_with_payload(cmd_: List[Union[str, Path, bytes]], stdin_input: Optional[Union[str, bytes]] = None, flag: Optional[bytes] = None, check: bool = False, check_signal: bool = True, timeout: int=10) -> Tuple[int, bytes]:
    #Convert Path to string
    assert isinstance(cmd_, list)
    cmd = map_path_as_posix(cmd_)

    assert stdin_input is None or isinstance(stdin_input, (bytes, str)), f'Unexpected type {type(stdin_input)}'
    assert(all([type(e) in (str, bytes) for e in cmd])), f'Wrong argument types {cmd}'

    # Check for embedded null bytes in the cmd.
    # subprocess.run raises a value error if null bytes are contained in the cmd.
    for e in cmd:
        if isinstance(e, str):
            e_bytes = e.encode()
        else:
            e_bytes = e
        for i, c in enumerate(e_bytes):
            if c == 0x00:
                raise RefUtilsError(
                    f'[!] Input "{decode_or_str(e)}"" contains a null byte at offset {i}!\n[!] Please remove the embedded null byte.'
                )

    p = run(cmd,
            check=check,
            input=stdin_input,
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
