import json
import requests

from datetime import date, datetime, timedelta
from typing import Dict
from ..shared import tools

# Upstream URLs for provider statuses
provider_urls = {
    "github": "https://kctbh9vrtdwd.statuspage.io/api/v2",
    "heroku": "https://status.heroku.com/api/v4",
}

# Time/Data Scoping Variables
time = datetime.now().strftime("%H:%M:%S")
today = date.today()
yesterday = today - timedelta(days=1)


def build_incident_channel_provider_updates(
    channel: str, provider: str
) -> Dict[str, str]:
    """Formats the notification that will be
    sent when a channel is started if service provider
    updates are enabled

    Args:
        channel: str
        provider: str

    Returns dict[str, str] containing the formatted message
    to be sent to Slack
    """
    if provider == "github":
        blocks = get_github_status(github_api=provider_urls["github"])
        blocks.append(
            {
                "block_id": "buttons",
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "GitHub Status",
                        },
                        "url": "https://githubstatus.com/",
                    }
                ],
            }
        )
        msg = {
            "channel": channel,
            "blocks": blocks,
        }
    elif provider == "heroku":
        blocks = get_heroku_status(heroku_api=provider_urls["heroku"])
        blocks.append(
            {
                "block_id": "buttons",
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Heroku Status",
                        },
                        "url": "https://status.heroku.com/",
                    }
                ],
            }
        )
        msg = {
            "channel": channel,
            "blocks": blocks,
        }
    return msg


def get_github_status(github_api) -> Dict[str, str]:
    sr = requests.get(f"{github_api}/summary.json")
    sp = json.loads(sr.text)
    apps_status = sp["components"]
    blocks = [
        {"type": "divider"},
        {
            "block_id": "header",
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Current GitHub Status",
            },
        },
    ]
    for a in apps_status:
        n = a["name"]
        s = a["status"]
        d = a["description"] or "None provided"

        blocks.append(
            {
                "block_id": f"{n}_info",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{n}* */* `{s}`",
                },
            },
        )
    blocks.append({"type": "divider"})
    return blocks


def get_heroku_status(heroku_api):
    sr = requests.get(f"{heroku_api}/current-status")
    sp = json.loads(sr.text)
    apps_status = sp["status"]
    blocks = [
        {"type": "divider"},
        {
            "block_id": "header",
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Current Heroku Status",
            },
        },
    ]
    for a in apps_status:
        l = a["system"]
        s = a["status"]

        blocks.append(
            {
                "block_id": f"{l}_info",
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{l}* */* `{s}`",
                },
            },
        )
    blocks.append({"type": "divider"})
    return blocks
