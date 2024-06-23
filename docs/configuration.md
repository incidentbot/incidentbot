# Configuration

## Application Configuration

All application settings are configured using environment variables/secrets for sensitive values and `config.yaml` for everything else.

There is an example of the `config.yaml` structure available at `backend/config.yaml` - note that this file is also covered in detail below.

You can change the following settings in this file:

- The incident digest channel
- Role definitions - you can create and define your own roles which will show up as claimable or assignable roles during incidents
- Severity definitions - you can create and define your own severity definitions which will be available to set on all incidents
- Status definitions - you can create and define your own status definitions which will be available to set on all incidents
- The default incident channel topic
- Incident channel name prefixes and date formatting (override defaults)
- The application's timezone for timestamps, timeline creation, etc.
- The default meeting link if not using Zoom auto create
- The ability to create incidents from reactions
- Groups to be automatically invited to new incidents
- Links that are provided as helpful guidelines in messages and modals

You can also enable and configure integrations:

- Confluence
- Jira
- Opsgenie
- PagerDuty
- Statuspage
- Zoom

Please review the [integrations](/integrations/) documentation for additional information on enabling and configuring integrations.

## Configuration Layout

Here is the standard layout of the `config.yaml` file and some examples for how to configure integrations and other features.

```yaml
# Control whether or not to enable the API for the frontend
# Disabling the API will disable all functionality for the frontend
# api:
  # Set to false to disable
  # enabled: true
# Options: slack
platform: slack
# The channel where incident activity is logged
digest_channel: incidents
# Roles defined here will appear as options for each incident
roles:
  incident_commander: "The Incident Commander is the decision maker during a major incident, delegating tasks and listening to input from subject matter experts in order to bring the incident to resolution. They become the highest ranking individual on any major incident call, regardless of their day-to-day rank. Their decisions made as commander are final.\\n\\nYour job as an Incident Commander is to listen to the call and to watch the incident Slack room in order to provide clear coordination, recruiting others to gather context and details. You should not be performing any actions or remediations, checking graphs, or investigating logs. Those tasks should be delegated.\\n\\nAn IC should also be considering next steps and backup plans at every opportunity, in an effort to avoid getting stuck without any clear options to proceed and to keep things moving towards resolution.\\n\\nMore information: https://response.pagerduty.com/training/incident_commander/"
  communications_liaison: "The purpose of the Communications Liaison is to be the primary individual in charge of notifying our customers of the current conditions, and informing the Incident Commander of any relevant feedback from customers as the incident progresses.\\n\\nIt's important for the rest of the command staff to be able to focus on the problem at hand, rather than worrying about crafting messages to customers.\\n\\nYour job as Communications Liaison is to listen to the call, watch the incident Slack room, and track incoming customer support requests, keeping track of what's going on and how far the incident is progressing (still investigating vs close to resolution).\\n\\nThe Incident Commander will instruct you to notify customers of the incident and keep them updated at various points throughout the call. You will be required to craft the message, gain approval from the IC, and then disseminate that message to customers.\\n\\nMore information: https://response.pagerduty.com/training/customer_liaison/"
# Severities defined here will appear as options for each incident
severities:
  sev1: 'This signifies a critical production scenario that impacts most or all users with a major impact on SLAs. This is an all-hands-on-deck scenario that requires swift action to restore operation. Customers must be notified.'
  sev2: 'This signifies a significant production degradation scenario impacting a large portion of users.'
  sev3: 'This signifies a minor production scenario that may or may not result in degradation. This situation is worth coordination to resolve quickly but does not indicate a critical loss of service for users.'
  sev4: 'This signifies an ongoing investigation. This incident has not been promoted to SEV3 yet, indicating there may be little to no impact, but the situation warrants a closer look. This is diagnostic in nature. This is the default setting for a new incident.'
# Whether or not to deliver incident update reminders for critical incidents
# This will send out a reminder message to an active incident channel at the supplied
# interval
incident_reminders:
  # Any severity in this list will have a scheduled reminder job created
  # This job will remind the channel to send out updates at the interval
  # specified rate below
  qualifying_severities:
    - sev1
  # rate determines how often reminders are sent to an incident channel
  # This is an int and is interpreted as minutes
  rate: 30
# Statuses defined here will appear as options for each incident
statuses:
  - investigating
  - identified
  - monitoring
  - resolved
jobs:
  # Customize jobs behavior
  scrape_for_aging_incidents:
    # Enabled by default - set to false to disable the job
    enabled: true
    # If the job is enabled, avoid sending updates for incidents with any of these statuses
    # This is useful if using customized statuses
    ignore_statuses: []
options:
  # Automatically invite Slack groups to newly created incidents
  # Adding this and providing a list of group names implies enabling the feature
  # auto_invite_groups:
  #   # List of group names as configured in Slack
  #   - my-slack-group
  #   - my-other-slack-group
  # By default, channel names are prefixed inc-YYYYMMDDHM-
  # You can override this behavior here.
  channel_naming:
    # The start of the channel name prefix.
    # inc by default
    channel_name_prefix: incd
    # The formatting for the timestamp
    # %Y%m%d%H%M by default
    # The value must follow datetime valid strings.
    time_format_in_channel_name: '%Y-%m-%d'
  # The topic that will be set on all incident channels
  channel_topic:
    default: 'This is the default incident channel topic.'
    # If set to true, set the channel topic to the meeting link. This will override channel_topic.
    set_to_meeting_link: true
  # If not using Zoom auto-create
  meeting_link: 'https://zoom.us'
  # Allow creation of an incident by reacting to a message
  # The value is the name of the reacji that will trigger the action
  # It must exist in your workspace
  create_from_reaction: create-incident
  # Ignore logging for requests from the following user-agents
  skip_logs_for_user_agent:
    # Kubernetes health check user-agent
    - kube-probe
    # AWS ELB health check user-agent
    - ELB-HealthChecker/2.0
  # App home only shows 5 most recent incidents by default - this can be supplied and adjusted
  # Note that setting it too high may cause errors due to limitations in the Slack API for blocks in messages
  show_most_recent_incidents_app_home_limit: 2
  # Timezone to use for logging, etc.
  timezone: UTC
integrations:
  # Secret data is provided as environment variables for integrations
  # Only non-secret data is configured here
  atlassian:
    # Enable Confluence integration
    confluence:
      # Set to true to automatically create a postmortem doc
      auto_create_postmortem: true
      space: ENGINEERIN
      parent: Postmortems
    # Enable Jira integration
    jira:
      project: 'IN'
      # Issue types that will populate the list of available options when creating a Jira issue.
      # This will override automatically fetching issue types.
      issue_types: ['Epic', 'Task']
      # Priorities that will populate the list of available options when creating a Jira issue.
      # This will override automatically fetching issue priorities.
      priorities: ['High', 'Low']
      # Labels to apply to created issues
      labels:
        - incident-management
      # Set to true to automatically create a Jira ticket when an incident is first created
      auto_create_incident: false
      # If auto_create_incident is true, this is the type of the Jira ticket that will be created.
      auto_create_incident_type: Subtask
      status_mapping:
        - incident_status: Investigating
          jira_status: Open
        - incident_status: Identified
          jira_status: In Progress
        - incident_status: Monitoring
          jira_status: In Review
        - incident_status: Resolved
          jira_status: Done
    opsgenie:
      # Note that providing the 'team' value here will limit creation of alerts to a single team.
      team: oncalls
  # Simply provide an empty dict to enable PagerDuty
  pagerduty: {}
  # Enable Statuspage integration
  statuspage:
    # The public URL of the Statuspage.
    url: https://status.mydomain
    # Which Slack groups have permissions to manage Statuspage incidents?
    # If not provided, everyone can manage Statuspage incidents from Slack.
    permissions:
      groups:
        - my-slack-group
  # Enable Zoom integration
  zoom:
    # Set to true to automatically generate a Zoom meeting for each incident
    auto_create_meeting: true
# Links are optional
# Whatever is added here is appended to incident management context messages
links:
  - title: Incident Guide
    url: https://mycompany.com/incidents
```

