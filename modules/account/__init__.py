# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from typing import TYPE_CHECKING


__all__ = ['MoveLineMixin']

if TYPE_CHECKING:
    from .move import MoveLineMixin


def __getattr__(name):
    if name == 'MoveLineMixin':
        from .move import MoveLineMixin
        return MoveLineMixin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
