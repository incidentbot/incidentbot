import json

from typing import Any, Dict


class ActionParameters:
    """Builds parameters based on actions input"""

    def __init__(self, payload: str):
        self.payload = payload
        self.payload_json = json.loads(payload)

    def actions(self) -> str:
        return self.payload_json["actions"][0]

    def channel_details(self) -> str:
        return self.payload_json["channel"]

    def message_details(self) -> str:
        return self.payload_json["message"]

    def user_details(self) -> str:
        return self.payload_json["user"]

    def state(self) -> str:
        return self.payload_json["state"]

    def parameters(self) -> Dict[str, Any]:
        self.parameters_payload = {
            "action_id": self.actions()["action_id"],
            "channel_id": self.channel_details()["id"],
            "channel_name": self.channel_details()["name"],
            "timestamp": self.message_details()["ts"],
            "user": self.user_details()["name"],
        }
        return self.parameters_payload
