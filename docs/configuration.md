# Configuration

Application configuration is handled using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

The bot is configured to look for environment variebles from the sys environment and a `.env` file (dotenv) in that order.

All other configuration options are handled by creating a `config.yaml` file. Almost all settings have default values, so you can run the application without creating a `config.yaml` file, but if you wish to enable integrations or change various settings, you'll want to create one.

Please review the [integrations](integrations.md) documentation for additional information on enabling and configuring integrations.

## Configurable Parameters

### API

Additional API routes are disabled by default. This flag only needs to be set to `true` if using the web interface.

Note that the API exposes a health check route.

!!! note

    The web interface is optional and is not required to use the application.

```yaml
api:
  enabled: true
```

With the API enabled, routes will be made available via `/api/v1`.

!!! warning

    API routes are only meant to serve the web interface. As such, they are secured using JWT and will not work without first running through the setup guide for the [web interface](ui.md).

!!! warning

    The default username and password for the web interface are set to `admin@example.com`:`changethis`. It is **strongly** recommended you change these variables before exposing the API.

    Set the environment variables `FIRST_SUPERUSER` and `FIRST_SUPERUSER_PASSWORD` to unique values before running the application the first time.

```python
# incidentbot/configuration/settings.py
FIRST_SUPERUSER: str = "admin@example.com"
FIRST_SUPERUSER_PASSWORD: str = "changethis"
```

#### Documentation Endpoints

All endpoints related to documentation for the API are **disabled** by default. You don't have to provide these values in the settings configuration if you don't wish to override them.

To enable them, use the following settings:

```yaml
# Set any of these to true to enable them.
api:
  enable_docs_endpoint: false # /docs
  enable_openapi_endpoint: false # /openapi.json
  enable_redoc_endpoint: false # /redoc
```

It is recommended to keep these disabled when the API is exposed to the general public.

### Digest Channel

The digest channel is where updates are sent regarding all incidents managed by the bot. The channel is `#incidents` by default.

To change it, set the following value in `config.yaml`:

```yaml
# This is the default value.
digest_channel: incidents
```

### Pinned Images

Pinning images to incident timelines is enabled by default.

To disable this behavior, set the following value in `config.yaml`:

```yaml
enable_pinned_images: false
```

!!! note

    You may not be able to pin images on a free/trial plan. The API method that it requires, `files.sharedPublicURL`, typically won't work.

    That being said, it has worked fine in the past despite the error that will show in the logs.

### Initial Communications Reminders

The bot will watch all incidents that are created and will send notifications to the channel to remind participants to send out updates and claim roles if they remain unclaimed.

To change the amount of time the bot waits before sending these notifications, set the following values in `config.yaml`:

```yaml
# These are the default values.
initial_comms_reminder_minutes: 30
initial_role_watcher_minutes: 10
```

### Links

foo do these even get used?

### Maintenance Windows

The bot has a feature that will send out notifications for scheduled maintenance. This feature is disabled by default.

To enabled this feature, set the following value in `config.yaml`:

```yaml
maintenance_windows:
  components:
    - API
    - Auth
    - Databases
    - Website
```

By setting a list of components that will show up as components related to a maintenance window, the feature will be enabled.

By default, statuses for maintenance windows are `Scheduled`, `In Progress`, `Complete`. If you wish to override these values, you can add the following block to the settings:


```yaml
maintenance_windows:
  statuses:
    - Scheduled
    - In Progress
    - Complete
```

Note that statuses should be stated in order of start to finish. The first status should be the initial status, etc.

### Options

There is an `options` section that holds several settings.

To change any of these values, set the following values in `config.yaml`:

```yaml
options:
  additional_welcome_messages:
    # Any additional messages to add to a new incident when it is opened.
    - message: "Welcome to the incident. Please be sure to..."
      pin: true # false by default
  auto_invite_groups:
    - name: str
      # Only if PagerDuty integration is enabled
      # Create a page when these groups are invited
      pagerduty_escalation_policy: some-policy
      pagerduty_escalation_priority: high
      severities: sev1,sev2
      # severities: all
  # This is the default value. This is what all incident channels are prefixed with.
  channel_name_prefix: inc
  # There is no default value for this. If one is set, this URL will be used for the meeting advertised with each incident.
  # Will not be used if using automatic Zoom meeting generation.
  meeting_link: None
  # If true, pin the meeting link to the incident channel upon creation.
  pin_meeting_link_to_channel: false
  # This limits the amount of incidents shown on the summary on the app home page.
  # It is not recommended to raise this value very high due to Slack limitations on how many blocks can appear in a message.
  # This is the default value.
  show_most_recent_incidents_app_home_limit: 5
  # Application timezone.
  # This is the default value.
  timezone: UTC
```

