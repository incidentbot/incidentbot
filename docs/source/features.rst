Features
=====

.. _incident-management:

Incident Management
------------

An overview of main features:

- Create a war-room in Slack to gather resources and handle incidents.
- A fully functioning digest channel that stays up to date with incident statuses that can be used by others to watch the status of incidents. Incident statuses are updated there in real time.
- Define your own roles, severities, and statuses. There are some provided out of the box, but you can control them.
- The ability to send out internal status updates that will be viewable in the incident digest channel.
- Automatically generate unique Zoom meetings for each incident and tell everyone about them.
- Create Statuspage incidents.
- Page teams in PagerDuty.
- Automatically create an RCA/postmortem document in Confluence.
- Notify participants when they are assigned a role.
- Automatically generate and manage a timeline of events.

.. _incident-management-requirements:

Incident Management Requirements
------------

Since this bot mainly helps run incidents, there are a few prerequisites.

- You should have a digest channel that serves as a collection of information for all of your incidents. Provide this as ``digest_channel`` in ``config.yaml`` - this is the channel **name**, not the **ID**. A common sense one is ``incidents``. The idea is that all information about ongoing incidents will be sent to this channel and everyone who cares about incident management can go look there.
- The app will automatically try to invite the box to the incidents digest channel, so you won't have to do that provided your permissions are configured correctly.
- If you'd like to react to messages in any other channel to automatically create an incident based on the message's content, you'll need to invite the bot to that channel first.

.. _starting-and-running-incidents:

Starting and Running Incidents
------------

It is beyond the scope of this application to establish incident response processes - however, there are several features that can advise on it.

- Incidents can be started by using the button on the app home, searching for the ``Start a new incident`` shortcut in the search bar or via slash lookup, from the web UI, or by reacting to messages if the feature is enabled.
- Once an incident is created, leverage the pinned control panel message that gets automatically added to each incident channel to assign roles, set severity, and set status. There are also pinned messages documenting where meetings are taking place, etc.
- You can manage incidents from the web UI as well if you choose to do so.

.. _postmortems:

Auto RCA/Postmortem Generation
------------

This feature only works with Confluence Cloud and requires an API token and username as well as other variables described below. The template for the generated RCA is provided as an html file located at ``backend/bot/templates/confluence/rca.py``. A basic template is provided, but you can add whatever you'd like.

See the setup guide for details on how to enable this feature.

.. _scheduled-actions:

Scheduled Actions
------------

By default, the app will look for incidents that are not resolved that are older than 7 days. You may adjust this behavior via the scheduler module if you wish.

When an incident is promoted to SEV2 or SEV1, a scheduled job will kick off that will look for whether or not the ``last_update_sent`` field has been updated in the last ``30`` minutes. If not, it will ping the channel to encourage you to send out an incident update as good practice.

From then on, a reminder is sent out every ``25`` minutes to encourage you to send out another update. You may change these timers if you wish. This establishes a pattern that critical incidents will update your internal teams using half-hour cadences.

.. _customization:

Customization
------------

You can change configurable parameters that are not secrets in the app's ``config.yaml`` file.

.. _pagerduty-integration:

PagerDuty Integration
------------

If the PagerDuty integration is enabled, the application can do the following:

- Show on-call information in the web UI
- Issue pages to teams using the ``Incident Bot Pager`` shortcut
- Automatically page teams on incident creation, configurable from the UI if the integration is enabled
- Automatically resolve PagerDuty incidents issued during incident creation when the incident is resolved in Slack

You must set the required environment variables detailed in the setup guide to enable the integration.

.. _pinning-items:

Pinning Items
------------

In any incident channel, you can use the ``pushpin`` emote in Slack to attach messages to the incident. This are viewable in the web UI where you can optionally delete them if you no longer want them. These are automatically added to the postmortem document when the incident is resolved. You can attach the following items:

- Messages - these are timestamped and added to the RCA showing which user sent the message
- Images - these are added to the RCA as attachments - note that if an image is attached with a message, only the image is attached to the incident

.. _automatic-timeline-generation:

Automatic Timeline Generation
------------

There is a section in the postmortem documentation that holds timeline information for the incident. The application will automatically added many of these events, such as:

- Status changes
- Severity changes
- User role assignments
- Postmortem doc creation

You are also able to add your own events to the timeline by using the application's ``Manage incident timeline`` shortcut searchable as a slash command or in the Slack search bar. This modal will show you all current timeline events and then allow you to add more.

These will automatically be populated in the table and added to the postmortem document when the incident is resolved.

.. _statuspage-integration:

Statuspage Integration
------------

If the Statuspage integration is enabled, the application can do the following:

- Prompt for Statuspage incident creation when a new incident is created - you're able to select components, etc
- Update Statuspage incidents directly from Slack
- Resolve Statuspage incidents when incidents are resolved in Slack

You must set the required environment variables detailed in the setup guide to enable the integration.

.. _automation:

Automation
------------

The following features are implemented to assist with managing incidents:

- If the bot sees messages being sent in the incidents digest channel, it will drop in a message encouraging users to open an incident. This helps to prevent hesitation in declaring and running incidents.
