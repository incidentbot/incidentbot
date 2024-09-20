# Usage Guide

## Interacting

The main method of interacting with the bot is via its slash command - `/incidentbot` by default.

Type `/incidentbot` (or whatever you've set the slash command to) in any channcel to get a prompt:

![Slash command](./assets/slashcommand.png){: style="width:400px"}

Once you hit `return`, you'll be presented with the core prompt:

![Slash command prompt](./assets/slashcommand_output.png){: style="width:500px"}

From here you can declare an incident, list all incidents, manage incident timelines, or send out incident updates.

## Running Incidents

### Starting an Incident

Use the `Declare Incident` option via the bot prompt and you'll be issued the modal to declare an incident:

![Declare incident modal](./assets/declare.png){: style="width:400px"}

Provide information as-needed and hit `Start` to kick off the incident management process for this new incident.

### Managing an Incident

The digest channel shows the status of any incident:

![Digest notification](./assets/digest_notification.png){: style="width:500px"}

When an incident has a meeting link:

![Digest notification with meeting link](./assets/digest_notification_meeting.png){: style="width:600px"}

When an incident is resolved:

![Digest notification resolved](./assets/digest_notification_resolved.png){: style="width:600px"}

From here, anyone can see the status of any incident at any time and join it if they choose to.

All new incidents receive a welcome message with context on things to do at the start of an incident:

![Welcome message](./assets/welcome_message.png){: style="width:500px"}

If the Jira integration is enabled, you'll see an option to create a Jira issue:

![Welcome message with Jira enabled](./assets/welcome_message_with_jira.png){: style="width:500px"}

From here, one can pick up a role by clicking on the role buttons:

![Role message](./assets/role_update.png)

The channel will be notified about the role being assigned. The person accepting the role will be sent information on what the role entails. These messages are customizable.

At any time, you can use the `Describe` function to output a message that describes all current incident parameters, including assigned roles:

![Describe incident](./assets/describe_incident.png){: style="width:600px"}

#### Interacting Directly

The bot contains a subcommand called `this`. Running `/incidentbot this` will provide a prompt to interact with an incident:

!!! warning

    The `this` subcommand only works within an incident channel.

![This](./assets/slashcommand_this.png){: style="width:500px"}

From here, you can:

Set severity:

![Severity](./assets/set_severity.png){: style="width:400px"}

Set status:

![Status](./assets/set_status.png){: style="width:400px"}

List responders:

![Responders](./assets/responders.png){: style="width:400px"}

!!! note

    With the `List Responders` option, you have the option to leave a role if you're currently assigned to it. You cannot remove others.

Get help:

![Help](./assets/help.png){: style="width:400px"}

...and various other features depending on what is enabled.

## App Home

You can click on Incident Bot in the Slack sidebar to go to the app home:

![App home](./assets/app_home.png){: style="width:500px"}

From here, you can declare an incident, create a maintenance window (if enabled), see open incidents, and see any maintenance windows.