Any time you'd like to change these settings, adjust them here and provide them to the app. In most cases this can be done by mounting the config file to a path and then setting that path to the value of the environment variable `CONFIG_FILE_PATH`.

If using the official Helm chart, the data from `config.yaml` can be provided as values and a `ConfigMap` will automatically be created and mounted. See the [Helm](/setup/#helm) documentation for more information.

### Disabling the API

!!! warning

    The API and frontend are enabled by default.

If you choose to run the bot without the API and the frontend, set the following section in `config.yaml`:

```yaml
api:
  enabled: false
```

This will only run the Slack portion of the app and will not serve API routes. This also means the frontend will not work. If you choose to use this option, you should use a version of the image suffixed with `-lite`.

As an example using the official Helm chart:

```yaml
# values.yaml
image:
  suffix: lite
```

This will automatically suffix the image tag and use the non-API enabled version.

### Adjusting Channel Naming

To adjust the structure of an incident channel name, you can pass in a block like this to `config.yaml`:

```yaml
options:
  # By default, channel names are prefixed inc-YYYYMMDDHM-
  # You can override this behavior here.
  channel_naming:
    # The start of the channel name prefix.
    # inc by default
    channel_name_prefix: incd
    # The formatting for the timestamp
    # %Y%m%d%H%M by default
    # The value must follow datetime valid strings.
    time_format_in_channel_name: '%Y-%m-%d'
```

By default, channels are named `inc-dateformat-description`.

### Adjusting Statuses and Severities

By default, the following statuses are configured:

```yaml
- investigating
- identified
- monitoring
- resolved
```

The following severities are configured:

```yaml
- sev1
- sev2
- sev3
- sev4
```

It is up to you to decide which statuses and severities you want to use with the bot, and this file is the soruce of truth for configuring them. Note that severities are a `map` and should establish both names and descriptions.

!!! warning

    It is recommended to keep the investigating and resolved statuses intact. There are dependencies throughout the application that rely on these statuses. You may do what you wish with the rest.

### Adjusting Jobs Behavior

#### Scrape For Aging Incidents

By default, the bot will alert the digest channel regarding incidents that are at least `7` days old and not set to `resolved` status. If you are providing additional statuses in the configuration, you may wish to exclude additional status types from this report:

```yaml
jobs:
  scrape_for_aging_incidents:
    ignore_statuses:
      - some-custom-status
```

This would disable sending updates for incidents that have a status set to `some-custom status`.

### Creating Via Reactions

It is possible to create an incident by reacting to a Slack message with the reacji specified by the `create_from_reaction` field of the `options` section in `config.yaml`.

By setting this field and then reacting using the reacji, an incident will be created and the message that was reacted to will be automatically quoted in the incident channel.

!!! warning

    If you wish to monitor for these reactions, the bot must be present in channels where the reaction will be applied.
