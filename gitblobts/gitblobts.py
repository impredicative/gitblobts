import calendar
import pathlib
import time
import typing
from typing import Iterable, List, NamedTuple, Optional, Union

import git


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

    class TimesNotUnique(TimeError):
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
        self._repo.remote().push()  # TODO: Pull and retry if there is a merge conflict.

    def _standardize_time_to_ns(self, time_utc: Union[None, str, float, time.struct_time]) -> int:
        def _convert_seconds_to_ns(seconds: Union[int, float]) -> int:
            return int(round(seconds * int(1e9)))
        if time_utc is None:
            return time.time_ns()
        elif isinstance(str, time_utc):
            return 'CONVERT SLANG UTC TIME'  # TODO: Convert slang UTC time.
        elif isinstance(float, time_utc):
            return _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, time.struct_time):
            if time_utc.tm_zone != 'UTC':
                raise self.TimeNotUTC(f"Provided timezone must be UTC, but it's {time_utc.tm_zone}.")
            return _convert_seconds_to_ns(calendar.timegm(time_utc))
        else:
            annotation = typing.get_type_hints(self.writeblob)['time_utc']
            raise self.TimeUnhandledType(f'Provided time is of an unhandled type "{type(time_utc)}. '
                                         f'It must be conform to {annotation}.')

    def writeblob(self, blob: bytes, time_utc: Optional[Union[float, time.struct_time]] = None,
                  sync_repo: Optional[bool] = True) -> None:
        repo = self._repo
        time_utc_ns = self._standardize_time_to_ns(time_utc)
        path = self._path / str(time_utc_ns)
        if sync_repo:
            self._pull_repo()  # TODO: Consider pull only if there is a merge conflict.
        path.write_bytes(blob)
        repo.index.add([path])
        if sync_repo:
            self._push_repo()
        assert blob == path.read_bytes()

    def writeblobs(self, blobs: List[bytes], times_utc: Optional[List[Union[float, time.struct_time]]] = None) -> None:
        repo = self._repo
        self._pull_repo()  # TODO: Consider pull only if there is a merge conflict.
        if len(times_utc) != len(set(times_utc)):
            raise self.TimesNotUnique("Provided times must be unique as they're used as filenames.")
        for blob, time_utc in zip(blobs, times_utc):
            self.writeblob(blob, times_utc, sync_repo=False)
        repo.index.commit('')
        repo.remote().push()  # TODO: Pull and retry if there is a merge conflict.

    def readblobs(self, start_utc: Union[str, float, time.struct_time],
                  end_utc: Optional[Union[str, float, time.struct_time]] = None) -> Iterable[Blob]:
        self._pull_repo()
        start_utc = self._standardize_time_to_ns(start_utc)
        end_utc = self._standardize_time_to_ns(end_utc)
        for path in self._path.iterdir():
            if path.is_file():
                time_utc_ns = int(path.name)
                if start_utc <= time_utc_ns <= end_utc:
                    yield Blob(time_utc_ns, path.read_bytes())
