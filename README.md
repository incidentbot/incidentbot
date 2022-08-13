# incident-bot

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/bot.png" width="125" height="125">

Incident management ChatOps bot for Slack to allow your teams to easily and effectively identify and manage technical incidents impacting your cloud infrastructure, your products, or your customers' ability to use your applications and services.

Interacting with the bot is incredibly easy through the use of modals and simplified commands.

[View documentation on readthedocs](https://incident-bot.readthedocs.io/en/latest/)

## Features at a Glance

- Fully featured web management UI
- Robust experience in Slack to create and manage incidents using actions, shortcuts, and modals
- Automatic creation of a centralized incident channel to partition conversation about incidents
- Automatically page teams (if PagerDuty integration is enabled) on incident creation and/or on-demand
- Select messages to pin to the incident that can be displayed in the web UI and automatically added to the RCA document
- Automatically create an RCA channel and an RCA document (if Confluence integration is enabled)
- Optional integration to manage Statuspage incidents directly from the Slack channel
- Optional integration to automatically fetch the status of upstream providers

- [incident-bot](#incident-bot)
  - [Features at a Glance](#features-at-a-glance)
  - [Architecture](#architecture)
  - [Requirements](#requirements)
  - [Documentation](#documentation)
  - [Testing](#testing)
  - [Feedback](#feedback)

## Architecture

The app is written in Python and backed by Postgresql and leverages the `slack-bolt` websocket framework to provide zero footprint for security concerns.

The web UI is written in React.

Each incident stores unique data referenced by processes throughout the app for lifecycle management on creation. The database should be durable and connection information should be passed to the application securely. In the event that a record is lost while an incident is open, the bot will be unable to manage that incident and none of the commands will work.

## Requirements

- [Create a Slack app](https://api.slack.com/apps?new_app=1) for this application. You can name it whatever you'd like, but `incident-bot` seems to make the most sense.
- Use the option to create the app from a manifest. Run `make render` to output `slack_app_manifest.yaml` at project root and paste in the contents. You can adjust these settings later as you see fit, but these are the minimum permissions required for the bot to function properly.
- Install the app to your workspace. You'll now have an OAuth token. Provide that as `SLACK_BOT_TOKEN`.
- Verify that websocket mode is enabled and provide the generated app token as `SLACK_APP_TOKEN` - you can generate an app token via the `Basic Information` page in your app's configuration.

## Documentation

The documentation covers all setup requirements and features of the app.

[View on readthedocs](https://incident-bot.readthedocs.io/en/latest/)

## Testing

Tests will run on each pull request and merge to the primary branch. To run them locally:

```bash
$ make -C backend run-tests
```

## Feedback

This application is not meant to solve every problem with regard to incident management. It was created as an open-source alternative to paid solutions that integrate with Slack.

If you encounter issues with functionality or wish to see new features, please open an issue and let us know.
