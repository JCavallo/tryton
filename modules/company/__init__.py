# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from typing import TYPE_CHECKING


__all__ = ['CompanyReport']

if TYPE_CHECKING:
    from .company import CompanyReport


def __getattr__(name):
    if name == 'CompanyReport':
        from .company import CompanyReport
        return CompanyReport
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
