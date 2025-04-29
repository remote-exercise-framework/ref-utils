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
import pickle
import io
import importlib
from functools import partial

from .utils import get_user_environment, print_err, map_path_as_posix, print_ok, decode_or_str, print_warn
from .error import RefUtilsError, RefUtilsProcessTimeoutError, RefUtilsProcessError

_DEFAULT_DROP_UID = 9999
_DEFAULT_DROP_GID = 9999

def ref_util_exception_hook(type_: Type[BaseException], value: BaseException, traceback: TracebackType, redact_traceback: bool = False) -> None:
    """
    An exception handler that converts some raised exceptions into a representation that is suitable to
    be displayed to the user. We use this handler to convert our custom exception type (RefUtilsError) into error messages
    for the user. If an error is raised that has not been converted to a RefUtilsError by us, the expection
    is printed as-is. This may leak details (through the backtrace) of the underlying submission test,
    but experience showed that having the full backtrace is worth the risk.
    """
    if isinstance(value, RefUtilsError):
        # We raised the exception, thus __str__() gives us a detailed error
        # description.
        print_err(str(value))
    elif isinstance(value, KeyboardInterrupt):
        print_err('[-] Keyboard Interrupt')
    else:
        if redact_traceback:
            # Setting the traceback limit removes all stack frames from the printed message.
            sys.tracebacklimit = 0
        sys.__excepthook__(type_, value, traceback)

def ref_util_install_global_exception_hook() -> None:
    """
    Replace sys.excepthook by non_leaking_excepthook
    """
    hook = partial(ref_util_exception_hook, redact_traceback=False)
    sys.excepthook = hook

# Hopefully safe, if not, please tell us, dont mess with the system. Thanks :)
class RestrictedUnpickler(pickle.Unpickler):
    ALLOWED_MODULE_NAME = {
        ("subprocess", "CompletedProcess"),
        ("ref_utils.error", "RefUtilsProcessError"),
        ("ref_utils.error", "RefUtilsProcessTimeoutError"),
        ("ref_utils.error", "RefUtilsAssertionError"),
        ("ref_utils.error", "RefUtilsError")
    }

    def find_class(self, module, name):
        for safe_module_name in RestrictedUnpickler.ALLOWED_MODULE_NAME:
            if safe_module_name == (module, name):
                m = importlib.import_module(module)
                return getattr(m, name)
        else:
            err = pickle.UnpicklingError(f"{module}.{name} is forbidden")
            raise RefUtilsError(f"Failed to parse the output of the target during testing. This should not happen. Please inform the staff. ({err})")

def restricted_loads(s):
    return RestrictedUnpickler(io.BytesIO(s)).load()

def _drop_and_execute(conn: Connection, uid: int, gid: int, original_func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    os.setresgid(gid, gid, gid)
    groups = [g for g in os.getgroups() if g != 0]
    os.setgroups(groups)
    os.setresuid(uid, uid, uid)
    try:
        ret = original_func(*args, **kwargs)
        pickled_ret = pickle.dumps(ret)
        conn.send_bytes(pickled_ret)
    except Exception as e:
        #Forward exception to our parent
        pickled_e = pickle.dumps(e)
        conn.send_bytes(pickled_e)
    finally:
        conn.close()

def drop_privileges(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator which drops the privileges to default UID, GID tuple before executing the decorated function.
    Uses fork and setuid to drop privileges.
    NOTE: The decorated function's output is communicated back via a pipe and encoded via pickle.
    Thus, we are unpickling untrusted data here!
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        parent_conn, child_conn = Pipe()
        p = Process(target=_drop_and_execute, args=(child_conn, _DEFAULT_DROP_UID, _DEFAULT_DROP_GID, func, *args,), kwargs=kwargs)
        p.start()
        pickled_ret: Any = parent_conn.recv_bytes()
        # ! Unpickle the data that was pickled by our untrusted party in `_drop_and_execute`.
        # ! We are only allowing a subset of python types.
        # ! It would be prefereable to use JSON here to make this actually feel safe.
        ret = restricted_loads(pickled_ret)
        p.join()
        if isinstance(ret, Exception):
            raise ret
        return ret
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
    Returns:
        The result of the executed `cmd` as CompletedProcess (depending on the used kwargs, see python's run documentation).
        NOTE: Every type returned from this function must be unpickable by the `RestrictedUnpickler`.
    """
    #Convert Path to string
    cmd = map_path_as_posix(cmd_)

    # Make sure nobody is messing with stdin's TTY if we do not use it.
    # This is for example an issue with gdb when it causes a timeout and is therefore
    # forcefully killed via SIGKILL. If this happened, gdb fails to restore the TTY
    # settings is changed on fd 0 and leaves the terminal in an unusable state.
    if "stdin" not in kwargs and "input" not in kwargs:
        kwargs["stdin"] = subprocess.DEVNULL

    if not 'env' in kwargs:
        # Restore the environment from the user as of the time she called `task ...`.
        # NOTE: The stored environment contains user controlled input!
        # Never restore the environment in a privileged context.
        env = get_user_environment()
        # Set the last executed command variable ("_") to the correct value.
        env["_"] = cmd[0]
        kwargs['env'] = env

    if 'timeout' not in kwargs:
        kwargs['timeout'] = 10

    check_signal = kwargs.get('check_signal', None)
    assert check_signal is None or type(check_signal) == bool
    if check_signal is not None:
        # Strip from kwargs we are about to pass to pythons run() method.
        del kwargs['check_signal']

    try:
        #pylint: disable=subprocess-run-check
        # ret will be of type CompletedProcess which is on the allow list of the `RestrictedUnpickler`.
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
        # FIXME: from os_err will not work with the pickle filter in place.
        raise RefUtilsError(f'Failed to execute: {os_err}.{hints}') from os_err

def run_capture_output(*args: str, check_signal: bool = True, **kwargs: Any) -> Tuple[int, bytes]:
    """
    Wrapper of subprocess.run that redirects stderr to stdout and returns
    (returncode, stdout). This methods raises the same exceptions as ref-utils
    run() method.
    If `env` is not set, the user environment when she called `task check` is restored.
    """
    p = run(*args, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check_signal=check_signal)
    return p.returncode, p.stdout

def get_payload_from_executable(cmd_: List[Union[str, Path, bytes]], check: bool = True, check_signal: bool = True, verbose: bool = True, timeout: int = 10) -> Tuple[int, bytes]:
    """
    Get the payload from a script/binary by executing it and returning the output.
    If `env` is not set, the user environment when she called `task check` is restored.
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
                    f'[!] Input "{decode_or_str(e)}" contains a null byte at offset {i}!\n[!] Please remove the embedded null byte.'
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
