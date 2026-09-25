# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from typing import TYPE_CHECKING


__all__ = ['AnalyticMixin']

if TYPE_CHECKING:
    from .account import AnalyticMixin


def __getattr__(name):
    if name == 'AnalyticMixin':
        from .account import AnalyticMixin
        return AnalyticMixin
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
