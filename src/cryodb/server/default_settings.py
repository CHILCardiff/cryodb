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