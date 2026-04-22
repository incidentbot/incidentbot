from incidentbot.logging import logger
from incidentbot.matrix.messages import MatrixMessages
from incidentbot.models.database import IncidentRecord, engine
from sqlmodel import Session, select


COMMAND_PREFIX = "!incident"


def parse(body: str) -> tuple[str, list[str]] | None:
    """Parse a message body into (subcommand, args). Returns None if not a bot command."""
    stripped = body.strip()
    if not stripped.startswith(COMMAND_PREFIX):
        return None
    parts = stripped[len(COMMAND_PREFIX):].strip().split()
    if not parts:
        return ("help", [])
    return (parts[0].lower(), parts[1:])


def handle_help(room_id: str, client, digest_room_id: str = "") -> None:
    plain, html = MatrixMessages.help(digest_room_id)
    client.send_text(room_id, plain, html)


def handle_status(room_id: str, client) -> None:
    with Session(engine) as session:
        incidents = session.exec(
            select(IncidentRecord).where(
                ~IncidentRecord.status.in_(["resolved", "archived"])
            )
        ).all()

    if not incidents:
        client.send_text(room_id, "No active incidents.")
        return

    lines_plain = ["Active incidents:"]
    lines_html = ["<b>Active incidents:</b><ul>"]
    for inc in incidents:
        room_link = f"https://matrix.to/#/{inc.channel_id}"
        lines_plain.append(
            f"  {inc.slug} | {inc.severity.upper()} | {inc.status.title()} — {inc.description}"
        )
        lines_html.append(
            f'<li><a href="{room_link}">{inc.slug}</a> '
            f"| {inc.severity.upper()} | {inc.status.title()} — {inc.description}</li>"
        )
    lines_html.append("</ul>")
    client.send_text(room_id, "\n".join(lines_plain), "".join(lines_html))




def handle_join(room_id: str, args: list[str], sender: str, client) -> None:
    if len(args) < 2:
        client.send_text(room_id, "Usage: !incident join <incident_id> <role>")
        return

    incident_id_str, role = args[0], " ".join(args[1:])
    try:
        incident_id = int(incident_id_str)
    except ValueError:
        client.send_text(room_id, f"Invalid incident ID: {incident_id_str}")
        return

    with Session(engine) as session:
        record = session.get(IncidentRecord, incident_id)
        if not record:
            client.send_text(room_id, f"Incident {incident_id} not found.")
            return
        roles = record.roles_all or []
        matched = [r for r in roles if role.lower() in r.lower()]
        if not matched:
            client.send_text(
                room_id,
                f"Unknown role '{role}'. Available: {', '.join(roles)}",
            )
            return
        assigned_role = matched[0]
        active_roles: dict = record.roles_active or {}
        active_roles[assigned_role] = sender
        record.roles_active = active_roles
        session.add(record)
        session.commit()

    client.send_text(
        room_id,
        f"{sender} joined {record.slug} as {assigned_role}.",
    )


def handle_severity(room_id: str, args: list[str], client) -> None:
    if len(args) < 2:
        client.send_text(room_id, "Usage: !incident severity <incident_id> <severity>")
        return

    incident_id_str, new_severity = args[0], args[1].lower()
    try:
        incident_id = int(incident_id_str)
    except ValueError:
        client.send_text(room_id, f"Invalid incident ID: {incident_id_str}")
        return

    with Session(engine) as session:
        record = session.get(IncidentRecord, incident_id)
        if not record:
            client.send_text(room_id, f"Incident {incident_id} not found.")
            return
        valid = list(record.severities or [])
        if new_severity not in valid:
            client.send_text(
                room_id,
                f"Invalid severity '{new_severity}'. Valid: {', '.join(valid)}",
            )
            return
        record.severity = new_severity
        session.add(record)
        session.commit()

    client.send_text(
        room_id,
        f"Severity for {record.slug} updated to {new_severity.upper()}.",
    )


def handle_resolve(room_id: str, args: list[str], client) -> None:
    if not args:
        client.send_text(room_id, "Usage: !incident resolve <incident_id>")
        return

    try:
        incident_id = int(args[0])
    except ValueError:
        client.send_text(room_id, f"Invalid incident ID: {args[0]}")
        return

    with Session(engine) as session:
        record = session.get(IncidentRecord, incident_id)
        if not record:
            client.send_text(room_id, f"Incident {incident_id} not found.")
            return
        final_status = next(
            (s for s, cfg in __import__("incidentbot.configuration.settings", fromlist=["settings"]).settings.statuses.items() if cfg.final),
            "resolved",
        )
        record.status = final_status
        session.add(record)
        session.commit()

    client.send_text(room_id, f"{record.slug} marked as {final_status}.")
