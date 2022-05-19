# incident-bot

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/bot.png" width="125" height="125">

Incident management ChatOps bot for Slack to allow your teams to easily and effectively identify and manage technical incidents impacting your cloud infrastructure, your products, or your customers' ability to use your applications and services.

Interacting with the bot is incredibly easy through the use of modals and simplified commands.

- [incident-bot](#incident-bot)
  - [Architecture](#architecture)
  - [Requirements](#requirements)
  - [Features](#features)
    - [Incident Management](#incident-management)
      - [Incident Management Module Requirements](#incident-management-module-requirements)
      - [Auto RCA/Postmortem Generation](#auto-rcapostmortem-generation)
      - [Scheduled Actions](#scheduled-actions)
  - [Updating Literature](#updating-literature)
  - [Required Variables](#required-variables)
  - [Optional Variables](#optional-variables)
  - [Database Migrations](#database-migrations)
  - [Testing](#testing)
  - [Demonstration](#demonstration)
  - [Feedback](#feedback)

## Architecture

The app is written in Python and backed by Postgresql and leverages the `slack-bolt` websockets framework to provide zero footprint for security concerns.

Each incident stores unique data referenced by processes throughout the app for lifecycle management on creation. The database should be durable and connection information should be passed to the application securely. In the event that a record is lost while an incident is open, the bot will be unable to manage that incident and none of the commands will work.

## Requirements

- [Create a Slack app](https://api.slack.com/apps?new_app=1) for this application. You can name it whatever you'd like, but `incident-bot` seems to make the most sense.
- Use the option to create the app from a manifest. Run `make render` to output `slack_app_manifest.yaml` at project root and paste in the contents. You can adjust these settings later as you see fit, but these are the minimum permissions required for the bot to function properly.
- Install the app to your workspace. You'll now have an OAuth token. Provide that as `SLACK_BOT_TOKEN`.
- Verify that websocket mode is enabled and provide the generated app token as `SLACK_APP_TOKEN` - you can generate an app token via the `Basic Information` page in your app's configuration.

## Features

### Incident Management

- Facilitates creation of incident channels.
- Allows assigning roles for incident management.
  - These roles are currently: `incident commander`, `communications liaison`, and `technical lead`.
  - The first two are based on the first and second tier of roles described by PagerDuty. The last can be thought of as a primary SME contact.
  - If you'd like to change these definitions within the app, see the section below on customization.
- A fully functioning digest channel that stays up to date with incident statuses that can be used by others to watch the status of incidents.
- Optional features documented below.

All incidents start as `sev4`. Incidents may be promoted through to `sev1`. Each time the `status` or `severity` of an incident is changed, an update is sent to the incident channel. The digest message is also updated. When an incident is resolved, the digest message will be changed to show this.

You are also able to send out incident updates so that those who are not actively participating in an incident can stay informed regarding its status. These updates will appear in the incident's digest channel.

When someone claims or is assigned a role during an incident, the bot will notify them via private message and automatically add them to the channel. The bot will also give them helpful information about the role they've been assigned. You are free to adjust these messages as you see fit.

When an incident is marked as `resolved`, a separate RCA channel is created for users to collaborate on scheduling followup actions. The `incident commander` and `technical lead` roles are automatically invited to this channel and may invite others as needed.

#### Incident Management Module Requirements

Since this bot mainly helps run incidents, there are a few prerequisites.

- You should have a digest channel that serves as a collection of information for all of your incidents. Provide this as `INCIDENTS_DIGEST_CHANNEL` - this is the channel **name**, not the **ID**. A common sense one is `incidents`. The idea is that all information about ongoing incidents will be sent to this channel and everyone who cares about incident management can go look there.
- Your Slack workspace name (`foobar.slack.com`) minus the domain (`foobar`) should be provided as `SLACK_WORKSPACE_ID`. This is used to format some things related to sending messages to Slack.
- You should invite your bot user to the aforementioned incidents digest channel at a minimum as well as anywhere else you'd like to use it. If you'd like to enable the react-to-create feature, the bot will need to be in every channel you plan to use this in. Common places are alert channels, etc.

#### Auto RCA/Postmortem Generation

This feature only works with Confluence Cloud and requires an API token and username as well as other variables described below. The template for the generated RCA is provided as an `html` file located at `templates/confluence/rca.html`. While a base template is provided, it is up to you to provide the rest. It is beyond the scope of this application to dictate the styles used in your documentation. One thing to keep in mind is that components provided should use unique `uuids`.

#### Scheduled Actions

By default, the app will look for incidents that are not `resolved` that are older than `7` days. You may adjust this behavior via the `scheduler` module if you wish.

When an incident is promoted to `sev1` or `sev2`, a scheduled job will kick off that will look for whether or not the `last_update_sent` field has been updated in the last `30` minutes. If not, it will ping the channel to encourage you to send out an incident update as good practice.

From then on, a reminder is sent out every `25` minutes to encourage you to send out another update. You may change these timers if you wish. This establishes a pattern that critical incidents will update your internal teams using half-hour cadences.

## Updating Literature

You can change the definitions of severity levels and the incident roles via the `templates/slack/` directory - whatever changes you make to the `json` files will impact the messaging the application uses when advertising information about severity levels, role responsibilities, etc.

You are encouraged to update these - it is beyond the scope of this application to determine the definitions and the provided ones are there as examples. It is common to work with customer experience or legal teams for defining these.

## Required Variables

- `POSTGRES_HOST` - the hostname of the database.
- `POSTGRES_NAME` - database name to use.
- `POSTGRES_USER` - database user to use.
- `POSTGRES_PASSWORD` - password for the user.
- `POSTGRES_PORT` - the port to use when connecting to the database.
- `INCIDENTS_DIGEST_CHANNEL` - the **name** of the incidents digest channel as described above.
- `INCIDENT_GUIDE_LINK` - a link to your internal guide for handling incidents. **Note:** This must be a fully formed URL - example: `https://mylink.com`.
- `INCIDENT_POSTMORTEMS_LINK` - a link to your postmortem process documentation or postmortem collection. **Note:** This must be a fully formed URL - example: `https://mylink.com`.
- `INCIDENT_CHANNEL_TOPIC` - the topic that will be set for all new incident channels. This is useful as a place to store a video meeting link.
- `SLACK_APP_TOKEN` - the app-level token for enabling websocket communication.
- `SLACK_BOT_TOKEN` - the API token to be used by your bot once it is deployed to your workspace.
- `SLACK_WORKSPACE_ID` - if your Slack workspace is `mycompany.slack.com`, this should be `mycompany`.

## Optional Variables

- `AUTH0_DOMAIN` - If using `auth0` as an entry when enabling status for external providers, you must provide this variable and set it to the name of your Auth0 domain.
- `INCIDENT_AUTO_GROUP_INVITE_ENABLED` - to enable the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to `true`.
- `INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME` - if enabling the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to the name of the Slack group. For example: `whatever-group`
- `INCIDENT_EXTERNAL_PROVIDERS_ENABLED` - if enabling status snapshots for external providers (documented above), set this to `true`.
- `INCIDENT_EXTERNAL_PROVIDERS_LIST` - if enabling status snapshots for external providers (documented above), set this to a comma-separated list of providers to enable. For example: `github,heroku`
- `INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED` - if enabling auto incident channel create based on react, set this to `true`.
- `INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME` - the name of the emoji that will trigger automatic incident creation.
- `STATUSPAGE_INTEGRATION_ENABLED` - set to `true` to enable the Statuspage integration.
- `STATUSPAGE_API_KEY` - Statuspage API key if enabling.
- `STATUSPAGE_PAGE_ID` - Statuspage page ID if enabling.
- `STATUSPAGE_URL` - Link to the public Statuspage for your organization. **Note:** This must be a fully formed URL - example: `https://status.foo.com`.
- `TEMPLATES_DIRECTORY` - set this to the directory your templates will be located in from the project root if you want to override the default of `templates/slack/`. You do not need to provide this otherwise. If you do, you must include the trailing `/` - i.e. `mydirfortemplates/`
- `WEB_INTERFACE_ENABLED` - set this to `true` to enable the optional web management interface. **Note:** The web interface is deprecated and will be removed in a future version.

It is also possible to automatically create an RCA/postmortem document when an incident is transitioned to resolved.

- `AUTO_CREATE_RCA` - Set this to `true` to enable RCA creation - this only works with Confluence Cloud. When enabled, this will automatically populate a postmortem document. If this is `true`, you must provide all values below.
- `CONFLUENCE_API_URL` - The URL of the Atlassian account.
- `CONFLUENCE_API_USERNAME` - Username that owns the API token.
- `CONFLUENCE_API_TOKEN` - The API token.
- `CONFLUENCE_SPACE` - The space in which the RCAs page lives.
- `CONFLUENCE_PARENT_PAGE` - The name of the page within the above space where RCAs are created as child objects.

Finally, you can integrate with PagerDuty to provide details about who is on call. To do so, provide the following variables. If either of these is blank, the feature will not be enabled.

- `PAGERDUTY_API_TOKEN`
- `PAGERDUTY_API_USERNAME`

You are then able to use the bot's `pager` command.

## Database Migrations

Migrations can be done using [Alembic](https://github.com/sqlalchemy/alembic). This process uses `config.database_url` so it depends on the same environment variables the main application does for the database. You will need to have a functioning `.env` file configured locally and this process must be done from your local machine for authorized users.

**Note:** The `.env` file is ignored via `.gitignore` - do not commit any sensitive information to your repository when running migrations locally.

To stage a migration file:

```bash
$ make stage_migration DESCRIPTION="Description of the change"
  Generating /Users/scott/src/incident-bot/alembic/versions/e585abb1f948_description_of_the_change_.py ...  done
```

Open the file that was created and adjust the `upgrade()` and `downgrade()` methods accordingly. Consult the [documentation](https://alembic.sqlalchemy.org/en/latest/) for full usage instructions. Create migrations for each necessary transaction.

Finally, run the migration:

```bash
$ make run_migrations
./venv/bin/alembic upgrade head
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade e585abb1f948 -> 476b2348392c, Description of the change
```

Past migrations can be viewed in the `alembic/` directory for reference and context. Don't delete them as they can be used for downgrading/rolling back.

It is possible you'll never need to use this functionality, but if you choose to add new columns to the database, it will come in handy.

## Testing

Tests will run on each pull request and merge to the primary branch. To run them locally:

```bash
$ make run-tests
```

## Demonstration

Search for the `start a new incident` shortcut via the Slack search bar and click on it:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/start-search.png">

Provide a short description and start a new incident:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/start-modal.png">

The digest channel shows that a new incident has been started:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/digest-new.png">

Upon joining the incident channel, the control panel is show where changes can be made to `status`, `severity`, and `roles`:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/boilerplate.png">

As `status`, `severity`, and `roles` are changed, the channel is notified of these events:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/updates.png">

Periodically, you can choose to provide those not involved directly in the incident about updates by searching for the `provide incident update` shortcut via the Slack search bar and clicking on it:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/provide-update-search.png">

You can then provide details regarding components and the nature of the update after selecting the incident channel. Only open incidents will show up in the list:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/provide-update-modal.png">

Now, everyone can see the updates in the digest channel without needing to join the incident:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/provide-update-message.png">

When an incident is promoted to `sev2` or `sev1`, the scheduled reminder to send out updates will be created. You can view these by using `scheduler list`:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/sev2-scheduler.png">

When an incident has reached its conclusion and has been resolved, a helpful message is sent to the incident channel - notice that there is a handy button to export a formatted chat history to attach to your postmortem:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/resolution-message.png">

The original message in the digest channel is changed to reflect the new status of the incident:

<img src="https://github.com/echoboomer/incident-bot/blob/main/assets/examples/resolution-digest-update.png">

This is only a simple explanation of the process for running an incident. There are plenty of features that will guide your teams along the way.

## Feedback

This application is not meant to solve every problem with regard to incident management. It was created as an open-source alternative to paid solutions that integrate with Slack.

If you encounter issues with functionality or wish to see new features, please open an issue and let us know.
