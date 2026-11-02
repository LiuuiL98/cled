"""Validation helpers for the Windows manual clipboard utility."""
import re

_CODE_RE = re.compile(r"^[0-9]{6}$")


def is_valid_code(value: str) -> bool:
    return bool(_CODE_RE.fullmatch(value or ""))
