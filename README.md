# incident-bot

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/bot.png" width="125" height="125">

![tests](https://github.com/echoboomer/incident-bot/actions/workflows/tests.yml/badge.svg)
![version](https://img.shields.io/github/v/release/echoboomer/incident-bot)

Incident management ChatOps bot for Slack to allow your teams to easily and effectively identify and manage technical incidents impacting your cloud infrastructure, your products, or your customers' ability to use your applications and services.

Interacting with the bot is incredibly easy through the use of modals and simplified commands.

[View documentation on readthedocs](https://incident-bot.readthedocs.io/en/latest/)

- [incident-bot](#incident-bot)
  - [Features at a Glance](#features-at-a-glance)
  - [Quick Start](#quick-start)
    - [Kubernetes](#kubernetes)
  - [Testing](#testing)
  - [Feedback](#feedback)
  
<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/incident-bot-demo-1.gif" width="700" height="500" />

Featuring a rich web management UI:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/incident-bot-demo-2.gif" width="700" height="500" />

## Features at a Glance

- Fully featured optional web management UI - you can manage everything directly from Slack if desired
- Robust experience in Slack to create and manage incidents using actions, shortcuts, and modals
- Automatic creation of a centralized incident channel to partition conversation about incidents
- Automatically page teams (if PagerDuty integration is enabled) on incident creation and/or on-demand
- Select messages to pin to the incident that can be displayed in the web UI and automatically added to the RCA document
- Automatically create an RCA channel and an RCA document (if Confluence integration is enabled)
- Optional integration to manage Statuspage incidents directly from the Slack channel

## Quick Start

- [Create a Slack app](https://api.slack.com/apps?new_app=1) for this application. You can name it whatever you'd like, but `incident-bot` seems to make the most sense.
- Select `from an app manifest` and copy `manifest.yaml` out of this repository and paste it in to automatically configure the app.
- You'll need the app token, bot token, and user token for your application and provide those as `SLACK_APP_TOKEN`, `SLACK_BOT_TOKEN`, and `SLACK_USER_TOKEN` - these can be found within the app's configuration page in Slack.
- You'll need a Postgres instance to connect to.
- Configure the app using `config.yaml` and deploy it to Kubernetes, Docker, or whichever platform you choose.

### Kubernetes

- You can use [kustomize](https://github.com/echoboomer/incident-bot/blob/main/deploy/kustomize/incident-bot/overlays/development/kustomization.yaml). More details available [here](https://incident-bot.readthedocs.io/en/latest/setup.html#kustomize).
- There's optionally a Helm chart - instructions are available [here](https://incident-bot.readthedocs.io/en/latest/setup.html#helm).

## Testing

Tests will run on each pull request and merge to the primary branch. To run them locally:

```bash
make -C backend run-tests
```

## Feedback

This application is not meant to solve every problem with regard to incident management. It was created as an open-source alternative to paid solutions that integrate with Slack.

If you encounter issues with functionality or wish to see new features, please open an issue and let us know!
