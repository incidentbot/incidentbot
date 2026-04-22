from incidentbot.logging import logger
from incidentbot.matrix import commands


class MatrixHandler:
    """
    Listens for Matrix room events and dispatches !incident commands.

    Delegates the sync loop to MatrixClient; this class handles routing only.
    """

    def __init__(self, matrix_client, widget_base_url: str | None = None):
        self._client = matrix_client
        self._widget_base_url = widget_base_url
        self._seen_events: set[str] = set()

    def start(self) -> None:
        """Start the background sync loop (non-blocking)."""
        self._client.start_sync(self._on_event)
        logger.info("Matrix sync loop started")

    async def _on_event(self, room_id: str, event) -> None:
        event_id = getattr(event, "event_id", None)
        if event_id in self._seen_events:
            return
        if event_id:
            self._seen_events.add(event_id)

        # Skip messages sent by the bot itself
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
                    commands.handle_help(room_id, self._client)
                case "status":
                    commands.handle_status(room_id, self._client)
                case "create":
                    commands.handle_create(room_id, self._client, self._widget_base_url)
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
