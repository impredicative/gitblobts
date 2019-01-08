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


class RepoTransportError(RepoError):
    pass


class RepoPushError(RepoTransportError):
    pass
