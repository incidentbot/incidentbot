Setup
=====

.. _setup:

Installation
------------

For those who wish to get started quickly without customizing core behavior, there is a public image available based on the latest primary build. The image is available `here <https://hub.docker.com/r/eb129/incident-bot>`_.

You can run the image however you choose. A Docker Compose file is provided for guidance. It is recommended to use the Helm chart if running in Kubernetes.

.. _kubernetes:

Kubernetes
------------

.. _helm:

Helm
------------

You can get started quickly by using the Helm chart:

``helm repo add echoboomer-charts https://charts.echoboomer.net``

Sensitive data should come from Kubernetes ``Secret`` objects at a minimum. Secret management is outside of the scope of this application. One method is to used something like `sealed secrets <https://github.com/bitnami-labs/sealed-secrets>`_.

If using ``sealed-secrets``, you could create your sensitive environment variables in a ``.env`` file and create the ``Secret`` like this:

.. code-block:: bash

  kubectl create secret generic incident-bot-secret --from-env-file=.env --dry-run='client' -ojson --namespace incident-bot >incident-bot-secret.json &&
    kubeseal --controller-name sealed-secrets <incident-bot-secret.json >incident-bot-secret-sealed.json &&
    kubectl create -f incident-bot-secret-sealed.json

Contained with ``.env``, you'd want to include the sensitive values for this application. For example (this is not a comprehensive collection of all options):

.. code-block:: bash

  CONFLUENCE_API_URL=https://my-confluence-tenant.atlassian.net
  CONFLUENCE_API_USERNAME=me@acme.com
  CONFLUENCE_API_TOKEN=mytoken
  CONFLUENCE_SPACE=SPACENAME
  CONFLUENCE_PARENT_PAGE=ParentPageName
  STATUSPAGE_API_KEY=populatemeifusing
  STATUSPAGE_PAGE_ID=none
  STATUSPAGE_URL=none
  PAGERDUTY_API_USERNAME=me@acme.com
  POSTGRES_HOST=db
  POSTGRES_DB=incident_bot
  POSTGRES_USER=incident_bot
  POSTGRES_PASSWORD=somepassword
  POSTGRES_PORT=5432
  SLACK_APP_TOKEN=xapp-1-...
  SLACK_BOT_TOKEN=xoxb-...
  DEFAULT_WEB_ADMIN_PASSWORD=somepassword
  JWT_SECRET_KEY=mysecretkey

This will create the required ``Secret`` in the ``Namespace`` ``incident-bot``. You may need to create the ``Namespace`` if it doesn't exist.

You can now install the application. As an example:

``helm install echoboomer-charts/incident-bot --version 0.1.1 --values incident-bot-values.yaml --namespace incident-bot``

In this scenario, you'd want to provide the values using the file ``incident-bot-values.yaml``. Here's an example:

.. code-block:: yaml

  database:
    # Only if enabling for development of testing
    # Don't do this in production
    enabled: true
    password: somepassword
  # This is what gets created via the steps below
  envFromSecret:
    enabled: true
    secretName: incident-bot-secret
  envVars:
    AUTH0_DOMAIN:
    AUTO_CREATE_RCA: false
    INCIDENTS_DIGEST_CHANNEL: incidents
    INCIDENT_AUTO_GROUP_INVITE_ENABLED: false
    INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME: mygroup
    INCIDENT_EXTERNAL_PROVIDERS_ENABLED: true
    INCIDENT_EXTERNAL_PROVIDERS_LIST: ["github"]
    INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED: true
    INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME: create-incident
    PAGERDUTY_INTEGRATION_ENABLED: false
    STATUSPAGE_INTEGRATION_ENABLED: false
  healthCheck:
    enabled: true
    path: /api/v1/health
    port: 3000
    scheme: HTTP
    initialDelaySeconds: 30
    periodSeconds: 30
    timeoutSeconds: 1
  image:
    repository: eb129/incident-bot
    pullPolicy: Always
  ingress:
    enabled: true
    className: ''
    annotations:
      kubernetes.io/ingress.class: nginx
      cert-manager.io/cluster-issuer: letsencrypt-prod
    hosts:
      - host: incident-bot.mydomain.com
        paths:
          - path: /
            pathType: ImplementationSpecific
    tls:
      - secretName: incident-bot-tls
        hosts:
          - incident-bot.mydomain.com
  podDisruptionBudget:
    enabled: false
    minAvailable: 1
  replicaCount: 1
  resources:
    limits:
      cpu: 1000m
      memory: 512M
    requests:
      cpu: 250m
      memory: 256M
  service:
    type: ClusterIP
    port: 3000

If you'd like to clean everything up:

``helm uninstall incident-bot --namespace incident-bot``

.. _kustomize:

Kustomize
------------

``kustomize`` manifests are provided for convenience.

The manifests are located at: ``deploy/kustomize/incident-bot``

To preview generated manifests, run: ``kubectl kustomize .``

To apply the resources, run: ``kubectl apply -k .``

.. warning::

  You will want to adjust the settings within the manifests to suit your needs before deploying. Specifically, ``.env`` in the overlay folder is used to generate a `Secret` containing sensitive values. Non-sensitive values are provided as literals in the overlay-level ``kustomization.yaml`` file.

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
- ``FLASK_APP_SECRET_KEY`` - this must be provided for the API.

Optional Variables
------------

- ``AUTH0_DOMAIN`` - If using ``auth0`` as an entry when enabling status for external providers, you must provide this variable and set it to the name of your Auth0 domain.
- ``INCIDENT_AUTO_GROUP_INVITE_ENABLED`` - to enable the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to ``true``.
- ``INCIDENT_AUTO_GROUP_INVITE_GROUP_NAME`` - if enabling the automatic invitation of a Slack group to each newly created incident channel (documented above), set this to the name of the Slack group.
- ``INCIDENT_EXTERNAL_PROVIDERS_ENABLED`` - if enabling status snapshots for external providers (documented above), set this to ``true``.
- ``INCIDENT_EXTERNAL_PROVIDERS_LIST`` - if enabling status snapshots for external providers (documented above), set this to a list of providers to enable. For example: ``["auth0", "github", "heroku"]``
- ``INCIDENT_AUTO_CREATE_FROM_REACT_ENABLED`` - if enabling auto incident channel create based on react, set this to ``true``.
- ``INCIDENT_AUTO_CREATE_FROM_REACT_EMOJI_NAME`` - the name of the emoji that will trigger automatic incident creation.

Other variables are covered in the sections below documenting additional integrations.

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

.. _zoom-ettings:

Zoom Settings
------------

At this time, the bot can automatically create a Zoom meeting for each new incident. In the future, other platforms may be supported.

If you want to automatically create an instant Zoom meeting for each incident, use the following steps to create a Zoom app and enable the integration.

#. Visit https://marketplace.zoom.us/develop/create
#. Create a Server-to-Server OAuth app.
#. Fill out the required generic information.
#. Add scope for View and manage all user meetings.
#. Activate app.
#. Add account ID, client ID, and client secret to env vars below.

.. warning::

  The account ID can be viewed on the app's page in the Zoom Marketplace developer app after it has been activated.

- ``ZOOM_AUTO_CREATE`` - set to ``true`` to enable the integration.
- ``ZOOM_ACCOUNT_ID`` - Account ID from the step above.
- ``ZOOM_CLIENT_ID`` - The OAuth app client ID from the step above.
- ``ZOOM_CLIENT_SECRET`` - The OAuth app client secret from the step above.
