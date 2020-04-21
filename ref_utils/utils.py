"""Functions related to colored printing"""
from colorama import Fore, Style

def print_ok(*args, **kwargs):
    """Print green to signal correctness"""
    print(Fore.GREEN, *args, Style.RESET_ALL, **kwargs, sep='')

def print_warn(*args, **kwargs):
    """Print yellow to warn user"""
    print(Fore.YELLOW, *args, Style.RESET_ALL, **kwargs, sep='')

def print_err(*args, **kwargs):
    """Print red to alert user"""
    print(Fore.RED, *args, Style.RESET_ALL, **kwargs, sep='')
