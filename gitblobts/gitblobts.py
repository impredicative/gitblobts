import pathlib
from typing import Iterable, NamedTuple, Optional, Union


class Blob(NamedTuple):
    timestamp: int
    blob: bytes


class Store:
    def __init__(self, path: Union[str, pathlib.Path]):
        self._path = pathlib.Path(path)

    def add(self, blob: Union[bytes, str], timestamp: Optional[int] = None) -> None:
        pass

    def get(self, start, end) -> Iterable[Blob]:
        pass
