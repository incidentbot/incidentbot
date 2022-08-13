Setup
=====

.. _setup:

Installation
------------

The app can be installed one of two ways - from Docker or from source.

The image can be built using the provided Dockerfile. There is also a public image available based on latest primary build. TBD

.. _docker-compose:

A sample compose file is provided with sample variables. This is useful for running the application locally or in environment that can leverage compose logic.

.. _variables:

Required Variables
------------

- `POSTGRES_HOST` - the hostname of the database.
- `POSTGRES_NAME` - database name to use.
- `POSTGRES_USER` - database user to use.
- `POSTGRES_PASSWORD` - password for the user.
- `POSTGRES_PORT` - the port to use when connecting to the database.
- `INCIDENTS_DIGEST_CHANNEL` - the **name** of the incidents digest channel referenced in the features documentation.
- `SLACK_APP_TOKEN` - the app-level token for enabling websocket communication.
- `SLACK_BOT_TOKEN` - the API token to be used by your bot once it is deployed to your workspace.
- `SLACK_WORKSPACE_ID` - if your Slack workspace is `mycompany.slack.com`, this should be `mycompany`.

Optional Variables
------------

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

You are then able to use the bot's `pager` command as well as the web features related to it.
