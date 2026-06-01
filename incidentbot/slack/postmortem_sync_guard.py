from threading import Lock


_sync_lock = Lock()
_channels_in_progress: set[str] = set()


def begin_postmortem_sync(channel_id: str) -> bool:
    with _sync_lock:
        if channel_id in _channels_in_progress:
            return False
        _channels_in_progress.add(channel_id)
        return True


def end_postmortem_sync(channel_id: str) -> None:
    with _sync_lock:
        _channels_in_progress.discard(channel_id)


def reset_postmortem_sync_guard() -> None:
    with _sync_lock:
        _channels_in_progress.clear()
