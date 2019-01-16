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
    """Instances of this class are returned by ``Store.getblobs``.

    This class is not meant to be initialized otherwise.
    """
    time_utc_ns: int
    blob: bytes


def generate_key() -> bytes:
    """Return a random new `Fernet <https://cryptography.io/en/stable/fernet/>`_ key.

    The key should be stored safely. If it is lost, it will not be possible to decrypt encrypted blobs.
    If anyone else gains access to it, it can be used to decrypt blobs.

    An example of a generated key is ``b'NrYgSuzXVRWtarWcczyuwFs6vZftN1rnlzZtGDaV7iE='``.

    Returns
    -------
    bytes
        Key used for encryption and decryption.
    """
    return cryptography.fernet.Fernet.generate_key()


class Store:
    """Initialize the interface to a preexisting cloned git repository."""

    def __init__(self, path: Union[str, pathlib.Path], *, compression: Optional[str] = None,
                 key: Optional[bytes] = None):
        self._path: pathlib.Path = pathlib.Path(path)
        self._compression = importlib.import_module(compression) if compression else None  # e.g. bz2, gzip, lzma
        self._encryption: cryptography.fernet.Fernet = cryptography.fernet.Fernet(key) if key else None
        self._repo: git.Repo = git.Repo(self._path)
        # The above line can raise git.exc.NoSuchPathError or git.exc.InvalidGitRepositoryError.

        self._int_merger: IntMerger = IntMerger(config.NUM_RANDOM_BITS)
        self._file_stem_encoder: IntBaseEncoder = IntBaseEncoder(config.FILENAME_ENCODING, signed=True)
        self._file_suffix_encoder: IntBaseEncoder = IntBaseEncoder(config.FILENAME_ENCODING, signed=False)
        self._file_suffix_encoded: str = self._file_suffix_encoder.encode(config.FILE_VERSION).decode()

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
        path = self._path / self._encode_name(time_utc_ns)  # Non-deterministic new file path.
        decoded_time_utc_ns = self._decode_name(path)
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
        remote = repo.remote()
        remote_name = remote.name
        branch_name = repo.active_branch.name

        # Note: repo.index.entries was observed to also include unpushed files in addition to uncommitted files.
        log.debug('Committing repository index in active branch "%s".', branch_name)
        self._repo.index.commit('')
        log.info('Committed repository index in active branch "%s".', branch_name)

        def _is_pushed(push_info: git.remote.PushInfo) -> bool:
            valid_flags = {push_info.FAST_FORWARD, push_info.NEW_HEAD}  # UP_TO_DATE flag is intentionally skipped.
            return push_info.flags in valid_flags  # This check can require the use of & instead.

        push_desc = f'active branch "{branch_name}" to repository remote "{remote_name}"'
        log.debug('Pushing %s.', push_desc)
        try:
            push_info = remote.push()[0]
        except git.exc.GitCommandError:  # Could be due to no upstream branch.
            log.warning('Failed to push %s. This could be due to no matching upstream branch.', push_desc)
            log.info('Reattempting to push %s using a lower-level command which also sets upstream branch.', push_desc)
            push_output = repo.git.push('--set-upstream', remote_name, branch_name)
            log.info('Push output was: %s', push_output)
            expected_msg = f"Branch '{branch_name}' set up to track remote branch '{branch_name}' from '{remote_name}'."
            if push_output != expected_msg:
                raise exc.RepoPushError(f'Failed to push {push_desc}.')
        else:
            is_pushed = _is_pushed(push_info)
            logger = log.debug if is_pushed else log.warning
            logger('Push flags were %s and message was "%s".', push_info.flags, push_info.summary.strip())
            if not is_pushed:
                log.warning('Failed first attempt at pushing %s. A pull will be performed.', push_desc)
                self._pull_repo()
                log.info('Reattempting to push %s.', push_desc)
                push_info = remote.push()[0]
                is_pushed = _is_pushed(push_info)
                logger = log.debug if is_pushed else log.error
                logger('Push flags were %s and message was "%s".', push_info.flags, push_info.summary.strip())
                if not is_pushed:
                    raise exc.RepoPushError(f'Failed to push {push_desc} despite a pull.')
        log.info('Pushed %s.', push_desc)

    def _compress_blob(self, blob: bytes) -> bytes:
        if self._compression:
            log.debug('Compressing blob.')
            return self._compression.compress(blob)  # type: ignore
        log.debug('Skipping blob compression.')
        return blob

    def _decode_name(self, filepath: pathlib.Path) -> int:
        _version: bytes = filepath.suffix.encode()
        version: int = self._file_suffix_encoder.decode(_version)
        if version > config.FILE_VERSION:
            msg = f'Blob with name {filepath.name} is of file format version {version} which is not supported. ' \
                f'The highest supported version is {config.FILE_VERSION}. Consider a newer version of this package.'
            raise exc.BlobVersionUnsupported(msg)
        _stem: bytes = filepath.stem.encode()
        stem: int = self._file_stem_encoder.decode(_stem)
        time_utc_ns: int = self._int_merger.split(stem)[0]
        return time_utc_ns

    def _decompress_blob(self, blob: bytes) -> bytes:
        if self._compression:
            log.debug('Decompressing blob.')
            return self._compression.decompress(blob)  # type: ignore
        log.debug('Skipping blob decompression.')
        return blob

    def _decrypt_blob(self, blob: bytes) -> bytes:
        if self._encryption:
            log.debug('Decrypting blob.')
            return self._encryption.decrypt(blob)
        log.debug('Skipping blob decryption.')
        return blob

    def _egress_blob(self, blob: bytes) -> bytes:
        return self._decompress_blob(self._decrypt_blob(blob))

    def _encode_name(self, time_utc_ns: int) -> str:
        random: int = secrets.randbits(config.NUM_RANDOM_BITS)
        _stem: int = self._int_merger.merge(time_utc_ns, random)
        stem: str = self._file_stem_encoder.encode(_stem).decode()
        filename: str = f'{stem}.{self._file_suffix_encoded}'
        return filename

    def _encrypt_blob(self, blob: bytes) -> bytes:
        if self._encryption:
            log.debug('Encrypting blob.')
            return self._encryption.encrypt(blob)
        log.debug('Skipping blob encryption.')
        return blob

    def _ingress_blob(self, blob: bytes) -> bytes:
        return self._encrypt_blob(self._compress_blob(blob))

    def _log_state(self) -> None:
        log.info('Number of random bits per filename is %s.', config.NUM_RANDOM_BITS)
        log.info('Repository path is "%s".', self._path)
        log.info('Compression is %s.',
                 f'enabled with {self._compression.__name__}' if self._compression else 'not enabled')
        log.info('Encryption is %s.',
                 f'enabled with {self._encryption.__class__.__name__}' if self._encryption else 'not enabled')
        log.info('File version for new files is %s, encoded to filename suffix %s.',
                 config.FILE_VERSION, self._file_suffix_encoded)

    def _pull_repo(self) -> None:
        repo = self._repo
        remote = repo.remote()
        remote_name = remote.name
        branch_name = repo.active_branch.name

        def _is_pulled(pull_info: git.remote.FetchInfo) -> bool:
            valid_flags = {pull_info.HEAD_UPTODATE, pull_info.FAST_FORWARD}
            return pull_info.flags in valid_flags  # This check can require the use of & instead.

        pull_desc = f'into active branch "{branch_name}" from repository remote "{remote_name}"'
        log.debug('Pulling %s.', pull_desc)
        try:
            pull_info = remote.pull()[0]
        except git.exc.GitCommandError:  # Could be due to no upstream branch.
            log.warning('Failed to pull %s. This could be due to no matching upstream branch.', pull_desc)
        else:
            is_pulled = _is_pulled(pull_info)
            logger = log.debug if is_pulled else log.error
            logger('Pull flags were %s.', pull_info.flags)
            if not is_pulled:
                raise exc.RepoPullError(f'Failed to pull {pull_desc}.')
            log.info('Pulled %s.', pull_desc)

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
            time_utc_dt = dateparser.parse(time_utc, settings={'TO_TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True,
                                                            'PREFER_DATES_FROM': 'past'})
            if time_utc_dt is None:
                raise exc.TimeInvalid(f'Provided time "{time_utc}" could not be parsed. It provided as a string, '
                                      'it must be parsable by dateparser.')
            return _convert_seconds_to_ns(time_utc_dt.timestamp())
        else:
            annotation = typing.get_type_hints(self._standardize_time_to_ns)['time_utc']
            raise exc.TimeUnhandledType(f'Provided time "{time_utc}" is of an unhandled type "{type(time_utc)}". '
                                        f'It must be conform to {annotation}.')

    def addblob(self, blob: bytes, time_utc: Optional[Timestamp] = None) -> int:
        """Add a blob and return its corresponding nanosecond timestamp."""
        return self._addblob(blob, time_utc, push=True)

    def addblobs(self, blobs: Iterable[bytes], times_utc: Optional[Iterable[Timestamp]] = None) -> List[int]:
        """Add multiple blobs and return a list of their corresponding nanosecond timestamps."""
        log.info('Adding blobs.')
        if times_utc is None:
            times_utc = itertools.repeat(None)
        times_utc_ns = [self._addblob(blob, time_utc, push=False) for blob, time_utc in zip(blobs, times_utc)]
        if times_utc_ns:
            self._commit_and_push_repo()
        log.info('Added %s blobs.', len(times_utc_ns))
        return times_utc_ns

    def getblobs(self, start_utc: Optional[Timestamp] = -math.inf, end_utc: Optional[Timestamp] = math.inf,
                 *, pull: Optional[bool] = False) -> Iterator[Blob]:
        """Yield ``Blob`` objects matching the specified time range."""
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
            order = 'descending'
            start_utc, end_utc = end_utc, start_utc

        time_path_tuples = ((self._decode_name(path), path) for path in self._path.iterdir() if path.is_file())
        time_path_tuples = ((t, p) for t, p in time_path_tuples if start_utc <= t <= end_utc)
        time_path_tuples = sorted(time_path_tuples, reverse=(order == 'descending'))  # type: ignore
        log.debug('Yielding %s blobs in %s chronological order.', len(time_path_tuples), order)  # type: ignore

        for time_utc_ns, path in time_path_tuples:
            log.debug('Yielding blob having timestamp %s and name %s.', time_utc_ns, path.name)
            yield Blob(time_utc_ns, self._egress_blob(path.read_bytes()))
            log.info('Yielded blob having timestamp %s and name %s.', time_utc_ns, path.name)
        log.info('Yielded %s blobs.', len(time_path_tuples))  # type: ignore
