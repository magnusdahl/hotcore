"""Helpers for dealing with optional third-party dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["H3_AVAILABLE", "HexAddress", "get_h3_module"]

try:
    import h3  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    h3 = None  # type: ignore[assignment]
    H3_AVAILABLE = False
else:  # pragma: no cover - exercised when h3 is installed
    H3_AVAILABLE = True


def get_h3_module():
    """Return the imported h3 module if available, otherwise None."""
    return h3


if TYPE_CHECKING:
    if H3_AVAILABLE:
        from h3.api.basic_str import HexAddress  # type: ignore[attr-defined]
    else:
        from typing import NewType

        HexAddress = NewType("HexAddress", str)
else:  # pragma: no cover - runtime fallback to keep things simple
    HexAddress = str
