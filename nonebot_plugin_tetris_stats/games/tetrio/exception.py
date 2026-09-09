from ...utils.exception import NeedCatchError


class LeagueSnapshotNotFoundError(NeedCatchError):
    """No persisted TETR.IO league snapshot is available."""
