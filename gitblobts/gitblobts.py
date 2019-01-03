import calendar
import pathlib
import time
import typing
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

    class TimeError(Exception):
        pass

    class TimeNotUTC(TimeError):
        pass

    class TimeUnhandledType(TimeError):
        pass

    def __init__(self, path: Union[str, pathlib.Path]):
        self._path = pathlib.Path(path)
        self.repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        self._check_repo()

    def _check_repo(self) -> None:
        repo = self.repo
        if repo.bare:  # This is not implicit.
            raise self.RepoBare('Repository must not be bare.')
        # if repo.active_branch.name != 'master':
        #     raise self.RepoBranchNotMaster('Active repository branch must be "master".')
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

    def _standardize_time(self, time_utc: Optional[Union[float, time.struct_time]] = None) -> int:
        def _convert_seconds_to_ns(seconds: Union[int, float]) -> int:
            return int(round(seconds * 1e9))
        if time_utc is None:
            time_utc_ns = time.time_ns()
        elif isinstance(float, time_utc):
            time_utc_ns = _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, time.struct_time):
            if time_utc.tm_zone != 'UTC':
                raise self.TimeNotUTC(f"Provided timezone must be UTC, but it's {time_utc.tm_zone}.")
            time_utc_ns = _convert_seconds_to_ns(calendar.timegm(time_utc))
        else:
            annotation = typing.get_type_hints(self.writeblob)['time_utc']
            raise self.TimeUnhandledType(f'Provided time is of an unhandled type "{type(time_utc)}. '
                                         f'It must be conform to {annotation}.')
        return time_utc_ns

    def writeblob(self, blob: bytes, time_utc: Optional[Union[float, time.struct_time]] = None) -> None:
        time_utc_ns = self._standardize_time(time_utc)
        path = self._path / str(time_utc_ns)
        path.write_bytes(blob)

    def readblobs(self, start, end) -> Iterable[Blob]:
        pass
