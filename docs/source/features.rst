Features
=====

.. _incident-management:

Incident Management
------------

- Facilitates creation of incident channels.
- Allows assigning roles for incident management.
  - These roles are currently: ``incident commander``, ``communications liaison``, and ``technical lead``.
  - The first two are based on the first and second tier of roles described by PagerDuty. The last can be thought of as a primary SME contact.
  - If you'd like to change these definitions within the app, see the section below on customization.
- A fully functioning digest channel that stays up to date with incident statuses that can be used by others to watch the status of incidents. Incident statuses are updated there in real time.
- The ability to send out internal status updates that will be viewable in the incident digest channel.
- Optional features documented below.

All incidents start as SEV4. Incidents may be promoted through to SEV1 accordingly. Each time the status or severity of an incident is changed, an update is sent to the incident channel. The digest message is also updated. When an incident is resolved, the digest message will be changed to show this.

You are also able to send out incident updates so that those who are not actively participating in an incident can stay informed regarding its status. These updates will appear in the incident's digest channel. This is done by using the "provide incident update" modal reachable by slash command or by searching in the search bar.

When someone claims or is assigned a role during an incident, the bot will notify them via private message and automatically add them to the channel. The bot will also give them helpful information about the role they've been assigned. There are definitions established by default that can be changed in the web UI under settings.

When an incident is marked as resolved, a separate RCA channel is created for users to collaborate on scheduling followup actions. The incident commander and technical lead roles are automatically invited to this channel and may invite others as needed.

.. _incident-management-requirements:

Incident Management Requirements
------------

Since this bot mainly helps run incidents, there are a few prerequisites.

- You should have a digest channel that serves as a collection of information for all of your incidents. Provide this as ``INCIDENTS_DIGEST_CHANNEL`` - this is the channel **name**, not the **ID**. A common sense one is ``incidents``. The idea is that all information about ongoing incidents will be sent to this channel and everyone who cares about incident management can go look there.
- You should invite your bot user to the aforementioned incidents digest channel at a minimum as well as anywhere else you'd like to use it. If you'd like to enable the react-to-create feature, the bot will need to be in every channel you plan to use this in. Common places are alert channels, etc.

.. _starting-and-running-incidents:

Starting and Running Incidents
------------

It is beyond the scope of this application to establish incident response processes - however, there are several features that can advise on it.

- Incidents can be started by using the button on the app home, searching for the ``Start a new incident`` shortcut in the search bar or via slash lookup, or from the web UI
- Once an incident is created, leverage the pinned control panel message that gets automatically added to each incident channel to assign roles, set severity, and set status
- You can optionally assign roles from the web UI incident view

.. _postmortems:

Auto RCA/Postmortem Generation
------------

This feature only works with Confluence Cloud and requires an API token and username as well as other variables described below. The template for the generated RCA is provided as an html file located at ``backend/templates/confluence/rca.html``. While a base template is provided, it is up to you to provide the rest. It is beyond the scope of this application to dictate the styles used in your documentation.

You must set the required environment variables detailed in the setup guide to enable the integration.

.. _scheduled-actions:

Scheduled Actions
------------

By default, the app will look for incidents that are not resolved that are older than 7 days. You may adjust this behavior via the scheduler module if you wish.

When an incident is promoted to SEV2 or SEV1, a scheduled job will kick off that will look for whether or not the ``last_update_sent`` field has been updated in the last `30` minutes. If not, it will ping the channel to encourage you to send out an incident update as good practice.

From then on, a reminder is sent out every `25` minutes to encourage you to send out another update. You may change these timers if you wish. This establishes a pattern that critical incidents will update your internal teams using half-hour cadences.

.. _customization:

Customization
------------

When the application is started the first time, several things are written to the database using stock definitions - you should update these. Once updated, they will persist in the database and be used by the application for various features.

This can be accomplished in the web UI under the settings section. Specifically, you should set:

- Incident channel topic
- Incident documentation
- Incident postmortems/RCA link
- Timezone
- Zoom Link

.. _pagerduty-integration:

PagerDuty Integration
------------

If the PagerDuty integration is enabled, the application can do the following:

- Show on-call information in the web UI
- Issue pages to teams using the ``Incident Bot Pager`` shortcut
- Automatically page teams on incident creation, configurable from the UI if the integration is enabled

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

.. _automated-helpers:

Automated Helpers
------------

The following features are implemented to assist with managing incidents:

- If the bot sees messages being sent in the incidents digest channel, it will drop in a message encouraging users to open an incident. This helps to prevent hesitation in declaring and running incidents.
