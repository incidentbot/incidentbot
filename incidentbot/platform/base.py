from abc import ABC, abstractmethod
from typing import Any


class PlatformAdapter(ABC):
    """Platform-agnostic interface for chat platform operations."""

    @abstractmethod
    def create_room(self, name: str, topic: str = "", private: bool = False) -> dict:
        """Create a room/channel. Returns dict with at least 'id' and 'name'."""
        ...

    @abstractmethod
    def set_room_topic(self, room_id: str, topic: str) -> None:
        ...

    @abstractmethod
    def send_text(self, room_id: str, text: str) -> str:
        """Send plain text to a room. Returns platform event/message id."""
        ...

    @abstractmethod
    def pin_message(self, room_id: str, event_id: str) -> None:
        ...

    @abstractmethod
    def add_bookmark(self, room_id: str, title: str, url: str, emoji: str = "") -> None:
        """Add a bookmark to a room. No-op on platforms without bookmark support."""
        ...

    @abstractmethod
    def invite_user(self, room_id: str, user_id: str) -> None:
        ...

    @abstractmethod
    def invite_users(self, room_id: str, user_ids: list[str]) -> None:
        ...

    @abstractmethod
    def make_room_admin(self, room_id: str, user_id: str) -> None:
        """Grant elevated room permissions to a user when supported."""
        ...

    @abstractmethod
    def get_group_members_by_name(self, group_name: str) -> list[str]:
        """Return list of user IDs belonging to a named group/usergroup."""
        ...

    @abstractmethod
    def get_user_display_name(self, user_id: str) -> str:
        ...

    @abstractmethod
    def room_url(self, room_id: str) -> str:
        """Return a shareable URL for the given room/channel."""
        ...

    @abstractmethod
    def post_incident_boilerplate(self, incident: Any) -> str:
        """Post structured incident info to incident room. Returns event id."""
        ...

    @abstractmethod
    def post_welcome_message(self, room_id: str) -> None:
        ...

    @abstractmethod
    def post_digest_notification(
        self,
        channel_id: str,
        has_private_channel: bool,
        incident_components: str,
        incident_description: str,
        incident_impact: str | None,
        incident_slug: str,
        initial_status: str,
        meeting_link: str | None,
        severity: str,
    ) -> str:
        """Post notification to digest room. Returns event id."""
        ...

    @abstractmethod
    def post_jira_issue(
        self, room_id: str, key: str, summary: str, issue_type: str, link: str
    ) -> str:
        """Post Jira issue details to room. Returns event id."""
        ...

    @abstractmethod
    def post_gitlab_incident(
        self, room_id: str, incident_id: int, summary: str, link: str
    ) -> str:
        """Post GitLab incident details to room. Returns event id."""
        ...

    @abstractmethod
    def post_statuspage_prompt(self, room_id: str) -> None:
        ...
