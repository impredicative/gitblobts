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

    def _check_repo(self) -> None:
        repo = self._repo
        log.debug('Checking repository.')
        if repo.bare:  # This is not implicit.
            log.error('Repository is bare.')
            raise exc.RepoBare('Repository must not be bare.')
        # if repo.active_branch.name != 'master':
        #     raise exc.RepoBranchNotMaster('Active repository branch must be "master".')
        log.info('Active repository branch is "%s".', repo.active_branch.name)
        if repo.is_dirty():
            raise exc.RepoDirty('Repository must not be dirty.')
        if repo.untracked_files:
            names = '\n'.join(repo.untracked_files)
            raise exc.RepoHasUntrackedFiles(f'Repository must not have any untracked files. It has these:\n{names}')
        if not repo.remotes:
            raise exc.RepoRemoteNotAdded('Repository must have a remote.')
        if not repo.remote().exists():
            raise exc.RepoRemoteNotExist('Repository remote must exist.')
        # if not repo.remote().name == 'origin':
        #     raise exc.RemoteRepoError('Repository remote name must be "origin".')
        log.info('Repository remote is "%s".', repo.remote().name)
        log.info('Finished checking repository.')

    def _pull_repo(self) -> None:
        remote = self._repo.remote()
        name = remote.name

        def _is_pulled(pull_info: git.remote.FetchInfo) -> bool:
            valid_flags = {pull_info.HEAD_UPTODATE, pull_info.FAST_FORWARD}
            return pull_info.flags in valid_flags  # This check can require the use of & instead.

        log.debug('Pulling from repository remote "%s".', name)
        try:
            pull_info = remote.pull()[0]
        except git.exc.GitCommandError:  # Could be due to no push ever.
            log.warning('Failed to pull from repository remote "%s".', name)
        else:
            is_pulled = _is_pulled(pull_info)
            logger = log.debug if is_pulled else log.error
            logger('Pull flags were %s.', pull_info.flags)
            if not is_pulled:
                raise exc.RepoPullError(f'Failed to pull from repository remote "{remote.name}".')
            log.info('Pulled from repository remote "%s".', name)

    def _commit_and_push_repo(self) -> None:
        repo = self._repo
        # Note: repo.index.entries was observed to also include unpushed files in addition to uncommitted files.
        log.debug('Committing repository index.')
        self._repo.index.commit('')
        log.info('Committed repository index.')

        def _is_pushed(push_info: git.remote.PushInfo) -> bool:
            return push_info.flags == push_info.FAST_FORWARD  # This check can require the use of & instead.

        remote = repo.remote()
        log.debug('Pushing to repository remote "%s".', remote.name)
        push_info = remote.push()[0]
        is_pushed = _is_pushed(push_info)
        logger = log.debug if is_pushed else log.warning
        logger('Push flags were %s and message was "%s".', push_info.flags, push_info.summary.strip())
        if not is_pushed:
            log.warning('Failed first attempt at pushing to repository remote "%s". A pull will be performed.',
                        remote.name)
            self._pull_repo()
            log.info('Reattempting to push to repository remote "%s".', remote.name)
            push_info = remote.push()[0]
            is_pushed = _is_pushed(push_info)
            logger = log.debug if is_pushed else log.error
            logger('Push flags were %s and message was "%s".', push_info.flags, push_info.summary.strip())
            if not is_pushed:
                raise exc.RepoPushError(f'Failed to push to repository remote "{remote.name}" despite a pull.')
        log.info('Pushed to repository remote "%s".', remote.name)

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

    def addblob(self, blob: bytes, time_utc: Optional[float] = None, *, sync_repo: Optional[bool] = True) -> int:
        log.info('Adding blob of length %s %s repository sync.', len(blob), 'with' if sync_repo else 'without')
        repo = self._repo
        time_utc_ns = self._standardize_time_to_ns(time_utc)

        while True:  # Use filename that doesn't already exist. Avoid overwriting existing file.
            path = self._path / str(time_utc_ns)
            if path.exists():
                time_utc_ns += 1
            else:
                break

        log.debug('Writing %s bytes to file %s.', len(blob), path.name)
        path.write_bytes(blob)
        log.info('Finished writing %s bytes to file %s.', len(blob), path.name)

        repo.index.add([str(path)])
        log.info('Added file %s to repository index.', path.name)
        if sync_repo:
            # TODO: Perhaps consider using a name arg as the commit message.
            self._commit_and_push_repo()
        assert blob == path.read_bytes()
        log.info('Added blob of length %s with name %s.', len(blob), path.name)
        return time_utc_ns

    def addblobs(self, blobs: Iterable[bytes], times_utc: Optional[Iterable[float]] = None) -> List[int]:
        log.info('Adding blobs.')
        if times_utc is None:
            times_utc = []
        times_utc_ns = [self.writeblob(blob, time_utc, sync_repo=False) for blob, time_utc in
                        itertools.zip_longest(blobs, times_utc)]
        self._commit_and_push_repo()
        log.info('Added %s blobs.', len(times_utc_ns))
        return times_utc_ns

    def getblobs(self, start_utc: Optional[Union[float, time.struct_time, str]] = None,
                  end_utc: Optional[Union[float, time.struct_time, str]] = None) -> Iterable[Blob]:
        log.info('Getting blobs from "%s" UTC to "%s" UTC.', start_utc, end_utc)
        self._pull_repo()
        start_utc = self._standardize_time_to_ns(start_utc) if start_utc is not None else 0
        end_utc = self._standardize_time_to_ns(end_utc) if end_utc is not None else float('inf')
        log.info('Getting blobs from "%s" UTC to "%s" UTC.', start_utc, end_utc)

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
