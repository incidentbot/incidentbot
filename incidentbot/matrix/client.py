import asyncio
import threading

from incidentbot.logging import logger
from nio import AsyncClient, RoomCreateResponse, RoomSendResponse


class MatrixClient:
    """
    Wraps matrix-nio AsyncClient with a sync-friendly interface.

    Runs a dedicated asyncio event loop in a background daemon thread so that
    synchronous callers (e.g. incident/core.py) can submit coroutines without
    needing to manage their own event loop.
    """

    def __init__(
        self,
        homeserver: str,
        user_id: str,
        access_token: str,
        device_id: str = "INCIDENTBOT",
    ):
        self.user_id = user_id
        self._client = AsyncClient(homeserver, user_id)
        self._client.access_token = access_token
        self._client.device_id = device_id

        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, daemon=True, name="matrix-io"
        )
        self._thread.start()

    def _run(self, coro, timeout: int = 30):
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    # ------------------------------------------------------------------
    # Room operations
    # ------------------------------------------------------------------

    def create_room(self, name: str, topic: str = "", private: bool = False) -> dict:
        """Create a Matrix room. Returns dict with 'id' and 'name'."""
        resp = self._run(
            self._client.room_create(
                name=name,
                topic=topic,
                is_direct=False,
                invite=[],
                initial_state=[
                    {
                        "type": "m.room.join_rules",
                        "content": {
                            "join_rule": "invite" if private else "public"
                        },
                    }
                ],
            )
        )
        if isinstance(resp, RoomCreateResponse):
            return {"id": resp.room_id, "name": name}
        logger.error(f"Matrix room creation failed: {resp}")
        return {}

    def set_room_topic(self, room_id: str, topic: str) -> None:
        self._run(
            self._client.room_put_state(
                room_id, "m.room.topic", {"topic": topic}
            )
        )

    def send_text(self, room_id: str, text: str, html: str | None = None) -> str:
        """Send a message. Returns event_id on success, empty string on failure."""
        content: dict = {"msgtype": "m.text", "body": text}
        if html:
            content["format"] = "org.matrix.custom.html"
            content["formatted_body"] = html
        resp = self._run(
            self._client.room_send(room_id, "m.room.message", content)
        )
        if isinstance(resp, RoomSendResponse):
            return resp.event_id
        logger.error(f"Matrix send_text failed for {room_id}: {resp}")
        return ""

    def pin_message(self, room_id: str, event_id: str) -> None:
        """Append event_id to the room's pinned events state."""
        async def _pin():
            resp = await self._client.room_get_state_event(
                room_id, "m.room.pinned_events", ""
            )
            current = getattr(resp, "content", {}).get("pinned", [])
            if event_id not in current:
                current.append(event_id)
            await self._client.room_put_state(
                room_id, "m.room.pinned_events", {"pinned": current}
            )

        self._run(_pin())

    def invite_user(self, room_id: str, user_id: str) -> None:
        self._run(self._client.room_invite(room_id, user_id))

    def get_display_name(self, user_id: str) -> str:
        resp = self._run(self._client.get_displayname(user_id))
        return getattr(resp, "displayname", None) or user_id

    def register_widget(self, room_id: str, widget_id: str, name: str, url: str) -> None:
        """Register a Matrix widget in a room via im.vector.modular.widgets state."""
        self._run(
            self._client.room_put_state(
                room_id,
                "im.vector.modular.widgets",
                {
                    "type": "m.custom",
                    "name": name,
                    "url": url,
                    "id": widget_id,
                },
                state_key=widget_id,
            )
        )

    # ------------------------------------------------------------------
    # Sync loop (event listener)
    # ------------------------------------------------------------------

    async def _sync_loop(self, on_message):
        """Continuous sync loop. Calls on_message for each m.room.message event."""
        while True:
            try:
                resp = await self._client.sync(timeout=30000, full_state=False)
                for room_id, room in resp.rooms.join.items():
                    for event in room.timeline.events:
                        if hasattr(event, "body"):
                            await on_message(room_id, event)
            except Exception as exc:
                logger.error(f"Matrix sync error: {exc}")
                await asyncio.sleep(5)

    def start_sync(self, on_message) -> None:
        """Start the sync loop in the background event loop (non-blocking)."""
        asyncio.run_coroutine_threadsafe(self._sync_loop(on_message), self._loop)
