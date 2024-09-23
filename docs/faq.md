# Frequently Asked Questions

## Why can't the bot delete channels?

The Slack API limits that ability to Enterprise Grid workspaces. Thus far, it has not been tested in any of those.

## Why do I get a message from the bot stating a public link was created to my file when an image I uploaded to an incident channel was pinned?

This is because a public link has to be created temporarily in order to fetch the image content from the Slack API. That public access is removed immediately afterward. This is normal and expected behavior.

## How do I handle database migrations?

Locally, you can use `make run-migrations`. If using the Helm chart, there's an option to run migrations an init container.

See the documentation for migrations [here](installation.md#database-migrations).
