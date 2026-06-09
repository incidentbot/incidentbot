from collections import deque

from incidentbot.logging import logger
from incidentbot.matrix import commands
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.util.widget_token import build_widget_url


class MatrixHandler:
    """
    Listens for Matrix room events and dispatches !incident commands.

    Delegates the sync loop to MatrixClient; this class handles routing only.
    On start, registers the incident creation widget in the digest room so users
    never need to type a command to create incidents — they open the widget panel.
    """

    def __init__(
        self,
        matrix_client,
        digest_room_id: str,
        widget_base_url: str | None = None,
    ):
        self._client = matrix_client
        self._digest_room_id = digest_room_id
        self._widget_base_url = widget_base_url
        self._seen_events: deque[str] = deque(maxlen=10_000)

    def start(self) -> None:
        """Start the background sync loop and register the digest room widget."""
        if self._client.join_room(self._digest_room_id):
            logger.info("joined matrix digest room", room_id=self._digest_room_id)
        if self._widget_base_url:
            self._register_digest_widget()
            self._reconcile_incident_room_widgets()
        self._client.start_sync(self._on_event)
        logger.info("matrix sync loop started")

    def _register_digest_widget(self) -> None:
        widget_url = build_widget_url(
            self._widget_base_url,
            "/widget/incident",
            self._digest_room_id,
            "incidentbot-create",
        )
        try:
            self._client.register_widget(
                room_id=self._digest_room_id,
                widget_id="incidentbot-create",
                name="Create Incident",
                url=widget_url,
            )
            logger.info(
                "incident creation widget registered in digest room", room_id=self._digest_room_id
            )
        except Exception as exc:
            logger.exception("failed to register digest room widget", error=exc)

    def _reconcile_incident_room_widgets(self) -> None:
        incidents = IncidentDatabaseInterface.list_all() or []
        refreshed = 0

        for incident in incidents:
            if not incident.channel_id:
                continue

            widget_url = build_widget_url(
                self._widget_base_url,
                "/widget/incident-room",
                incident.channel_id,
                "incidentbot-controls",
            )
            try:
                self._client.register_widget(
                    room_id=incident.channel_id,
                    widget_id="incidentbot-controls",
                    name="Incident Controls",
                    url=widget_url,
                )
                refreshed += 1
            except Exception as exc:
                logger.exception(
                    "failed to refresh incident controls widget", channel_id=incident.channel_id, error=exc
                )

        logger.info("refreshed matrix incident room widgets", count=refreshed)

    async def _on_event(self, room_id: str, event) -> None:
        event_id = getattr(event, "event_id", None)
        if event_id in self._seen_events:
            return
        if event_id:
            self._seen_events.append(event_id)

        sender = getattr(event, "sender", "")
        if sender == self._client.user_id:
            return

        body = getattr(event, "body", "")
        parsed = commands.parse(body)
        if parsed is None:
            return

        subcommand, args = parsed
        logger.info("matrix command", subcommand=subcommand, sender=sender, room_id=room_id)

        try:
            match subcommand:
                case "help":
                    await commands.handle_help(
                        room_id, self._client, self._digest_room_id
                    )
                case "status":
                    await commands.handle_status(room_id, self._client)
                case "join":
                    await commands.handle_join(
                        room_id, args, sender, self._client
                    )
                case "severity":
                    await commands.handle_severity(room_id, args, self._client)
                case "resolve":
                    await commands.handle_resolve(room_id, args, self._client)
                case _:
                    await self._client.send_text_async(
                        room_id,
                        f"Unknown command '{subcommand}'. Try !incident help",
                    )
        except Exception as exc:
            logger.exception("error handling matrix command", subcommand=subcommand, error=exc)
            await self._client.send_text_async(room_id, f"Error: {exc}")
