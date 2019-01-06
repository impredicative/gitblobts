import calendar
import itertools
import pathlib
import time
import typing
from typing import Iterable, List, NamedTuple, Optional, Union

import git

import gitblobts.config as config


class Blob(NamedTuple):
    time_utc_ns: int
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
        self._repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        self._check_repo()
        self._pull_repo()

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
        if not repo.remote().exists():
            raise self.RepoRemoteNotExist('Repository remote must exist.')
        # if not self._repo.remote().name == 'origin':
        #     raise self.RemoteRepoError('Repository remote name must be "origin".')

    def _pull_repo(self) -> None:
        try:
            self._repo.remote().pull()
        except git.exc.GitCommandError:  # Could be due to no push yet.
            pass

    def _push_repo(self) -> None:
        self._repo.index.commit('')
        self._repo.remote().push()  # TODO: Pull and retry push to handle a merge conflict.

    def _standardize_time_to_ns(self, time_utc: Union[None, float, time.struct_time, str]) -> int:
        def _convert_seconds_to_ns(seconds: Union[int, float]) -> int:
            return int(round(seconds * int(1e9)))
        if time_utc is None:
            return time.time_ns()
        elif isinstance(float, time_utc):
            return _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, time.struct_time):
            if time_utc.tm_zone != 'UTC':
                raise self.TimeNotUTC(f"Provided timezone must be UTC, but it's {time_utc.tm_zone}.")
            return _convert_seconds_to_ns(calendar.timegm(time_utc))
        elif isinstance(str, time_utc):
            return 'CONVERT SLANG UTC TIME'  # TODO: Convert slang UTC time.
        else:
            annotation = typing.get_type_hints(self.writeblob)['time_utc']
            raise self.TimeUnhandledType(f'Provided time is of an unhandled type "{type(time_utc)}. '
                                         f'It must be conform to {annotation}.')

    def writeblob(self, blob: bytes, time_utc: Optional[float] = None, sync_repo: Optional[bool] = True) -> int:
        repo = self._repo
        time_utc_ns = self._standardize_time_to_ns(time_utc)
        if sync_repo:
            self._pull_repo()  # TODO: Consider pull only if there is a merge conflict.

        while True:  # Use filename that doesn't already exist. Avoid overwriting existing file.
            path = self._path / str(time_utc_ns)
            if path.exists():
                time_utc_ns += 1
            else:
                break

        path.write_bytes(blob)
        repo.index.add([path])
        if sync_repo:
            self._push_repo()
        assert blob == path.read_bytes()
        return time_utc_ns

    def writeblobs(self, blobs: Iterable[bytes], times_utc: Optional[Iterable[float]] = None) -> List[int]:
        self._pull_repo()  # TODO: Consider pull only if there is a merge conflict.
        if times_utc is None:
            times_utc = []
        times_utc_ns = [self.writeblob(blob, time_utc, sync_repo=False) for blob, time_utc in
                        itertools.zip_longest(blobs, times_utc)]
        self._push_repo()
        return times_utc_ns

    def readblobs(self, start_utc: Optional[Union[float, time.struct_time, str]] = None,
                  end_utc: Optional[Union[float, time.struct_time, str]] = None) -> Iterable[Blob]:
        self._pull_repo()
        start_utc = self._standardize_time_to_ns(start_utc) if start_utc is not None else 0
        end_utc = self._standardize_time_to_ns(end_utc) if end_utc is not None else float('inf')
        paths = (path for path in self._path.iterdir() if path.is_file())
        if start_utc <= end_utc:
            times_utc_ns = (int(path.name) for path in paths if start_utc <= int(path.name) <= end_utc)
            times_utc_ns = sorted(times_utc_ns)
        else:
            times_utc_ns = (int(path.name) for path in paths if end_utc <= int(path.name) <= start_utc)
            times_utc_ns = sorted(times_utc_ns, reverse=True)

        for time_utc_ns in times_utc_ns:
            path = self._path / str(time_utc_ns)
            yield Blob(time_utc_ns, path.read_bytes())
