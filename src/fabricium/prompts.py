"""Interactive prompt utilities for Hermes plugins.

TTY-aware prompts that fall back to safe defaults in non-interactive
contexts (CI, cron, piped input).
"""

import sys


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Ask a yes/no question interactively.

    Returns *default* when stdin is not a TTY (non-interactive).
    """
    if not sys.stdin.isatty():
        return default
    hint = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{hint}] ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")
