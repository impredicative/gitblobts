import pathlib
from typing import Iterable, NamedTuple, Optional, Union

import git


class Blob(NamedTuple):
    timestamp: int
    blob: bytes


class Store:

    class RepoError(Exception):
        pass

    class RepoBare(RepoError):
        pass

    class RepoUnclean(RepoError):
        pass

    class RepoDirty(RepoUnclean):
        pass

    class RepoHasUntrackedFiles(RepoUnclean):
        pass

    class RepoNoRemote(RepoError):
        pass

    class RepoRemoteNotAdded(RepoNoRemote):
        pass

    class RepoRemoteNotExist(RepoNoRemote):
        pass

    def __init__(self, path: Union[str, pathlib.Path]):
        self._path = pathlib.Path(path)
        self.repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        self._check_repo()

    def _check_repo(self) -> None:
        repo = self.repo
        if repo.bare:  # This is not implicit.
            raise self.RepoBare('Repository must not be bare.')
        if repo.active_branch.name != 'master':
            raise self.RepoBranchNotMaster('Active repository branch must be "master".')
        if repo.is_dirty():
            raise self.RepoDirty('Repository must not be dirty.')
        if repo.untracked_files:
            names = '\n'.join(repo.untracked_files)
            raise self.RepoHasUntrackedFiles(f'Repository must not have any untracked files. It has these:\n{names}')
        if not repo.remotes:
            raise self.RepoRemoteNotAdded('Repository must have a remote.')
        if not repo.remotes().exists():
            raise self.RepoRemoteNotExist('Repository remote must exist.')
        # if not self.repo.remote().name == 'origin':
        #     raise self.RemoteRepoError('Repository remote name must be "origin".')

    def add(self, blob: Union[bytes, str], timestamp: Optional[int] = None) -> None:
        pass

    def get(self, start, end) -> Iterable[Blob]:
        pass
