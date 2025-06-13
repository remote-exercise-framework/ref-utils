from typing import Any
from .utils import decode_or_str
import signal

class RefUtilsError(Exception):
    """
    Base class of all exceptions we might raise during test execution.
    This class allows a "submission test" to distinguish exceptions raised
    on purpose from those unexpected and not properly handled by the
    ref-utils.
    """
    def __init__(self, *args: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

class RefUtilsProcessTimeoutError(RefUtilsError):
    
    def __init__(self, cmd: str, timeout: int) -> None:
        self.cmd: str = cmd
        self.timeout: int = timeout
        self.msg = f'[!] Timeout error for: {cmd} (after {timeout}s)'

    def __str__(self) -> str:
        return self.msg

class RefUtilsProcessError(RefUtilsError):
    
    def __init__(self, cmd: str, exit_code: int, stdout: bytes, stderr: bytes) -> None:
        self.exit_code = exit_code
        if exit_code < 0:
            exit_code_str = f'{exit_code} ({signal.Signals(exit_code*-1).name})'
        else:
            exit_code_str = str(exit_code)
        self.stdout = stdout
        self.stderr = stderr
        self.msg = f'[!] Execution of {cmd} failed with exitcode {exit_code_str}.\n'
        self.msg += '--------------------- STDOUT ---------------------\n'
        self.msg += decode_or_str(self.stdout)
        self.msg += '\n--------------------- STDERR ---------------------\n'
        self.msg += decode_or_str(self.stderr)

    def __str__(self) -> str:
        return self.msg

class RefUtilsAssertionError(RefUtilsError):
    pass
