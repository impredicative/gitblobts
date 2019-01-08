class StoreError(Exception):
    pass


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
