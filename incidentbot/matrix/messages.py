from html import escape
from incidentbot.models.database import IncidentRecord


class MatrixMessages:
    """Builds HTML-formatted Matrix messages equivalent to Slack Block Kit content."""

    @staticmethod
    def boilerplate(incident: IncidentRecord) -> tuple[str, str]:
        """Returns (plain_text, html) for the incident boilerplate message."""
        lines_plain = [
            f"== {incident.slug.upper()} ==",
            f"Description: {incident.description}",
            f"Severity: {incident.severity.upper()}",
            f"Status: {incident.status.title()}",
            f"Components: {incident.components}",
        ]
        lines_html = [
            f"<h3>🚨 {escape(incident.slug.upper())}</h3>",
            f"<b>Description:</b> {escape(incident.description)}<br>",
            f"<b>Severity:</b> {escape(incident.severity.upper())}<br>",
            f"<b>Status:</b> {escape(incident.status.title())}<br>",
            f"<b>Components:</b> {escape(incident.components)}<br>",
        ]
        if incident.impact:
            lines_plain.append(f"Impact: {incident.impact}")
            lines_html.append(f"<b>Impact:</b> {escape(incident.impact)}<br>")
        if incident.meeting_link:
            link = escape(incident.meeting_link)
            lines_plain.append(f"Meeting: {incident.meeting_link}")
            lines_html.append(f"<b>Meeting:</b> <a href='{link}'>{link}</a><br>")
        return "\n".join(lines_plain), "".join(lines_html)

    @staticmethod
    def welcome(room_id: str) -> tuple[str, str]:
        plain = (
            "Welcome to this incident channel.\n"
            "Open the widget panel to manage roles, severity, and status."
        )
        html = (
            "<b>Welcome to this incident channel.</b><br>"
            "Open the widget panel to manage roles, severity, and status."
        )
        return plain, html

    @staticmethod
    def digest_notification(
        channel_id: str,
        has_private_channel: bool,
        incident_components: str,
        incident_description: str,
        incident_impact: str | None,
        incident_slug: str,
        initial_status: str,
        meeting_link: str | None,
        severity: str,
    ) -> tuple[str, str]:
        room_link = f"https://matrix.to/#/{channel_id}"
        privacy = " 🔒 Private" if has_private_channel else ""
        lines_plain = [
            f"🚨 New Incident: {incident_slug}{privacy}",
            f"Description: {incident_description}",
            f"Severity: {severity.upper()}",
            f"Status: {initial_status.title()}",
            f"Components: {incident_components}",
        ]
        lines_html = [
            f"<h4>🚨 New Incident: <b>{escape(incident_slug)}</b>{privacy}</h4>",
            f"<b>Description:</b> {escape(incident_description)}<br>",
            f"<b>Severity:</b> {escape(severity.upper())}<br>",
            f"<b>Status:</b> {escape(initial_status.title())}<br>",
            f"<b>Components:</b> {escape(incident_components)}<br>",
        ]
        if incident_impact:
            lines_plain.append(f"Impact: {incident_impact}")
            lines_html.append(f"<b>Impact:</b> {escape(incident_impact)}<br>")
        if meeting_link:
            link = escape(meeting_link)
            lines_plain.append(f"Meeting: {meeting_link}")
            lines_html.append(f"<b>Meeting:</b> <a href='{link}'>{link}</a><br>")
        lines_plain.append(f"Room: {room_link}")
        lines_html.append(f'<a href="{escape(room_link)}">Join incident room →</a>')
        return "\n".join(lines_plain), "".join(lines_html)

    @staticmethod
    def jira_issue(
        key: str, summary: str, issue_type: str, link: str
    ) -> tuple[str, str]:
        plain = f"Jira {issue_type}: {key} — {summary}\n{link}"
        html = (
            f"📋 <b>Jira {escape(issue_type)}:</b> "
            f'<a href="{escape(link)}">{escape(key)}</a><br>'
            f"<b>Summary:</b> {escape(summary)}"
        )
        return plain, html

    @staticmethod
    def gitlab_incident(incident_id: int, summary: str, link: str) -> tuple[str, str]:
        plain = f"GitLab Incident #{incident_id}: {summary}\n{link}"
        html = (
            f"🦊 <b>GitLab Incident #{incident_id}:</b> "
            f'<a href="{escape(link)}">{escape(summary)}</a>'
        )
        return plain, html

    @staticmethod
    def help(digest_room_id: str = "") -> tuple[str, str]:
        create_hint = "Open the widget panel in the incidents room " + (
            f"(https://matrix.to/#/{digest_room_id})" if digest_room_id else ""
        )
        commands = [
            ("!incident help", "Show this help"),
            ("!incident status", "List active incidents"),
            ("!incident join <id> <role>", "Join an incident with a role"),
            ("!incident severity <id> <sev>", "Update incident severity"),
            ("!incident resolve <id>", "Mark incident as resolved"),
        ]
        plain = (
            f"To create an incident: {create_hint}\n\n"
            "Other commands:\n"
            + "\n".join(f"  {cmd}  —  {desc}" for cmd, desc in commands)
        )
        digest_link = (
            f'<a href="https://matrix.to/#/{escape(digest_room_id)}">incidents room</a>'
            if digest_room_id
            else "the incidents room"
        )
        html = (
            f"<b>To create an incident:</b> Open the widget panel in {digest_link}<br><br>"
            "<b>Other commands:</b><ul>"
            + "".join(f"<li><code>{cmd}</code> — {desc}</li>" for cmd, desc in commands)
            + "</ul>"
        )
        return plain, html

    @staticmethod
    def reminder(reminder, slug: str) -> tuple[str, str]:
        """Returns (plain_text, html) for a config-driven reminder message."""
        # ponytail: escape only, no mrkdwn translation. Reminder messages are
        # authored as Slack mrkdwn, so `<url|label>` renders literally on Matrix.
        # Write a converter if anyone actually puts links in reminders.
        plain = f"[{slug.upper()}] Reminder: {reminder.message}"
        html = f"<b>⏰ {escape(slug.upper())}</b><br>{escape(reminder.message)}"
        return plain, html
