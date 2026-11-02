"""Discord limits the planner and applier respect (from Discord's API docs)."""
MAX_CHANNELS = 500            # channels + categories per server
MAX_ROLES = 250               # roles per server (incl. @everyone)
MAX_CHANNELS_PER_CATEGORY = 50
MAX_NAME = 100                # channel / category / role name
MIN_NAME = 1
MAX_TOPIC = 1024
MAX_SLOWMODE = 21600          # seconds
MAX_MESSAGE = 2000
MAX_EMBED_TOTAL = 6000
MAX_EMBED_FIELDS = 25
MAX_EMBED_FIELD_VALUE = 1024
MAX_EMBED_FIELD_NAME = 256
MAX_EMBED_DESCRIPTION = 4096
MAX_EMBED_TITLE = 256
MAX_AUTOMOD_KEYWORD_RULES = 6
MAX_AUTOMOD_KEYWORDS = 1000
MAX_AUTOMOD_KEYWORD_LEN = 60
MAX_FORUM_TAGS = 20
MAX_FORUM_TAG_NAME = 20
# what one /setup may add at most (keeps a prompt from flooding a server)
PLAN_MAX_CATEGORIES = 20
PLAN_MAX_CHANNELS = 150
PLAN_MAX_ROLES = 40
