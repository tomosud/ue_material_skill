"""Exact source-symbol matching shared by evidence generation and QA.

Reference strings may contain several symbols separated by `` / ``. Once a
qualified symbol supplies an owner, following unqualified names may be members
of that same owner or global helpers. All names use exact identifier tokens.
"""

from __future__ import annotations

from pathlib import Path
import re


_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
_QUALIFIED_RE = re.compile(rf"^{_IDENTIFIER}(?:::{_IDENTIFIER})+$")
_GLOBAL_RE = re.compile(rf"^{_IDENTIFIER}$")


def _qualified_pattern(symbol: str) -> re.Pattern[str]:
    components = symbol.split("::")
    joined = r"\s*::\s*".join(re.escape(component) for component in components)
    return re.compile(rf"(?<![A-Za-z0-9_]){joined}(?![A-Za-z0-9_])")


def _global_pattern(symbol: str) -> re.Pattern[str]:
    # A global helper must not be the leaf of another qualified symbol.
    return re.compile(rf"(?<![A-Za-z0-9_:]){re.escape(symbol)}(?![A-Za-z0-9_:])")


def symbol_is_present(text: str, reference: str) -> bool:
    """Return whether every exact symbol in *reference* occurs in *text*."""

    owner: str | None = None
    parts = [part.strip() for part in reference.split(" / ")]
    if not parts or any(not part for part in parts):
        return False
    for part in parts:
        if _QUALIFIED_RE.fullmatch(part):
            owner, _ = part.rsplit("::", 1)
            candidate = part
            pattern = _qualified_pattern(candidate)
        elif _GLOBAL_RE.fullmatch(part):
            # Audit shorthand commonly omits a repeated owner, while some
            # references pair an owned method with a global helper. Accept
            # either exact form, but never a mere leaf for the first qualified
            # symbol (the source of MadeUpClass::Compile false positives).
            patterns = [_global_pattern(part)]
            if owner is not None:
                patterns.insert(0, _qualified_pattern(f"{owner}::{part}"))
            if not any(pattern.search(text) is not None for pattern in patterns):
                return False
            continue
        else:
            return False
        if pattern.search(text) is None:
            return False
    return True


def source_file_has_symbol(path: Path, reference: str) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return symbol_is_present(text, reference)
