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
- A fully functioning digest channel that stays up to date with incident statuses that can be used by others to watch the status of incidents.
- Optional features documented below.

All incidents start as SEV4. Incidents may be promoted through to SEV1 accordingly. Each time the status or severity of an incident is changed, an update is sent to the incident channel. The digest message is also updated. When an incident is resolved, the digest message will be changed to show this.

You are also able to send out incident updates so that those who are not actively participating in an incident can stay informed regarding its status. These updates will appear in the incident's digest channel. This is done by using the "provide incident update" modal reachable by slash command or by searching in the search bar.

When someone claims or is assigned a role during an incident, the bot will notify them via private message and automatically add them to the channel. The bot will also give them helpful information about the role they've been assigned. There are definitions established by default that can be changed in the web UI under settings.

When an incident is marked as resolved, a separate RCA channel is created for users to collaborate on scheduling followup actions. The incident commander and technical lead roles are automatically invited to this channel and may invite others as needed.

Incident Management Requirements
------------

Since this bot mainly helps run incidents, there are a few prerequisites.

- You should have a digest channel that serves as a collection of information for all of your incidents. Provide this as ``INCIDENTS_DIGEST_CHANNEL`` - this is the channel **name**, not the **ID**. A common sense one is ``incidents``. The idea is that all information about ongoing incidents will be sent to this channel and everyone who cares about incident management can go look there.
- Your Slack workspace name (``foobar.slack.com``) minus the domain (``foobar``) should be provided as ``SLACK_WORKSPACE_ID``. This is used to format some things related to sending messages to Slack.
- You should invite your bot user to the aforementioned incidents digest channel at a minimum as well as anywhere else you'd like to use it. If you'd like to enable the react-to-create feature, the bot will need to be in every channel you plan to use this in. Common places are alert channels, etc.

.. _postmortems:

Auto RCA/Postmortem Generation
------------

This feature only works with Confluence Cloud and requires an API token and username as well as other variables described below. The template for the generated RCA is provided as an html file located at ``backend/templates/confluence/rca.html``. While a base template is provided, it is up to you to provide the rest. It is beyond the scope of this application to dictate the styles used in your documentation.

.. _scheduled-actions:

Scheduled Actions
------------

By default, the app will look for incidents that are not resolved that are older than 7 days. You may adjust this behavior via the scheduler module if you wish.

When an incident is promoted to SEV2 or SEV1, a scheduled job will kick off that will look for whether or not the ``last_update_sent`` field has been updated in the last `30` minutes. If not, it will ping the channel to encourage you to send out an incident update as good practice.

From then on, a reminder is sent out every `25` minutes to encourage you to send out another update. You may change these timers if you wish. This establishes a pattern that critical incidents will update your internal teams using half-hour cadences.

.. _customization:

Customization
------------

When the application is started the first time, several things are written to the database using stock definitions - you are encouraged to adjust them as-needed.
