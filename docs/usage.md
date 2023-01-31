# Usage Guide

## Starting an Incident

Search for the `start a new incident` shortcut via the Slack search bar and click on it:

![Start a search](./assets/start-search.png)

Provide a short description and fill out some other info to start the incident:

![Start incident modal](./assets/start-modal.png)

## Managing an Incident

The digest channel shows that a new incident has been started:

![Digest message sample](./assets/digest-new.png)

Upon joining the incident channel, the control panel is shown where changes can be made to `status`, `severity`, and `roles`. This is also pinned to the channel for quick access.

![Incident management pahel](./assets/boilerplate.png)

As `status`, `severity`, and `roles` are changed, the channel is notified of these events:

![Incident status updates](./assets/updates.png)

Periodically, you can choose to provide those not involved directly in the incident about updates by searching for the `provide incident update` shortcut via the Slack search bar and clicking on it:

![Provide an incident update search](./assets/provide-update-search.png)

You can then provide details regarding components and the nature of the update after selecting the incident channel. Only open incidents will show up in the list:

![Provide an incident update modal](./assets/provide-update-modal.png)

Now, everyone can see the updates in the digest channel without needing to join the incident:

![Provide an incident update message](./assets/provide-update-message.png)

When an incident is promoted to `sev2` or `sev1`, the scheduled reminder to send out updates will be created. You can view these by using `scheduler list`:

![SEV2 Scheduler](./assets/sev2-scheduler.png)

## Resolving an Incident

When an incident has reached its conclusion and has been resolved, a helpful message is sent to the incident channel - notice that there is a handy button to export a formatted chat history to attach to your postmortem:

![Resolution message](./assets/resolution-message.png)

The original message in the digest channel is changed to reflect the new status of the incident:

![Resolution message update](./assets/resolution-digest-update.png)

This is only a simple explanation of the process for running an incident. There are plenty of features that will guide your teams along the way.
