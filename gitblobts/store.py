import calendar
import dataclasses
import itertools
import logging
import pathlib
import time
import typing
from typing import Iterable, List, Optional, Union

import git

import gitblobts.config as config
import gitblobts.exc as exc

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Blob:
    time_utc_ns: int
    blob: bytes


class Store:

    def __init__(self, path: Union[str, pathlib.Path]):
        self._path = pathlib.Path(path)
        self._repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        log.info('Repository path is "%s".', self._path)
        self._check_repo()
        self._pull_repo()

    def _check_repo(self) -> None:
        repo = self.repo
        log.debug('Checking repository.')
        if repo.bare:  # This is not implicit.
            log.error('Repository is bare.')
            raise exc.RepoBare('Repository must not be bare.')
        # if repo.active_branch.name != 'master':
        #     raise exc.RepoBranchNotMaster('Active repository branch must be "master".')
        if repo.is_dirty():
            raise exc.RepoDirty('Repository must not be dirty.')
        if repo.untracked_files:
            names = '\n'.join(repo.untracked_files)
            raise exc.RepoHasUntrackedFiles(f'Repository must not have any untracked files. It has these:\n{names}')
        if not repo.remotes:
            raise exc.RepoRemoteNotAdded('Repository must have a remote.')
        if not repo.remote().exists():
            raise exc.RepoRemoteNotExist('Repository remote must exist.')
        # if not self._repo.remote().name == 'origin':
        #     raise exc.RemoteRepoError('Repository remote name must be "origin".')
        log.info('Finished checking repository.')

    def _pull_repo(self) -> None:
        remote = self._repo.remote()
        name = remote.name
        log.debug('Pulling from repository remote "%s".', name)
        try:
            remote.pull()
        except git.exc.GitCommandError:  # Could be due to no push yet.
            log.warning('Failed to pull from repository remote "%s".', name)
            pass
        else:
            log.info('Pulled from repository remote "%s".', name)

    def _push_repo(self) -> None:
        repo = self._repo
        index = repo.index
        if not index.entries:
            log.warning('There is no entry in the repository index to commit.')
        else:
            log.debug('Committing repository index having %s entries.', len(index))
            self._repo.index.commit('')
            log.info('Committed repository index having %s entries.', len(index))

        remote = repo.remote
        name = remote.name
        log.debug('Pushing to repository remote "%s".', name)
        remote.push()  # TODO: In case of a merge conflict, pull and retry push.
        log.info('Pushed to repository remote "%s".', name)

    def _standardize_time_to_ns(self, time_utc: Union[None, float, time.struct_time, str]) -> int:
        def _convert_seconds_to_ns(seconds: Union[int, float]) -> int:
            return int(round(seconds * int(1e9)))
        if time_utc is None:
            return time.time_ns()
        elif isinstance(float, time_utc):
            return _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, time.struct_time):
            if time_utc.tm_zone != 'UTC':
                raise exc.TimeNotUTC(f"Provided timezone must be UTC, but it's {time_utc.tm_zone}.")
            return _convert_seconds_to_ns(calendar.timegm(time_utc))
        elif isinstance(str, time_utc):
            return 'CONVERT SLANG UTC TIME'  # TODO: Convert slang UTC time.
        else:
            annotation = typing.get_type_hints(self.writeblob)['time_utc']
            raise exc.TimeUnhandledType(f'Provided time is of an unhandled type "{type(time_utc)}. '
                                         f'It must be conform to {annotation}.')

    def writeblob(self, blob: bytes, time_utc: Optional[float] = None, sync_repo: Optional[bool] = True) -> int:
        log.debug('Writing blob of length %s %s repository sync.', len(blob), 'with' if sync_repo else 'without')
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

        log.debug('Writing %s bytes to file %s.', len(blob), path.name)
        path.write_bytes(blob)
        log.info('Finished writing %s bytes to file %s.', len(blob), path.name)

        repo.index.add([path])
        log.info('Added file %s to repository index.', path.name)
        if sync_repo:
            # TODO: Perhaps consider using a name arg as the commit message.
            self._push_repo()
        assert blob == path.read_bytes()
        log.info('Finished writing blob of length %s with name %s.', len(blob), path.name)
        return time_utc_ns

    def writeblobs(self, blobs: Iterable[bytes], times_utc: Optional[Iterable[float]] = None) -> List[int]:
        log.debug('Writing blobs.')
        self._pull_repo()  # TODO: Consider pull only if there is a merge conflict.
        if times_utc is None:
            times_utc = []
        times_utc_ns = [self.writeblob(blob, time_utc, sync_repo=False) for blob, time_utc in
                        itertools.zip_longest(blobs, times_utc)]
        self._push_repo()
        log.info('Finished writing %s blobs.', len(times_utc_ns))
        return times_utc_ns

    def readblobs(self, start_utc: Optional[Union[float, time.struct_time, str]] = None,
                  end_utc: Optional[Union[float, time.struct_time, str]] = None) -> Iterable[Blob]:
        log.debug('Reading blobs from "%s" UTC to "%s" UTC.', start_utc, end_utc)
        self._pull_repo()
        start_utc = self._standardize_time_to_ns(start_utc) if start_utc is not None else 0
        end_utc = self._standardize_time_to_ns(end_utc) if end_utc is not None else float('inf')
        log.debug('Reading blobs from "%s" UTC to "%s" UTC.', start_utc, end_utc)

        paths = (path for path in self._path.iterdir() if path.is_file())
        if start_utc <= end_utc:
            order = 'ascending'
            times_utc_ns = (int(path.name) for path in paths if start_utc <= int(path.name) <= end_utc)
            times_utc_ns = sorted(times_utc_ns)
        else:
            order = 'descending'
            times_utc_ns = (int(path.name) for path in paths if end_utc <= int(path.name) <= start_utc)
            times_utc_ns = sorted(times_utc_ns, reverse=True)
        log.debug('Yielding %s blobs in %s chronological order.', len(times_utc_ns), order)

        for time_utc_ns in times_utc_ns:
            path = self._path / str(time_utc_ns)
            log.debug('Yielding blob %s.', path.name)
            yield Blob(time_utc_ns, path.read_bytes())
            log.info('Yielded blob %s.', path.name)
        log.info('Yielded %s blobs.', len(times_utc_ns))
