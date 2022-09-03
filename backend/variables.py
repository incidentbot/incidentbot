from bot.slack.client import get_digest_channel_id

# To prevent circular imports, there needs to be a neutral space to declare variables.
digest_channel_id = get_digest_channel_id()
