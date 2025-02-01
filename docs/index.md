# Incident Bot Documentation

Incident Bot is an open-source incident management framework.

The core feature is a ChatOps bot to allow your teams to easily and effectively identify and manage technical incidents impacting your cloud infrastructure, your products, or your customers' ability to use your applications and services.

## Core Technologies

 - [Pydantic](https://docs.pydantic.dev/latest/) is used to handle data validation and type safety across the platform.
 - [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) is used to handle application configuration settings.
 - [SQLModel](https://sqlmodel.tiangolo.com/) is used to handle the relationship between application objects and backend databases.
 - [FastAPI](https://fastapi.tiangolo.com/) is used to handle the API.

## Features at a Glance

- Create a channel in Slack to gather resources and handle incidents.
- Digest channel to keep the rest of the organization up to date with incidents at all time.
- Define your own roles, severities, and statuses, or use ones configured right out of the box.
- Keep stakeholders updated using dynamic updates.
- Craft a postmortem document using an integration with Confluence that allows you to use your own templates.
- Create issues in Jira directly from incident channels.
- Page teams in PagerDuty or OpsGenie.
- Manage Statuspage incidents directly from incident channels.
- Create Zoom meetings for each incident to keep communications organized.
- A web interface with advanced features and administrative functionality.

## Integrations

For more information on integrations, check out the [integrations](integrations.md) documentation.

## Quick Start

- [Create a Slack app](https://api.slack.com/apps?new_app=1) for this application.
- Select `from an app manifest` and copy `manifest.yaml` out of this repository and paste it in to automatically configure the app.
- You'll need the app token, bot token, and user token for your application and provide those as `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, and `SLACK_USER_TOKEN` - these can be found within the app's configuration page in Slack.
- You'll need a Postgres instance to connect to.
- Create a channel to serve as your incident "digest" channel - something like `#incidents`.
- Configure the app using `config.yaml` and deploy it to Kubernetes, Docker, or whichever platform you choose. Check out the [installation](installation.md) guide for more details.
