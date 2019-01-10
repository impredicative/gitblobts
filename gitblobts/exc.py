import logging

log = logging.getLogger(__name__)


class StoreError(Exception):
    def __init__(self, msg: str):
        log.error(msg)
        super().__init__(msg)


class RepoError(StoreError):
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


class BlobError(StoreError):
    pass


class BlobTypeInvalid(BlobError):
    pass


class TimeError(StoreError):
    pass


class TimeInvalid(TimeError):
    pass


class TimeUnhandledType(TimeError):
    pass


class RepoTransportError(RepoError):
    pass


class RepoPullError(RepoTransportError):
    pass


class RepoPushError(RepoTransportError):
    pass
