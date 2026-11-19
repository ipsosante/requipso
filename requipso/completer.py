"""Custom IPython completer for Polars column names.

Provides tab-completion for column names inside ``pl.col("...")`` expressions.
Columns are sourced from all Polars DataFrames/LazyFrames referenced in the
current cell being edited.

Usage::

    from requipso.completer import install
    install()
"""

from __future__ import annotations
from typing import Iterator

import ast
import re

import polars as pl
from IPython.core.getipython import get_ipython
from IPython.core.completer import Completion

# Matches cursor inside pl.col("...") / pl.cols("...") / pl.col(["..."])
_COL_RE = re.compile(r"pl\.cols?\(\[?[\"']([^\"']*?)$")


def _extract_names(code: str) -> set[str]:
    """Extract variable names referenced in a code string.

    Uses AST when possible; falls back to regex for incomplete code
    (the usual state when the user is still typing).
    """
    try:
        tree = ast.parse(code)
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    except SyntaxError:
        return set(re.findall(r"\b([a-zA-Z_]\w*)\b", code))


def _polars_col_completions(text: str, offset: int) -> Iterator[Completion]:
    """Yield column-name ``Completion`` objects when the cursor is inside ``pl.col("…")``."""
    text_to_cursor = text[:offset]
    match = _COL_RE.search(text_to_cursor)
    if not match:
        return

    prefix = match.group(1)
    start = match.start(1)

    ip = get_ipython()
    if ip is None:
        # IPython environment not available, can't provide completions
        return
    # Collect names referenced in the *current cell* (= full `text`)
    cell_names = _extract_names(text)

    columns: set[str] = set()
    for name in cell_names:
        obj = ip.user_ns.get(name)
        if isinstance(obj, (pl.DataFrame, pl.LazyFrame)):
            columns.update(obj.columns)

    for col in sorted(columns):
        if col.startswith(prefix):
            yield Completion(start=start, end=offset, text=col, type="property")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install() -> None:
    """Patch IPython's completer to suggest Polars column names."""
    ip = get_ipython()
    if ip is None:
        return

    completer = ip.Completer

    # Store the original only once so repeated calls don't stack wrappers.
    if not hasattr(completer, "_original_completions"):
        completer._original_completions = completer.completions

    original = completer._original_completions

    def _patched(text, offset):
        yield from _polars_col_completions(text, offset)
        yield from original(text, offset)

    completer.completions = _patched


def uninstall() -> None:
    """Restore the original completer."""
    ip = get_ipython()
    if ip is None:
        return
    completer = ip.Completer
    if hasattr(completer, "_original_completions"):
        completer.completions = completer._original_completions
        del completer._original_completions
        print("✓ Polars column completer removed")
