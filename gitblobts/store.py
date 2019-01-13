import calendar
import dataclasses
import importlib
import itertools
import logging
import math
import pathlib
import secrets
import time
import typing
from typing import Iterable, Iterator, List, Optional, Union

import cryptography.fernet
import dateparser
import git

import gitblobts.config as config
import gitblobts.exc as exc
from gitblobts.util import IntBaseEncoder, IntMerger

log = logging.getLogger(__name__)

Timestamp = Union[None, float, time.struct_time, str]


@dataclasses.dataclass
class Blob:
    time_utc_ns: int
    blob: bytes


def generate_key() -> bytes:
    return cryptography.fernet.Fernet.generate_key()


class Store:

    def __init__(self, path: Union[str, pathlib.Path], *, compression: Optional[str] = None,
                 key: Optional[bytes] = None):
        self._path = pathlib.Path(path)
        self._compression = importlib.import_module(compression) if compression else None  # e.g. bz2, gzip, lzma
        self._encryption = cryptography.fernet.Fernet(key) if key else None
        self._repo = git.Repo(self._path)  # Can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.
        self._int_merger = IntMerger(config.NUM_RANDOM_BITS)
        self._int_encoder = IntBaseEncoder('urlsafe_b64', signed=True)  # Don't use "b64" as it's not filesystem safe.
        self._log_state()
        self._check_repo()

    def _addblob(self, blob: bytes, time_utc: Union[None, Timestamp], *, push: bool) -> int:
        push_state = 'with' if push else 'without'
        log.info('Adding blob of length %s and time "%s" %s repository push.', len(blob), time_utc, push_state)
        if not isinstance(blob, bytes):
            raise exc.BlobTypeInvalid('Blob must be an instance of type bytes, but it is of '
                                      f'type {type(blob).__qualname__}.')

        repo = self._repo
        time_utc_ns = self._standardize_time_to_ns(time_utc)
        path = self._path / self._encode_time(time_utc_ns)  # Non-deterministic new file path.
        decoded_time_utc_ns = self._decode_time(path)
        assert_error = f'Time {time_utc_ns} was encoded to name {path.name} which was then decoded to a ' \
            f'different time {decoded_time_utc_ns}.'
        assert time_utc_ns == decoded_time_utc_ns, assert_error
        blob_original = blob
        blob = self._ingress_blob(blob)
        log.debug('Writing %s bytes of timestamp %s to file %s.', len(blob), time_utc_ns, path.name)
        path.write_bytes(blob)
        log.info('Wrote %s bytes of timestamp %s to file %s.', len(blob), time_utc_ns, path.name)

        repo.index.add([str(path)])
        log.info('Added file %s of timestamp %s to repository index.', path.name, time_utc_ns)
        if push:
            self._commit_and_push_repo()
        assert blob_original == self._egress_blob(path.read_bytes())
        log.info('Added blob of raw length %s and processed length %s of timestamp %s with name %s.',
                 len(blob_original), len(blob), time_utc_ns, path.name)
        return time_utc_ns

    def _check_repo(self) -> None:
        repo = self._repo
        log.debug('Checking repository.')
        if repo.bare:  # This is not implicit.
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

    def _compress_blob(self, blob: bytes) -> bytes:
        log.debug('Compressing blob.') if self._compression else log.debug('Skipping blob compression.')
        return self._compression.compress(blob) if self._compression else blob

    def _decode_time(self, filepath: pathlib.Path) -> int:
        filename: str = filepath.name
        encoded: bytes = filename.encode()
        merged: int = self._int_encoder.decode(encoded)
        time_utc_ns: int = self._int_merger.split(merged)[0]
        return time_utc_ns

    def _decompress_blob(self, blob: bytes) -> bytes:
        log.debug('Decompressing blob.') if self._compression else log.debug('Skipping blob decompression.')
        return self._compression.decompress(blob) if self._compression else blob

    def _decrypt_blob(self, blob: bytes) -> bytes:
        log.debug('Decrypting blob.') if self._encryption else log.debug('Skipping blob decryption.')
        return self._encryption.decrypt(blob) if self._encryption else blob

    def _egress_blob(self, blob: bytes) -> bytes:
        return self._decompress_blob(self._decrypt_blob(blob))

    def _encode_time(self, time_utc_ns: int) -> str:
        random: int = secrets.randbits(config.NUM_RANDOM_BITS)
        merged: int = self._int_merger.merge(time_utc_ns, random)
        encoded: bytes = self._int_encoder.encode(merged)
        filename: str = encoded.decode()
        return filename

    def _encrypt_blob(self, blob: bytes) -> bytes:
        log.debug('Encrypting blob.') if self._encryption else log.debug('Skipping blob encryption.')
        return self._encryption.encrypt(blob) if self._encryption else blob

    def _ingress_blob(self, blob: bytes) -> bytes:
        return self._encrypt_blob(self._compress_blob(blob))

    def _log_state(self) -> None:
        log.info('Number of random bits per filename is %s.', config.NUM_RANDOM_BITS)
        log.info('Repository path is "%s".', self._path)
        log.info('Compression is %s.',
                 f'enabled with {self._compression.__name__}' if self._compression else 'not enabled')
        log.info('Encryption is %s.',
                 f'enabled with {self._encryption.__class__.__name__}' if self._encryption else 'not enabled')

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

    def _standardize_time_to_ns(self, time_utc: Timestamp) -> int:
        def _convert_seconds_to_ns(seconds: Union[int, float]) -> int:
            return int(round(seconds * int(1e9)))

        if time_utc is None:
            return time.time_ns()
        elif time_utc == 0:  # OK as int since 0 seconds is 0 nanoseconds.
            return 0
        elif isinstance(time_utc, float):
            if not math.isfinite(time_utc):
                raise exc.TimeInvalid(f'Provided time "{time_utc}" must be finite and not NaN for use as a filename.')
            return _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, time.struct_time):
            time_utc = calendar.timegm(time_utc) if time_utc.tm_zone == 'GMT' else time.mktime(time_utc)
            # Note: Above conversion is per From-To-Use conversion table at https://docs.python.org/library/time.html
            return _convert_seconds_to_ns(time_utc)
        elif isinstance(time_utc, str):
            time_utc_input = time_utc
            time_utc = dateparser.parse(time_utc, settings={'TO_TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True,
                                                            'PREFER_DATES_FROM': 'past'})
            if time_utc is None:
                raise exc.TimeInvalid(f'Provided time "{time_utc_input}" could not be parsed. It provided as a string, '
                                      ' it must be parsable by dateparser.')
            return _convert_seconds_to_ns(time_utc.timestamp())
        else:
            annotation = typing.get_type_hints(self._standardize_time_to_ns)['time_utc']
            raise exc.TimeUnhandledType(f'Provided time "{time_utc}" is of an unhandled type "{type(time_utc)}". '
                                        f'It must be conform to {annotation}.')

    def addblob(self, blob: bytes, time_utc: Optional[Timestamp] = None) -> int:
        return self._addblob(blob, time_utc, push=True)

    def addblobs(self, blobs: Iterable[bytes], times_utc: Optional[Iterable[Timestamp]] = None) -> List[int]:
        log.info('Adding blobs.')
        if times_utc is None:
            times_utc = itertools.repeat(None)
        times_utc_ns = [self._addblob(blob, time_utc, push=False) for blob, time_utc in zip(blobs, times_utc)]
        self._commit_and_push_repo()
        log.info('Added %s blobs.', len(times_utc_ns))
        return times_utc_ns

    def getblobs(self, start_utc: Optional[Timestamp] = -math.inf, end_utc: Optional[Timestamp] = math.inf,
                 *, pull: Optional[bool] = False) -> Iterator[Blob]:
        pull_state = 'with' if pull else 'without'
        log.info('Getting blobs from "%s" to "%s" UTC %s repository pull.', start_utc, end_utc, pull_state)

        def standardize_time_to_ns(time_utc: Timestamp, *, default: float) -> Union[int, float]:
            if time_utc is None:
                return default
            if isinstance(time_utc, float):
                if math.isnan(time_utc):
                    return default
                if not math.isfinite(time_utc):
                    return time_utc
            return self._standardize_time_to_ns(time_utc)

        # Note: Either one of start_utc and end_utc can rightfully be smaller.
        start_utc = standardize_time_to_ns(start_utc, default=-math.inf)
        end_utc = standardize_time_to_ns(end_utc, default=math.inf)
        log.info('Getting blobs from %s to %s UTC %s repository pull.', start_utc, end_utc, pull_state)

        if pull:
            self._pull_repo()

        if start_utc <= end_utc:
            order = 'ascending'
        else:
            assert end_utc > start_utc
            order = 'descending'
            start_utc, end_utc = end_utc, start_utc

        time_path_tuples = ((self._decode_time(path), path) for path in self._path.iterdir() if path.is_file())
        time_path_tuples = ((t, p) for t, p in time_path_tuples if start_utc <= t <= end_utc)
        time_path_tuples = sorted(time_path_tuples, reverse=(order == 'descending'))
        log.debug('Yielding %s blobs in %s chronological order.', len(time_path_tuples), order)

        for time_utc_ns, path in time_path_tuples:
            log.debug('Yielding blob having timestamp %s and name %s.', time_utc_ns, path.name)
            yield Blob(time_utc_ns, self._egress_blob(path.read_bytes()))
            log.info('Yielded blob having timestamp %s and name %s.', time_utc_ns, path.name)
        log.info('Yielded %s blobs.', len(time_path_tuples))
