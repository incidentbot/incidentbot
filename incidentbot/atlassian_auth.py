from functools import lru_cache
from math import isfinite
from re import fullmatch
from threading import Lock
from time import monotonic
from typing import Any
from urllib.parse import urlparse

import requests
from requests.auth import AuthBase

from incidentbot.configuration.settings import Settings


class AtlassianOAuth(AuthBase):
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = Lock()

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        url = urlparse(request.url)
        if url.scheme != "https" or url.netloc != "api.atlassian.com":
            raise ValueError("Atlassian OAuth requires the API gateway")

        with self._lock:
            now = monotonic()
            if self._token is None or now >= self._expires_at:
                try:
                    response = requests.post(
                        "https://auth.atlassian.com/oauth/token",
                        data={
                            "grant_type": "client_credentials",
                            "client_id": self.client_id,
                            "client_secret": self.client_secret,
                        },
                        timeout=10,
                        allow_redirects=False,
                    )
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"Atlassian OAuth token request failed (HTTP {response.status_code})"
                        )
                    payload = response.json()
                except (requests.RequestException, ValueError):
                    raise RuntimeError("Unable to obtain Atlassian OAuth access token") from None

                token = payload.get("access_token") if isinstance(payload, dict) else None
                expires = payload.get("expires_in") if isinstance(payload, dict) else None
                token_type = payload.get("token_type") if isinstance(payload, dict) else None
                if (
                    not isinstance(token, str)
                    or not fullmatch(r"[A-Za-z0-9._~+/-]+=*", token)
                    or not isinstance(token_type, str)
                    or token_type.lower() != "bearer"
                    or isinstance(expires, bool)
                    or not isinstance(expires, (int, float))
                    or not isfinite(expires)
                    or expires <= 0
                ):
                    raise RuntimeError("Invalid Atlassian OAuth token response")

                self._token = token
                self._expires_at = now + expires - min(30, expires / 10)
            request.headers["Authorization"] = f"Bearer {self._token}"
        return request


@lru_cache(maxsize=1)
def _oauth_auth(client_id: str, client_secret: str) -> AtlassianOAuth:
    return AtlassianOAuth(client_id, client_secret)


def client_auth(settings: Settings) -> dict[str, Any]:
    if settings.ATLASSIAN_CLIENT_ID:
        session = requests.Session()
        session.auth = _oauth_auth(settings.ATLASSIAN_CLIENT_ID, settings.ATLASSIAN_CLIENT_SECRET)
        return {"session": session}
    return {"username": settings.ATLASSIAN_API_USERNAME, "password": settings.ATLASSIAN_API_TOKEN}
