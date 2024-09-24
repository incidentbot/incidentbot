# Changelog

## v2.0.5 (2024-09-24)

- Fixes bug where `postmortem_link` was no longer a valid argument for generating a digest message update.
- Adds link to postmortem in a digest message if one is passed in when the method is called.
- Adds retry logic to all Slack API requests to avoid failures based on data not populating.
- Fixes bug where a user's real name being unavailable for parsing would cause other things to fail.

## v2.0.4 (2024-09-23)

- Fixes bug where the incident list functionality did not work via command or within app home in Slack.
- Fixes incorrect content in some Helm templates.
- Adds value to Helm chart to set database password if using built-in database.
- Fixes bug in Helm chart where the `ConfigMap` data to populate `config.yaml` did not mount anything, resulting in the app always using default values.
- Fixes some spelling mistakes in the documentation.
- Adds clarity to documentation around database migrations.
- Fixes bug where the `enterprise` value in Slack responses was assumed to always be `str`, but can actually be `dict`.
- Cleans up some minor errors around the pager modal.

## v2.0.3 (2024-09-20)

- Adds unit testing to Helm chart.
- Adds better readme for Helm chart.
- Minor chart cleanup and fixes.

## v2.0.1 (2024-09-20)

- Add init containers to Helm chart to handle database migrations.
- Add Dockerfile to build utility image for use with migrations and other tasks.
- Clarify in documentation any steps regarding database migrations.
- Add jobs to CircleCI build to test util and docs builds and build util image.
- Move all Dockerfiles to root and fix references.
- Update .gitignore file.
- Fix versioning script.

## v2.0.0 (2024-09-19)

- Poetry has been adopted for Python package management, replacing the legacy pattern.
- Pydantic is now used for both type-safety and convenience as well as configuration management.
- SQLModel is now used to manage database models, extending the usefulness of Pydantic.
- The database schema has changed entirely. It is recommended to start fresh if you have an existing deployment.
- FastAPI has replaced Flask as the API framework, further extending the usefulness of Pydantic.
- Configuration has been flattened and simplified. There is now no hard requirement to provide a `config.yaml` file if accepting all defaults.
- Statuses are now fully customizable and there are no hard dependencies on specific ones. You have the ability to decide initial and final statuses.
- There is now a feature to create and manage maintenance windows to advertise scheduled maintenance. This feature is new and will have more functionality added over time.
- There is now an option to create an additional "comms" channel alongside incident channels to separate critical communications. This is entirely optional.
- All message formatting has been rebuilt to be cleaner and easier to look at.
- Reacji to pin content is now customizable.
- Reacting with reacji to messages to open incidents has been removed.
- Migrations are now required for all database operations. A base Alembic migration is provided and must be run prior to first startup.
- All use of shortcuts has been removed and replaced with slash commands. No more searching for specific commands.
- All interaction is handled using ephemeral messages to reduce clutter in public channels.
- Timestamp issues have been fixed by removing storing string timestamps in the database as strings and handling this via native database time columns.
- Introduces patterns to adopt more providers than Slack in future releases.
- Logs can now be pretty printed or JSON.
- There are new jobs for communications reminders and role watcher. These jobs will send messages to an incident channel to remind participants to send out regular updates and to claim unclaimed roles. Either can be disabled or dismissed.
- Postmortem generation now requires a Confluence template. The bot will no longer generate an entire page layout for you. There are template strings that can be placed in a template to inject values from the incident, leaving the rest up to you.
- The UI has been replaced with a new framework largely inspired by FastAPI's fullstack example.
