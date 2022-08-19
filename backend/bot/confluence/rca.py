import config

from bot.audit import log
from bot.confluence.api import confluence, logger, today
from bot.models.pg import IncidentLogging, Session
from bot.shared import tools
from typing import Any, Dict, List


def create_rca(
    incident_id: str,
    rca_title: str,
    incident_commander: str,
    technical_lead: str,
    severity: str,
    severity_definition: str,
    parent_page: str = config.confluence_parent_page,
    space: str = config.confluence_space,
):
    """
    Creates a starting RCA page and returns the create page's URL
    """
    title = f"{today} - {rca_title.title()}"
    parent_page_id = confluence.get_page_id(space, parent_page)
    logger.info(
        f"Creating RCA {title} in Confluence space {space} under parent {parent_page}..."
    )
    # Get any pinned items
    attachments = (
        Session.query(IncidentLogging)
        .filter(IncidentLogging.incident_id == incident_id)
        .all()
    )
    # Generate html for rca doc
    body = render_rca_html(
        incident_commander=incident_commander,
        technical_lead=technical_lead,
        severity=severity,
        severity_definition=severity_definition,
        timeline=generate_timeline(log.read(incident_id=incident_id)),
        attachments=generate_pinned_items(attachments),
    )
    # Create rca doc
    if confluence.page_exists(space=space, title="RCAs"):
        try:
            confluence.create_page(
                space,
                title,
                body,
                parent_id=parent_page_id,
                type="page",
                representation="storage",
                editor="v2",
            )
            created_page_id = confluence.get_page_id(space, title)
            created_page_info = confluence.get_page_by_id(page_id=created_page_id)
            url = (
                created_page_info["_links"]["base"]
                + created_page_info["_links"]["webui"]
            )
            # If there are images in pinned items, attach them
            if len(attachments) > 0:
                for item in attachments:
                    if item.img != b"":
                        try:
                            logger.info(f"Attaching pinned item to {title}...")
                            confluence.attach_content(
                                item.img,
                                name=item.title,
                                content_type=item.mimetype,
                                page_id=created_page_id,
                                space=config.confluence_space,
                                comment=f"This item was pinned to the incident by {item.user} at {item.ts}.",
                            )
                        except Exception as error:
                            logger.error(f"Error attaching file to {title}: {error}")
            return url
        except Exception as error:
            logger.error(error)
    else:
        logger.error("Couldn't create RCA page, does the parent page exist?")


def find_user_id(user: str) -> tuple[bool, Any]:
    """
    Accepts the publicName of a user in Atlassian Cloud and returns the ID if it exists
    """
    groups = confluence.get_all_groups(start=0, limit=50)
    for g in groups:
        users = confluence.get_group_members(group_name=g["name"], start=0, limit=1000)
        for u in users:
            if user in u["publicName"]:
                return True, u["accountId"]
            else:
                pass
    return False, None


def generate_pinned_items(items: IncidentLogging) -> str:
    if len(items) == 0:
        return "<p>No items were pinned for this incident.</p>"
    all_items_formatted = ""
    for item in items:
        if item.img == b"":
            all_items_formatted += f"<blockquote><p><strong>{item.user} @ {item.ts} - </strong> {item.content}</p></blockquote><p />"
    return all_items_formatted


def generate_timeline(items: List[Dict]) -> str:
    if len(items) == 0:
        return """
<tr>
    <td>
        <p>None.</p>
    </td>
    <td>
        <p>No items were added to this incident's timeline.</p>
    </td>
</tr>
"""
    all_items_formatted = ""
    for item in items:
        all_items_formatted += f"""
<tr>
    <td>
        <p>{item["ts"]}</p>
    </td>
    <td>
        <p>{item["log"]}</p>
    </td>
</tr>
"""
    # Boilerplate
    all_items_formatted += f"""
<tr>
    <td>
        <p>&hellip;</p>
    </td>
    <td>
        <p>&hellip;</p>
    </td>
</tr>
"""
    return all_items_formatted


def render_rca_html(
    incident_commander: str,
    technical_lead: str,
    severity: str,
    severity_definition: str,
    timeline: str,
    attachments: str,
) -> str:
    """Renders HTML for use in Confluence documents"""
    variables = {
        "incident_commander": user_mention_format(incident_commander),
        "technical_lead": user_mention_format(technical_lead),
        "severity": severity.upper(),
        "severity_definition": severity_definition,
        "timeline": timeline,
        "attachments": attachments,
    }
    return tools.render_html(f"templates/confluence/rca.html", variables)


def user_mention_format(role: str) -> str:
    """
    Determines whether a user mention is a link or a string based on whether or
    not we could find the user ID
    """
    result = find_user_id(role)
    if result[0]:
        return f"""
            <ac:link>
                <ri:user ri:userkey="{result[1]}" />
            </ac:link>
        """
    else:
        return f"@{role}"
