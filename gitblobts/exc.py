import time


class StoreError(Exception):
    def __init__(self, msg: str):
        time.sleep(.01)  # Provides time for prior log messages to flush.
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


class TimeError(StoreError):
    pass


class TimeInvalid(TimeError):
    pass


class TimeNotUTC(TimeError):
    pass


class TimeUnhandledType(TimeError):
    pass


class RepoTransportError(RepoError):
    pass


class RepoPullError(RepoTransportError):
    pass


class RepoPushError(RepoTransportError):
    pass
