"""Annotation helpers. Runtime no-ops; meaning comes from the mypy plugin."""
from typing import Any, Generic, TypeVar

_T = TypeVar('_T')


class Record(Generic[_T]):
    """One record of a Tryton model, resolved in the annotated file's scope.

        def rate(self, contracts: list[Record[Literal['contract']]]) -> None:
    """
    def __init__(self, *a: Any, **kw: Any) -> None: ...