### Platform

Right now, the only valid value for the `platform` field is `slack`.

### Roles

You can use the default incident management roles or define your own.

Roles are configured using the following format. The "commander," or "lead" role, should be marked with `is_lead`.

!!! note

    You do not need to provide the default values displayed below if you wish to use the default values. This is provided as an example of how to configure custom values.

```yaml
roles:
  incident_commander:
    description: "The Incident Commander is the decision maker during a major incident, delegating tasks and listening to input from subject matter experts in order to bring the incident to resolution. They become the highest ranking individual on any major incident call, regardless of their day-to-day rank. Their decisions made as commander are final.\n\nYour job as an Incident Commander is to listen to the call and to watch the incident Slack room in order to provide clear coordination, recruiting others to gather context and details. You should not be performing any actions or remediations, checking graphs, or investigating logs. Those tasks should be delegated.\n\nAn IC should also be considering next steps and backup plans at every opportunity, in an effort to avoid getting stuck without any clear options to proceed and to keep things moving towards resolution.\n\nMore information: https://response.pagerduty.com/training/incident_commander/"
    is_lead: true
  scribe:
    description: "The purpose of the Scribe is to maintain a timeline of key events during an incident, documenting actions, and keeping track of any follow-up items that will need to be addressed.\n\nMore information: https://response.pagerduty.com/training/scribe/"
  subject_matter_expert:
    description: "A Subject Matter Expert (SME) is a domain expert or designated owner of a component or service that is part of the software stack. These are critical members of the incident response process that play pivotal roles in identifying and resolving individual components of impacted ecosystems.\n\nMore information: https://response.pagerduty.com/training/subject_matter_expert/"
  communications_liaison:
    description: "The purpose of the Communications Liaison is to be the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses.\n\nIt's important for the rest of the command staff to be able to focus on the problem at hand, rather than worrying about crafting messages to customers.\nYour job as Communications Liaison is to listen to the call, watch the incident Slack room, and track incoming customer support requests, keeping track of what's going on and how far the incident is progressing (still investigating vs close to resolution).\n\nThe Incident Commander will instruct you to notify customers of the incident and keep them updated at various points throughout the call. You will be required to craft the message, gain approval from the IC, and then disseminate that message to customers.\n\nMore information: https://response.pagerduty.com/training/customer_liaison/"
```

### Severities

You can use the default incident management severities or define your own.

Severities are configured using the following format.

!!! note

    You do not need to provide the default values displayed below if you wish to use the default values. This is provided as an example of how to configure custom values.

```yaml
severities:
  sev1: "This signifies a critical production scenario that impacts most or all users with a major impact on SLAs. This is an all-hands-on-deck scenario that requires swift action to restore operation. Customers must be notified."
  sev2: "This signifies a significant production degradation scenario impacting a large portion of users."
  sev3: "This signifies a minor production scenario that may or may not result in degradation. This situation is worth coordination to resolve quickly but does not indicate a critical loss of service for users."
  sev4: "This signifies an ongoing investigation. This incident has not been promoted to SEV3 yet, indicating there may be little to no impact, but the situation warrants a closer look. This is diagnostic in nature. This is the default setting for a new incident."
```

### Statuses

You can use the default incident management statuses or define your own.

Statuses are configured using the following format.

!!! note

    You do not need to provide the default values displayed below if you wish to use the default values. This is provided as an example of how to configure custom values.

```yaml
statuses:
  investigating:
    initial: true
  identified: {}
  monitoring: {}
  resolved:
    final: true
```

It is important to mark a status as `initial` and a status as `final` either way. This tells the bot the starting and finishing value for incident statuses.

### Slash Command

The bot's default slash command is `/incidentbot`. If you wish to override it, you ca

To change this value, set the following value in `config.yaml`:

```yaml
# This is the default value.
root_slash_command: '/incidentbot'
```

!!! note

    If you change this value, be sure to update the manifest to match.

### Updates

When using the "provide incident update" functionality, default behavior is to add any updates for an incident as comments under the original thread in the digest channel. If you wish to send all updates to the digest channel directly instead, set the following value in `config.yaml`:

```yaml
options:
  updates_in_threads: true
```
