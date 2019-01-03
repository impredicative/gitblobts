import pathlib
from typing import Iterable, NamedTuple, Optional, Union

import git


class Blob(NamedTuple):
    timestamp: int
    blob: bytes


class Store:

    class RepoError(Exception):
        pass

    class BareRepoError(RepoError):
        pass

    class DirtyRepoError(RepoError):
        pass

    class UntrackedFilesRepoError(RepoError):
        pass

    def __init__(self, path: Union[str, pathlib.Path]):
        self._path = pathlib.Path(path)
        self.repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        self._check_repo()

    def _check_repo(self) -> None:
        if self.repo.bare:  # This is not implicit.
            raise self.BareRepoError('Repository must not be bare.')
        if self.repo.is_dirty():
            raise self.DirtyRepoError('Repository must not be dirty.')
        if self.repo.untracked_files:
            names = '\n'.join(self.repo.untracked_files)
            raise self.UntrackedFilesRepoError(f'Repository must not have any untracked files. It has these:\n{names}')

    def add(self, blob: Union[bytes, str], timestamp: Optional[int] = None) -> None:
        pass

    def get(self, start, end) -> Iterable[Blob]:
        pass
