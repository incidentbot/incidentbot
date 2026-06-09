import jwt

from incidentbot.configuration.settings import settings

_ALGORITHM = "HS256"
_TOKEN_TYPE = "widget"


def generate_widget_token(room_id: str) -> str:
    """
    Generate a signed token scoped to a specific Matrix room.
    No expiry — token lifetime is tied to SECRET_KEY. Set a fixed SECRET_KEY
    in .env for persistence across restarts; leave it random for ephemeral use.
    """
    return jwt.encode(
        {"type": _TOKEN_TYPE, "room_id": room_id},
        settings.SECRET_KEY,
        algorithm=_ALGORITHM,
    )


def build_widget_url(
    base_url: str, path: str, room_id: str, widget_id: str
) -> str:
    token = generate_widget_token(room_id)
    return (
        f"{base_url.rstrip('/')}{path}"
        f"?roomId={room_id}"
        f"&widgetId={widget_id}"
        f"&userId=$userId"
        f"&matrix_user_id=$matrix_user_id"
        f"&token={token}"
    )


def verify_widget_token(token: str) -> dict:
    """
    Verify and decode a widget token. Raises jwt.InvalidTokenError on failure.
    Returns the decoded payload on success.
    """
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
    if payload.get("type") != _TOKEN_TYPE:
        raise jwt.InvalidTokenError("Not a widget token")
    return payload
