# janus

<img src="https://github.com/echoboomer/janus/blob/main/assets/janus-icon.png" width="125" height="125">

An incident management ChatOps bot for Slack.

- [janus](#janus)
  - [Incident Management Fundamentals](#incident-management-fundamentals)
  - [Architecture](#architecture)
  - [Requirements](#requirements)
  - [Features](#features)
    - [Incident Management](#incident-management)
      - [Incident Management Module Requirements](#incident-management-module-requirements)
      - [Using Incident Management](#using-incident-management)
      - [Incident Management Features](#incident-management-features)
        - [Automatically inviting specific members to the channel every time an incident is started.](#automatically-inviting-specific-members-to-the-channel-every-time-an-incident-is-started)
        - [Automatically posting information regarding external providers](#automatically-posting-information-regarding-external-providers)
        - [Automatically creating an incident via a react](#automatically-creating-an-incident-via-a-react)
      - [Statuspage Integration](#statuspage-integration)
  - [Templates](#templates)
  - [Required Variables](#required-variables)
  - [Optional Variables](#optional-variables)
  - [Testing and Development](#testing-and-development)
  - [Deploying](#deploying)
      - [Docker](#docker)
        - [Building From Local Code](#building-from-local-code)
        - [Using eb129/janus](#using-eb129janus)
      - [Kubernetes](#kubernetes)
  - [Caveats](#caveats)
  - [Customizing](#customizing)

## Incident Management Fundamentals

This bot does not cover all use cases for incident management practices. In fact, the role names and certain fundamentals featured in this bot are best practices as described by [PagerDuty](https://response.pagerduty.com/before/different_roles/). Check out their fantastic documentation on incident management, on-call frameworks, etc.

This bot is designed for you to extend as needed for your use cases. There are templates that you can tweak. If you don't want or need to do that, however, the default configurations are good enough for most use cases.

Don't let this bot drive your incident management process - customize it to match instead. If you don't have one yet, use this as inspiration.

## Architecture

The app is written in Python and backed by Postgresql.

When using Docker, the `postgres` image is used with a common sense latest version. `nginx` is also used as a reverse proxy.

The following environment variables are referenced for the database:

- `DATABASE_HOST` - the hostname of the database. In Dockerized environments, this is `db` by default.
- `DATABASE_NAME` - database name to use.
- `DATABASE_USER` - database user to use.
- `DATABASE_PASSWORD` - password for the user.
- `DATABASE_PORT` - the port to use when connecting to the database.

Each incident stores unique data referenced by processes throughout the app for lifecycle management on creation. The database should be durable and connection information should be passed to the application securely. In the event that a record is lost while an incident is open, the bot will be unable to manage that incident and none of the commands will work.

If you plan on allowing users to reopen incidents by setting their status back to anything other than `Resolved`, you will need to keep these records intact as well.

## Requirements

- [Create a Slack app](https://api.slack.com/apps?new_app=1) for this application. Call it whatever you want.
- Use the option to create the app from a manifest. Alter the contents of `slack_app_manifest.json` as needed, paste it in, click next. You can change this stuff later, but for now this gets the app up quickly.
- Install the app to your workspace. You'll now have an OAuth token. Provide that as `SLACK_BOT_TOKEN`.
- Find your `App Credentials` and provide the signing secret as `SLACK_SIGNING_SECRET`.
- Provide the verification token as `SLACK_VERIFICATION_TOKEN`.

You can create an `.env` file and provide these locally, or the app will just look for them as OS environment variables. Handle this however you deploy apps in your environments. The `docker-compose.yml` file included here can be used for local development and testing or as a basis for running in something like Elastic Beanstalk, etc.

## Features

### Incident Management

- Facilitates creation of incident channels.
- Allows assigning roles for incident management.
  - These roles are currently: `incident commander`, `communications liaison`, and `technical lead`.
  - The first two are based on the first and second tier of roles described by PagerDuty. The last can be thought of as a primary SME contact.
- A fully functioning digest channel that stays up to date with incident statuses that can be used by others to watch the status of incidents.
- Optionally sources information from external providers and provides a snapshot of their statuses at the time of incident creation.

#### Incident Management Module Requirements

Since this bot mainly helps run incidents, there are a few prerequisites.

- You should have a digest channel that serves as a collection of information for all of your incidents. Provide this as `INCIDENTS_DIGEST_CHANNEL` - this is the channel **name**, not the **ID**. A common sense one is `incidents`. The idea is that all information about ongoing incidents will be sent to this channel and everyone who cares about incident management can go look there. There is only one of these digest channels.
- Your Slack workspace name (`foobar.slack.com`) minus the domain (`foobar`) should be provided as `SLACK_WORKSPACE_ID`. This is used to format some things related to sending messages to Slack.
- You should invite your bot user to the aforementioned incidents channel at a minimum or anywhere else you'd like to use it.
- You should ideally have a perpetual Zoom, Google Meet, etc. link prepared and provide the link via the variable listed below to help with coordinating communication efforts during incidents.

#### Using Incident Management

Invite your bot to a channel where you'd like to create incidents.

The following command creates incidents:

`/incident foo-bar`

Incident channels, by default, are named `inc-date-description`.

`foo-bar` here is a brief description. You aren't required to add hyphens - you can use spaces and the app converts them for you. This description is tacked on to the end of the incident channel name. If you don't provide at least something for the description, the bot will yell at you until you do. For example:

`inc-202110281725-foobar`

This should be a brief description like `/incident www-down` - something that is short and to the point and describes what is happening.

Once a channel is created, the bot will message you and tell you what the channel ID is along with other helpful hints. The digest channel will also be updated.

You can click on the link that is sent directly to you or the green button in the digest message to join the channel.

Once you join the channel, there's a pinned boilerplate message with buttons to claim or assign roles and a dropdown box to change the status of the incident.

If you've opted to enable external provider status updates, you'll see those too.

Invite others to help run the incident - incident management is approached in different ways, and the holistic process it outside of the scope of this document. If you wish to change the role names, you can. You can change the statuses, add more statuses, and whatever else you need to do to customize this app. The sky is the limit.

From here, others can claim roles or assign roles and the status can be changed. Each change will update the original digest message. Once the incident is resolved, the status changes to match this in the digest channel.

When someone claims a role or is assigned a role, the bot will message that user with some helpful information regarding the role.

Finally, whenever a role is assigned or claimed or the status is changed, the bot will message the incident channel.

You can mention the bot and type `help` for a help menu.

#### Incident Management Features

There are two optional features with the incident management module:

##### Automatically inviting specific members to the channel every time an incident is started.

Set the OS environment variable `INCIDENT_AUTO_GROUP_INVITE_ENABLED` to `true`.

Set the OS environment variable `INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME` to the name of the Slack group you want to invite to each newly created incident channel.

##### Automatically posting information regarding external providers

This feature currently supports the following providers, but you can write your own using the existing logic:

- GitHub
- Heroku

To enable, set `INCIDENT_EXTERNAL_PROVIDERS_ENABLED` to `true` and set `INCIDENT_EXTERNAL_PROVIDERS_LIST` to a comma-separated list of providers you'd like to enable. Example: `github,heroku`

By enabling this feature, a message will be dropped into each new incident channel providing a snapshot of the provider's current status.

##### Automatically creating an incident via a react

If setting `INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED` to `true` and `INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME` to the name of a Slack emoji, you can automatically have an incident create based on reacting to a message. The bot will create the channel with the suffix `auto-<random 6 char hashed value>` and will paste the contents of the message that was reacted to in the incident channel.

#### Statuspage Integration

If enabling the variable to set the Statuspage integration to enabled (see below) and providing the API key and page ID for your Statuspage account, the bot will drop in a message after the incident is opened that will allow you to create a corresponding Statuspage incident. In a future update, this process will be automated and tied to stages managed by the bot.

For now, you can kick off a new incident by providing a title, description, impact, and by selecting impacted components. You can then move the Statuspage incident through phases until is resolved. Each time you do this, the message will automatically update in your incident channel.

## Templates

In cases where the bot communicates with Slack, the formatting for the Slack message is stored as a `json` file at whatever the value of the variable `TEMPLATES_DIRECTORY` is set to in relation to the project root - `templates/` is the default directory but can be overridden. Either way, you need a copy of each standard placeholder file located in `templates/` in this repository in whatever folder you choose to use.
 
The application uses these templates to format message [blocks](https://api.slack.com/block-kit) for Slack. The application will look for the directory at the path provided, either via the variable or at the default location of `templates/`, and it will not start if the directory is not present.

You can alter the existing templates as needed to suit your own purposes or add new ones to extend the functionality of the app. There is an interpolation process that will look for certain keywords in these templates and replace them with variables. For example:

```python
    variables = {
        "header_var_placeholder": header,
        "incident_id_var_placeholder": incident_id,
        "new_status_placeholder": new_status,
        "message_var_placeholder": message,
        "slack_workspace_id_var_placeholder": slack_workspace_id,
    }
    return tools.render_json(
        f"{templates_directory}/incident_digest_notification_update.json", variables
    )
```

Within `{templates_directory}/incident_digest_notification_update.json`, the app will look for `{header_var_placeholder}` and so on and replace these statements with the value of the passed in variable.

Note that `{templates_directory}` is replaced with the value of the `TEMPLATES_DIRECTORY` environment variable which is `templates/` by default. You do not have to provide this variable. See below.

## Required Variables

- `DATABASE_HOST` - the hostname of the database.
- `DATABASE_NAME` - database name to use.
- `DATABASE_USER` - database user to use.
- `DATABASE_PASSWORD` - password for the user.
- `DATABASE_PORT` - the port to use when connecting to the database.
- `INCIDENTS_DIGEST_CHANNEL` - the **name** of the incidents digest channel as described above.
- `SLACK_SIGNING_SECRET` - the signing secret pulled from the OAuth data for your Slack app.
- `SLACK_BOT_TOKEN` - the API token to be used by your bot once it is deployed to your workspace.
- `SLACK_VERIFICATION_TOKEN` - the verification token pulled from the OAuth data for your Slack app.
- `SLACK_WORKSPACE_ID` - if your Slack workspace is `mycompany.slack.com`, this should be `mycompany`.

## Optional Variables

- `INCIDENT_AUTO_GROUP_INVITE_ENABLED` - to enable the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to `true`.
- `INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME` - if enabling the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to the name of the Slack group. For example: `whatever-group`
- `INCIDENT_EXTERNAL_PROVIDERS_ENABLED` - if enabling status snapshots for external providers (documented above), set this to `true`.
- `INCIDENT_EXTERNAL_PROVIDERS_LIST` - if enabling status snapshots for external providers (documented above), set this to a comma-separated list of providers to enable. For example: `github,heroku`
- `INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED` - if enabling auto incident channel create based on react, set this to `true`.
- `INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME` - the name of the emoji that will trigger automatic incident creation.
- `STATUSPAGE_INTEGRATION_ENABLED` - set to `true` to enable the Statuspage integration.
- `STATUSPAGE_API_KEY` - Statuspage API key if enabling.
- `STATUSPAGE_PAGE_ID` - Statuspage page ID if enabling.
- `TEMPLATES_DIRECTORY` - set this to the directory your templates will be located in from the project root if you want to override the default of `templates/`. You do not need to provide this otherwise. If you do, you must include the trailing `/` - i.e. `mydirfortemplates/`
- `VIDEO_CONFERENCING_LINK` - by default, the topic for each incident channel is set to a string containing the video conferencing link. By providing this value, it will automatically set it. If you choose not to provide this value, the topic will simply be blank.

## Testing and Development

You can run `python3 main.py` from the project root to start the app after adding required vars to `.env` and then use something like [ngrok](https://ngrok.com/) to route to your app for testing. It's handy to have a test Slack workspace for this.

Alternatively, you can use `docker-compose.yml` and provide the environment variables. Doing this method will also run and start the database for you as well as `nginx`.

If you simply wish to start the database for local testing without starting the app, you can run `docker compose up db`. This is useful when running the app via Python directly.

Keep in mind that regardless of environment, the app uses `waitress` as a production-grade WSGI. The default Flask Werkzeug process will never be used.

## Deploying

#### Docker

##### Building From Local Code

The Dockerfile can be used to create your own Docker image. All you need to change is the directory for the templates if not using the default location. Otherwise, the file is ready to build after you've made your changes.

If you choose to use a different directory, update the environment variable `TEMPLATES_DIRECTORY` and then change the command in the Dockerfile to copy over the contents of that directory.

##### Using eb129/janus

There is a version of the Dockerfile in this repository available for use according to the latest tags. In order to use this image, you'll need to have a `templates/` directory (or, again, whatever the value of `TEMPLATES_DIRECTORY` is if choosing to override) ready to be volumed in.

Visit the [Dockerhub page](https://hub.docker.com/repository/docker/eb129/janus) for all available tags.

#### Kubernetes

Kubernetes manifests are provided and can be installed using `kustomize`:

`kubectl apply -k=deploy/manifests`

You may tweak the files as needed or optionally remove the database.

## Caveats

You have to have `postgresql` installed locally if attempting to start the app or even install dependencies via `requirements.txt`.

Since the app uses `psycopg2`, it won't install if you don't have `postgresql` installed.

[postgres.app](https://postgresapp.com/) makes this easy.

## Customizing

You can add or change any of the templates in the `templates/` directory to suit your needs.

For events-related functionality, the contents of `lib/core/slack_events.py` can be updated to add new features. Check out the documentation [here](https://github.com/slackapi/python-slack-events-api).
