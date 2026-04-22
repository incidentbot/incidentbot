from incidentbot.logging import logger
from incidentbot.matrix import commands
from incidentbot.util.widget_token import generate_widget_token


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
        self._seen_events: set[str] = set()

    def start(self) -> None:
        """Start the background sync loop and register the digest room widget."""
        if self._widget_base_url:
            self._register_digest_widget()
        self._client.start_sync(self._on_event)
        logger.info("Matrix sync loop started")

    def _register_digest_widget(self) -> None:
        token = generate_widget_token(self._digest_room_id)
        widget_url = (
            f"{self._widget_base_url.rstrip('/')}/widget/incident"
            f"?roomId={self._digest_room_id}&widgetId=incidentbot-create&token={token}"
        )
        try:
            self._client.register_widget(
                room_id=self._digest_room_id,
                widget_id="incidentbot-create",
                name="Create Incident",
                url=widget_url,
            )
            logger.info(
                f"Incident creation widget registered in digest room {self._digest_room_id}"
            )
        except Exception as exc:
            logger.error(f"Failed to register digest room widget: {exc}")

    async def _on_event(self, room_id: str, event) -> None:
        event_id = getattr(event, "event_id", None)
        if event_id in self._seen_events:
            return
        if event_id:
            self._seen_events.add(event_id)

        sender = getattr(event, "sender", "")
        if sender == self._client.user_id:
            return

        body = getattr(event, "body", "")
        parsed = commands.parse(body)
        if parsed is None:
            return

        subcommand, args = parsed
        logger.info(f"Matrix command '{subcommand}' from {sender} in {room_id}")

        try:
            match subcommand:
                case "help":
                    commands.handle_help(room_id, self._client, self._digest_room_id)
                case "status":
                    commands.handle_status(room_id, self._client)
                case "join":
                    commands.handle_join(room_id, args, sender, self._client)
                case "severity":
                    commands.handle_severity(room_id, args, self._client)
                case "resolve":
                    commands.handle_resolve(room_id, args, self._client)
                case _:
                    self._client.send_text(
                        room_id,
                        f"Unknown command '{subcommand}'. Try !incident help",
                    )
        except Exception as exc:
            logger.error(f"Error handling Matrix command '{subcommand}': {exc}")
            self._client.send_text(room_id, f"Error: {exc}")
