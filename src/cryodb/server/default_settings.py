##############################################################################
# Database settings
##############################################################################
# Options:
#   "mariadb" - use a MariaDB SQL database
#   "sqlite"  - use a local SQL database
DATABASE = "mariadb"
CRYODB_USER = "cryodb_user"
CRYODB_PASSWORD = "cryodb_password"
CRYODB_DATABASE = "cryodb"

# MariaDB settings
CRYODB_PORT = 3306
CRYODB_HOST = "localhost"

# Sqlite settings
CRYODB_SQLITE_PATH = "cryo.db"
CRYODB_SQLITE_CREATE = False

##############################################################################
# Testing settings
##############################################################################
TESTING = False

##############################################################################
# Reverse proxy settings
##############################################################################
# - see https://werkzeug.palletsprojects.com/en/stable/middleware/proxy_fix/
#   for details
REVERSE_PROXY           = False
REVERSE_PROXY_X_FOR     = 1
REVERSE_PROXY_X_PROTO   = 1
REVERSE_PROXY_X_PORT    = 1
REVERSE_PROXY_X_HOST    = 1
REVERSE_PROXY_X_PREFIX  = 1

##############################################################################
# LingoMO configuration
##############################################################################
# Assign the event ID for the webhook/LingoMO Ingest Event
LINGOMO_EVENT_ID = None