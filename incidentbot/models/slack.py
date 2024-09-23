from pydantic import BaseModel
from typing import Any


class Channel(BaseModel):
    id: str | None = None
    name: str | None = None


class CommandInvocation(BaseModel):
    token: str | None = None
    team_id: str | None = None
    team_domain: str | None = None
    channel_id: str | None = None
    channel_name: str | None = None
    user_id: str | None = None
    user_name: str | None = None
    command: str | None = None
    text: str | None = None
    api_app_id: str | None = None
    is_enterprise_install: str | None = None
    response_url: str | None = None
    trigger_id: str | None = None


class Message(BaseModel):
    user: str | None = None
    type: str | None = None
    ts: str | None = None
    bot_id: str | None = None
    app_id: str | None = None
    text: str | None = None
    team: str | None = None
    blocks: list[dict] | None = None


class State(BaseModel):
    values: dict | None = None


class Team(BaseModel):
    id: str | None = None
    domain: str | None = None


class User(BaseModel):
    id: str | None = None
    username: str | None = None
    name: str | None = None
    team_id: str | None = None


class SlackBlockActionsResponse(BaseModel):
    type: str | None = None
    user: User | None = None
    api_app_id: str | None = None
    token: str | None = None
    container: dict[str, Any]
    trigger_id: str | None = None
    team: Team | None = None
    enterprise: str | dict | None = None
    is_enterprise_install: bool | None = None
    channel: Channel | None = None
    message: Message | None = None
    state: State | None = None
    actions: list[dict[str, Any]]


class SlackView(BaseModel):
    id: str | None = None
    team_id: str | None = None
    type: str | None = None
    blocks: list[dict[str, Any]] | None = None
    private_metadata: str | None = None
    callback_id: str | None = None
    state: State | None = None
    hash: str | None = None
    title: dict[str, Any] | None = None
    clear_on_close: bool | None = None
    notify_on_close: bool | None = None
    close: None
    submit: dict[str, Any] | None = None
    previous_view_id: str | None = None
    root_view_id: str | None = None
    app_id: str | None = None
    external_id: str | None = None
    app_installed_team_id: str | None = None
    bot_id: str | None = None


class SlackViewSubmissionResponse(BaseModel):
    type: str | None = None
    team: Team | None = None
    user: User | None = None
    api_app_id: str | None = None
    token: str | None = None
    trigger_id: str | None = None
    view: SlackView | None = None
    response_urls: list[str] | None = None
    is_enterprise_install: bool | None = None
    enterprise: str | dict | None = None
