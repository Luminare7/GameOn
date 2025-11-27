"""UI module for GameOn."""

from .cli import main as cli_main
from .gui import run_gui

__all__ = ['cli_main', 'run_gui']

