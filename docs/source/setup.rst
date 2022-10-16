Setup
=====

.. _setup:

Installation
------------

The app can be installed one of two ways - from Docker or from source.

The image can be built using the provided Dockerfile. There is also a public image available based on latest primary build. The image is available `here <https://hub.docker.com/r/eb129/incident-bot>`_.

To run the application using the public Docker image, simply create a Docker compose file based on the provided example and reference the public image. Alternatively, Kubernetes manifests are provided via the ``deploy/`` directory.

.. _kubernetes:

Kubernetes
------------

``kustomize`` manifests are provided for convenience and are the recommended way to deploy the application in Kubernetes.

The manifests are located at: ``deploy/kubernetes/incident-bot``

To preview generated manifests, run: ``kubectl kustomize .``

To apply the resources, run: ``kubectl apply -k .``

.. warning::

  You will want to adjust the settings within the manifests to suit your needs before deploying. Specifically, ``application.properties`` is used to generate a `ConfigMap` for non-sensitive values and ``secrets.txt`` is used to generate a `Secret` containing sensitive values.

  In production, you should use a secret management tool that integrates with Kubernetes. You should not hardcode sensitive values. This setup is provided for convenience.

.. _docker-compose:

A sample compose file is provided with sample variables. This is useful for running the application locally or in environment that can leverage compose logic. In this scenario, the database runs as a container. This is not recommended for production usage.

.. warning::

  Management of a database is outside of the scope of this application. Setup for a containerized database is provided for convenience when using Docker Compose.

  You should use a Postgres provider of your choice and provide the parameters in the variables mentioned below. At a minimum, the ``user``, ``password``, and ``database`` should already exist.

.. _variables:

Required Variables
------------

- ``POSTGRES_HOST`` - the hostname of the database.
- ``POSTGRES_DB`` - database name to use.
- ``POSTGRES_USER`` - database user to use.
- ``POSTGRES_PASSWORD`` - password for the user.
- ``POSTGRES_PORT`` - the port to use when connecting to the database.
- ``INCIDENTS_DIGEST_CHANNEL`` - the **name** of the incidents digest channel referenced in the features documentation.
- ``SLACK_APP_TOKEN`` - the app-level token for enabling websocket communication.
- ``SLACK_BOT_TOKEN`` - the API token to be used by your bot once it is deployed to your workspace.
- ``DEFAULT_WEB_ADMIN_PASSWORD`` - the default password for the default admin account. See section on user management for more details.
- ``JWT_SECRET_KEY`` - this must be provided for user management. Set to a secure string.

Optional Variables
------------

- ``AUTH0_DOMAIN`` - If using ``auth0`` as an entry when enabling status for external providers, you must provide this variable and set it to the name of your Auth0 domain.
- ``INCIDENT_AUTO_GROUP_INVITE_ENABLED`` - to enable the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to ``true``.
- ``INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME`` - if enabling the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to the name of the Slack group.
- ``INCIDENT_EXTERNAL_PROVIDERS_ENABLED`` - if enabling status snapshots for external providers (documented above), set this to ``true``.
- ``INCIDENT_EXTERNAL_PROVIDERS_LIST`` - if enabling status snapshots for external providers (documented above), set this to a comma-separated list of providers to enable. For example: ``auth0,github,heroku``
- ``INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED`` - if enabling auto incident channel create based on react, set this to ``true``.
- ``INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME`` - the name of the emoji that will trigger automatic incident creation.

.. _access:

Access
------------

It is recommended to deploy this application in a private network or at least behind a private load balancer. There is no need to expose the application to the public Internet.

The web UI should only be accessible internally, and websocket mode eliminates the need to expose any endpoints to Slack.

Please exercise good judgment and caution when deploying this application.

.. _user-management:

User Management
------------

The value of ``DEFAULT_WEB_ADMIN_PASSWORD`` will become the default login password for the admin user for the web UI.

The automatically created web UI admin user is ``admin@admin.com``. Once you login, you can disable this user. We don't recommend deleting it in the event you need to use it again.

You're able to add new users from the settings page. You can optionally enable/disable and delete the users as well.

At this time, this is basic username (in the form of email) and password authentication. In the future, integration with OAuth providers will be added.

.. _confluence-settings:

Confluence Settings
------------

It is also possible to automatically create an RCA/postmortem document when an incident is transitioned to resolved. This only works with Confluence at this time.

- ``AUTO_CREATE_RCA`` - Set this to ``true`` to enable RCA creation - this only works with Confluence Cloud. When enabled, this will automatically populate a postmortem document. If this is ``true``, you must provide all values below.
- ``CONFLUENCE_API_URL`` - The URL of the Atlassian account.
- ``CONFLUENCE_API_USERNAME`` - Username that owns the API token.
- ``CONFLUENCE_API_TOKEN`` - The API token.
- ``CONFLUENCE_SPACE`` - The space in which the RCAs page lives.
- ``CONFLUENCE_PARENT_PAGE`` - The name of the page within the above space where RCAs are created as child objects.

.. _pagerduty-settings:

PagerDuty Settings
------------

You can integrate with PagerDuty to provide details about who is on call and page teams either manually or automatically. To do so, provide the following variables. If either of these is blank, the feature will not be enabled.

- ``PAGERDUTY_INTEGRATION_ENABLED`` - This must be provided and set to the string ``true`` if enabling the integration.
- ``PAGERDUTY_API_TOKEN``
- ``PAGERDUTY_API_USERNAME``

You are then able to use the bot's ``pager`` command and paging-related shortcuts as well as the web features related to them.

.. _statuspage-settings:

Statuspage Settings
------------

You can integrate with Statuspage to automatically prompt for Statuspage incident creation for new incidents. You can also update them directly from Slack.

- ``STATUSPAGE_INTEGRATION_ENABLED`` - set to ``true`` to enable the Statuspage integration.
- ``STATUSPAGE_API_KEY`` - Statuspage API key if enabling.
- ``STATUSPAGE_PAGE_ID`` - Statuspage page ID if enabling.
- ``STATUSPAGE_URL`` - Link to the public Statuspage for your organization. **Note:** This must be a fully formed URL - example: ``https://status.foo.com``.
