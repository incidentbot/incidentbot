from dataclasses import dataclass
from typing import Any, Dict


class ActionParametersSlack:
    """Builds parameters based on Slack actions input"""

    def __init__(self, payload: str):
        self.payload = payload

    @property
    def actions(self) -> str:
        return self.payload["actions"][0]

    @property
    def channel_details(self) -> str:
        return self.payload["channel"]

    @property
    def message_details(self) -> str:
        return self.payload["message"]

    @property
    def user_details(self) -> str:
        return self.payload["user"]

    @property
    def state(self) -> str:
        return self.payload["state"]

    @property
    def parameters(self) -> Dict[str, Any]:
        parameters_payload = {
            "action_id": self.actions["action_id"],
            "channel_id": self.channel_details["id"],
            "channel_name": self.channel_details["name"],
            "timestamp": self.message_details["ts"],
            "user": self.user_details["name"],
            "user_id": self.user_details["id"],
        }
        return parameters_payload


@dataclass
class ActionParametersWeb:
    """Builds paramters based on web UI input"""

    incident_id: str
    channel_id: str
    role: str
    bp_message_ts: str
    user: str
